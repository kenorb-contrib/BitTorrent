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
        return '%d hour %02d min %02d sec' % (h, m, sec)
    else:
        return '%d min %02d sec' % (m, sec)

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
        self.display({})

    def failed(self):
        self.done = true
        self.percentDone = '0'
        self.timeEst = 'Download Failed!'
        self.downRate = ''
        self.display({})

    def error(self, errormsg):
        self.errors.append(errormsg)
        self.display({})

    def display(self, dict):
        if dict.has_key('fractionDone'):
            self.percentDone = str(float(int(dict['fractionDone'] * 1000)) / 10)
        if dict.has_key('timeEst'):
            self.timeEst = hours(dict['timeEst'])
        if dict.has_key('activity') and not self.done:
            self.timeEst = dict['activity']
        if dict.has_key('downRate'):
            self.downRate = '%.0f kB/s' % (float(dict['downRate']) / (1 << 10))
        if dict.has_key('upRate'):
            self.upRate = '%.0f kB/s' % (float(dict['upRate']) / (1 << 10))
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
        self.file = '%s (%.1f MB)' % (default, float(size) / (1 << 20))
        if saveas != '':
            default = saveas
        self.downloadTo = abspath(default)
        return default

    def newpath(self, path):
        self.downloadTo = path

def run(params):
    try:
        import curses
        curses.initscr()
        cols = curses.COLS
        curses.endwin()
    except:
        cols = 80

    h = HeadlessDisplayer()
    download(params, h.chooseFile, h.display, h.finished, h.error, Event(), cols, h.newpath)
    if not h.done:
        h.failed()

if __name__ == '__main__':
    run(argv[1:])
