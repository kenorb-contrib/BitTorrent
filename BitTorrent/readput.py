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
    h.request('PUT', path, data)
    response = h.getresponse()
    if response.status != 200:
        raise ValueError, ('unexpected response - ' + 
            str(response.status) + ' ' + response.reason)
    return response.read()

class putqueue:
    def __init__(self, url):
        self.running = false
        self.url = url
        self.requests = []
        self.lock = Lock()

    def addrequest(self, data):
        try:
            self.lock.acquire()
            self.requests.append(data)
            if not self.running and self.requests != []:
                Thread(target = self.requestall).start()
                self.running = true
        finally:
            self.lock.release()

    def requestall(self):
        while true:
            try:
                self.lock.acquire()
                if self.requests == []:
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





