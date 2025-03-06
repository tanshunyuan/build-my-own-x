import os
import re
import configparser
from constants import GIT_DIR, GIT_CONFIG_FILE
from loguru import logger
import traceback
import zlib
import hashlib
import io
import json


from typing import BinaryIO, TypedDict, NamedTuple

from collections import namedtuple


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


class GitTag(GitCommit):
    fmt = b"tag"


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
    Read the contents of the object, based off the SHA provided.
    Return a GitObject whose exact type depends on the object.

    Object binary file format:
        - It's made of two parts: header & content
        - Contents is everything after the header
        - Header format: [obj-type] space [content size in ASCII] null. [obj-type] represent the type of
    """
    obj_dir_name, obj_file_name = split_obj_sha(sha)

    logger.debug(f"obj_dir_name: {obj_dir_name} | obj_file_name: {obj_file_name}")
    path = repo_file(repo, "objects", obj_dir_name, obj_file_name)
    logger.debug(f"path: {path}")

    if not os.path.isfile(path):
        return None

    f: BinaryIO
    with open(path, "rb") as f:
        raw = zlib.decompress(f.read())
        logger.debug(f"raw: {raw}")

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
    """
    Cannot find stuff??
    """
    sha = object_resolve(repo, name)
    if not sha:
        raise Exception(f"No such reference {name}.")

    if len(sha) > 1:
        raise Exception(
            "Ambiguous reference {name}: Candidates are:\n - {'\n - '.join(sha)}."
        )

    sha = sha[0]

    if not fmt:
        return sha

    while True:
        obj = object_read(repo, sha)

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


def object_resolve(repo: GitRepository, name: str):
    """
    Resolve name to an object hash in repo.

    If name == HEAD, returns .git/HEAD
    If name == full hash, returns full hash
    If name == short hash, return a list containing full hash beginning with a short hash
    If name == tags/branch, return matching name
    """

    logger.debug(f"repo: {repo} | name: {name}")
    if not name.strip():
        logger.warning(f"{name} is empty")
        return None

    if name == "HEAD":
        return [ref_resolve(repo, "HEAD")]

    candidates = list()
    hashRE = re.compile(r"^[0-9A-Fa-f]{4,40}$")

    if hashRE.match(name):
        # Hash can either be short or full
        name = name.lower()
        obj_dir = name[0:2]
        path = repo_dir(repo, "objects", obj_dir, mkdir=False)
        if path:
            obj_file_name = name[2:]
            for file in os.listdir(path):
                if file.startswith(obj_file_name):
                    full_hash = obj_dir + obj_file_name
                    candidates.append(full_hash)
        else:
            logger.warning(f"{path} is empty")

    as_tag = ref_resolve(repo, "refs/tags/" + name)
    logger.debug(f"as_tag: {as_tag}")
    if as_tag:
        candidates.append(as_tag)

    as_branch = ref_resolve(repo, "refs/heads/" + name)
    logger.debug(f"as_branch: {as_branch}")
    if as_branch:
        candidates.append(as_branch)
    return candidates


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

        if obj.fmt == b"tree":
            os.mkdir(dest)
            tree_checkout(repo, obj, dest)
        elif obj.fmt == b"blob":
            # @TODO Support symlinks (identified by mode 12****)
            with open(dest, "wb") as f:
                f.write(obj.blobdata)


def ref_resolve(repo: GitRepository, ref: str):
    """
    Recursively resolving a indirect reference (`ref: <path/to/a/ref>`) to a direct reference (hash)
    """
    path = repo_file(repo, ref)

    if not os.path.isfile(path):
        logger.warning(f"{path} is not a file")
        return None

    data: str
    with open(path, "r") as fp:
        data = fp.read()[:-1]
        # Drop final \n ^^^^^

    if data.startswith("ref: "):
        logger.debug("returning indirect reference")
        logger.debug(f"data: {data} | data[5:]: {data[5:]}")
        # @TODO figure out why is it data[5:]
        return ref_resolve(repo, data[5:])
    else:
        # reached direct ref
        return data


def ref_list(repo: GitRepository, path=None):
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


def tag_create(repo: GitRepository, name: str, ref: str, create_tag_object=False):
    """
    create_tag_object=True: creates a tag with more information much like a commit
    create_tag_object=False: creates a lightweight tag without any additional information
    """
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


class ObjShaParts(NamedTuple):
    obj_dir_name: str
    obj_file_name: str

def split_obj_sha(sha: str) -> ObjShaParts:
    """
    Returns a dictionary with the obj directory and obj file name
    """
    obj_dir_name = sha[0:2]
    obj_file_name = sha[2:]

    # return {"obj_dir_name": obj_dir_name, "obj_file_name": obj_file_name}
    return ObjShaParts(obj_dir_name, obj_file_name)


# -------------------------------- HELPER END -------------------------------- #
