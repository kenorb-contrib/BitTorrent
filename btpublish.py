#!/usr/bin/env python

# Written by Bram Cohen
# see LICENSE.txt for license information

from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"
from httplib import HTTP
from urlparse import urlparse
from os.path import getsize, split, join, abspath, isdir
from os import listdir
from sha import sha
from copy import copy
from BitTorrent.suck import suck
from BitTorrent.bencode import bencode, bdecode

def publish(file, url):
    announce(makeinfo(file), url)

def announce(data, url):
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

def makeinfo(file, piece_length = 2 ** 20):
    file = abspath(file)
    if isdir(file):
        subs = subfiles(file)
        subs.sort()
        pieces = []
        sh = sha()
        done = 0
        fs = []
        for p, f in subs:
            pos = 0
            size = getsize(f)
            fs.append({'length': size, 'path': p})
            h = open(f, 'rb')
            while pos < size:
                a = min(size - pos, piece_length - done)
                sh.update(suck(h, a))
                done += a
                pos += a
                if done == piece_length:
                    pieces.append(sh.digest())
                    done = 0
                    sh = sha()
            h.close()
        if done > 0:
            pieces.append(sh.digest())
        return bencode({'type': 'multiple', 'pieces': pieces,
            'piece length': piece_length, 'files': fs, 
            'name': split(file)[1]})
    else:
        size = getsize(file)
        pieces = []
        p = 0
        h = open(file, 'rb')
        while p < size:
            h.seek(p)
            pieces.append(sha(suck(h, piece_length)).digest())
            p += piece_length
        h.close()
        return bencode({'type': 'single', 'pieces': pieces, 
            'piece length': piece_length, 'length': size, 
            'name': split(file)[1]})

def subfiles(d):
    r = []
    stack = [([], d)]
    while len(stack) > 0:
        p, n = stack.pop()
        if isdir(n):
            for s in listdir(n):
                if s != 'CVS' and s != 'core':
                    stack.append((copy(p) + [s], join(n, s)))
        else:
            r.append((p, n))
    return r

if __name__ == '__main__':
    publish(argv[1], argv[2])
