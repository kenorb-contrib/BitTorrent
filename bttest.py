#!/usr/bin/env python

# Written by Bram Cohen
# This file is public domain
# The authors disclaim all liability for any damages resulting from
# any use of this software.

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
