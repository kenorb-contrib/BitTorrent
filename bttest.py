#!/usr/bin/env python

# Written by Bram Cohen
# see LICENSE.txt for license information

from BitTorrent import testtest
import bttrack
import btpublish
import btdownloadgui
import btdownloadheadless
import btdownloadlibrary

def run():
    testtest.try_all(['urllib', 'StringIO', 'random', 'urlparse', 
        'BaseHTTPServer', 'httplib', 'BitTorrent.RawServer'])

if __name__ == '__main__':
    run()
