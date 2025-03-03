
import os
import sys
from common.parser import sub_parsers
from common.helper_classes import object_read, object_find, repo_root_finder
from loguru import logger

wyag_catfile = sub_parsers.add_parser("cat-file",
                                 help="Provide content of repository objects")

wyag_catfile.add_argument("type",
                   metavar="type",
                   choices=["blob", "commit", "tag", "tree"],
                   help="Specify the type")

wyag_catfile.add_argument("object",
                   metavar="object",
                   help="The object to display")

def cmd_cat_file(args):
    repo = repo_root_finder()
    cat_file(repo, args.object, fmt=args.type.encode())

def cat_file(repo, obj, fmt=None):
    obj = object_read(repo, object_find(repo, obj, fmt=fmt))
    sys.stdout.buffer.write(obj.serialize())