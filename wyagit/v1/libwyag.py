import argparse  # Parse CLI arguments
import configparser
from datetime import datetime
import grp, pwd
from fnmatch import fnmatch  # support .gitignore
import hashlib  # provides hash for commits
from math import ceil
import os
import re
import sys
import zlib  # git compresses items to zlib

# from typing import Tuple, Optional, Union, List, str
from loguru import logger

argparser = argparse.ArgumentParser(description="The stupidest content tracker")
# Handle subcommands: git info -> main subcommand
argsubparsers = argparser.add_subparsers(
    title="Commands",
    dest="command",  # Logical name of the subcommands
    required=True,  # Can't call the main command without a subcommand
)

argsp = argsubparsers.add_parser("init", help="Initialize a new, empty repository.")
argsp.add_argument(
    "path",
    metavar="directory",
    nargs="?",
    default=".",
    help="Where to create the repository.",
)


def cmd_init(args):
    repo_create(args.path)


argsp = argsubparsers.add_parser(
    "cat-file", help="Provide content of repository objects"
)
argsp.add_argument(
    "type",
    metavar="type",
    choices=["blob", "commit", "tag", "tree"],
    help="Specify the type",
)
argsp.add_argument("object", metavar="object", help="The object to display")


def cmd_cat_file(args):
    repo = repo_find()
    cat_file(repo, args.object, fmt=args.type.encode())


def cat_file(repo, obj, fmt=None):
    obj = object_read(repo, object_find(repo, obj, fmt=fmt))
    sys.stdout.buffer.write(obj.serialize())


# how does this keeps getting reassigned?
argsp = argsubparsers.add_parser(
    "hash-object", help="Compute object ID and optionally creates a blob from a file"
)

argsp.add_argument(
    "-t",
    metavar="type",
    dest="type",
    choices=["blob", "commit", "tag", "tree"],
    default="blob",
    help="Specify the type",
)

argsp.add_argument(
    "-w",
    dest="write",
    action="store_true",
    help="Actually write the object into the database",
)

argsp.add_argument("path", help="Read object from <file>")

argsp = argsubparsers.add_parser("log", help="Display history of a given commit.")
argsp.add_argument("commit", default="HEAD", nargs="?", help="Commit to start at.")


def cmd_log(args):
    repo = repo_find()
    print("digraph wyaglog{")
    print("  node[shape=rect]")
    log_graphviz(repo, object_find(repo, args.commit), set())
    print("}")


# @OPTIONAL
def log_graphviz(repo, sha, seen):
    """
    Don't really need to care too much about this as it's just a way to visualise the commit
    """

    if sha in seen:
        return
    seen.add(sha)

    commit = object_read(repo, sha)
    message = commit.kvlm[None].decode("utf8").strip()
    message = message.replace("\\", "\\\\")
    message = message.replace('"', '\\"')

    if "\n" in message:  # Keep only the first line
        message = message[: message.index("\n")]

    print(f'  c_{sha} [label="{sha[0:7]}: {message}"]')
    assert commit.fmt == b"commit"

    if not b"parent" in commit.kvlm.keys():
        # Base case: the initial commit.
        return

    parents = commit.kvlm[b"parent"]

    if type(parents) != list:
        parents = [parents]

    for p in parents:
        p = p.decode("ascii")
        print(f"  c_{sha} -> c_{p};")
        log_graphviz(repo, p, seen)


def cmd_hash_object(args):
    repo = None
    if args.write:
        repo = repo_find()

    with open(args.path, "rb") as fd:
        sha = object_hash(fd, args.type.encode(), repo)
        print(sha)


def object_hash(fd, fmt, repo=None):
    """
    Hash object, writing it to repo if provided
    """
    data = fd.read()

    # Choose constructor according to fmt argument
    match fmt:
        case b"commit":
            obj = GitCommit(data)
        case b"tree":
            obj = GitTree(data)
        case b"tag":
            obj = GitTag(data)
        case b"blob":
            obj = GitBlob(data)
        case _:
            raise Exception(f"Unknown type {fmt}!")

    return object_write(obj, repo)


def object_find(repo, name, fmt=None, follow=True):
    """
    Name resolution fn
    """
    print(f"object_find -> repo: {repo}; name: {name}; fmt: {fmt}; follow: {follow}")
    sha = object_resolve(repo, name)

    if not sha:
        raise Exception(f"No such reference {name}.")

    if len(sha) > 1:
        raise Exception(
            "Ambiguous reference {name}: Candidates are:\n - {'\n - '.join(sha)}."
        )

    while True:
        print(f"object_find.while True.obj -> repo: {repo}; sha: {sha}")
        obj = object_read(repo, sha)
        #     ^^^^^^^^^^^ < this is a bit agressive: we're reading
        # the full object just to get its type.  And we're doing
        # that in a loop, albeit normally short.  Don't expect
        # high performance here.

        if obj.fmt == fmt:
            return sha

        if not follow:
            return None

        # Follow tags
        if obj.fmt == b"tag":
            sha = obj.kvlm[b"object"].decode("ascii")
        elif obj.fmt == b"commit" and fmt == b"tree":
            sha = obj.kvlm[b"tree"].decode("ascii")
        else:
            return None


