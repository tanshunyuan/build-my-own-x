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
    return name

argsp = argsubparsers.add_parser("ls-tree", help="Pretty-print a tree object.")
argsp.add_argument("-r",
                   dest="recursive",
                   action="store_true",
                   help="Recurse into sub-trees")

argsp.add_argument("tree",
                   help="A tree-ish object.")

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
        
        match type: # Determine the type.
            case b'04': type = "tree"
            case b'10': type = "blob" # A regular file.
            case b'12': type = "blob" # A symlink. Blob contents is link target.
            case b'16': type = "commit" # A submodule
            case _: raise Exception(f"Weird tree leaf mode {item.mode}")

        if not (recursive and type=='tree'): # This is a leaf
            print(f"{'0' * (6 - len(item.mode)) + item.mode.decode("ascii")} {type} {item.sha}\t{os.path.join(prefix, item.path)}")
        else: # This is a branch, recurse
            ls_tree(repo, item.sha, recursive, os.path.join(prefix, item.path))
            
argsp = argsubparsers.add_parser("checkout", help="Checkout a commit inside of a directory.")

argsp.add_argument("commit",
                   help="The commit or tree to checkout.")

argsp.add_argument("path",
                   help="The EMPTY directory to checkout on.")

def cmd_checkout(args):
    repo = repo_find()
    obj = object_read(repo, object_find(repo, args.commit))

    # If the object is a commit, we grab its tree
    if obj.fmt == b'commit':
        obj = object_read(repo, obj.kvlm[b'tree'].decode('ascii'))
    
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

        if obj.fmt == b'tree':
            os.mkdir(dest)
            tree_checkout(repo, obj, dest)
        elif obj.fmt == b'blob':
            # @TODO Support symlinks (identified by mode 12****)
            with open(dest, 'wb') as f:
                f.write(obj.blobdata)

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
    return os.path.join(repo.gitdir, *path)


# E.g. repo_file("my_repo", "dir1", "dir2", "file.txt", mkdir=True)
def repo_file(repo, *path, mkdir=False):
    """
    Same as repo_path, but create dirname(*path) if absent.
    For example, repo_file(r, \"refs\", \"remotes\", \"origin\", \"HEAD\") will create .git/refs/remotes/origin.
    """
    if repo_dir(repo, *path[:-1], mkdir=mkdir):  # creates the directory
        return repo_path(repo, *path)  # return the path


def repo_dir(repo, *path, mkdir=False):
    """
    Same as repo_path, but validates *path and creates a directory
    if mkdir is True
    """

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
