# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.
#
# Written by Matt Chisholm
# Client list updated by Ed Savage-Jones - May 28th 2005

import re

v64p = '[\da-zA-Z.-]'

matches = (
           ('-AZ(?P<version>\d+)-+.+$'     , "Azureus"             ),
           ('M(?P<version>\d-\d-\d)--.+$'  , "BitTorrent"          ),
           ('T(?P<version>%s+)-+.+$'%v64p  , "BitTornado"          ),
           ('-TS(?P<version>\d+)-+.+$'     , "TorrentStorm"        ),
           ('exbc(?P<bcver>.*)LORD.+$'     , "BitLord"             ),
           ('exbc(?P<bcver>.*).+$'         , "BitComet"            ),
           ('FUTB(?P<bcver>.*).+$'         , "BitComet Mod1"       ),
           ('xUTB(?P<bcver>.*).+$'         , "BitComet Mod2"       ),
           ('A(?P<version>%s+)-+.+$'%v64p  , "ABC"                 ),
           ('S(?P<version>%s+)-+.+$'%v64p  , "Shadow's"            ),
           ('-G3.+$'                       , "G3Torrent"           ),
           ('-LT(?P<version>\d+)-+.+$'     , "libtorrent"          ),
           ('Mbrst(?P<version>\d-\d-\d).+$', "burst!"              ),
           ('eX.+$'                        , "eXeem"               ),
           ('\x00\x02BS.+$'                , "BitSpirit v2"        ),
           ('.*(?=HTTPBT$|UDP0$).+$'       , "BitSpirit"           ),
# Clients I've never actually seen in a peer list:           
           ('-BB(?P<version>\d+)-+.+$'     , "BitBuddy"            ),
           ('-CT(?P<version>\d+)-+.+$'     , "CTorrent"            ),
           ('-MT(?P<version>\d+)-+.+$'     , "MoonlightTorrent"    ),
           ('-BX(?P<version>\d+)-+.+$'     , "BitTorrent X"        ),
           ('-TN(?P<version>\d+)-+.+$'     , "TorrentDotNET"       ),
           ('-SS(?P<version>\d+)-+.+$'     , "SwarmScope"          ),
           ('-XT(?P<version>\d+)-+.+$'     , "XanTorrent"          ),
           ('U(?P<version>\d+)-+.+$'       , "UPnP NAT Bit Torrent"),
           ('-BOWP?(?P<version>\d+)-.+$'   , "Bits on Wheels"      ),
# added by Ed Savage-Jones :
           ('-AR(?P<version>\d+)-+.+$'     , "Arctic"              ),
           ('(?P<rsver>.*)BM.+$'           , "BitMagnet"           ),
           ('BG(?P<version>\d+).+$'        , "BtGetit"             ),
           ('-eX.+$'                       , "eXeem beta"          ),
           ('Plus.+$'                      , "Plus! II"            ),
           ('(?P<rsver>.*)RS.+$'           , "Rufus"               ),
           ('XBT(?P<version>\d+)-+.+$'     , "XBT"                 ),
           ('-ZT(?P<version>\d+)-+.+$'     , "ZipTorrent"          ),
# Unknown peerids
           (chr(0)*12 + '.+$'              , "\\0 * 12"            ),
           )

matches = [(re.compile(pattern, re.DOTALL), name) for pattern, name in matches]

unknown_clients = {}

def identify_client(peerid, log=None):
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
                if version.find('.') >= 0:
                    version = ''.join(version.split('.'))

                version = list(version)
                for i,c in enumerate(version):
                    if '0' <= c <= '9':
                        version[i] = c
                    elif 'A' <= c <= 'Z':
                        version[i] = str(ord(c) - 55)
                    elif 'a' <= c <= 'z':
                        version[i] = str(ord(c) - 61)
                    elif c == '.':
                        version[i] = '62'
                    elif c == '-':
                        version[i] = '63'
                    else:
                        break
                version = '.'.join(version)
            elif d.has_key('bcver'):
                bcver = d['bcver']
                version += str(ord(bcver[0])) + '.'
                version += str(ord(bcver[1])/10)
                version += str(ord(bcver[1])%10)
            elif d.has_key('rsver'):
                rsver = d['rsver']
                version += str(ord(rsver[0])) + '.'
                version += str(ord(rsver[1])/10) + '.'
                version += str(ord(rsver[1])%10)
            break
    if client == 'unknown' and log is not None:
        if not unknown_clients.has_key(peerid):
            unknown_clients[peerid] = True
            log.write('%s\n'%peerid)
            log.write('------------------------------\n')
    return client, version
