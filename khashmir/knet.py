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

from khashmir import Khashmir
from random import randrange
import sys, os

class Network:
    def __init__(self, size=0, startport=5555, localip='127.0.0.1'):
        self.num = size
        self.startport = startport
        self.localip = localip

    def _done(self, val):
        self.done = 1
        
    def setUp(self):
        self.kfiles()
        self.l = []
        for i in range(self.num):
            self.l.append(Khashmir('', self.startport + i, '/tmp/kh%s.db' % (self.startport + i)))
        reactor.iterate()
        reactor.iterate()
        
        for i in self.l:
            i.addContact(self.localip, self.l[randrange(0,self.num)].port)
            i.addContact(self.localip, self.l[randrange(0,self.num)].port)
            i.addContact(self.localip, self.l[randrange(0,self.num)].port)
            reactor.iterate()
            reactor.iterate()
            reactor.iterate() 
            
        for i in self.l:
            self.done = 0
            i.findCloseNodes(self._done)
            while not self.done:
                reactor.iterate()
        for i in self.l:
            self.done = 0
            i.findCloseNodes(self._done)
            while not self.done:
                reactor.iterate()

    def tearDown(self):
        for i in self.l:
            i.listenport.stopListening()
        self.kfiles()
        
    def kfiles(self):
        for i in range(self.startport, self.startport+self.num):
            try:
                os.unlink('/tmp/kh%s.db' % i)
            except:
                pass
            
        reactor.iterate()
    
if __name__ == "__main__":
    n = Network(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])
    n.setUp()
    try:
        reactor.run()
    finally:
        n.tearDown()
