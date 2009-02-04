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

from BTL.translation import _

from BitTorrent import BTFailure

ints = (long, int)


def check_peers(message):
    if type(message) != dict:
        raise BTFailure
    if message.has_key('failure reason'):
        if type(message['failure reason']) != str:
            raise BTFailure, _("failure reason must be a string")
        return
    if message.has_key('warning message'):
        if type(message['warning message']) != str:
            raise BTFailure, _("warning message must be a string")
    peers = message.get('peers')
    if type(peers) == list:
        for p in peers:
            if type(p) != dict:
                raise BTFailure, _("invalid entry in peer list - peer info must be a dict")
            if type(p.get('ip')) != str:
                raise BTFailure, _("invalid entry in peer list - peer ip must be a string")
            port = p.get('port')
            if type(port) not in ints or p <= 0:
                raise BTFailure, _("invalid entry in peer list - peer port must be an integer")
            if p.has_key('peer id'):
                peerid = p.get('peer id')
                if type(peerid) != str or len(peerid) != 20:
                    raise BTFailure, _("invalid entry in peer list - invalid peerid")
    elif type(peers) != str or len(peers) % 6 != 0:
        raise BTFailure, _("invalid peer list")
    interval = message.get('interval', 1)
    if type(interval) not in ints or interval <= 0:
        raise BTFailure, _("invalid announce interval")
    minint = message.get('min interval', 1)
    if type(minint) not in ints or minint <= 0:
        raise BTFailure, _("invalid min announce interval")
    if type(message.get('tracker id', '')) != str:
        raise BTFailure, _("invalid tracker id")
    npeers = message.get('num peers', 0)
    if type(npeers) not in ints or npeers < 0:
        raise BTFailure, _("invalid peer count")
    dpeers = message.get('done peers', 0)
    if type(dpeers) not in ints or dpeers < 0:
        raise BTFailure, _("invalid seed count")
    last = message.get('last', 0)
    if type(last) not in ints or last < 0:
        raise BTFailure, _('invalid "last" entry')
