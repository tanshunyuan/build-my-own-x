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
    tag_create,
    object_find
)

wyag_revparse = sub_parsers.add_parser(
    "rev-parse",
    help="Parse revision (or other objects) identifiers")

wyag_revparse.add_argument("--wyag-type",
                   metavar="type",
                   dest="type",
                   choices=["blob", "commit", "tag", "tree"],
                   default=None,
                   help="Specify the expected type")

wyag_revparse.add_argument("name",
                   help="The name to parse")

def cmd_rev_parse(args):
    if args.type:
        fmt = args.type.encode()
    else:
        fmt = None

    repo = repo_root_finder()

    print (object_find(repo, args.name, fmt, follow=True))