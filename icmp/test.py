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

import os
import socket
from socket import AF_UNIX, SOCK_STREAM
import struct
from struct import pack, unpack

def toint(s):
    return unpack("!i", s)[0]

path = "/home/dave/.bittorrent/xicmp-unix-socket"
if os.path.exists(path): 
    print "unix socket exists at ", path
else:
    print "unix socket does not exist. path=", path
    exit -1
sock = socket.socket( AF_UNIX, SOCK_STREAM, 0 );
sock.connect(path)
print "connected to ", path

while 1:
    buf = sock.recv(4)
    len = toint(buf)
    print "lenbuf=", buf
    print "len=", len
    buf = sock.recv(len)
    print "buf=", buf.encode("hex")
