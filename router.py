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

from BTL.translation import _

from khashmir. khashmir import KhashmirBase
from khashmir import krpc
import sys
import thread

krpc.KRPC.noisy = 0

class Router(KhashmirBase):
    def krpc_get_peers(self, info_hash, id, _krpc_sender):
        return self.krpc_find_node(info_hash, id, _krpc_sender)
    
def go(host, port, data_dir):
    k = Router(host, port, data_dir, max_ul_rate=0)
    thread.start_new_thread(k.rawserver.listen_forever, ())
    return k

if __name__=="__main__":
    r = 0
    if len(sys.argv) not in [4, 5]:
        print "Usage %s <bind> <port> <data_dir> | <max_ul_rate>" % sys.argv[0]
        sys.exit(1)
    if len(sys.argv) == 5:
        r = int(sys.argv[4])
    k = Router(sys.argv[1], int(sys.argv[2]), sys.argv[3], max_ul_rate=r)
    k.rawserver.listen_forever()

