#!/usr/bin/env python

# Written by Bram Cohen
# this file is public domain

import sys
assert sys.version >= '2', "Install Python 2.0 or greater"

from BitTorrent import testtest
import bttrack
import btpublish
import btdownloadgui
import btdownloadheadless
import btdownloadlibrary

def run():
    testtest.try_all(['urllib', 'StringIO', 'random', 'urlparse', 'BaseHTTPServer'])

if __name__ == '__main__':
    run()
