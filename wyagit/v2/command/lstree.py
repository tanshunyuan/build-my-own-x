import os
from common.parser import sub_parsers
from common.helper_classes import object_hash, repo_root_finder, object_find, object_read
from loguru import logger

wyag_lstree = sub_parsers.add_parser("ls-tree", help="Pretty-print a tree object.")
wyag_lstree.add_argument("-r",
                   dest="recursive",
                   action="store_true",
                   help="Recurse into sub-trees")

wyag_lstree.add_argument("tree",
                   help="A tree-ish object.")

def cmd_ls_tree(args):
  repo = repo_root_finder()
  ls_tree(repo, args.tree, args.recursive)

def ls_tree(repo, ref, recursive=None, prefix=""):
  sha = object_find(repo, ref, fmt=b"tree")
  obj = object_read(repo, sha)

  for item in obj.items:
    if len(item.mode) == 5:
      type = item.mode[0:1]
    else:
      type = item.mode[0:2]
    
    logger.debug(f"type: {type}")
  
    match type: # Determine the type.
        case b'04': type = "tree"
        case b'10': type = "blob" # A regular file.
        case b'12': type = "blob" # A symlink. Blob contents is link target.
        case b'16': type = "commit" # A submodule
        case _: raise Exception(f"Weird tree leaf mode {item.mode}")

    if not (recursive and type=='tree'): # This is a leaf
        print(f"{'0' * (6 - len(item.mode)) + item.mode.decode('ascii')} {type} {item.sha}\t{os.path.join(prefix, item.path)}")
    else: # This is a branch, recurse
        ls_tree(repo, item.sha, recursive, os.path.join(prefix, item.path))