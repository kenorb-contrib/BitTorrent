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

# Written by Henry 'Pi' James

from sys import *
from os.path import *
from sha import *
from BitTorrent.bencode import *

NAME, EXT = splitext(basename(argv[0]))
VERSION = '20021119'

print '%s %s - change the suggested filename in a .torrent file' % (NAME, VERSION)
print

if len(argv) != 3:
  print '%s file.torrent new.filename.ext' % argv[0]
  print
  exit(2) # common exit code for syntax error

metainfo_file = open(argv[1], 'rb')
metainfo = bdecode(metainfo_file.read())
metainfo_file.close()
print 'old filename: %s' % metainfo['info']['name']
metainfo['info']['name'] = argv[2]
print 'new filename: %s' % metainfo['info']['name']
metainfo_file = open(argv[1], 'wb')
metainfo_file.write(bencode(metainfo))
metainfo_file.close
print
print 'done.'
print
