#!/usr/bin/env python

# Written by Bram Cohen
# see LICENSE.txt for license information

from BitTorrent.download import download
from threading import Event
from sys import argv, version, stdout
assert version >= '2', "Install Python 2.0 or greater"

f = ''
pd = ''
te = ''
dr = ''
ur = ''
s = ''

def display(percentDone = None, timeEst = None, 
        downRate = None, upRate = None,
        cancelText = None, size=None):
    global f, pd, te, dr, ur, s
    if percentDone:
        pd = percentDone
    if timeEst:
        te = timeEst
    if downRate:
        dr = downRate
    if upRate:
        ur = upRate
    if size:
        s = ' (' + size + ')'
    print '\n\n\n\n'
    print 'saving:        ', f + s
    print 'percent done:  ', pd
    print 'time left:     ', te
    print 'download rate: ', dr
    print 'upload rate:   ', ur
    stdout.flush()

def displayerror(error):
    print '\n\n\n\nERROR: ', error

def chooseFile(default):
    global f
    f = default
    return default

def run(params):
    try:
        import curses
        curses.initscr()
        cols = curses.COLS
        curses.endwin()
    except:
        cols = 80

    download(params, chooseFile, display, display, Event(), cols)

if __name__ == '__main__':
    run(argv[1:])
