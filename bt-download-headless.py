#!/usr/bin/env python

# Written by Bram Cohen
# this file is public domain

from BitTorrent.download import downloadurl
from BitTorrent.parseargs import parseargs
from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

def getname(default):
    root = Tk()
    root.withdraw()
    return asksaveasfilename(initialfile = default)

if __name__ == '__main__':
    config, files = parseargs(argv[1:])
    if len(files) != 2:
        print 'usage - download.py url localfilename'
    else:
        downloadurl(files[0], files[1], config)
