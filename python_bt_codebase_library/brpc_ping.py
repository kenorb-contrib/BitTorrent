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
import time
import socket
import pycurl
import urlparse
from BTL.brpclib import ServerProxy
from BTL.platform import bttime

s = sys.argv[1]
scheme, host, j,j,j = urlparse.urlsplit(s)
if ':' in host:
    host, port = host.split(':', 1)
elif scheme == 'http':
    port = 80
elif scheme == 'https':
    port = 443
ip = socket.gethostbyname(host)
print "BRPC Pinging %s [%s] with 32 bytes of data:" % (s, ip)
s = ServerProxy(s)
n = 4
if len(sys.argv) > 2:
    n = int(sys.argv[2])
for i in xrange(n):
    start = bttime()
    try:
        r = s.ping('*' * 32)
    except pycurl.error, e:
        if e[0] == 28:
            print "Request timed out."
        else:
            raise
    except:
        raise
    else:
        b = len(r[0])
        t = bttime() - start
        t *= 1000
        t = int(t)
        print "Reply from %s: bytes=%s time=%sms" % (ip, b, t)
    time.sleep(1)
