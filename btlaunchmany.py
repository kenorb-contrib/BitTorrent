#!/usr/bin/env python2

# Written by Bram Cohen
# see LICENSE.txt for license information

from BitTorrent.download import download
from threading import Thread, Event
from os import listdir
from os.path import join, exists
from sys import argv
true = 1
false = 0

ext = '.torrent'

def dummy(*args, **kwargs):
    pass

def runmany(d, params):
    files = listdir(d)
    for file in files:
        if file[-len(ext):] == ext and file[:-len(ext)] in files:
            Thread(target = runsingle, args = [join(d, file), params]).start()

def runsingle(file, params):
    def err(msg, file = file):
        print 'error in' + file + ' - ' + msg
    def failed(file = file):
        print 'failed ' + file
    def choose(default, size, saveas, dir, file = file):
        return file[:-len(ext)]
    download(params + ['--responsefile', file], choose, dummy, dummy, err, Event(), 80)

if __name__ == '__main__':
    runmany(argv[1], argv[2:])
