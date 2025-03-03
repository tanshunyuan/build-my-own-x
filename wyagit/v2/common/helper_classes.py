import os
import configparser
from constants import GIT_DIR, GIT_CONFIG_FILE
from loguru import logger
import traceback


### CLASSES_START
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


### CLASSES_END


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


def repo_default_config():
    ret = configparser.ConfigParser()

    ret.add_section("core")
    ret.set("core", "repositoryformatversion", "0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")

    return ret
