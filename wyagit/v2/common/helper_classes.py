import os
import configparser
from constants import GIT_DIR, GIT_CONFIG_FILE
from loguru import logger
import traceback
import zlib
import hashlib
import io

from typing import BinaryIO


# ------------------------------- CLASSES_START ------------------------------ #
class GitRepository:
    """
    It's a storage system that tracks the changes of a working tree
    over time

    It must contain a `.git` directory in the working tree, this is
    where the actual storage of changes is stored

    A valid git storage must contain `.git` and a `.git/config`
    """

    worktree: str | None = None
    gitdir: str | None = None
    conf: configparser.ConfigParser | None = None

    def __init__(self, path: str, force=False):
        self.worktree = path
        self.gitdir = os.path.join(path, GIT_DIR)

        valid_gitdir = force or os.path.isdir(self.gitdir)

        if not valid_gitdir:
            raise Exception(f"Not a Git repository {path}")

        # Read configuration file in .git/config
        self.conf = configparser.ConfigParser()
        config_file = repo_file(self, GIT_CONFIG_FILE)

        config_file_exists = config_file and os.path.exists(config_file)

        if config_file_exists:
            self.conf.read([config_file])
        elif not force:
            raise Exception("Configuration file missing")

        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0:
                raise Exception("Unsupported repositoryformatversion: {vers}")


class GitObject:
    """
    Generic class which commit, tags, tree, blob object MUST implement
    """

    fmt: bytes | None = None

    def __init__(self, data=None):
        data_exist = data != None
        if data_exist:
            self.deserialize(data)
        else:
            self.init()

    def serialize(self, repo):
        """This function MUST be implemented by subclasses.

        It must read the object's contents from self.data, a byte string, and
        do whatever it takes to convert it into a meaningful representation.
        What exactly that means depend on each subclass.

        """
        raise Exception("Unimplemented!")

    def deserialize(self, data):
        raise Exception("Unimplemented!")

    def init(self):
        pass  # Just do nothing. This is a reasonable default!


class GitBlob(GitObject):
    fmt = b"blob"

    def serialize(self):
        return self.blobdata

    def deserialize(self, data):
        self.blobdata = data


# -------------------------------- CLASSES_END ------------------------------- #


# ------------------------------- HELPER START ------------------------------- #
def repo_path(repo: GitRepository, *path: str):
    """
    Compute path under a repo's gitdir (.git)
    """
    try:
        return os.path.join(repo.gitdir, *path)
    except Exception as e:
        # Log the exception type and message
        logger.error(f" {type(e).__name__}: {str(e)}")

        # Log the arguments that were passed
        logger.debug(f"repo: {repo} | *path: {path}")


def repo_file(repo: GitRepository, *path: str, mkdir=False):
    """
    A wrapper fn around repo_dir

    E.g. repo_file(r, \"refs\", \"remotes\", \"origin\", \"HEAD\") will create .git/refs/remotes/origin.
    origin is a directory
    If it doesn't exist, note that it only creates the folder
    """

    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        return repo_path(repo, *path)


def repo_dir(repo: GitRepository, *path: str, mkdir=False):
    """
    Same as repo_path, but it creates a directory from *path if it doesn't exist
    """

    try:
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
    except Exception as e:
        logger.error(f" {type(e).__name__}: {str(e)}")
        logger.debug(f"repo: {repo} | *path: {path} | mkdir: {mkdir}")


def repo_root_finder(path=".", required=True):
    """
    Find the root of the repo, regardless of current location within the worktree

    E.g.
    Root = ~/Documents/MyProject
    Current = ~/Documents/MyProject/src/tui/frames/mainview/

    If incoming path is Current, it'll find Root which returns ~/Documents/MyProject
    """

    path = os.path.realpath(path)  # Ignore symlinks
    is_root = os.path.isdir(os.path.join(path, GIT_DIR))
    if is_root:
        return GitRepository(path)

    # Recursively go up the directory and find parent

    parent = os.path.realpath(os.path.join(path, ".."))
    logger.debug(f"parent: {parent} | path: {path}")

    # os.path.join('/', '..') == '/'
    if parent == path:
        if required:
            raise Exception("No git directory")
        else:
            return None

    return repo_root_finder(parent, required)


def repo_default_config():
    ret = configparser.ConfigParser()

    ret.add_section("core")
    ret.set("core", "repositoryformatversion", "0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")

    return ret


def object_read(repo: GitRepository, sha: str):
    """
    Read object sha from Git repo. Return a GitObject whose exact type depends on the object.

    Object binary file format:
    [object-type] space [content size in ASCII] null [content]
    """
    obj_dir_name = sha[0:2]
    obj_b_file_name = sha[2:]
    path = repo_file(repo, "objects", obj_dir_name, obj_b_file_name)

    if not os.path.isfile(path):
        return None

    f: BinaryIO
    with open(path, "rb") as f:
        raw = zlib.decompress(f.read())

        # Read object type
        obj_type_end_idx = raw.find(b" ")  # find the first space
        fmt = raw[0:obj_type_end_idx] # obj_type idk why they put fmt

        # Read and validate object size
        obj_size_end_idx = raw.find(
            b"\x00", obj_type_end_idx
        )  # find null after the first space
        obj_size = int(
            raw[obj_type_end_idx:obj_size_end_idx].decode("ascii")
        )  # grab the in-between

        logger.info(f"fmt: {fmt} | obj_size: {obj_size}")

        if obj_size != len(raw) - obj_size_end_idx - 1:
            raise Exception(f"Malformed object {sha}: bad length")

        # Pick constructor
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
                raise Exception(
                    f"Unknown type {fmt.decode('ascii')} for object {sha}"
                )
        # Call constructor and return object
        return c(raw[obj_size_end_idx + 1 :])


def object_write(obj: GitObject, repo=None | GitRepository):
    """
    Object binary file format:
    [object-type] space [content size in ASCII] null [content]
    """
    data = obj.serialize()
    result = obj.fmt + b" " + str(len(data)).encode() + b"\x00" + data
    sha = hashlib.sha1(result).hexdigest()

    if repo:
        obj_dir_name = sha[0:2]
        obj_b_file_name = sha[2:]
        path = repo_file(repo, "objects", obj_dir_name, obj_b_file_name, mkdir=True)

        if not os.path.exists(path):
            f: BinaryIO
            with open(path, "wb") as f:
                f.write(zlib.compress(result))
    return sha


def object_find(repo: GitRepository, name, fmt=None, follow=True):
    return name

def object_hash(fd: io.BufferedReader, fmt: str, repo: GitRepository | None=None):
    """
    Wrapper fn to create a hash
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

# -------------------------------- HELPER END -------------------------------- #
