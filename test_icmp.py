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


# NOTE: RawServer provides only server-side support for UNIX sockets.
# Thus we implement the server-side of the UNIX socket is in Python
# while the client-side is implemented in C++.  We thus spawn
# the C++ program only after creating the server-side socket.

if __name__ == "__main__":
    app_name = "BitTorrent"

from BTL.translation import _
import sys
import os
print "After import translation"
sys.stdout.flush()

#from icmp import icmp
from BitTorrent.RawServer_twisted import RawServer
from BTL.defer import DeferredEvent
from BitTorrent import configfile
from BitTorrent.defaultargs import get_defaults
from icmp import IcmpIPC

print "After imports"
sys.stdout.flush()


def message_dump(data):
    print "Received: ", data.encode("hex")

def shutdown():
    print "shutdown."
    rawserver.stop()

if __name__ == "__main__":
    print "test2"
    sys.stdout.flush()
    uiname = "bittorrent-console"
    defaults = get_defaults(uiname)
    config, args = configfile.parse_configuration_and_args(defaults,
                                       uiname, sys.argv[1:], 0, 1)
    
    core_doneflag = DeferredEvent()
    rawserver = RawServer(config)
    core_doneflag.addCallback(
            lambda r: rawserver.external_add_task(0, shutdown))
    rawserver.install_sigint_handler(core_doneflag)

    print "Creating IcmpIPC"
    icmp = IcmpIPC(rawserver)
    icmp.create()
    print "Starting IcmpIPC"
    icmp.start(message_dump)
    rawserver.listen_forever()
    
