import os
from common.parser import sub_parsers
from common.helper_classes import (
    repo_dir,
    repo_file,
    repo_default_config,
    GitRepository,
    repo_root_finder,
    ref_list,
    ref_resolve,
)
from loguru import logger

wyag_showref = sub_parsers.add_parser("show-ref", help="List references.")


def cmd_show_ref(args):
    repo = repo_root_finder()
    refs = ref_list(repo)
    logger.debug(f"repo: {repo} | refs: {refs}")
    show_ref(repo, refs, prefix="refs")


def show_ref(repo, refs, with_hash=True, prefix=""):
    if prefix:
        prefix = f"{prefix}/"

    for key, value in refs.items():
        if type(value) == str and with_hash:
            print(f"{value} {prefix}{key}")
        elif type(value) == str:
            print(f"{prefix}{key}")
        else:
            show_ref(repo, value, with_hash=with_hash, prefix=f"{prefix}{key}")
