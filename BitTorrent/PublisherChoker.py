# written by Bram Cohen
# this file is public domain

from random import randrange
true = 1
false = 0

class Choker:
    def __init__(self, max_uploads, schedule, interval, measurefunc, rand = true):
        self.max_uploads = max_uploads
        self.schedule = schedule
        self.interval = interval
        self.measurefunc = measurefunc
        self.rand = rand
        self.connections = []
        schedule(self.round_robin, interval)
    
    def round_robin(self):
        self.schedule(self.round_robin, self.interval)
        min = 1000000000
        minc = None
        for c in self.connections:
            n = self.measurefunc(c)
            if not c.is_choked() and c.is_interested() and n < min:
                min = n
                minc = c
        if minc is not None:
            self.connections.remove(minc)
            self.connections.append(minc)
            self.rechoke()
    
    def rechoke(self):
        count = 0
        for c in self.connections:
            if count < self.max_uploads:
                if c.is_choked():
                    c.unchoke()
                if c.is_interested():
                    count += 1
            else:
                if not c.is_choked():
                    c.choke()

    def connection_made(self, connection):
        if self.rand:
            self.connections.insert(randrange(len(self.connections)), connection)
        else:
            self.connections.append(connection)
        self.rechoke()

    def connection_lost(self, connection):
        self.connections.remove(connection)
        self.rechoke()

    def interested(self, connection):
        self.rechoke()

    def not_interested(self, connection):
        self.rechoke()

class DummyScheduler:
    def __init__(self):
        self.s = []

    def schedule(self, func, delay):
        self.s.append((func, delay))

class DummyConnection:
    def __init__(self):
        self.interested = false
        self.choked = false
        self.v = 0.
        
    def choke(self):
        self.choked = true
        
    def unchoke(self):
        self.choked = false
        
    def is_choked(self):
        return self.choked
        
    def is_interested(self):
        return self.interested

def test_round_robin_with_no_downloads():
    s = DummyScheduler()
    ch = Choker(2, s.schedule, 3, lambda x: 0, false)
    assert s.s == [(ch.round_robin, 3)]
    c1 = DummyConnection()
    c2 = DummyConnection()
    ch.connection_made(c1)
    ch.connection_made(c2)
    del s.s[:]
    ch.round_robin()
    assert s.s == [(ch.round_robin, 3)]
    assert not c1.choked
    assert not c2.choked

def test_choke_after_hits_max():
    s = DummyScheduler()
    ch = Choker(1, s.schedule, 3, lambda x: 0, false)
    assert s.s == [(ch.round_robin, 3)]
    c1 = DummyConnection()
    c2 = DummyConnection()
    c3 = DummyConnection()
    ch.connection_made(c1)
    ch.connection_made(c2)
    ch.connection_made(c3)

    c2.interested = true
    ch.interested(c2)
    assert not c1.choked
    assert not c2.choked
    assert c3.choked

def test_unchokes_after_lost_interest():
    s = DummyScheduler()
    ch = Choker(1, s.schedule, 3, lambda x: 0, false)
    assert s.s == [(ch.round_robin, 3)]
    c1 = DummyConnection()
    c2 = DummyConnection()
    ch.connection_made(c1)
    ch.connection_made(c2)

    c1.interested = true
    ch.interested(c1)
    assert not c1.choked
    assert c2.choked

    c1.interested = false
    ch.not_interested(c1)
    assert not c1.choked
    assert not c2.choked

def test_interrupt():
    s = DummyScheduler()
    ch = Choker(1, s.schedule, 3, lambda x: 0, false)
    assert s.s == [(ch.round_robin, 3)]
    c1 = DummyConnection()
    c2 = DummyConnection()
    ch.connection_made(c1)
    ch.connection_made(c2)

    c2.interested = true
    ch.interested(c2)
    assert not c1.choked
    assert not c2.choked

    c1.interested = true
    ch.interested(c1)
    assert not c1.choked
    assert c2.choked

def test_choke_at_start():
    s = DummyScheduler()
    ch = Choker(1, s.schedule, 3, lambda x: 0, false)
    assert s.s == [(ch.round_robin, 3)]
    c1 = DummyConnection()
    ch.connection_made(c1)

    c1.interested = true
    ch.interested(c1)
    assert not c1.choked

    c2 = DummyConnection()
    ch.connection_made(c2)
    assert not c1.choked
    assert c2.choked

def test_measurefunc():
    s = DummyScheduler()
    ch = Choker(2, s.schedule, 3, lambda x: x.v, false)
    assert s.s == [(ch.round_robin, 3)]
    c1 = DummyConnection()
    c2 = DummyConnection()
    c3 = DummyConnection()
    c4 = DummyConnection()
    c5 = DummyConnection()
    ch.connection_made(c1)
    ch.connection_made(c2)
    ch.connection_made(c3)
    ch.connection_made(c4)
    ch.connection_made(c5)

    c2.v = 1

    c2.interested = true
    ch.interested(c2)
    assert not c1.choked
    assert not c2.choked
    assert not c3.choked
    assert not c4.choked
    assert not c5.choked

    c4.interested = true
    ch.interested(c4)
    assert not c1.choked
    assert not c2.choked
    assert not c3.choked
    assert not c4.choked
    assert c5.choked

    ch.round_robin()
    assert not c1.choked
    assert not c2.choked
    assert not c3.choked
    assert not c4.choked
    assert not c5.choked

    c5.interested = true
    ch.interested(c5)
    assert not c1.choked
    assert not c2.choked
    assert not c3.choked
    assert c4.choked
    assert not c5.choked

def test_measurefunc2():
    s = DummyScheduler()
    ch = Choker(2, s.schedule, 3, lambda x: x.v, false)
    assert s.s == [(ch.round_robin, 3)]
    c1 = DummyConnection()
    c2 = DummyConnection()
    c3 = DummyConnection()
    c4 = DummyConnection()
    c5 = DummyConnection()
    ch.connection_made(c1)
    ch.connection_made(c2)
    ch.connection_made(c3)
    ch.connection_made(c4)
    ch.connection_made(c5)

    c4.v = 1

    c2.interested = true
    ch.interested(c2)
    assert not c1.choked
    assert not c2.choked
    assert not c3.choked
    assert not c4.choked
    assert not c5.choked

    c4.interested = true
    ch.interested(c4)
    assert not c1.choked
    assert not c2.choked
    assert not c3.choked
    assert not c4.choked
    assert c5.choked

    ch.round_robin()
    assert not c1.choked
    assert not c2.choked
    assert not c3.choked
    assert not c4.choked
    assert not c5.choked

    c5.interested = true
    ch.interested(c5)
    assert not c1.choked
    assert c2.choked
    assert not c3.choked
    assert not c4.choked
    assert not c5.choked


