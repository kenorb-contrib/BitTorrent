#!/usr/bin/env python

# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bram Cohen and Matt Chisholm

from distutils.core import setup
import py2exe
import glob

opts = {
    "py2exe": {
    "includes":"pango,atk,gobject"
               ",encodings,encodings.*"
#               ",cjkcodecs,cjkcodecs.*"
               ",dns,dns.rdtypes.ANY.*,dns.rdtypes.IN.*"
    ,

# Uncomment the following lines if you want a dist\ directory build by
# py2exe that works under Win32 with a GTK runtime installed
# separately:
##    "dll_excludes":["iconv.dll", "intl.dll", "libatk-1-1.0-0.dll",
##                    "libgdk_pixbuf-2.0-0.dll", "libgdk-win32-2.0-0.dll",
##                    "libglib-2.0-0.dll", "libgmodule-2.0-0.dll",
##                    "libgobject-2.0-0.dll", "libgthread-2.0-0.dll",
##                    "libgtk-win32-2.0-0.dll", "libpango-1.0-0.dll",
##                    "libpangowin32-1.0-0.dll",
##                    ],
    }
}

setup(windows=[{'script': 'btdownloadgui.py',
                "icon_resources": [(1, "images\\bittorrent.ico")]},
               {'script': 'btmaketorrentgui.py',
                "icon_resources": [(1, "images\\bittorrent.ico")]}],
      options=opts,
      data_files=[('',["credits.txt", "LICENSE.txt",
                       "README.txt", "redirdonate.html"]),
                  ("images", glob.glob("images\\*png")+["images\\bittorrent.ico"]),
                  ("images\\logo", glob.glob("images\\logo\\*png")) ],
                )
