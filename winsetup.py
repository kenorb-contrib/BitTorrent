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
