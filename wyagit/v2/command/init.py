import os
from common.parser import sub_parsers
from common.helper_classes import repo_dir, repo_file, repo_default_config, GitRepository
from loguru import logger


def repo_create(path: str):
    """
    Create a new repository at path
    """

    repo = GitRepository(path, True)

    # Make sure the path doesn't exist or it's empty dir
    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception(f"{path} is not a directory")
        gitdir_not_empty = os.path.exists(repo.gitdir) and os.listdir(repo.gitdir)
        if gitdir_not_empty:
            raise Exception(f"{path} is not empty!")
    else:
        os.makedirs(repo.worktree)

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
            


wyag_init = sub_parsers.add_parser("init", help="Initialize a new, empty repository.")
wyag_init.add_argument(
    "path",
    metavar="directory",
    nargs="?",
    default=".",
    help="Where to create the repository.",
)


def cmd_init(args):
    repo_create(args.path)
