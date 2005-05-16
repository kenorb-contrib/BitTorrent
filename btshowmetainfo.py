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

# Written by Henry 'Pi' James and Loring Holden

import gettext
gettext.install('bittorrent', 'locale')

from sys import *
from os.path import *
from sha import *
from BitTorrent.bencode import *
from BitTorrent import version, app_name

NAME, EXT = splitext(basename(argv[0]))

print _("%s %s - decode %s metainfo files") % (NAME, version, app_name)
print 

if len(argv) == 1:
    print _("Usage: %s [TORRENTFILE [TORRENTFILE ... ] ]") % argv[0]
    print
    exit(2) # common exit code for syntax error

for metainfo_name in argv[1:]:
    metainfo_file = open(metainfo_name, 'rb')
    metainfo = bdecode(metainfo_file.read())
    metainfo_file.close()
    announce = metainfo['announce']
    info = metainfo['info']
    info_hash = sha(bencode(info))

    print _("metainfo file.: %s") % basename(metainfo_name)
    print _("info hash.....: %s") % info_hash.hexdigest()
    piece_length = info['piece length']
    if info.has_key('length'):
        # let's assume we just have a file
        print _("file name.....: %s") % info['name']
        file_length = info['length']
        name = _("file size.....:")
    else:
        # let's assume we have a directory structure
        print _("directory name: %s") % info['name']
        print _("files.........: ")
        file_length = 0;
        for file in info['files']:
            path = ''
            for item in file['path']:
                if (path != ''):
                   path = path + "/"
                path = path + item
            print '   %s (%d)' % (path, file['length'])
            file_length += file['length']
        name = _("archive size..:")
    piece_number, last_piece_length = divmod(file_length, piece_length)
    print '%s %i (%i * %i + %i)' \
          % (name,file_length, piece_number, piece_length, last_piece_length)
    print _("announce url..: %s") % announce
    print _("comment.......: \n")
    if metainfo.has_key('comment'):
        print metainfo['comment']
        print
