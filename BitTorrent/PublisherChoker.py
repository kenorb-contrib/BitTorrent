# written by Bram Cohen
# this file is public domain

from random import randrange
true = 1
false = 0

class Choker:
    def __init__(self, max_uploads, schedule, interval, rand = true):
        self.max_uploads = max_uploads
        self.schedule = schedule
        self.interval = interval
        self.rand = rand
        self.connections = []
        schedule(self.round_robin, interval)
    
    def round_robin(self):
        self.schedule(self.round_robin, self.interval)
        for c in self.connections:
            if c.is_choked():
                return
            if c.is_interested():
                self.connections.remove(c)
                self.connections.append(c)
                self.rechoke()
                return
    
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

"""

def test_round_robin_with_no_downloads():
    start two
    do round robin
    just checking for no internal pukes

def test_choke_after_hits_max():
    start three with max one
    start middle downloading
    assert first unchoked and third choked
    assert both others unchoked

def test_unchokes_after_lost_interest():
    start two with max one
    start downloading one
    lose interest, assert other unchoked

def test_interrupt():
    start two with second downloading
    make first interested
    assert second throttled

"""
