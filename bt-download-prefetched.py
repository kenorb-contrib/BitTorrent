#!/usr/bin/env python

# Written by Bram Cohen
# this file is public domain

from BitTorrent.download import download
from BitTorrent.parseargs import parseargs
from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

if __name__ == '__main__':
    config, files = parseargs(argv[1:])
    h = open(files[0])
    r = h.read()
    h.close()
    download(r, None, config)
