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

# Written by Bram Cohen, Matt Chisholm and Greg Hazel

import os
import sys
from distutils.core import setup
import py2exe
import glob
from BTL.language import languages

if os.name != 'nt':
    print "This script is only for use on Win32. Use setup.py to install on a Unix OS."
    sys.exit()

from BitTorrent.platform import get_shell_dir, shellcon

excludes = ["curses",
            "email",
            "statvfs",
            "cProfile",
            "lsprofcalltree",
            "lsprof",
            "hotshot",
            "hotshot.log",
            "hotshot.stats",
            "pdb",
            'bz2',
            'textwrap',
            'tty',
            "popen2",
            'os2emxpath',
            'pywin.dialogs',
            'pywin.dialogs.list',
            'pywin.dialogs.status',
            'pywin.mfc.dialog',
            'pywin.mfc.thread',
            'pywin.mfc.window',
            'quopri',
            'smtplib',
            #'win32api',
            'win32evtlog',
            'win32evtlogutil',
            'zipfile',
            'UserList',
            'wx.lib.dialogs',
            'wx.lib.layoutf',
            "macpath",
            "macurl2path",
            "twisted.spread",
            "twisted.internet.kqreactor",
            "twisted.internet.unix",
            "twisted.internet.fdesc",
            "twisted.internet.pollreactor",
            ]

old_excludes = list(excludes)
excludes = []
for e in old_excludes:
    excludes.append(e)
    excludes.append(e + ".*")

# wtf
includes = ["encodings", "encodings.*", "twisted.web.resource",
            "BitTorrent.sparse_set", "BitTorrent.bitfield",]

opts = {
    "py2exe": {
        # this compression makes the installed size smaller, but the installer size larger
        #"compressed": 1,
        "optimize": 2,
        "excludes": excludes,
        "includes": includes,
#                    ",cjkcodecs,cjkcodecs.*"
#                    ",dns,dns.rdtypes.ANY.*,dns.rdtypes.IN.*"
    }
}

# needed for py2exe to find win32com.shell; from http://starship.python.net/crew/theller/moin.cgi/WinShell
if 1:
    try:
        import modulefinder, sys
        import win32com
        for p in win32com.__path__[1:]:
            modulefinder.AddPackagePath("win32com", p)
        for extra in ["win32com.shell"]: #,"win32com.mapi"
            __import__(extra)
            m = sys.modules[extra]
            for p in m.__path__[1:]:
                modulefinder.AddPackagePath(extra, p)
    except ImportError:
        # no build path setup, no worries.
        pass

mfc = os.path.join(get_shell_dir(shellcon.CSIDL_SYSTEM), "mfc71.dll").encode('utf8')
unicows = os.path.join(get_shell_dir(shellcon.CSIDL_SYSTEM), "unicows.dll").encode('utf8')
ms = [mfc, unicows, ]

try:
    import psyco
    psyco.full()
except ImportError:
    pass

setup(windows=[{'script': 'bittorrent.py' ,
                "icon_resources": [(1, "images\\bittorrent.ico")]},
               {'script': 'maketorrent.py',
                "icon_resources": [(1, "images\\bittorrent.ico")]},
               {'script': 'choose_language.py',
                "icon_resources": [(1, "images\\bittorrent.ico")]},
               ],
      options=opts,
      data_files=[('',["credits.txt", "LICENSE.txt", "README.txt",
                       "TRACKERLESS.txt", "public.key", "addrmap.dat",
                       ]),
                  ("images", ["images\\bittorrent.ico"]),
                  ("images\\themes\\default", glob.glob("images\\themes\\default\\*png")),
                  ("images\\themes\\default\\torrentstate", glob.glob("images\\themes\\default\\torrentstate\\*png")),
                  #("images\\themes\\default\\statuslight", glob.glob("images\\themes\\default\\statuslight\\*png")),
                  ("images\\themes\\default\\torrentops", glob.glob("images\\themes\\default\\torrentops\\*png")),
                  ("images\\themes\\default\\fileops", glob.glob("images\\themes\\default\\fileops\\*png")),
                  ("images\\flags", glob.glob("images\\flags\\*png")),
                  #("images\\logo", glob.glob("images\\logo\\*png")),
                  ("images\\logo", ["images\\logo\\banner.png",
                                    "images\\logo\\bittorrent_icon_16.png"]),
                  ] + ms,
                )

