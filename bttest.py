#!/usr/bin/env python

# Written by Bram Cohen
# see LICENSE.txt for license information

try:
    import psyco
    assert psyco.__version__ >= 0x010100f0
    psyco.full()
except:
    pass

from BitTorrent import testtest
import bttrack
import btmakemetafile
import btdownloadheadless

def run():
    testtest.try_all(['urllib', 'urllib2', 'StringIO', 'random', 'urlparse', 
        'BaseHTTPServer', 'httplib', 'BitTorrent.RawServer', 'BitTorrent.zurllib', 
        'base64', 'ftplib', 'gopherlib'])

if __name__ == '__main__':
    run()
