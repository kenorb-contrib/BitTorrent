# written by Bram Cohen
# this file is public domain

from random import randrange
true = 1
false = 0

class Choker:
    def __init__(self, max_uploads, schedule, interval):
        self.max_uploads = max_uploads
        self.schedule = schedule
        self.interval = interval
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
        self.connections.insert(randrange(len(self.connections)), connection)
        self.rechoke()

    def connection_lost(self, connection):
        self.connections.remove(connection)
        self.rechoke()

    def interested(self, connection):
        self.rechoke()

    def not_interested(self, connection):
        self.rechoke()
