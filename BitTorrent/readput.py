# written by Bram Cohen
# see LICENSE.txt for license information

from httplib import HTTPConnection, HTTPSConnection
from urlparse import urlparse
from threading import Thread, Lock
from traceback import print_exc
true = 1
false = 0

def readput(url, data):
    protocol, host, path, g1, g2, g3 = urlparse(url)
    if protocol == 'http':
        h = HTTPConnection(host)
    elif protocol == 'https':
        h = HTTPSConnection(host)
    else:
        raise ValueError, "can't handle protocol '" + protocol + "'"
    h.putrequest('PUT', path)
    h.putheader('content-length', str(len(data)))
    h.endheaders()
    h.send(data)
    reply, message, headers = h.getreply()
    if reply != 200:
        raise ValueError, 'unexpected response - ' + str(reply)
    f = h.getfile()
    r = f.read(int(headers.getheader('content-length')))
    f.close()
    return r

class putqueue:
    def __init__(self, url):
        self.running = false
        self.url = url
        self.requests = []
        self.lock = Lock()

    def addrequest(self, data):
        try:
            self.lock.acquire()
            if len(self.requests) == 0 and not self.running:
                Thread(target = self.requestall).start()
                self.running = true
            self.requests.append(data)
        finally:
            self.lock.release()

    def requestall(self):
        while true:
            try:
                self.lock.acquire()
                if len(self.requests) == 0:
                    self.running = false
                    return
                data = self.requests[0]
                del self.requests[0]
            finally:
                self.lock.release()
            try:
                readput(self.url, data)
            except:
                print_exc()