def object_resolve(repo, name: str):
    """
    Resolve name to an object hash in repo
    - if name = HEAD, resolve the value in '.git/HEAD'
    - if name is a full hash, return this hash
    - if name is a short hash, return a list of objects with this hash
    - resolve tags & branches matching name
    """

    candidates = list()
    hash_regex = re.compile(r"^[0-9A-Fa-f]{4,40}$")

    # Abort if empty string
    if not name.strip():
        return None

    # Head is non-ambiguious
    if name == "HEAD":
        return [ref_resolve(repo, "HEAD")]

    # If it's a hash string, try for a hash
    if hash_regex.match(name):
        # This may be a hash, either small or full.  4 seems to be the
        # minimal length for git to consider something a short hash.
        # This limit is documented in man git-rev-parse
        name = name.lower()
        prefix = name[0:2]
        path = repo_dir(repo, "objects", prefix, mkdir=False)
        if path:
            rem = name[2:]
            for file in os.listdir(path):
                if file.startswith(rem):
                    # Notice a string startswith() itself, so this
                    # works for full hashes.
                    candidates.append(prefix + file)

    # Try for references
    as_tags = ref_resolve(repo, "refs/tags/" + name)
    if as_tags:
        candidates.append(as_tags)

    as_branch = ref_resolve(repo, "refs/heads/" + name)
    if as_branch:
        candidates.append(as_branch)

    return candidates


argsp = argsubparsers.add_parser("ls-tree", help="Pretty-print a tree object.")
argsp.add_argument(
    "-r", dest="recursive", action="store_true", help="Recurse into sub-trees"
)

argsp.add_argument("tree", help="A tree-ish object.")


def cmd_ls_tree(args):
    repo = repo_find()
    ls_tree(repo, args.tree, args.recursive)


def ls_tree(repo, ref, recursive=None, prefix=""):
    sha = object_find(repo, ref, fmt=b"tree")
    obj = object_read(repo, sha)

    for item in obj.items:
        if len(item.mode) == 5:
            type = item.mode[0:1]
        else:
            type = item.mode[0:2]

        match type:  # Determine the type.
            case b"04":
                type = "tree"
            case b"10":
                type = "blob"  # A regular file.
            case b"12":
                type = "blob"  # A symlink. Blob contents is link target.
            case b"16":
                type = "commit"  # A submodule
            case _:
                raise Exception(f"Weird tree leaf mode {item.mode}")

        if not (recursive and type == "tree"):  # This is a leaf
            print(
                f"{'0' * (6 - len(item.mode)) + item.mode.decode('ascii')} {type} {item.sha}\t{os.path.join(prefix, item.path)}"
            )
        else:  # This is a branch, recurse
            ls_tree(repo, item.sha, recursive, os.path.join(prefix, item.path))


argsp = argsubparsers.add_parser(
    "checkout", help="Checkout a commit inside of a directory."
)

argsp.add_argument("commit", help="The commit or tree to checkout.")

argsp.add_argument("path", help="The EMPTY directory to checkout on.")


def cmd_checkout(args):
    repo = repo_find()
    obj = object_read(repo, object_find(repo, args.commit))

    # If the object is a commit, we grab its tree
    if obj.fmt == b"commit":
        obj = object_read(repo, obj.kvlm[b"tree"].decode("ascii"))

    # Verify that path is an empty directory
    # @WHY
    if os.path.exists(args.path):
        if not os.path.isdir(args.path):
            raise Exception(f"Not a directory {args.path}!")
        if os.listdir(args.path):
            raise Exception(f"Not empty {args.path}!")
    else:
        os.makedirs(args.path)

    tree_checkout(repo, obj, os.path.realpath(args.path))


def tree_checkout(repo, tree, path):
    for item in tree.items:
        obj = object_read(repo, item.sha)
        dest = os.path.join(path, item.path)

        if obj.fmt == b"tree":
            os.mkdir(dest)
            tree_checkout(repo, obj, dest)
        elif obj.fmt == b"blob":
            # @TODO Support symlinks (identified by mode 12****)
            with open(dest, "wb") as f:
                f.write(obj.blobdata)


argsp = argsubparsers.add_parser("show-ref", help="List references.")


def cmd_show_ref(args):
    repo = repo_find()
    refs = ref_list(repo)
    show_ref(repo, refs, prefix="refs")


def show_ref(repo, refs, with_hash=True, prefix=""):
    if prefix:
        prefix = prefix + "/"
    for k, v in refs.items():
        if type(v) == str and with_hash:
            print(f"{v} {prefix}{k}")
        elif type(v) == str:
            print(f"{prefix}{k}")
        else:
            show_ref(repo, v, with_hash=with_hash, prefix=f"{prefix} {k}")


