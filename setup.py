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

import os
os.system('sh ./makei18n.sh')

import gettext
gettext.install('bittorrent', 'locale')

import sys
from distutils.core import setup, Extension
from BitTorrent import version, languages
from BitTorrent.platform import calc_unix_dirs

import glob

symlinks = ["bittorrent" , "bittorrent-curses", "bittorrent-console",
           "maketorrent",                      "maketorrent-console",
                          "launchmany-curses", "launchmany-console",
                                               "changetracker-console",
                                               "torrentinfo-console",
           "bittorrent-tracker",
           ]

scripts = []

for s in symlinks:
    script = s+'.py'
    if not os.access(s, os.F_OK):
        os.symlink(script, s)
    scripts.append(script)
    os.chmod(script, 0755)

use_scripts = symlinks
if sys.argv[1:2] == ['sdist']:
    use_scripts = scripts

img_root, doc_root, locale_root = calc_unix_dirs()

translations = []
for l in languages:
    translations.append (("%s/%s/LC_MESSAGES"          % (locale_root, l),
                          ["locale/%s/LC_MESSAGES/bittorrent.mo" % l]))

data_files = [ (img_root        , glob.glob('images/*png')+['images/bittorrent.ico',]),
               (img_root+'/logo', glob.glob('images/logo/bittorrent_[0-9]*.png')     ),
               (doc_root        , ['credits.txt', 'credits-l10n.txt',
                                   'LICENSE.txt', 'README.txt',
                                   'TRACKERLESS.txt', 'redirdonate.html',
                                   'public.key',
                                   ]       ),
               ] + translations

setup(
    name = "BitTorrent",
    version = version,
    author = "Bram Cohen",
    author_email = "bram@bitconjurer.org",
    url = "http://bittorrent.com/",
    license = "BitTorrent Open Source License",
    scripts = use_scripts,
    packages = ["BitTorrent", "khashmir"],
    data_files = data_files,
    )

for s in symlinks:
    if os.path.islink(s):
        os.remove(s)
