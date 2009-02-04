import sys
import time
import socket
import pycurl
import urlparse
from BTL.ebrpclib import ServerProxy
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
print "EBRPC Pinging %s [%s] with 32 bytes of data:" % (s, ip)
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
