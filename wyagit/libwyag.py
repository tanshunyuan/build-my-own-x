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
import zlib