argsp = argsubparsers.add_parser(
    "rev-parse", help="Parse revision (or other objects) identifiers"
)

argsp.add_argument(
    "--wyag-type",
    metavar="type",
    dest="type",
    choices=["blob", "commit", "tag", "tree"],
    default=None,
    help="Specify the expected type",
)

argsp.add_argument("name", help="The name to parse")


def cmd_rev_parse(args):
    if args.type:
        fmt = args.type.encode()
    else:
        fmt = None

    repo = repo_find()

    print(object_find(repo, args.name, fmt, follow=True))


def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    match args.command:
        case "add":
            cmd_add(args)
        case "cat-file":
            cmd_cat_file(args)
        case "check-ignore":
            cmd_check_ignore(args)
        case "checkout":
            cmd_checkout(args)
        case "commit":
            cmd_commit(args)
        case "hash-object":
            cmd_hash_object(args)
        case "init":
            cmd_init(args)
        case "log":  # @WARN not working
            cmd_log(args)
        case "ls-files":
            cmd_ls_files(args)
        case "ls-tree":
            cmd_ls_tree(args)
        case "rev-parse":
            cmd_rev_parse(args)
        case "rm":
            cmd_rm(args)
        case "show-ref":
            cmd_show_ref(args)
        case "status":
            cmd_status(args)
        case "tag":
            cmd_tag(args)
        case _:
            print("Bad command.")


class GitRepository(object):
    worktree = (
        None  # Files that are meant to be version controlled. Aka our regular files
    )
    gitdir = None  # .git folder which contains Git configuration data
    conf = None  # Git configuration data

    # force = a flag to disable check. Allows to create a git repo in still invalid folder
    def __init__(self, path, force=False):
        self.worktree = path
        self.gitdir = os.path.join(path, ".git")

        is_gitrepo = os.path.isdir(
            self.gitdir
        )  # only considred a git repo with .git dir
        if not (force or is_gitrepo):
            raise Exception(f"Not a Git repository {path}")

        # Read configuration file in .git/config
        self.conf = configparser.ConfigParser()
        cf = repo_file(self, "config")

        cf_exists = cf and os.path.exists(cf)

        if cf_exists:
            self.conf.read([cf])
        elif not force:
            raise Exception("Configuration file missing")

        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0:
                raise Exception("Unsupported repositoryformatversion: {vers}")


# * in *path makes the fn variadic aka like the ...rest operator in js
# allows the path variable to take in multiple arguments
# E.g. repo_path(repo, "objects", "df", "4ec9fc2ad990cb9da906a95a6eda6627d7b7b0")
def repo_path(repo, *path):
    """Compute path under repo's gitdir AKA get the path"""
    logger.debug(f"repo: {repo}; path: {path}")
    return os.path.join(repo.gitdir, *path)


# E.g. repo_file("my_repo", "dir1", "dir2", "file.txt", mkdir=True)
def repo_file(repo, *path, mkdir=False):
    """
    Same as repo_path, but create dirname(*path) if absent.
    For example, repo_file(r, \"refs\", \"remotes\", \"origin\", \"HEAD\") will create .git/refs/remotes/origin.
    """
    logger.debug(f"repo: {repo}; path: {path}, mkdir: {mkdir}")
    if repo_dir(repo, *path[:-1], mkdir=mkdir):  # creates the directory
        return repo_path(repo, *path)  # return the path


def repo_dir(repo, *path, mkdir=False):
    """
    Same as repo_path, but validates *path and creates a directory
    if mkdir is True
    """
    print(f"repo_dir -> repo:{repo}; path:{path}; mkdir:{mkdir}")

    path = repo_path(repo, *path)
    if os.path.exists(path):
        if os.path.isdir(path):
            return path
        else:
            raise Exception(f"Not a directory {path}")

    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None


