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
