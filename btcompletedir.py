#!/usr/bin/env python

# Written by Bram Cohen
# see LICENSE.txt for license information

from os import listdir
from os.path import join
from sys import argv
from btmakemetafile import calcsize, make_meta_file

def dummy(x):
    pass

def completedir(dir, url, c = dummy):
    files = listdir(dir)
    ext = '.torrent'

    togen = []
    for f in files:
        if f[-len(ext):] != ext and (f + ext) not in files:
            togen.append(join(dir, f))
        
    total = 0
    for i in togen:
        total += calcsize(i)

    subtotal = [0]
    def callback(x, subtotal = subtotal, total = total, c = c):
        subtotal[0] += x
        c(float(subtotal[0]) / total)
    for i in togen:
        print i
        make_meta_file(i, url, progress = callback)

def dc(v):
    print v

if __name__ == '__main__':
    completedir(argv[1], argv[2], dc)
