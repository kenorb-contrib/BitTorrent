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

app_name = "BitTorrent"
from BTL.translation import _

import sys
import locale
from BitTorrent.defaultargs import get_defaults
from BitTorrent import configfile
from BitTorrent.makemetafile import make_meta_files
from BitTorrent.parseargs import parseargs, printHelp
from BitTorrent import BTFailure

defaults = get_defaults('maketorrent-console')
defaults.extend([
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
                                                    sys.argv[1:], minargs=2)

    le = locale.getpreferredencoding()

    try:
        url_list = None
        if config.get('url'):
            url_list = [config['url']]
        make_meta_files(args[0],
                        [s.decode(le) for s in args[1:]],
                        url_list=url_list,
                        progressfunc=prog,
                        filefunc=dc,
                        piece_len_pow2=config['piece_size_pow2'],
                        title=config['title'],
                        comment=config['comment'],
                        content_type=config['content_type'], # what to do in
                                                             # multifile case?
                        target=config['target'],
                        use_tracker=config['use_tracker'],
                        data_dir=config['data_dir'])
    except BTFailure, e:
        print unicode(e.args[0])
        sys.exit(1)
