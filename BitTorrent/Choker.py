# Written by Bram Cohen
# see LICENSE.txt for license information

from random import randrange
from bisect import insort
true = 1
false = 0

class Choker:
    def __init__(self, max_uploads, schedule, measurefunc):
        self.max_uploads = max_uploads
        self.schedule = schedule
        self.measurefunc = measurefunc
        self.connections = []
        self.preforder = []
        self.count = 0
        self.interrupted = false
        schedule(self.round_robin, 10)
    
    def round_robin(self):
        self.schedule(self.round_robin, 10)
        self.count += 1
        if self.count % 3 == 0:
            if not self.interrupted and self.connections != []:
                x = self.connections[0]
                del self.connections[0]
                self.connections.append(x)
            self.interrupted = false
        self.preforder = [(-self.measurefunc(x), x) for x in self.connections]
        self.preforder.sort()
        self.rechoke()
    
    def rechoke(self):
        if self.connections == []:
            return
        count = 0
        for garbage, c in [(0, self.connections[0])] + self.preforder:
            if c == self.connections[0] and count > 0:
                continue
            u = c.get_upload()
            if count < self.max_uploads:
                u.unchoke()
                if u.is_interested():
                    count += 1
            else:
                u.choke()

    def connection_made(self, connection, p = None):
        if p is None:
            p = randrange(-2, len(self.connections) + 1)
        if p <= 0:
            self.connections.insert(0, connection)
            self.interrupted = true
        else:
            self.connections.insert(p, connection)
        insort(self.preforder, (-self.measurefunc(connection), connection))
        self.rechoke()

    def connection_lost(self, connection):
        if self.connections[0] == connection:
            self.interrupted = true
        self.connections.remove(connection)
        for i in xrange(len(self.preforder)):
            if self.preforder[i][1] == connection:
                del self.preforder[i]
                break
        self.rechoke()

    def interested(self, connection):
        if not connection.get_upload().is_choked():
            self.rechoke()

    def not_interested(self, connection):
        if not connection.get_upload().is_choked():
            self.rechoke()

class DummyScheduler:
    def __init__(self):
        self.s = []

    def __call__(self, func, delay):
        self.s.append((func, delay))

class DummyConnection:
    def __init__(self, v = 0):
        self.v = v
        self.u = DummyUploader()
    
    def get_upload(self):
        return self.u

def dummymeasure(c):
    return c.v

class DummyUploader:
    def __init__(self):
        self.i = false
        self.c = true

    def choke(self):
        self.c = true
        
    def unchoke(self):
        self.c = false

    def is_choked(self):
        return self.c

    def is_interested(self):
        return self.i

def test_round_robin_with_no_downloads():
    s = DummyScheduler()
    choker = Choker(2, s, dummymeasure)
    assert len(s.s) == 1
    assert s.s[0][1] == 10
    s.s[0][0]()
    del s.s[0]
    assert len(s.s) == 1
    assert s.s[0][1] == 10
    s.s[0][0]()
    del s.s[0]
    s.s[0][0]()
    del s.s[0]
    s.s[0][0]()
    del s.s[0]

def test_resort():
    s = DummyScheduler()
    choker = Choker(1, s, dummymeasure)
    c1 = DummyConnection()
    c2 = DummyConnection(1)
    c3 = DummyConnection(2)
    c4 = DummyConnection(3)
    c2.u.i = true
    c3.u.i = true
    choker.connection_made(c1)
    assert not c1.u.c
    choker.connection_made(c2, 1)
    assert not c1.u.c
    assert not c2.u.c
    choker.connection_made(c3, 1)
    assert not c1.u.c
    assert c2.u.c
    assert not c3.u.c
    c2.v = 2
    c3.v = 1
    choker.connection_made(c4, 1)
    assert not c1.u.c
    assert c2.u.c
    assert not c3.u.c
    assert not c4.u.c
    choker.connection_lost(c4)
    assert not c1.u.c
    assert c2.u.c
    assert not c3.u.c
    s.s[0][0]()
    assert not c1.u.c
    assert not c2.u.c
    assert c3.u.c

def test_interest():
    s = DummyScheduler()
    choker = Choker(1, s, dummymeasure)
    c1 = DummyConnection()
    c2 = DummyConnection(1)
    c3 = DummyConnection(2)
    c2.u.i = true
    c3.u.i = true
    choker.connection_made(c1)
    assert not c1.u.c
    choker.connection_made(c2, 1)
    assert not c1.u.c
    assert not c2.u.c
    choker.connection_made(c3, 1)
    assert not c1.u.c
    assert c2.u.c
    assert not c3.u.c
    c3.u.i = false
    choker.not_interested(c3)
    assert not c1.u.c
    assert not c2.u.c
    assert not c3.u.c
    c3.u.i = true
    choker.interested(c3)
    assert not c1.u.c
    assert c2.u.c
    assert not c3.u.c
    choker.connection_lost(c3)
    assert not c1.u.c
    assert not c2.u.c

