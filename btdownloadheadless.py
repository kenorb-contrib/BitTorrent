#!/usr/bin/env python

# Written by Bram Cohen
# see LICENSE.txt for license information

from BitTorrent.download import download
from threading import Event
from sys import argv, version, stdout
assert version >= '2', "Install Python 2.0 or greater"

def display(text, type):
    print '\n\n\n\n' + text
    stdout.flush()

def run(params):
    try:
        import curses
        curses.initscr()
        cols = curses.COLS
        curses.endwin()
    except:
        cols = 80

    download(params, lambda x: x, display, Event(), cols)

if __name__ == '__main__':
    run(argv[1:])
