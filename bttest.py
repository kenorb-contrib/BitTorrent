#!/usr/bin/env python

# Written by Bram Cohen
# see LICENSE.txt for license information

import sys
assert sys.version >= '2', "Install Python 2.0 or greater"

from BitTorrent import testtest
import bttrack
import btpublish
import btdownloadgui
import btdownloadheadless
import btdownloadlibrary

def run():
    testtest.try_all(['urllib', 'StringIO', 'random', 'urlparse', 'BaseHTTPServer', 'httplib'])

if __name__ == '__main__':
    run()
