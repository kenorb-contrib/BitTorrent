#!/usr/bin/env python

# Written by Bram Cohen
# see LICENSE.txt for license information

from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"
from btdownloadgui import run

if __name__ == '__main__':
    run(['--responsefile=' + argv[1]])
