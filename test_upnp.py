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

import sys
from BitTorrent.RawServer_twisted import RawServer, Handler
from BTL.greenlet_yielddefer import coroutine, like_yield
from BitTorrent.NatTraversal import *

nat_logger.setLevel(logging.DEBUG)

def print_list(list):
    print "Currently mapped ports:", len(list)
    for mapping in list:
        print mapping

@coroutine
def run_tests(internal_port):
    list = like_yield(nattraverser.list_ports())
    print_list(list)

    df = nattraverser.register_port(internal_port, internal_port, "TCP")
    external_port = like_yield(df)
    print "Mapped:", external_port

    list = like_yield(nattraverser.list_ports())
    print_list(list)

    # synchronous
    nattraverser.unregister_port(external_port, "TCP")
    
    list = like_yield(nattraverser.list_ports())
    print_list(list)


if __name__ == "__main__":
    rawserver = RawServer({'upnp': True})
    nattraverser = NatTraverser(rawserver)

    port = 6881
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
        
    df = run_tests(port)
    def error(f):
        print f
    df.addErrback(error)
    df.addBoth(lambda r: rawserver.stop())
    rawserver.listen_forever()
