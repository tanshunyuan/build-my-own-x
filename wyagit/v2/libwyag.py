from common.parser import main_parsers
from command.init import cmd_init
from command.catfile import cmd_cat_file
from command.hashobject import cmd_hash_object
from command.log import cmd_log
from command.lstree import cmd_ls_tree
from command.checkout import cmd_checkout
from command.showref import cmd_show_ref
from command.tag import cmd_tag
from command.revparse import cmd_rev_parse
from loguru import logger

import sys

def main(argv=sys.argv[1:]):
    args = main_parsers.parse_args(argv)
    match args.command:
        case "add"          : cmd_add(args)
        case "cat-file"     : cmd_cat_file(args)
        case "check-ignore" : cmd_check_ignore(args)
        case "checkout"     : cmd_checkout(args)
        case "commit"       : cmd_commit(args)
        case "hash-object"  : cmd_hash_object(args)
        case "init"         : cmd_init(args)
        case "log"          : cmd_log(args)
        case "ls-files"     : cmd_ls_files(args)
        case "ls-tree"      : cmd_ls_tree(args)
        case "rev-parse"    : cmd_rev_parse(args)
        case "rm"           : cmd_rm(args)
        case "show-ref"     : cmd_show_ref(args)
        case "status"       : cmd_status(args)
        case "tag"          : cmd_tag(args)
        case _              : print("Bad command.")


if __name__ == "__main__":
    main()
