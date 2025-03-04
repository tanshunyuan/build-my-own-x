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
    tag_create
)
from loguru import logger
from command.showref import show_ref

wyag_tag = sub_parsers.add_parser("tag", help="List and create tags")

wyag_tag.add_argument(
    "-a",
    action="store_true",
    dest="create_tag_object",
    help="Whether to create a tag object",
)

wyag_tag.add_argument("name", nargs="?", help="The new tag's name")

wyag_tag.add_argument(
    "object", default="HEAD", nargs="?", help="The object the new tag will point to"
)


def cmd_tag(args):
    repo = repo_root_finder()

    if args.name:
        tag_create(
            repo, args.name, args.object, create_tag_object=args.create_tag_object
        )
    else:
        refs = ref_list(repo)
        show_ref(repo, refs["tags"], with_hash=False)
