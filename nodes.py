### generate a bunch of nodes that use a single contact point
usage = "usage: nodes.py <num_nodes> <bind> <start_port> <contact_ip> <contact_port>"

from BTL.translation import _

from khashmir.utkhashmir import UTKhashmir
from BitTorrent.RawServer_magic import RawServer
from BitTorrent.defaultargs import common_options, rare_options
from whrandom import randrange
from threading import Event
import sys, os

from khashmir.krpc import KRPC
KRPC.noisy = 1

class Network:
    def __init__(self, size, bind, startport, chost, cport):
        self.num = size
        self.startport = startport
        self.chost = chost
        self.cport = cport
        self.bind = bind
        
    def _done(self, val):
        self.done = 1
        
    def simpleSetUp(self):
        #self.kfiles()
        d = dict([(x[0],x[1]) for x in common_options + rare_options])
        self.r = RawServer(Event(), d)
        self.l = []
        for i in range(self.num):
            self.l.append(UTKhashmir(self.bind, self.startport + i, 'kh%s.db' % (self.startport + i), self.r))
        
        for i in self.l:
            i.addContact(self.chost, self.cport)
            self.r.listen_once(1)
            self.r.listen_once(1)            
            self.done = 0
            i.findCloseNodes(self._done)
            #while not self.done:
            #  self.r.listen_once(1)

    def tearDown(self):
        for i in self.l:
            i.rawserver.stop_listening_udp(i.socket)
            i.socket.close()
        #self.kfiles()
        
    def kfiles(self):
        for i in range(self.startport, self.startport+self.num):
            try:
                os.unlink('kh%s.db' % i)
            except:
                pass
            
        self.r.listen_once(1)
    
if __name__ == "__main__":
    if len(sys.argv) != 6:
        print usage
    else:
        n = Network(int(sys.argv[1]), sys.argv[2], int(sys.argv[3]), sys.argv[4], int(sys.argv[5]))
        n.simpleSetUp()
        print ">>> network ready"
        try:
            n.r.listen_forever()
        finally:
            n.tearDown()

