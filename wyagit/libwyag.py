import argparse  # Parse CLI arguments
import configparser
from datetime import datetime
import grp, pwd
from fnmatch import fnmatch # support .gitignore
import hashlib # for commits i guess
from math import ceil
import os
import re
import sys
import zlib # git compresses items to zlib

argparser = argparse.ArgumentParser(
    description="Testing 123"
)
# Handle subcommands: git info -> main subcommand
argsubparsers = argparser.add_subparsers(
    title="What is this sub parser?",
    dest="command", # Logical name of the subcommands
    required=True # Can't call the main command without a subcommand
)

def main(argv: sys.argv[1:]):
    args = argparser.parse_args(argv)
    match args.command:
        case 'init': cmd_init(args)

class GitRepository (object):
    worktree = None # Files that are meant to be version controlled. Aka our regular files
    gitdir = None # .git folder which contains Git configuration data
    conf = None # Git configuration data
    
    # force = a flag to disable check. Allows to create a git repo in still invalid folder
    def __init__(self, path, force=False):
        self.worktree = path
        self.gitdir = os.path.join(path, '.git')

        is_gitrepo = os.path.isdir(self.gitdir) # only considred a git repo with .git dir
        if not (force or is_gitrepo):
            raise Exception(f"Not a Git repository {path}")
        
        # Read configuration file in .git/config
        self.conf = configparser.ConfigParser()
        cf = repo_file(self, 'config')
        
        cf_exists = cf and os.path.exists(cf)
        
        if cf_exists:
            self.conf.read([cf])
        elif not force:
            raise Exception('Configuration file missing')

        if not force:
            vers = int(self.conf.get('core', 'repositoryformatversion'))
            if vers != 0:
                raise Exception("Unsupported repositoryformatversion: {vers}")

# * in *path makes the fn variadic aka like the ...rest operator in js
# allows the path variable to take in multiple arguments
# E.g. repo_path(repo, "objects", "df", "4ec9fc2ad990cb9da906a95a6eda6627d7b7b0") 
def repo_path(repo, *path):
    """Compute path under repo's gitdir"""
    return os.path.join(repo.gitdir, *path)