#!/usr/bin/env python

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Written by Bram Cohen and Matt Chisholm

import sys
import os
from distutils.core import setup, Extension
import BitTorrent

import glob

scripts = ["btdownloadgui.py", "btdownloadcurses.py", "btdownloadheadless.py", 
           "btmaketorrentgui.py", "btmaketorrent.py",
           "btlaunchmany.py", "btlaunchmanycurses.py", 
           "bttrack.py", "btreannounce.py", "btrename.py", "btshowmetainfo.py",
           "bttest.py"]

img_root, doc_root = BitTorrent.calc_unix_dirs()

data_files = [ (img_root        , glob.glob('images/*png')+['images/bittorrent.ico',]),
               (img_root+'/logo', glob.glob('images/logo/bittorrent_[0-9]*.png')     ),
               (doc_root        , ['credits.txt', 'LICENSE.txt',
                                   'README.txt', 'redirdonate.html']       ),
               ]

setup(
    name = "BitTorrent",
    version = BitTorrent.version,
    author = "Bram Cohen",
    author_email = "bram@bitconjurer.org",
    url = "http://bittorrent.com/",
    license = "BitTorrent Open Source License",
    scripts = scripts,
    packages = ["BitTorrent"],
    data_files = data_files,
    )
