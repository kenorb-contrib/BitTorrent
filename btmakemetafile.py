#!/usr/bin/env python2

# Written by Bram Cohen
# see LICENSE.txt for license information

from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"
from os.path import getsize, split, join, abspath, isdir
from os import listdir
from sha import sha
from copy import copy
from string import strip
from BitTorrent.bencode import bencode
from BitTorrent.btformats import check_info
from threading import Event

def dummy(v):
    pass

def make_meta_file(file, url, piece_length = 2 ** 18, 
        flag = Event(), progress = dummy):
    a, b = split(file)
    if b == '':
        f = a + '.torrent'
    else:
        f = join(a, b + '.torrent')
    info = makeinfo(file, piece_length, flag, progress)
    if flag.isSet():
        return
    check_info(info)
    h = open(f, 'wb')
    h.write(bencode({'info': info, 'announce': strip(url)}))
    h.close()

def calcsize(file):
    if not isdir(file):
        return getsize(file)
    total = 0
    for s in subfiles(abspath(file)):
        total += getsize(s[1])
    return total

def makeinfo(file, piece_length, flag, progress):
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
                sh.update(h.read(a))
                if flag.isSet():
                    return
                done += a
                pos += a
                if done == piece_length:
                    pieces.append(sh.digest())
                    done = 0
                    sh = sha()
                progress(a)
            h.close()
        if done > 0:
            pieces.append(sh.digest())
        return {'pieces': ''.join(pieces),
            'piece length': piece_length, 'files': fs, 
            'name': split(file)[1]}
    else:
        size = getsize(file)
        pieces = []
        p = 0
        h = open(file, 'rb')
        while p < size:
            x = h.read(min(piece_length, size - p))
            if flag.isSet():
                return
            pieces.append(sha(x).digest())
            p += piece_length
            if p > size:
                p = size
            progress(float(p) / size)
        h.close()
        return {'pieces': ''.join(pieces), 
            'piece length': piece_length, 'length': size, 
            'name': split(file)[1]}

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

def prog(amount):
    print '%.1f%% complete' % (amount * 100)

if __name__ == '__main__':
    make_meta_file(argv[1], argv[2], progress = prog)