def repo_create(path):
    """
    Creates a new repository given the path.
    A repository will contain .git files with
        - .git/objects/
        - .git/refs/
        - .git/HEAD/
        - .git/config
        - .git/description
    """

    repo = GitRepository(path, True)

    def validate_path():
        """
        Ensure path either doesn't exist or is a empty dir.
        Else create the directory
        """
        if os.path.exists(repo.worktree):
            if not os.path.isdir(repo.worktree):
                raise Exception(f"{path} is not a directory!")
            if os.path.exists(repo.gitdir) and os.listdir(repo.gitdir):
                # path contains .git and there's content
                raise Exception(f"{path} is not empty")
        else:
            os.makedirs(repo.worktree)

    validate_path()

    assert repo_dir(repo, "branches", mkdir=True)
    assert repo_dir(repo, "objects", mkdir=True)
    assert repo_dir(repo, "refs", "tags", mkdir=True)
    assert repo_dir(repo, "refs", "heads", mkdir=True)

    # .git/description
    with open(repo_file(repo, "description"), "w") as f:
        f.write(
            "Unnamed repository; edit this file 'description' to name the repository.\n"
        )

    # .git/HEAD
    with open(repo_file(repo, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")

    with open(repo_file(repo, "config"), "w") as f:
        config = repo_default_config()
        config.write(f)

    return repo


# Creates a INI like file: https://en.wikipedia.org/wiki/INI_file
def repo_default_config() -> configparser.ConfigParser:
    ret = configparser.ConfigParser()

    ret.add_section("core")
    ret.set("core", "repositoryformatversion", "0")
    ret.set(
        "core", "filemode", "false"
    )  # disable tracking of file permission changes in the work tree
    ret.set("core", "bare", "false")

    return ret


def repo_find(path=".", required=True):
    """
    Find the root from a child directory recursively and also check for the presence of git

    Repo root: ~/Documents/MyProject
    Child directory: ~/Documents/MyProject/src/tui/frames/mainview/
    """
    path = os.path.realpath(
        path
    )  # realpath resolves symlinks, relative path and returns a abs path

    # Recursively finds till a .git folder is hit
    is_git_dir = os.path.isdir(os.path.join(path, ".git"))
    if is_git_dir:
        return GitRepository(path)

    parent = os.path.realpath(os.path.join(path, ".."))

    if parent == path:
        # Bottom case
        # os.path.join("/", "..") == "/":
        # If parent==path, then path is root.
        if required:
            raise Exception("No git directory.")
        else:
            return None

    # Recursive case
    return repo_find(parent, required)


class GitObject(object):
    """
    Generic GitObject class sharing common fns across objects
    """

    def __init__(self, data=None):
        if data != None:
            self.deserialize(data)
        else:
            self.init()

    def serialize(self, repo):
        """
        This function MUST be implemented by subclasses.

        It must read the object's contents from self.data, a byte string, and
        do whatever it takes to convert it into a meaningful representation.
        What exactly that means depend on each subclass.
        """
        raise Exception("Unimplemented!")

    def deserialize(self, data):
        raise Exception("Unimplemented!")

    def init(self):
        pass  # Just do nothing. This is a reasonable default!


def object_read(repo, sha):
    """
    Read object sha from Git repository repo. Return a
    GitObject whose exact tyep depends on the object
    """

    # sha[0:2] - directory of file
    # sha[:2] - name of the file
    path = repo_file(repo, "objects", sha[0:2], sha[:2])

    if not os.path.isfile(path):
        return None

    # rb = read binary
    with open(path, "rb") as f:
        raw = zlib.decompress(f.read())

        # Read object type
        x = raw.find(b" ")
        fmt = raw[0:x]

        # Read and validate object size
        y = raw.find(b"\x00", x)
        size = int(raw[x:y].decode("ascii"))
        if size != len(raw) - y - 1:
            raise Exception(f"Malformed object {sha}: bad length")

        # Pick constructor
        # b'<COMMIT_TYPE>'
        match fmt:
            case b"commit":
                c = GitCommit
            case b"tree":
                c = GitTree
            case b"tag":
                c = GitTag
            case b"blob":
                c = GitBlob
            case _:
                raise Exception(f"Unknown type {fmt.decode('ascii')} for object {sha}")

        # Call constructor and return object
        return c(raw[y + 1 :])


def object_write(obj, repo=None):
    # zlib(hash(header + serialise(file)))

    # Serialize object data
    data = obj.serialize()
    # Add header
    result = obj.fmt + b" " + str(len(data)).encode() + b"\x00" + data
    # Compute hash
    sha = hashlib.sha1(result).hexdigest()

    if repo:
        # Compute path
        path = repo_file(repo, "objects", sha[0:2], sha[2:], mkdir=True)

        if not os.path.exists(path):
            with open(path, "wb") as f:
                # Compress and write
                f.write(zlib.compress(result))

    return sha


class GitBlob(GitObject):
    fmt = b"blob"

    def serialize(self):
        return self.blobdata

    def deserialize(self, data):
        self.blobdata = data


# kvlm = key-value list with message
# The third argument: dct=None is NOT declared as dct=dict()
# as all call to the function will endless grow with the SAME dict
def kvlm_parse(raw, start=0, dct=None):
    if not dct:
        dct = dict()

    # Search for the next space and newline
    space = raw.find(b" ", start)
    new_line = raw.find(b"\n", start)

    # If a space appears before newline, we have a keyword. E.g. tree <HASH>
    # Otherwise, it's the final message, which we just read to the eof

    # Base Case
    # =========
    # Return -1 if there's no space at all
    # If newline appears first, we assume a blank line.
    # A blank line means the remainder of the data is the message.
    # We store it in the dictionary, with None as the key, and return
    if (space < 0) or (new_line < space):
        assert new_line == start
        dct[None] = raw[start + 1 :]
        return dct

    # Recursive case
    # ==============
    # Read a key-value pair and recurse for the next
    key = raw[start:space]

    # Find the end of the value. Continuation line begin with a space,
    # so we loop until we find a new line ('\n') not followed by a space
    end = start
    while True:
        end = raw.find(b"\n", end + 1)
        if raw[end + 1] != ord(" "):
            break

    # Grab the value
    # Also, drop the leading space on continuation lines
    value = raw[space + 1 : end].replace(b"\n", b"\n")

    # Don't overwrite existing data contents
    if key in dct:
        if type(dct[key]) == list:
            dct[key].append(value)
        else:
            dct[key] = [dct[key], value]
    else:
        dct[key] = value

    return kvlm_parse(raw, start=end + 1, dct=dct)


def kvlm_serialize(kvlm):
    ret = b""

    for k in kvlm.keys():
        # Skip the message itself
        if k == None:
            continue
        val = kvlm[k]

        # Normalize to a list
        if type(val) != list:
            val = [val]

        for v in val:
            ret += k + b" " + (v.replace(b"\n", b"\n")) + b"\n"

    ret += b"\n" + kvlm[None]
    return ret


class GitCommit(GitObject):
    fmt = b"commit"

    def deserialize(self, data):
        self.kvlm = kvlm_parse(data)

    def serialize(self):
        return kvlm_serialize(self.kvlm)

    def init(self):
        self.kvlm = dict()


class GitTreeLeaf(object):
    def __init__(self, mode, path, sha):
        self.mode = mode
        self.path = path
        self.sha = sha


# Format of a tree: [mode] space [path] 0x00 [sha-1]
def main_tree_parser(raw, start=0):
    # Find the space terminator of the mode
    x = raw.find(b" ", start)
    mode_identifier = x - start  # can be a file or directory mode
    assert mode_identifier == 5 or mode_identifier == 6  # checking the bytes

    # Read the mode
    mode = raw[start:x]
    if len(mode) == 5:
        # Normalize to six bytes
        mode = b"0" + mode

    # Find the NULL terminator of the path
    y = raw.find(b"\x00", x)
    # and read the path
    path = raw[x + 1 : y]

    # Read the SHA...
    raw_sha = int.from_bytes(raw[y + 1 : y + 21], "big")
    # and convert it into an hex string, padded to 40 chars
    # with zeros if needed.
    sha = format(raw_sha, "040x")
    return y + 21, GitTreeLeaf(mode, path.decode("utf8"), sha)


def tree_parse(raw):
    """
    A wrapper fn that just iteratively parses the raw content.
    While the actual parsing occurs in `main_tree_parser`
    """
    pos = 0
    max = len(raw)
    ret = list()
    while pos < max:
        pos, data = main_tree_parser(raw, pos)
        ret.append(data)
    return ret


# Notice this isn't a comparison function, but a conversion function.
# Python's default sort doesn't accept a custom comparison function,
# like in most languages, but a `key` arguments that returns a new
# value, which is compared using the default rules.  So we just return
# the leaf name, with an extra / if it's a directory.
def tree_leaf_sort_key(leaf):
    if leaf.mode.startswith(b"10"):
        return leaf.path
    else:
        return leaf.path + "/"


def tree_serialize(obj):
    obj.items.sort(key=tree_leaf_sort_key)
    ret = b""
    for i in obj.items:
        ret += i.mode
        ret += b" "
        ret += i.path.encode("utf8")
        ret += b"\x00"
        sha = int(i.sha, 16)
        ret += sha.to_bytes(20, byteorder="big")
    return ret


class GitTree(GitObject):
    fmt = b"tree"

    def deserialize(self, data):
        self.items = tree_parse(data)

    def serialize(self):
        return tree_serialize(self)

    def init(self):
        self.items = list()


def ref_resolve(repo, ref):
    path = repo_file(repo, ref)

    # Sometimes, an indirect reference may be broken.  This is normal
    # in one specific case: we're looking for HEAD on a new repository
    # with no commits.  In that case, .git/HEAD points to "ref:
    # refs/heads/main", but .git/refs/heads/main doesn't exist yet
    # (since there's no commit for it to refer to).
    if not os.path.isfile(path):
        return None

    with open(path, "r") as fp:
        data = fp.read()[:-1]
        # Drop final \n ^^^^^

    # Used to identify: ref: refs/remotes/origin/master from the file
    if data.startswith("ref: "):
        return ref_resolve(repo, data[5:])
    else:
        return data


def ref_list(repo, path=None):
    if not path:
        path = repo_dir(repo, "refs")
    ret = dict()

    for f in sorted(os.listdir(path)):
        can = os.path.join(path, f)
        if os.path.isdir(can):
            ret[f] = ref_list(repo, can)
        else:
            ret[f] = ref_resolve(repo, can)
    return ret


class GitTag(GitCommit):
    fmt = b"tag"


argsp = argsubparsers.add_parser("tag", help="List and create tags")

argsp.add_argument(
    "-a",
    action="store_true",
    dest="create_tag_object",
    help="Whether to create a tag object",
)

argsp.add_argument("name", nargs="?", help="The new tag's name")

argsp.add_argument(
    "object", default="HEAD", nargs="?", help="The object the new tag will point to"
)


def cmd_tag(args):
    repo = repo_find()

    if args.name:
        tag_create(
            repo, args.name, args.object, create_tag_object=args.create_tag_object
        )
    else:
        refs = ref_list(repo)
        show_ref(repo, refs["tags"], with_hash=False)


def tag_create(repo, name, ref, create_tag_object=False):
    # get the GitObject from the object reference
    sha = object_find(repo, ref)

    if create_tag_object:
        # create tag object (commit)
        tag = GitTag()
        tag.kvlm = dict()
        tag.kvlm[b"object"] = sha.encode()
        tag.kvlm[b"type"] = b"commit"
        tag.kvlm[b"tag"] = name.encode()
        # Feel free to let the user give their name!
        # Notice you can fix this after commit, read on!
        tag.kvlm[b"tagger"] = b"Wyag <wyag@example.com>"
        # …and a tag message!
        tag.kvlm[None] = (
            b"A tag generated by wyag, which won't let you customize the message!\n"
        )
        tag_sha = object_write(tag, repo)
        # create reference
        ref_create(repo, "tags/" + name, tag_sha)
    else:
        # create lightweight tag (ref)
        ref_create(repo, "tags/" + name, sha)


def ref_create(repo, ref_name, sha):
    with open(repo_file(repo, "refs/" + ref_name), "w") as fp:
        fp.write(sha + "\n")


class GitIndexEntry(object):
    def __init__(
        self,
        ctime=None,
        mtime=None,
        dev=None,
        ino=None,
        mode_type=None,
        mode_perms=None,
        uid=None,
        gid=None,
        fsize=None,
        sha=None,
        flag_assume_valid=None,
        flag_stage=None,
        name=None,
    ):
        # The last time a file's metadata changed.  This is a pair
        # (timestamp in seconds, nanoseconds)
        self.ctime = ctime
        # The last time a file's data changed.  This is a pair
        # (timestamp in seconds, nanoseconds)
        self.mtime = mtime
        # The ID of device containing this file
        self.dev = dev
        # The file's inode number
        self.ino = ino
        # The object type, either b1000 (regular), b1010 (symlink),
        # b1110 (gitlink).
        self.mode_type = mode_type
        # The object permissions, an integer.
        self.mode_perms = mode_perms
        # User ID of owner
        self.uid = uid
        # Group ID of ownner
        self.gid = gid
        # Size of this object, in bytes
        self.fsize = fsize
        # The object's SHA
        self.sha = sha
        self.flag_assume_valid = flag_assume_valid
        self.flag_stage = flag_stage
        # Name of the object (full path this time!)
        self.name = name


class GitIndex(object):
    version = None
    entries = []

    def __init__(self, version=2, entries=None):
        if not entries:
            entries = list()

        self.version = version
        self.entries = entries


def index_read(repo):
    index_file = repo_file(repo, "index")

    # New repositories have no index!
    if not os.path.exists(index_file):
        return GitIndex()

    with open(index_file, "rb") as f:
        raw = f.read()

    header = raw[:12]
    signature = header[:4]
    assert signature == b"DIRC"  # Stands for "DirCache"
    version = int.from_bytes(header[4:8], "big")
    assert version == 2, "wyag only supports index file version 2"
    count = int.from_bytes(header[8:12], "big")

    entries = list()

    content = raw[12:]
    idx = 0
    for i in range(0, count):
        # Read creation time, as a unix timestamp (seconds since
        # 1970-01-01 00:00:00, the "epoch")
        ctime_s = int.from_bytes(content[idx : idx + 4], "big")
        # Read creation time, as nanoseconds after that timestamps,
        # for extra precision.
        ctime_ns = int.from_bytes(content[idx + 4 : idx + 8], "big")
        # Same for modification time: first seconds from epoch.
        mtime_s = int.from_bytes(content[idx + 8 : idx + 12], "big")
        # Then extra nanoseconds
        mtime_ns = int.from_bytes(content[idx + 12 : idx + 16], "big")
        # Device ID
        dev = int.from_bytes(content[idx + 16 : idx + 20], "big")
        # Inode
        ino = int.from_bytes(content[idx + 20 : idx + 24], "big")
        # Ignored.
        unused = int.from_bytes(content[idx + 24 : idx + 26], "big")
        assert 0 == unused
        mode = int.from_bytes(content[idx + 26 : idx + 28], "big")
        mode_type = mode >> 12
        assert mode_type in [0b1000, 0b1010, 0b1110]
        mode_perms = mode & 0b0000000111111111
        # User ID
        uid = int.from_bytes(content[idx + 28 : idx + 32], "big")
        # Group ID
        gid = int.from_bytes(content[idx + 32 : idx + 36], "big")
        # Size
        fsize = int.from_bytes(content[idx + 36 : idx + 40], "big")
        # SHA (object ID).  We'll store it as a lowercase hex string
        # for consistency.
        sha = format(int.from_bytes(content[idx + 40 : idx + 60], "big"), "040x")
        # Flags we're going to ignore
        flags = int.from_bytes(content[idx + 60 : idx + 62], "big")
        # Parse flags
        flag_assume_valid = (flags & 0b1000000000000000) != 0
        flag_extended = (flags & 0b0100000000000000) != 0
        assert not flag_extended
        flag_stage = flags & 0b0011000000000000
        # Length of the name.  This is stored on 12 bits, some max
        # value is 0xFFF, 4095.  Since names can occasionally go
        # beyond that length, git treats 0xFFF as meaning at least
        # 0xFFF, and looks for the final 0x00 to find the end of the
        # name --- at a small, and probably very rare, performance
        # cost.
        name_length = flags & 0b0000111111111111

        # We've read 62 bytes so far.
        idx += 62

        if name_length < 0xFFF:
            assert content[idx + name_length] == 0x00
            raw_name = content[idx : idx + name_length]
            idx += name_length + 1
        else:
            print(f"Notice: Name is 0x{name_length:X} bytes long.")
            # This probably wasn't tested enough.  It works with a
            # path of exactly 0xFFF bytes.  Any extra bytes broke
            # something between git, my shell and my filesystem.
            null_idx = content.find(b"\x00", idx + 0xFFF)
            raw_name = content[idx:null_idx]
            idx = null_idx + 1

        # Just parse the name as utf8.
        name = raw_name.decode("utf8")

        # Data is padded on multiples of eight bytes for pointer
        # alignment, so we skip as many bytes as we need for the next
        # read to start at the right position.

        idx = 8 * ceil(idx / 8)

        # And we add this entry to our list.
        entries.append(
            GitIndexEntry(
                ctime=(ctime_s, ctime_ns),
                mtime=(mtime_s, mtime_ns),
                dev=dev,
                ino=ino,
                mode_type=mode_type,
                mode_perms=mode_perms,
                uid=uid,
                gid=gid,
                fsize=fsize,
                sha=sha,
                flag_assume_valid=flag_assume_valid,
                flag_stage=flag_stage,
                name=name,
            )
        )

    return GitIndex(version=version, entries=entries)


argsp = argsubparsers.add_parser("ls-files", help="List all the stage files")
argsp.add_argument("--verbose", action="store_true", help="Show everything.")


def cmd_ls_files(args):
    repo = repo_find()
    index = index_read(repo)

    if args.verbose:
        print(
            f"Index file format v{index.version}, containing {len(index.entries)} entries."
        )

    for e in index.entries:
        print(e.name)
        if args.verbose:
            entry_type = {
                0b1000: "regular file",
                0b1010: "symlink",
                0b1110: "git link",
            }[e.mode_type]
            print(f"  {entry_type} with perms: {e.mode_perms:o}")
            print(f"  on blob: {e.sha}")
            print(
                f"  created: {datetime.fromtimestamp(e.ctime[0])}.{e.ctime[1]}, modified: {datetime.fromtimestamp(e.mtime[0])}.{e.mtime[1]}"
            )
            print(f"  device: {e.dev}, inode: {e.ino}")
            print(
                f"  user: {pwd.getpwuid(e.uid).pw_name} ({e.uid})  group: {grp.getgrgid(e.gid).gr_name} ({e.gid})"
            )
            print(f"  flags: stage={e.flag_stage} assume_valid={e.flag_assume_valid}")


argsp = argsubparsers.add_parser(
    "check-ignore", help="Check path(s) against ignore rules."
)
argsp.add_argument("path", nargs="+", help="Paths to check")


def cmd_check_ignore(args):
    repo = repo_find()
    rules = gitignore_read(repo)
    for path in args.path:
        if check_ignore(rules, path):
            print(path)


def gitignore_parse1(raw: str) -> tuple[str, bool] | None:
    raw = raw.strip()
    # Ignore the rest as it's a commented out line
    if not raw or raw[0] == "#":
        return None
    # Negates pattern
    elif raw[0] == "!":
        return (raw[1:], False)
    # Backslash are escapes
    elif raw[0] == "\\":
        return (raw[1:], True)
    else:
        return (raw, True)


def gitignore_parse(lines: list[str]) -> list[str]:
    ret = list()

    for line in lines:
        parsed = gitignore_parse1(line)
        if parsed:
            ret.append(parsed)
    return ret


class GitIgnore(object):
    absolute: list[str] | None
    scoped: dict[str, list[str]] | None

    def __init__(
        self,
        absolute: list[str] | None = None,
        scoped: dict[str, list[str]] | None = None,
    ):
        self.absolute = absolute
        self.scoped = scoped


def gitignore_read(repo):
    # @WHY is the following valid
    # ret = GitIgnore(absolute=list(), scoped=list())
    ret = GitIgnore(absolute=list(), scoped=dict())

    # Read local configuration in .git/info/exclude
    repo_file = os.path.join(repo.gitdir, "info/exclude")
    if os.path.exists(repo_file):
        with open(repo_file, "r") as f:
            ret.absolute.append(gitignore_parse(f.readlines()))

    # Global configuration
    if "XDG_CONFIG_HOME" in os.environ:
        config_home = os.environ["XDG_CONFIG_HOME"]
    else:
        config_home = os.path.expanduser("~/.config")

    global_file = os.path.join(config_home, "git/ignore")

    if os.path.exists(global_file):
        with open(global_file, "r") as f:
            ret.absolute.append(gitignore_parse(f.readlines()))

    # .gitignore files in the index
    index = index_read(repo)

    for entry in index.entries:
        if entry.name == ".gitignore" or entry.name.endswith("/.gitignore"):
            dir_name = os.path.dirname(entry.name)
            contents = object_read(repo, entry.sha)
            lines = contents.blobdata.decode("utf8").splitlines()
            ret.scoped[dir_name] = gitignore_parse(lines)
    return ret


def check_ignore1(rules, path: str) -> bool | None:
    result = None
    for pattern, value in rules:
        if fnmatch(path, pattern):
            result = value
    return result


def check_ignore_scoped(rules, path: str) -> str | None:
    parent = os.path.dirname(path)
    while True:
        if parent in rules:
            result = check_ignore1(rules[parent], path)
            if result != None:
                return result
        if parent == "":
            break
        parent = os.path.dirname(parent)
    return None


def check_ignore_absolute(rules, path: str):
    parent = os.path.dirname(path)
    for ruleset in rules:
        result = check_ignore1(ruleset, path)
        if result != None:
            return result
    return False


def check_ignore(rules, path):
    if os.path.isabs(path):
        raise Exception(
            "This function requires path to be relative to the repository's root"
        )

    result = check_ignore_scoped(rules.scoped, path)
    if result != None:
        return result

    return check_ignore_absolute(rules.absolute, path)


# Things to add into anki:
# 1. How are git files named? The name of a git file is mathematically derived from it's content
# 2. you don’t modify a file in git, you create a new file in a different location
# 3. Why is git considered a value-value store? Because the filename (key) is computed from data
# 5. How is the path where git stores a object computed? By calculating the SHA-1 hash of its content
# 6. How is the path name represented? The hash is lowercase and split into two parts: the first two characters and the rest.
#       First part is the directory name, rest as filename.
#       E.g. Hash = e673d1b7eaa0aa01b5bc2442d570a765bdaae751
#            Hash Expanded = First Two Char + / + Remaining Hash character = .git/objects/e6/73d1b7eaa0aa01b5bc2442d570a765bdaae751
# 7. Despite the different types of object in Git, what are some common function it shares? The same storage/retrieval mechanism
#       and the same general header format
# 8. What are the different type of objects in git? Files, commit, tree, tags. Almost everything in git is stored as an object
# 9. What compression format is used for git files? zlib
# 10. What is extracted out of the decompressed data?  we extract the two header components: the object type and its size
# 11. What is a GitBlob? The content of every file the user put in git
# 12. How is a commit object formatted?
#       - On a line, if the first space is surrounded by two characters. The left will be the key and the anything to the right is the value before '\n'
#       - If there are multi lines a space at the start is required. And this leading space needs to be removed. The terminal point of this is when the parser
#         doesn't detect a leading space anymore on a new line
# 13. Does a python HashMap preserve order insertion? Yes.
# 14. What are the two rules pertaining to object identity in Git?
#       - The same name will always refer to the same object
#       - The same object will always be reffered by the same name. Which means there can't be two equivalent object under different name
# 15. What's the difference between a space and 0x00? space is the delimeter between a key-value pair, whereas 0x00 is a null byte that separates header from content
# 16. How is a tree object formatted? [mode] space [path] 0x00 [sha-1]
# 17. What does a tree object represent? A folder
# 18. What is a indirect reference? A ref referencing another ref. E.g. ref:path/to/other/ref
# 19. What is a direct reference? A ref with a SHA-1 object
# 20. What is a ref? It's a human-readable name that represent a object hash or other refs
# 21. What is a tag? It's a ref.
# 22. What are the two types of tag? Lightweight tag & Tag objects (same format as a commit obj)
# 23. What is a branch? It's a ref to a commit (hash)
# 24. Where does tag live in .git? `.git/refs/tags`
# 25. Where does branches live in .git? `.git/refs/heads`
# 26. Where does the current/active branch live in .git? `.git/HEAD`, this is a ref file containing
#       a indirect reference aka path/to/other/ref
# 27. How does a short hash look like? 5bd254 instead of 5bd254aa973646fa16f66d702a5826ea14a3eb45
# 28. What is the two step process when performing a commit? A git add / git rm followed by a git commit -m <MESSAGE>
# 29. What's the name of the intermediate stage between the last and next commit. And what's used to represent this stage?
#       The stage is called: staging area and a binary file located at .git/index is used to represent the changes in this stage
# 30. What are the types of gitignore file and where does it live?
#   absolute - lives in '~/.config/git/ignore' or '.git/info/exclude'; global ignore file
#   scoped - lives in `<REPO>/.gitignore`
# 31. What's the heirachy of ignore? Scope first then global
