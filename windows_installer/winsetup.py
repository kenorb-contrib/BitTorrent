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

import os
import sys
from distutils.core import setup
import py2exe
import glob
from BitTorrent import languages

if os.name != 'nt':
    print "This script is only for use on Win32. Use setup.py to install on a Unix OS."
    sys.exit()

from BitTorrent.platform import get_shell_dir, shellcon

opts = {
    "py2exe": {
    "includes":"pango,atk,gobject"
               ",encodings,encodings.*"
#               ",cjkcodecs,cjkcodecs.*"
#               ",dns,dns.rdtypes.ANY.*,dns.rdtypes.IN.*"
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

mfc = os.path.join(get_shell_dir(shellcon.CSIDL_SYSTEM), "mfc71.dll")
ms = [mfc, ]

translations = []
for l in languages:
    path = os.path.join('locale', l, 'LC_MESSAGES', 'bittorrent.mo')
    if os.access(path, os.F_OK):
        translations.append(("locale\\%s\\LC_MESSAGES"                 % l,
                             ["locale\\%s\\LC_MESSAGES\\bittorrent.mo" % l,
                              #"locale\\%s\\LC_MESSAGES\\bittorrent.po" % l,
                              ]))
        gtk_mo = []
        
        gtk_path = ""

        import gtk

        if (gtk.gtk_version[1] == 4):
            gtk_path = os.path.join(os.environ["GTK_BASEPATH"], "lib\\locale\\%s\\LC_MESSAGES" % l)
        elif ((gtk.gtk_version[1] == 6) or (gtk.gtk_version[1] == 8)):
            gtk_path = os.path.join(os.environ["GTK_BASEPATH"], "share\\locale\\%s\\LC_MESSAGES" % l)
        else:
            gtk_path = os.path.join(os.environ["GTK_BASEPATH"], "share\\locale\\%s\\LC_MESSAGES" % l)
            if not os.path.exists(gtk_path):            
                raise Exception("Unknown gtk version, please locate gtk20.mo etc, and modify this script")
        
        for fn in ("glib20.mo", "gtk20.mo", "gtk20-properties.mo"):
            moname = os.path.join(gtk_path, fn)
            if os.access(moname, os.F_OK):
                gtk_mo.append(moname) 
        translations.append(("share\\locale\\%s\\LC_MESSAGES" % l, gtk_mo))

setup(windows=[{'script': 'bittorrent.py' ,
                "icon_resources": [(1, "images\\bittorrent.ico")]},
               {'script': 'maketorrent.py',
                "icon_resources": [(1, "images\\bittorrent.ico")]},
               {'script': 'choose_language.py',
                "icon_resources": [(1, "images\\bittorrent.ico")]},
               ],
      options=opts,
      data_files=[('',["credits.txt", "LICENSE.txt",
                       "README.txt", "redirdonate.html",
                       "TRACKERLESS.txt","public.key",
                       ]),
                  ("images", ["images\\bittorrent.ico"]),
                  ("images\\icons\\default", glob.glob("images\\icons\\default\\*png")),
                  ("images\\logo", glob.glob("images\\logo\\*png")),
                  ] + ms + translations,
                )
