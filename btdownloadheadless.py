#!/usr/bin/env python

# Written by Bram Cohen
# see LICENSE.txt for license information

from BitTorrent.download import download
from threading import Event
from os.path import abspath
from sys import argv, version, stdout
assert version >= '2', "Install Python 2.0 or greater"
true = 1
false = 0

def kify(n):
    return str(long((float(n) / (2 ** 10)) * 10) / 10.0)

def mbfy(n):
    return str(long((float(n) / (2 ** 20)) * 10) / 10.0)

def ex(n):
    if n >= 10:
        return str(n)
    else:
        return '0' + str(n)

def hours(n):
    if n == -1:
        return '<unknown>'
    if n == 0:
        return 'complete!'
    n = int(n)
    h, r = divmod(n, 60 * 60)
    m, sec = divmod(r, 60)
    if h > 1000000:
        return '<unknown>'
    if h > 0:
        return str(h) + ' hour ' + ex(m) + ' min ' + ex(sec) + ' sec'
    else:
        return str(m) + ' min ' + ex(sec) + ' sec'

class HeadlessDisplayer:
    def __init__(self):
        self.done = false
        self.file = ''
        self.percentDone = ''
        self.timeEst = ''
        self.downloadTo = ''
        self.downRate = ''
        self.upRate = ''
        self.errors = []

    def finished(self):
        self.done = true
        self.percentDone = '100'
        self.timeEst = 'Download Succeeded!'
        self.downRate = ''
        self.display()

    def failed(self):
        self.done = true
        self.percentDone = '0'
        self.timeEst = 'Download Failed!'
        self.downRate = ''
        self.display()

    def error(self, errormsg):
        self.errors.append(errormsg)
        self.display()

    def display(self, fractionDone = None, timeEst = None, 
            downRate = None, upRate = None, activity = None):
        if fractionDone is not None:
            self.percentDone = str(float(int(fractionDone * 1000)) / 10)
        if timeEst is not None:
            self.timeEst = hours(timeEst)
        if activity is not None and not self.done:
            self.timeEst = activity
        if downRate is not None:
            self.downRate = kify(downRate) + ' K/s'
        if upRate is not None:
            self.upRate = kify(upRate) + ' K/s'
        print '\n\n\n\n'
        for err in self.errors:
            print 'ERROR:\n' + err + '\n'
        print 'saving:        ', self.file
        print 'percent done:  ', self.percentDone
        print 'time left:     ', self.timeEst
        print 'download to:   ', self.downloadTo
        print 'download rate: ', self.downRate
        print 'upload rate:   ', self.upRate
        stdout.flush()

    def chooseFile(self, default, size, saveas, dir):
        self.file = default + ' (' + mbfy(size) + ' MB)'
        if saveas != '':
            default = saveas
        self.downloadTo = abspath(default)
        return default

def run(params):
    try:
        import curses
        curses.initscr()
        cols = curses.COLS
        curses.endwin()
    except:
        cols = 80

    h = HeadlessDisplayer()
    download(params, h.chooseFile, h.display, h.finished, h.error, Event(), cols)
    if not h.done:
        h.failed()

if __name__ == '__main__':
    run(argv[1:])
