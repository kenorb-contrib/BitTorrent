#!/usr/bin/env python

# Written by Bram Cohen
# This file is public domain
# The authors disclaim all liability for any damages resulting from
# any use of this software.

from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

from BitTorrent.publish import publish

if __name__ == '__main__':
    try:
        import curses
        curses.initscr()
        cols = curses.COLS
        curses.endwin()
    except:
        cols = 80

    publish(argv[1:], cols)
