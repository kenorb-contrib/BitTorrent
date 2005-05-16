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

# Written by Henry 'Pi' James

import gettext
gettext.install('bittorrent', 'locale')

from sys import *
from os.path import *
from sha import *
from BitTorrent.bencode import *
from BitTorrent import version, app_name

NAME, EXT = splitext(basename(argv[0]))

print _("%s %s - change the suggested filename in a .torrent file") % (NAME,
                                                                    version)
print

if len(argv) != 3:
  print _("Usage: %s TORRENTFILE NEW_FILE_NAME") % argv[0]
  print
  exit(2) # common exit code for syntax error

metainfo_file = open(argv[1], 'rb')
metainfo = bdecode(metainfo_file.read())
metainfo_file.close()
print _("old filename: %s") % metainfo['info']['name']
metainfo['info']['name'] = argv[2]
print _("new filename: %s") % metainfo['info']['name']
metainfo_file = open(argv[1], 'wb')
metainfo_file.write(bencode(metainfo))
metainfo_file.close
print
print _("done.")
print
