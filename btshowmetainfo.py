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

# Written by Henry 'Pi' James and Loring Holden

from sys import *
from os.path import *
from sha import *
from BitTorrent.bencode import *

NAME, EXT = splitext(basename(argv[0]))
VERSION = '20021207'

print '%s %s - decode BitTorrent metainfo files' % (NAME, VERSION)
print

if len(argv) == 1:
    print '%s file1.torrent file2.torrent file3.torrent ...' % argv[0]
    print
    exit(2) # common exit code for syntax error

for metainfo_name in argv[1:]:
    metainfo_file = open(metainfo_name, 'rb')
    metainfo = bdecode(metainfo_file.read())
    metainfo_file.close()
    announce = metainfo['announce']
    info = metainfo['info']
    info_hash = sha(bencode(info))

    print 'metainfo file.: %s' % basename(metainfo_name)
    print 'info hash.....: %s' % info_hash.hexdigest()
    piece_length = info['piece length']
    if info.has_key('length'):
        # let's assume we just have a file
        print 'file name.....: %s' % info['name']
        file_length = info['length']
        name ='file size.....:'
    else:
        # let's assume we have a directory structure
        print 'directory name: %s' % info['name']
        print 'files.........: '
        file_length = 0;
        for file in info['files']:
            path = ''
            for item in file['path']:
                if (path != ''):
                   path = path + "/"
                path = path + item
            print '   %s (%d)' % (path, file['length'])
            file_length += file['length']
        name = 'archive size..:'
    piece_number, last_piece_length = divmod(file_length, piece_length)
    print '%s %i (%i * %i + %i)' \
          % (name,file_length, piece_number, piece_length, last_piece_length)
    print 'announce url..: %s' % announce
    print
