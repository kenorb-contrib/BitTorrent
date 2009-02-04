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

# Written by Greg Hazel

import os
import sys
from setuptools import setup
from BitTorrent import version
from BitTorrent.platform import calc_unix_dirs

import glob

img_root = './images/'

data_files = [
    ('.', ['BTL/addrmap.dat', 'credits.txt', 'LICENSE.txt', 'README.txt',
           'TRACKERLESS.txt', 'redirdonate.html', 'public.key',
           'INSTALL.unix.txt', ] ),
    (img_root, ['images/bittorrent.ico',]),
    ]

for d in ('flags', 'logo', 'themes/default',
          'themes/default/statuslight', 'themes/default/torrentstate',
          'themes/default/torrentops' , 'themes/default/fileops'     ,):
    data_files.append(
        (os.path.join(img_root, d),
         glob.glob(os.path.join('images', d, '*.png')) +
	 glob.glob(os.path.join('images', d, '*.gif'))
	 )
        )

attrs = {
    'name' : "BitTorrent",
    'version' : version,
    'author' : "Bram Cohen",
    'author_email' : "bugs@bittorrent.com",
    'url' : "http://bittorrent.com/",
    'license' : "GNU Public License version 3",
    'packages' : ["BTL", "BitTorrent", "khashmir", "BitTorrent.GUI_wx",],
    'package_dir' : {"BTL": "BTL"},
    'package_data' : {"BTL": ["*.dat"]},
    'py_modules' : ["Zeroconf",],
    'data_files' : data_files,
    'description' : "Scatter-gather network file transfer",
    'long_description' : """BitTorrent is a tool for distributing files.  It's extremely easy to use - downloads are started by clicking on hyperlinks.  Whenever more than one person is downloading at once they send pieces of the file(s) to each other, thus relieving the central server's bandwidth burden.  Even with many simultaneous downloads, the upload burden on the central server remains quite small, since each new downloader introduces new upload capacity.""",

    'app' : ['bittorrent.py'],
    'options' : {'py2app': {'argv_emulation': True,
                            'optimize': 2,
                            'iconfile': os.path.abspath('./images/logo/bittorrent_icon.icns')}},
    'setup_requires' : ['py2app'],

}

setup(**attrs)

import shutil
from BitTorrent.NewVersion import Version

currentversion = Version.from_str(version)
version_str = version
if currentversion.is_beta():
    version_str = version_str + '-Beta'
d = 'BitTorrent-%s' % version_str
try:
    shutil.rmtree(d)
except OSError:
    pass
os.rename('dist', d)
try:
    os.remove('%s.dmg' % d)
except OSError:
    pass
os.system('sh makedmg.sh %s' % d)
