#!/usr/bin/env python

# Written by Bram Cohen
# see LICENSE.txt for license information

import sys
assert sys.version >= '2', "Install Python 2.0 or greater"
from distutils.core import setup, Extension
import BitTornado

setup(
    name = "BitTornado",
    version = BitTornado.version,
    author = "Bram Cohen, John Hoffman, Uoti Arpala et. al.",
    author_email = "<theshadow@degreez.net>",
    url = "http://www.bittornado.com",
    license = "MIT",
    
    packages = ["BitTornado","BitTornado.BT1"],

    scripts = ["btdownloadgui.py", "btdownloadheadless.py", "btdownloadlibrary.py", 
        "bttrack.py", "btmakemetafile.py", "btlaunchmany.py", "btcompletedir.py",
        "btdownloadcurses.py", "btcompletedirgui.py", "btlaunchmanycurses.py", 
        "btmakemetafile.py", "btreannounce.py", "btrename.py", "btshowmetainfo.py",
        "bttest.py",
        'btmaketorrentgui.py', 'btcopyannounce.py', 'btsethttpseeds.py', 'bt-t-make.py',
        'alloc.gif','black1.ico','black.ico','blue.ico','green1.ico','green.ico',
        'icon_bt.ico','icon_done.ico','red.ico','white.ico',
        'yellow1.ico','yellow.ico']
    )
