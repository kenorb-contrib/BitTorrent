#!/usr/bin/env python

# Written by Bram Cohen
# this file is public domain

from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

from BitTorrent.parseargs import parseargs
from BitTorrent.publish import publish

if __name__ == '__main__':
    config, files = parseargs(argv[1:])
    publish(config, files)
