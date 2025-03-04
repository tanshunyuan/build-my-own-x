import os
import configparser
from constants import GIT_DIR, GIT_CONFIG_FILE
from loguru import logger
import traceback
import zlib
import hashlib
import io
import json


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


class GitCommit(GitObject):
    fmt = b"commit"

    def deserialize(self, data):
        self.kvlm = kvlm_parse(data)

    def serialize(self):
        return kvlm_serialize(self.kvlm)

    def init(self):
        self.kvlm = dict()


class GitTreeLeaf:
    """
    mode: ??
    path: points to a blob (file) or a tree (dir)
    sha: SHA-1 of the object
    """

    def __init__(self, mode: str, path: str, sha: str):
        self.mode = mode
        self.path = path
        self.sha = sha


class GitTree(GitObject):
    fmt = b"tree"

    def deserialize(self, data):
        self.items = tree_parse(data)

    def serialize(self):
        return tree_serialize(self)

    def init(self):
        self.items = list()


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
    logger.debug(f"obj_dir_name: {obj_dir_name} | obj_b_file_name: {obj_b_file_name}")
    path = repo_file(repo, "objects", obj_dir_name, obj_b_file_name)
    logger.debug(f"path: {path}")

    if not os.path.isfile(path):
        return None

    f: BinaryIO
    with open(path, "rb") as f:
        raw = zlib.decompress(f.read())

        # Read object type
        obj_type_end_idx = raw.find(b" ")  # find the first space
        fmt = raw[0:obj_type_end_idx]  # obj_type idk why they put fmt

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
                raise Exception(f"Unknown type {fmt.decode('ascii')} for object {sha}")
        # Call constructor and return object
        obj = c(raw[obj_size_end_idx + 1 :])
        return obj


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


def object_hash(fd: io.BufferedReader, fmt: str, repo: GitRepository | None = None):
    """
    Wrapper fn to create a hash
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


# dct=None is done instead of dct=dict() as dct=dict() will cause
# the same dictionary to grow across different function calls
# @REVISIT
def kvlm_parse(raw: str, start=0, dct=None):
    """
    Key Value List with Message (kvlm_parse)

    This deserialises a commit object content.

    The fn is recursive, it reads a key/value pair, calls itself to a new position.
    """

    # logger.debug(f"raw: {raw} | start: {start} | dct: {dct}")

    if not dct:
        dct = dict()

    # If a space appears before a new line, we have a keyword. Otherwise,
    # it's the final message, which we just read to eof
    space = raw.find(b" ", start)
    new_line = raw.find(b"\n", start)

    logger.debug(f"space: {space} | new_line: {new_line} | start: {start}")

    # If there's no space or a newline appears first. It's a blank line
    # A blank line means the remainder of the data is message. We store it in the dict
    # with None as the key, and return
    if (space < 0) or (new_line < space):
        assert new_line == start
        dct[None] = raw[start + 1 :]
        return dct

    key = raw[start:space]

    logger.debug(f"key: {key}")

    # Find the end of the value. Continuation lines begin with a
    # space, so we loop until we find a '\n' not followed by a space
    end = start
    while True:
        end = raw.find(b"\n", end + 1)
        if raw[end + 1] != ord(" "):
            break
    logger.debug(f"end: {end}")

    # Drop the leading space on continuation lines
    wo_lead_space = space + 1
    value = raw[wo_lead_space:end].replace(b"\n ", b"\n")

    logger.debug(f"value: {value}")

    if key in dct:
        if type(dct[key]) == list:
            dct[key].append(value)
        else:
            dct[key] = [dct[key], value]
    else:
        dct[key] = value

    logger.debug("")
    return kvlm_parse(raw, start=end + 1, dct=dct)


def kvlm_serialize(kvlm):
    """
    Used to serialise a commit object
    """

    ret = b""

    for k in kvlm.keys():
        # skip the message itself
        if k == None:
            continue
        val = kvlm[k]
        if type(val) != list:
            val = [val]

        for v in val:
            ret += k + b" " + (v.replace(b"\n", b"\n ")) + b"\n"

    ret += b"\n" + kvlm[None]

    return ret


def tree_parse_worker(raw: bytes, start=0):
    """
    Format of a tree: [mode] space [path] 0x00 [sha-1]
    """
    space_pos = raw.find(b" ", start)
    mode_len = space_pos - start
    assert mode_len == 5 or mode_len == 6

    mode = raw[start:space_pos]
    logger.debug(f"mode: {mode}")
    if len(mode) == 5:
        # Normalize to 6 bytes
        mode = b"0" + mode

    null_pos = raw.find(b"\x00", space_pos)
    path = raw[space_pos + 1 : null_pos]

    raw_sha = int.from_bytes(raw[null_pos + 1 : null_pos + 21], "big")

    # Convert it into an hex string, padded to 40 chars with zero if needed
    sha = format(raw_sha, "040x")
    return null_pos + 21, GitTreeLeaf(mode, path.decode("utf8"), sha)


def tree_parse(raw: bytes):
    pos = 0
    max = len(raw)
    ret = list()
    while pos < max:
        pos, data = tree_parse_worker(raw, pos)
        ret.append(data)
    return ret


def tree_leaf_sort_key(leaf: GitTreeLeaf):
    if leaf.mode.startswith(b"10"):
        return leaf.path
    else:
        return f"{leaf.path}/"


def tree_serialize(obj: GitTree):
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

def tree_checkout(repo: GitRepository, tree: GitTree, path: str):
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
# -------------------------------- HELPER END -------------------------------- #
