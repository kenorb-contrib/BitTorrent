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
