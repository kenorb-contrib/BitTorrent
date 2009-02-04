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

#
#  knet.py
#  create a network of khashmir nodes
# usage: knet.py <num_nodes> <start_port> <ip_address>

from utkhashmir import UTKhashmir
from BitTorrent.RawServer_twisted import RawServer
from BitTorrent.defaultargs import common_options, rare_options
from random import randrange
from BitTorrent.stackthreading import Event
import sys, os

from krpc import KRPC
KRPC.noisy = 1

class Network:
    def __init__(self, size=0, startport=5555, localip='127.0.0.1'):
        self.num = size
        self.startport = startport
        self.localip = localip

    def _done(self, val):
        self.done = 1
        
    def simpleSetUp(self):
        #self.kfiles()
        d = dict([(x[0],x[1]) for x in common_options + rare_options])
        self.r = RawServer(Event(), d)
        self.l = []
        for i in range(self.num):
            self.l.append(UTKhashmir('', self.startport + i, 'kh%s.db' % (self.startport + i), self.r))
        
        for i in self.l:
            i.addContact(self.localip, self.l[randrange(0,self.num)].port)
            i.addContact(self.localip, self.l[randrange(0,self.num)].port)
            i.addContact(self.localip, self.l[randrange(0,self.num)].port)
            self.r.listen_once(1)
            self.r.listen_once(1)
            self.r.listen_once(1) 
            
        for i in self.l:
            self.done = 0
            i.findCloseNodes(self._done)
            while not self.done:
                self.r.listen_once(1)
        for i in self.l:
            self.done = 0
            i.findCloseNodes(self._done)
            while not self.done:
                self.r.listen_once(1)

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
    n = Network(int(sys.argv[1]), int(sys.argv[2]))
    n.simpleSetUp()
    print ">>> network ready"
    try:
        n.r.listen_forever()
    finally:
        n.tearDown()
