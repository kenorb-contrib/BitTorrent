# Written by Bram Cohen
# see LICENSE.txt for license information

from random import randrange
true = 1
false = 0

class Choker:
    def __init__(self, max_uploads, schedule, done = lambda: false):
        self.max_uploads = max_uploads
        self.schedule = schedule
        self.connections = []
        self.count = 0
        self.done = done
        schedule(self._round_robin, 10)
    
    def _round_robin(self):
        self.schedule(self._round_robin, 10)
        self.count += 1
        if self.count % 3 == 0:
            for i in xrange(len(self.connections)):
                u = self.connections[i].get_upload()
                if u.get_hit() or u.is_choked():
                    self.connections = self.connections[i:] + self.connections[:i]
                    break
            self._rechoke()
            for c in self.connections:
                c.get_upload().set_not_hit()
        else:
            self._rechoke()

    def _snubbed(self, c):
        if self.done():
            return false
        return c.get_download().is_snubbed()

    def _rate(self, c):
        if self.done():
            return c.get_upload().get_rate()
        else:
            return c.get_download().get_rate()

    def _rechoke(self):
        preferred = []
        for c in self.connections:
            if not self._snubbed(c) and c.get_upload().is_interested():
                preferred.append((self._rate(c), c))
        preferred.sort()
        preferred.reverse()
        del preferred[self.max_uploads - 1:]
        if self.max_uploads == 0:
            preferred = []
        preferred = [x[1] for x in preferred]
        for c in preferred:
            c.get_upload().unchoke()
        count = len(preferred)
        for c in self.connections:
            if c in preferred:
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
        else:
            self.connections.insert(p, connection)
        self._rechoke()

    def connection_lost(self, connection):
        self.connections.remove(connection)
        if not connection.get_upload().is_choked():
            self._rechoke()

    def interested(self, connection):
        if not connection.get_upload().is_choked():
            self._rechoke()

    def not_interested(self, connection):
        if not connection.get_upload().is_choked():
            self._rechoke()

class DummyScheduler:
    def __init__(self):
        self.s = []

    def __call__(self, func, delay):
        self.s.append((func, delay))

class DummyConnection:
    def __init__(self, v = 0):
        self.u = DummyUploader()
        self.d = DummyDownloader(self)
        self.v = v
    
    def get_upload(self):
        return self.u

    def get_download(self):
        return self.d

class DummyDownloader:
    def __init__(self, c):
        self.s = false
        self.c = c

    def is_snubbed(self):
        return self.s

    def get_rate(self):
        return self.c.v

class DummyUploader:
    def __init__(self):
        self.i = false
        self.c = true
        self.hit = true

    def choke(self):
        if not self.c:
            self.c = true
            self.hit = true
        
    def unchoke(self):
        if self.c:
            self.c = false
            self.hit = true

    def is_choked(self):
        return self.c

    def is_interested(self):
        return self.i

    def set_not_hit(self):
        self.hit = false

    def get_hit(self):
        return self.hit

def test_round_robin_with_no_downloads():
    s = DummyScheduler()
    Choker(2, s)
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
    choker = Choker(1, s)
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
    assert c2.u.c
    assert not c3.u.c

def test_interest():
    s = DummyScheduler()
    choker = Choker(1, s)
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
    choker = Choker(1, s)
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
    choker = Choker(1, s)
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
    choker = Choker(1, s)
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
    choker = Choker(1, s)
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
    choker = Choker(1, s)
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
    choker = Choker(1, s)
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
    
def test_multi():
    s = DummyScheduler()
    choker = Choker(4, s)
    c1 = DummyConnection(0)
    c2 = DummyConnection(0)
    c3 = DummyConnection(0)
    c4 = DummyConnection(8)
    c5 = DummyConnection(0)
    c6 = DummyConnection(0)
    c7 = DummyConnection(6)
    c8 = DummyConnection(0)
    c9 = DummyConnection(9)
    c10 = DummyConnection(7)
    c11 = DummyConnection(10)
    choker.connection_made(c1, 0)
    choker.connection_made(c2, 1)
    choker.connection_made(c3, 2)
    choker.connection_made(c4, 3)
    choker.connection_made(c5, 4)
    choker.connection_made(c6, 5)
    choker.connection_made(c7, 6)
    choker.connection_made(c8, 7)
    choker.connection_made(c9, 8)
    choker.connection_made(c10, 9)
    choker.connection_made(c11, 10)
    c2.u.i = true
    c4.u.i = true
    c6.u.i = true
    c8.u.i = true
    c10.u.i = true
    c2.d.s = true
    c6.d.s = true
    c8.d.s = true
    s.s[0][0]()
    assert not c1.u.c
    assert not c2.u.c
    assert not c3.u.c
    assert not c4.u.c
    assert not c5.u.c
    assert not c6.u.c
    assert c7.u.c
    assert c8.u.c
    assert c9.u.c
    assert not c10.u.c
    assert c11.u.c

    #uninterested
    #interested snubbed, 
    #uninterested, 
    #interested first priority, 
    #uninterested, 
    #interested snubbed, 
    #uninterested, 
    #interested third priority snubbed, 
    #uninterested zeroth priority, 
    #interested second priority
    #uninterested

