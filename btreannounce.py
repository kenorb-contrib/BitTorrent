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

# Written by Henry 'Pi' James and Bram Cohen

from sys import argv
from BitTorrent.bencode import bencode, bdecode

if len(argv) < 3:
    print '%s http://new.uri:port/announce file1.torrent file2.torrent' % argv[0]
    print
    exit(2) # common exit code for syntax error

for f in argv[2:]:
    h = open(f, 'rb')
    metainfo = bdecode(h.read())
    h.close()
    if metainfo['announce'] != argv[1]:
        print 'old announce for %s: %s' % (f, metainfo['announce'])
        metainfo['announce'] = argv[1]
        h = open(f, 'wb')
        h.write(bencode(metainfo))
        h.close()
