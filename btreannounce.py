#!/usr/bin/env python2

# Written by Henry 'Pi' James
# see LICENSE.txt for license information

from sys import *
from os.path import *
from sha import *
from BitTorrent.bencode import *

NAME, EXT = splitext(basename(argv[0]))
VERSION = '20021119'

print '%s %s - change the annoucement URI in a .torrent file' % (NAME, VERSION)
print

if len(argv) != 3:
  print '%s file.torrent http://new.uri:port/announce' % argv[0]
  print
  exit(2) # common exit code for syntax error

metainfo_file = open(argv[1])
metainfo = bdecode(metainfo_file.read())
metainfo_file.close()
print 'old announce: %s' % metainfo['announce']
metainfo['announce'] = argv[2]
print 'new announce: %s' % metainfo['announce']
metainfo_file = open(argv[1], 'w')
metainfo_file.write(bencode(metainfo))
metainfo_file.close
print
print 'done.'
print
