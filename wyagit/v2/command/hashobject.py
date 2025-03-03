from common.parser import sub_parsers
from common.helper_classes import object_hash, repo_root_finder

hashobject = sub_parsers.add_parser(
    "hash-object", help="Compute object ID and optionally creates a blob from a file"
)

hashobject.add_argument(
    "-t",
    metavar="type",
    dest="type",
    choices=["blob", "commit", "tag", "tree"],
    default="blob",
    help="Specify the type",
)

hashobject.add_argument(
    "-w",
    dest="write",
    action="store_true",
    help="Actually write the object into the database",
)

hashobject.add_argument("path", help="Read object from <file>")


def cmd_hash_object(args):
    if args.write:
        repo = repo_root_finder()
    else:
        repo = None

    with open(args.path, "rb") as fd:
        sha = object_hash(fd, args.type.encode(), repo)
        print(sha)
