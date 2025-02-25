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

argsp = argsubparsers.add_parser("cat-file", help="Provide content of repository objects")
argsp.add_argument(
    "type",
    metavar="type",
    choices=["blob", "commit", "tag", "tree"],
    help="Specify the type"
)
argsp.add_argument(
    "object",
    metavar="object",
    help="The object to display"
)

def cmd_cat_file(args):
    repo = repo_find()
    cat_file(repo, args.object, fmt=args.type.encode())

def cat_file(repo, obj, fmt=None):
    obj = object_read(repo, object_find(repo, obj, fmt=fmt))
    sys.stdout.buffer.write(obj.serialize())

# how does this keeps getting reassigned?
argsp = argsubparsers.add_parser(
    "hash-object",
    help="Compute object ID and optionally creates a blob from a file"
)

argsp.add_argument(
    "-t",
    metavar="type",
    dest="type",
    choices=["blob", "commit", "tag", "tree"],
    default="blob",
    help="Specify the type"
)

argsp.add_argument(
    "-w",
    dest="write",
    action="store_true",
    help="Actually write the object into the database"
)

argsp.add_argument(
    "path",
    help="Read object from <file>"
)

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
        case b'commit' : obj=GitCommit(data)
        case b'tree'   : obj=GitTree(data)
        case b'tag'    : obj=GitTag(data)
        case b'blob'   : obj=GitBlob(data)
        case _: raise Exception(f"Unknown type {fmt}!")

    return object_write(obj, repo)

def object_find(repo, name, fmt=None, follow=True):
    """
    Name resolution fn
    """
    return name

def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    match args.command:
        case "add"          : cmd_add(args)
        case "cat-file"     : cmd_cat_file(args)
        case "check-ignore" : cmd_check_ignore(args)
        case "checkout"     : cmd_checkout(args)
        case "commit"       : cmd_commit(args)
        case "hash-object"  : cmd_hash_object(args)
        case "init"         : cmd_init(args)
        case "log"          : cmd_log(args)
        case "ls-files"     : cmd_ls_files(args)
        case "ls-tree"      : cmd_ls_tree(args)
        case "rev-parse"    : cmd_rev_parse(args)
        case "rm"           : cmd_rm(args)
        case "show-ref"     : cmd_show_ref(args)
        case "status"       : cmd_status(args)
        case "tag"          : cmd_tag(args)
        case _              : print("Bad command.")


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
    path = os.path.realpath(path) # realpath resolves symlinks, relative path and returns a abs path

    # Recursively finds till a .git folder is hit
    is_git_dir = os.path.isdir(os.path.join(path, ".git"))
    if is_git_dir:
        return GitRepository(path)
    
    parent = os.path.realpath(os.path.join(path), "..")

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
        
class GitObject (object):
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
        pass # Just do nothing. This is a reasonable default!

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
    with open (path, "rb") as f:
        raw = zlib.decompress(f.read())
       
        # Read object type
        x = raw.find(b' ')
        fmt = raw[0:x]
        
        # Read and validate object size
        y = raw.find(b'\x00', x)
        size = int(raw[x:y].decode('ascii'))
        if size != len(raw)-y-1:
            raise Exception(f"Malformed object {sha}: bad length")
        
        # Pick constructor
        # b'<COMMIT_TYPE>'
        match fmt:
            case b'commit' : c=GitCommit
            case b'tree'   : c=GitTree
            case b'tag'    : c=GitTag
            case b'blob'   : c=GitBlob
            case _:
                raise Exception(f"Unknown type {fmt.decode("ascii")} for object {sha}")

        # Call constructor and return object
        return c(raw[y+1:])

def object_write(obj, repo=None):
    # zlib(hash(header + serialise(file)))
    
    # Serialize object data
    data = obj.serialize()
    # Add header
    result = obj.fmt + b' ' + str(len(data)).encode() + b'\x00' + data
    # Compute hash
    sha = hashlib.sha1(result).hexdigest()

    if repo:
        # Compute path
        path = repo_file(repo, "objects", sha[0:2], sha[2:], mkdir=True)

        if not os.path.exists(path):
            with open(path, 'wb') as f:
                # Compress and write
                f.write(zlib.compress(result))
    
    return sha

class GitBlob(GitObject):
    fmt=b'blob'
    
    def serialize(self):
        return self.blobdata
    
    def deserialize(self, data):
        self.blobdata = data
        

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
# 8. What are the different type of objects in git? Files, commit, tree tags. Almost everything in git is stored as an object
# 9. What compression format is used for git files? zlib
# 10. What is extracted out of the decompressed data?  we extract the two header components: the object type and its size
# 11. What is a GitBlob? The content of every file the user put in git