def test_robin_interest():
    s = DummyScheduler()
    choker = Choker(1, s, dummymeasure)
    c1 = DummyConnection(0)
    c2 = DummyConnection(1)
    c1.u.i = true
    choker.connection_made(c2)
    assert not c2.u.c
    choker.connection_made(c1, 0)
    assert not c1.u.c
    assert c2.u.c
    c1.u.i = false
    choker.not_interested(c1)
    assert not c1.u.c
    assert not c2.u.c
    c1.u.i = true
    choker.interested(c1)
    assert not c1.u.c
    assert c2.u.c
    choker.connection_lost(c1)
    assert not c2.u.c

def test_interrupt_by_connection_lost():
    s = DummyScheduler()
    choker = Choker(1, s, dummymeasure)
    c1 = DummyConnection(0)
    c2 = DummyConnection(1)
    c3 = DummyConnection(2)
    c1.u.i = true
    c2.u.i = true
    c3.u.i = true
    choker.connection_made(c1)
    choker.connection_made(c2, 1)
    choker.connection_made(c3, 2)
    f = s.s[0][0]
    f()
    assert not c1.u.c
    assert c2.u.c
    assert c3.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    assert c3.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    assert c3.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    assert c3.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    assert c3.u.c
    choker.connection_lost(c1)
    assert not c2.u.c
    assert c3.u.c
    f()
    assert not c2.u.c
    assert c3.u.c

def test_connection_lost_no_interrupt():
    s = DummyScheduler()
    choker = Choker(1, s, dummymeasure)
    c1 = DummyConnection(0)
    c2 = DummyConnection(1)
    c3 = DummyConnection(2)
    c1.u.i = true
    c2.u.i = true
    c3.u.i = true
    choker.connection_made(c1)
    choker.connection_made(c2, 1)
    choker.connection_made(c3, 2)
    f = s.s[0][0]
    f()
    assert not c1.u.c
    assert c2.u.c
    assert c3.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    assert c3.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    assert c3.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    assert c3.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    assert c3.u.c
    choker.connection_lost(c2)
    assert not c1.u.c
    assert c3.u.c
    f()
    assert c1.u.c
    assert not c3.u.c

def test_interrupt_by_connection_made():
    s = DummyScheduler()
    choker = Choker(1, s, dummymeasure)
    c1 = DummyConnection(0)
    c2 = DummyConnection(1)
    c3 = DummyConnection(2)
    c1.u.i = true
    c2.u.i = true
    c3.u.i = true
    choker.connection_made(c1)
    choker.connection_made(c2, 1)
    f = s.s[0][0]
    f()
    assert not c1.u.c
    assert c2.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    choker.connection_made(c3, 0)
    assert c1.u.c
    assert c2.u.c
    assert not c3.u.c
    f()
    assert c1.u.c
    assert c2.u.c
    assert not c3.u.c

def test_connection_made_no_interrupt():
    s = DummyScheduler()
    choker = Choker(1, s, dummymeasure)
    c1 = DummyConnection(0)
    c2 = DummyConnection(1)
    c3 = DummyConnection(2)
    c1.u.i = true
    c2.u.i = true
    c3.u.i = true
    choker.connection_made(c1)
    choker.connection_made(c2, 1)
    f = s.s[0][0]
    f()
    assert not c1.u.c
    assert c2.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    choker.connection_made(c3, 1)
    assert not c1.u.c
    assert c2.u.c
    assert c3.u.c
    f()
    assert c1.u.c
    assert c2.u.c
    assert not c3.u.c

def test_round_robin():
    s = DummyScheduler()
    choker = Choker(1, s, dummymeasure)
    c1 = DummyConnection(0)
    c2 = DummyConnection(1)
    c1.u.i = true
    c2.u.i = true
    choker.connection_made(c1)
    choker.connection_made(c2, 1)
    f = s.s[0][0]
    f()
    assert not c1.u.c
    assert c2.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    f()
    assert c1.u.c
    assert not c2.u.c
    f()
    assert c1.u.c
    assert not c2.u.c
    f()
    assert c1.u.c
    assert not c2.u.c
    f()
    assert not c1.u.c
    assert c2.u.c
    
    
    pass
    #make a max limit of 1
    #assert alternates between two connections
