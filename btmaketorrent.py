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

# Written by Bram Cohen

import sys
from BitTorrent.makemetafile import make_meta_files
from BitTorrent.parseargs import parseargs, printHelp
from BitTorrent import BTFailure

defaults = [
    ('piece_size_pow2', 18,
        "which power of 2 to set the piece size to"),
    ('comment', '',
        "optional human-readable comment to put in .torrent"),
    ('target', '',
        "optional target file for the torrent"),
    ('filesystem_encoding', '',
     "character encoding used on the local filesystem. If left empty, autodetected. Autodetection doesn't work under python versions older than 2.3.")
    ]


def dc(v):
    print v

def prog(amount):
    print '%.1f%% complete\r' % (amount * 100),

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        printHelp('btmaketorrent', defaults)
    else:
        try:
            config, args = parseargs(sys.argv[1:], defaults, 2, None)
            make_meta_files(args[0], args[1:], piece_len_pow2=config['piece_size_pow2'], progressfunc=prog, filefunc=dc, comment=config['comment'], target=config['target'], filesystem_encoding=config['filesystem_encoding'])
        except BTFailure, e:
            print str(e)
            sys.exit(1)
