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
            u = c.get_upload()
            n = self.measurefunc(c)
            if not u.is_choked() and u.is_interested() and n < min:
                min = n
                minc = c
        if minc is not None:
            self.connections.remove(minc)
            self.connections.append(minc)
            self.rechoke()
    
    def rechoke(self):
        count = 0
        for c in self.connections:
            u = c.get_upload()
            if count < self.max_uploads:
                if u.is_choked():
                    u.unchoke()
                if u.is_interested():
                    count += 1
            else:
                if not u.is_choked():
                    u.choke()

    def connection_made(self, connection):
        if self.rand:
            self.connections.insert(randrange(len(self.connections) + 1), connection)
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
        self.v = 0
        self.u = DummyUploader()
    
    def get_upload(self):
        return self.u
        
class DummyUploader:
    def __init__(self):
        self.interested = false
        self.choked = false

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
    assert not c1.u.choked
    assert not c2.u.choked

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

    c2.u.interested = true
    ch.interested(c2)
    assert not c1.u.choked
    assert not c2.u.choked
    assert c3.u.choked

def test_unchokes_after_lost_interest():
    s = DummyScheduler()
    ch = Choker(1, s.schedule, 3, lambda x: 0, false)
    assert s.s == [(ch.round_robin, 3)]
    c1 = DummyConnection()
    c2 = DummyConnection()
    ch.connection_made(c1)
    ch.connection_made(c2)

    c1.u.interested = true
    ch.interested(c1)
    assert not c1.u.choked
    assert c2.u.choked

    c1.u.interested = false
    ch.not_interested(c1)
    assert not c1.u.choked
    assert not c2.u.choked

def test_interrupt():
    s = DummyScheduler()
    ch = Choker(1, s.schedule, 3, lambda x: 0, false)
    assert s.s == [(ch.round_robin, 3)]
    c1 = DummyConnection()
    c2 = DummyConnection()
    ch.connection_made(c1)
    ch.connection_made(c2)

    c2.u.interested = true
    ch.interested(c2)
    assert not c1.u.choked
    assert not c2.u.choked

    c1.u.interested = true
    ch.interested(c1)
    assert not c1.u.choked
    assert c2.u.choked

def test_choke_at_start():
    s = DummyScheduler()
    ch = Choker(1, s.schedule, 3, lambda x: 0, false)
    assert s.s == [(ch.round_robin, 3)]
    c1 = DummyConnection()
    ch.connection_made(c1)

    c1.u.interested = true
    ch.interested(c1)
    assert not c1.u.choked

    c2 = DummyConnection()
    ch.connection_made(c2)
    assert not c1.u.choked
    assert c2.u.choked

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

    c2.u.interested = true
    ch.interested(c2)
    assert not c1.u.choked
    assert not c2.u.choked
    assert not c3.u.choked
    assert not c4.u.choked
    assert not c5.u.choked

    c4.u.interested = true
    ch.interested(c4)
    assert not c1.u.choked
    assert not c2.u.choked
    assert not c3.u.choked
    assert not c4.u.choked
    assert c5.u.choked

    ch.round_robin()
    assert not c1.u.choked
    assert not c2.u.choked
    assert not c3.u.choked
    assert not c4.u.choked
    assert not c5.u.choked

    c5.u.interested = true
    ch.interested(c5)
    assert not c1.u.choked
    assert not c2.u.choked
    assert not c3.u.choked
    assert c4.u.choked
    assert not c5.u.choked

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

    c2.u.interested = true
    ch.interested(c2)
    assert not c1.u.choked
    assert not c2.u.choked
    assert not c3.u.choked
    assert not c4.u.choked
    assert not c5.u.choked

    c4.u.interested = true
    ch.interested(c4)
    assert not c1.u.choked
    assert not c2.u.choked
    assert not c3.u.choked
    assert not c4.u.choked
    assert c5.u.choked

    ch.round_robin()
    assert not c1.u.choked
    assert not c2.u.choked
    assert not c3.u.choked
    assert not c4.u.choked
    assert not c5.u.choked

    c5.u.interested = true
    ch.interested(c5)
    assert not c1.u.choked
    assert c2.u.choked
    assert not c3.u.choked
    assert not c4.u.choked
    assert not c5.u.choked


