#!/usr/bin/env python

# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bram Cohen

if __name__ == '__main__':
    from BitTorrent.platform import install_translation
    install_translation()

import sys
from BitTorrent.defaultargs import get_defaults
from BitTorrent import configfile
from BitTorrent.makemetafile import make_meta_files
from BitTorrent.parseargs import parseargs, printHelp
from BitTorrent import BTFailure

defaults = get_defaults('maketorrent-console')
defaults.extend([
    ('comment', '',
     _("optional human-readable comment to put in .torrent")),
    ('target', '',
     _("optional target file for the torrent")),
    ])

defconfig = dict([(name, value) for (name, value, doc) in defaults])
del name, value, doc

def dc(v):
    print v

def prog(amount):
    print '%.1f%% complete\r' % (amount * 100),

if __name__ == '__main__':
    config, args = configfile.parse_configuration_and_args(defaults,
                                                           'maketorrent-console',
                                                           sys.argv[1:],
                                                           0, None)

    if len(sys.argv) <= 1:
        printHelp('maketorrent-console', defaults)
    else:
        try:
            make_meta_files(args[0],
                            args[1:],
                            progressfunc=prog,
                            filefunc=dc,
                            piece_len_pow2=config['piece_size_pow2'],
                            comment=config['comment'],
                            target=config['target'],
                            filesystem_encoding=config['filesystem_encoding'],
                            use_tracker=config['use_tracker'],
                            data_dir=config['data_dir'])
        except BTFailure, e:
            print str(e)
            sys.exit(1)
