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

### generate a bunch of nodes that use a single contact point
usage = "usage: inserter.py <contact host> <contact port>"

from utkhashmir import UTKhashmir
from BitTorrent.RawServer_twisted import RawServer
from BitTorrent.defaultargs import common_options, rare_options
from khashmir.khash import newID
from random import randrange
from BitTorrent.stackthreading import Event
import sys, os

from khashmir.krpc import KRPC
KRPC.noisy = 1
done = 0
def d(n):
    global done
    done = done+1
    
if __name__=="__main__":
    host, port = sys.argv[1:]
    x = UTKhashmir("", 22038, "/tmp/cgcgcgc")
    x.addContact(host, int(port))
    x.rawserver.listen_once()
    x.findCloseNodes(d)
    while not done:
        x.rawserver.listen_once()
    l = []
    for i in range(10):
        k = newID()
        v = randrange(10000,20000)
        l.append((k, v))
        x.announcePeer(k, v, d)
    done = 1
    while done < 10:
        x.rawserver.listen_once(1)
    for k,v in l:
        print ">>>", `k`, v
