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

import os

# thanks Drue!
app_name = "BitTorrent"

from BitTorrent.platform import install_translation
install_translation()

import sys
from distutils.core import setup, Extension
from BitTorrent import version
from BitTorrent.platform import calc_unix_dirs
from BTL.language import languages

import glob

# detect case-insensitive filesystem
case_sensitive_filesystem = True
os.mkdir('FOO')
try:
    f = open('foo', 'w')
except:
    case_sensitive_filesystem = False
else:
    f.close()
    os.remove('foo')
os.rmdir('FOO')
# done detecting case-insensitive filesystem

extra_docs = []

symlinks = ["bittorrent" ,
            "bittorrent-curses",
            "bittorrent-console",
            "maketorrent",
            "maketorrent-console",
            "launchmany-curses",
            "launchmany-console",
            "changetracker-console",
            "torrentinfo-console",
            "bittorrent-tracker",
            ]

scripts = [s + '.py' for s in symlinks]
for script in scripts:
    os.chmod(script, 0755)

if sys.argv[1:2] == ['sdist'] or not case_sensitive_filesystem:
    use_scripts = scripts
else:
    for s in symlinks:
        script = s + '.py'
        if not os.access(s, os.F_OK):
            os.symlink(script, s)
        scripts.append(script)
    use_scripts = symlinks


if os.name == 'nt':
    extra_docs.append('BUILD.windows.txt')


img_root, doc_root, locale_root = calc_unix_dirs()


data_files = [
    (img_root, ['images/bittorrent.ico',]),
    (doc_root, ['credits.txt', 'LICENSE.txt', 'README.txt',
                'TRACKERLESS.txt', 'redirdonate.html', 'public.key',
                'INSTALL.unix.txt', ] + extra_docs),
    ]

for d in ('flags', 'logo', 'themes/default',
          'themes/default/statuslight', 'themes/default/torrentstate',
          'themes/default/torrentops' , 'themes/default/fileops'     ,):
    data_files.append(
        (os.path.join(img_root, d),
         glob.glob(os.path.join('images', d, '*.png')))
        )

if not os.path.exists('locale'):
    os.system('sh ./makei18n.sh')

for l in languages:
    path = os.path.join('locale', l, 'LC_MESSAGES', 'bittorrent.mo')
    if os.access(path, os.F_OK):
        data_files.append((os.path.join(locale_root, l, 'LC_MESSAGES'),
                             [path,]))

attrs = {
    'name' : "BitTorrent",
    'version' : version,
    'author' : "Bram Cohen",
    'author_email' : "bugs@bittorrent.com",
    'url' : "http://bittorrent.com/",
    'license' : "GNU Public License version 3",
    'scripts' : use_scripts,
    'packages' : ["BTL", "BitTorrent", "khashmir", "BitTorrent.GUI_wx",],
    'package_dir' : {"BTL": "BTL"},
    'package_data' : {"BTL": ["*.dat"]},
    'py_modules' : ["Zeroconf",],
    'data_files' : data_files,
    'description' : "Scatter-gather network file transfer",
    'long_description' : """BitTorrent is a tool for distributing files.  It's extremely easy to use - downloads are started by clicking on hyperlinks.  Whenever more than one person is downloading at once they send pieces of the file(s) to each other, thus relieving the central server's bandwidth burden.  Even with many simultaneous downloads, the upload burden on the central server remains quite small, since each new downloader introduces new upload capacity.""",
}

setup(**attrs)

for s in symlinks:
    if os.path.islink(s):
        os.remove(s)
