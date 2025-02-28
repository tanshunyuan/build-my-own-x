from common.parser import sub_parsers

wyag_init = sub_parsers.add_parser("init", help="Initialize a new, empty repository.")
wyag_init.add_argument(
    "path",
    metavar="directory",
    nargs="?",
    default=".",
    help="Where to create the repository.",
)