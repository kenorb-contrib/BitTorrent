#!/usr/bin/env python

# Written by Bram Cohen
# this file is public domain

from BitTorrent.download import downloadurl, defaults
from BitTorrent.parseargs import parseargs, formatDefinitions
from threading import Event
from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

def display(text, type):
    print '\n\n\n\n' + text

if __name__ == '__main__':
    if len(argv) == 1:
        print "usage: %s [options] <url> <file>" % argv[0]
        print formatDefinitions(configDefinitions)
    else:
        config, files = parseargs(argv[1:], defaults, 2, 2) 
        downloadurl(files[0], lambda x: files[1], display, Event(), config)
