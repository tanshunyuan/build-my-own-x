import argparse

main_parsers = argparse.ArgumentParser(description="The stupidest content tracker")
sub_parsers = main_parsers.add_subparsers(
    title="Commands", dest="command", required=True
)