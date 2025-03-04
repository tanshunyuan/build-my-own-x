import os
from common.parser import sub_parsers
from common.helper_classes import object_hash, repo_root_finder, object_find, object_read, tree_checkout
from loguru import logger

wyag_checkout = sub_parsers.add_parser(
    "checkout", help="Checkout a commit inside of a directory."
)

wyag_checkout.add_argument("commit", help="The commit or tree to checkout.")

wyag_checkout.add_argument("path", help="The EMPTY directory to checkout on.")

def cmd_checkout(args):
  repo = repo_root_finder()
  sha = object_find(repo, args.commit)
  obj = object_read(repo, sha)

  logger.debug(f"repo: {repo} | sha: {sha} | obj: {obj}")

  # If obj is a commit, we grab its tree
  if obj.fmt == b'commit':
    obj = object_read(repo, obj.kvlm[b'tree'].decode('ascii'))
  
    # Verify that path is an empty directory
  if os.path.exists(args.path):
      if not os.path.isdir(args.path):
          raise Exception(f"Not a directory {args.path}!")
      if os.listdir(args.path):
          raise Exception(f"Not empty {args.path}!")
  else:
      os.makedirs(args.path)

  tree_checkout(repo, obj, os.path.realpath(args.path))
  