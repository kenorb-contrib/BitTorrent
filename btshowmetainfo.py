#!/usr/bin/env python2

# Written by Henry 'Pi' James
# see LICENSE.txt for license information

from sys import *
from os.path import *
from sha import *
from BitTorrent.bencode import *

NAME, EXT = splitext(basename(argv[0]))
VERSION = '20021110'

print '%s %s - show the metainfo in .torrent files' % (NAME, VERSION)
print

if len(argv) == 1:
  print '%s file1.torrent file2.torrent file3.torrent ...' % argv[0]
  print
  exit(2) # common exit code for syntax error

for metainfo_name in argv[1:]:
  metainfo_file = open(metainfo_name)
  metainfo = bdecode(metainfo_file.read())
  announce = metainfo['announce']
  info = metainfo['info']
  info_hash = sha(bencode(info))
  file_length = info['length']
  piece_length = info['piece length']
  piece_count, last_piece_length = divmod(file_length, piece_length)

  print 'metainfo file: %s' % basename(metainfo_name)
  print 'info hash....: %s' % info_hash.hexdigest()
  print 'file name....: %s' % info['name']
  print 'file size....: %i (%i * %i + %i)' \
    % (file_length, piece_count, piece_length, last_piece_length)
  print 'announce url.: %s' % announce
  print
