#!/usr/bin/env python

# Written by Bram Cohen
# see LICENSE.txt for license information

from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"
from httplib import HTTP
from urlparse import urlparse
from os.path import getsize, split
from sha import sha
from BitTorrent.suck import suck
from BitTorrent.bencode import bencode, bdecode

def publish(file, url):
    piece_length = 2 ** 20
    size = getsize(file)
    pieces = []
    p = 0
    h = open(file, 'rb')
    while p < size:
        h.seek(p)
        pieces.append(sha(suck(h, piece_length)).digest())
        p += piece_length
    h.close()
    data = bencode({'type': 'single', 'pieces': pieces, 
        'piece length': piece_length, 'length': size, 
        'name': split(file)[1]})
    protocol, host, path, g1, g2, g3 = urlparse(url)
    if protocol != 'http':
        raise ValueError, "can't handle protocol '" + protocol + "'"
    h = HTTP(host)
    h.putrequest('PUT', path)
    h.putheader('content-length', str(len(data)))
    h.putheader('Content-Type', 'application/x-bittorrent')
    h.endheaders()
    h.send(data)
    print h.getreply()
    f = h.getfile()
    r = f.read(int(h.headers.getheader('content-length')))
    f.close()
    print r

if __name__ == '__main__':
    publish(argv[1], argv[2])
