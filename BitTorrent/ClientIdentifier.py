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

import re

matches = (
           ('-AZ(?P<version>\d+)-+.+$'     , "Azureus"             ),
           ('M(?P<version>\d-\d-\d)--.+$'  , "BitTorrent"          ),
           ('T(?P<version>\d+)-+.+$'       , "BitTornado"          ),
           ('-TS(?P<version>\d+)-+.+$'     , "TorrentStorm"        ),
           ('S(?P<version>\d+[\dAB])-+.+$' , "Shadow's"            ),
           ('A(?P<version>\d+)-+.+$'       , "ABC"                 ),
           ('-G3.+$'                       , "G3Torrent"           ),
           ('exbc.+$'                      , "BitComet"            ),
           ('-LT(?P<version>\d+)-+.+$'     , "libtorrent"          ),
           ('Mbrst(?P<version>\d-\d-\d).+$', "burst!"              ),
           ('-BB(?P<version>\d+)-+.+$'     , "BitBuddy"            ),
           ('-CT(?P<version>\d+)-+.+$'     , "CTorrent"            ),
           ('-MT(?P<version>\d+)-+.+$'     , "MoonlightTorrent"    ),
           ('-BX(?P<version>\d+)-+.+$'     , "BitTorrent X"        ),
           ('-TN(?P<version>\d+)-+.+$'     , "TorrentDotNET"       ),
           ('-SS(?P<version>\d+)-+.+$'     , "SwarmScope"          ),
           ('-XT(?P<version>\d+)-+.+$'     , "XanTorrent"          ),
           ('U(?P<version>\d+)-+.+$'       , "UPnP NAT Bit Torrent"),
           )

matches = [(re.compile(pattern, re.DOTALL), name) for pattern, name in matches]

def identify_client(peerid):
    client = 'unknown'
    version = ''
    for pat, name in matches:
        m = pat.match(peerid)
        if m:
            client = name
            d = m.groupdict()
            if d.has_key('version'):
                version = d['version']
                version = version.replace('-','.')
                if version.find('.') == -1:
                    version = '.'.join(version)
            break
    return client, version
