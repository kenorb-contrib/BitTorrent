#!/usr/bin/env python

# Written by Bram Cohen
# this file is public domain

from BitTorrent.download import downloadurl
from BitTorrent.parseargs import parseargs
from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

if __name__ == '__main__':
    config, files = parseargs(argv[1:])
    if len(files) == 0:
        print 'usage - download.py url localfilename'
    else:
        if len(files) == 2:
            downloadurl(files[0], files[1], config)
        else:
            downloadurl(files[0], None, config)
