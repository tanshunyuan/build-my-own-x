from common.parser import main_parsers
import command.init
import sys


def main(argv=sys.argv[1:]):
    args = main_parsers.parse_args(argv)
    match args.command:
        case "add":
            cmd_add(args)


if __name__ == "__main__":
    main()
