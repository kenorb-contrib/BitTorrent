# Written by Bram Cohen
# This file is public domain
# The authors disclaim all liability for any damages resulting from
# any use of this software.

from time import time

true = 1
false = 0

class Download:
    def __init__(self, connection, data, backlog, max_rate_period):
        self.connection = connection
        self.data = data
        self.backlog = backlog
        self.choked = false
        self.interested = false
        self.max_rate_period = max_rate_period
        self.ratesince = time()
        self.lastin = self.ratesince
        self.rate = 0
        data.connected(self)

    def adjust(self):
        data = self.data
        if self.choked:
            if self.interested:
                if not data.do_I_want_more(self):
                    self.interested = false
                    self.connection.send_message({'type': 'done'})
            else:
                if data.do_I_want_more(self):
                    self.interested = true
                    self.connection.send_message({'type': 'interested'})
            return
        f = {}
        while true:
            if data.num_current(self) >= self.backlog:
                break
            s = data.get_next(self)
            if s is None:
                if self.interested and data.num_current(self) == 0:
                    self.interested = false
                    self.connection.send_message({'type': 'done'})
                break
            blob, begin, length, full = s
            self.interested = true
            self.connection.send_message({'type': 'send', 
                'blob': blob, 'begin': begin, 'length': length})
            for x in full:
                f[x] = 1
        for x in f.keys():
            if x is not self:
                x.adjust()

    def got_choke(self):
        if self.choked:
            return
        self.choked = true
        if self.interested:
            for i in self.data.cleared(self):
                i.adjust()

    def got_unchoke(self):
        if not self.choked:
            return
        self.choked = false
        if self.interested:
            self.adjust()

    def is_choked(self):
        return self.choked

    def is_interested(self):
        return self.interested

    def update_rate(self, amount):
        t = time()
        self.rate = (self.rate * (self.lastin - self.ratesince) + 
            amount) / (t - self.ratesince)
        self.lastin = t
        if self.ratesince < t - self.max_rate_period:
            self.ratesince = t - self.max_rate_period

    def got_slice(self, message):
        complete, check = self.data.came_in(self, 
            message['blob'], message['begin'], message['slice'])
        self.update_rate(len(message['slice']))
        self.adjust()
        for c in check:
            c.adjust()
        if complete:
            return message['blob']
        return None

    def got_I_have(self, message):
        if self.data.has_blobs(self, 
                message['blobs']) and not self.interested:
            self.adjust()

    def disconnected(self):
        for i in self.data.disconnected(self):
            i.adjust()
        del self.connection
        del self.data
        del self.choked

class DummyConnection:
    def __init__(self):
        self.m = []
        self.more = []
        self.choked = false
        self.disconnected = false
        self.current = 0
        
    def send_message(self, message):
        self.m.append(message)

class DummyData:
    def __init__(self):
        self.all = []

    def cleared(self, d):
        d.connection.current = 0
        return self.all
        
    def do_I_want_more(self, d):
        return len(d.connection.more) > 0

    def num_current(self, d):
        return d.connection.current
        
    def get_next(self, d):
        c = d.connection
        if len(c.more) == 0:
            return None
        r = c.more[0]
        del c.more[0]
        c.current += 1
        if len(c.more) == 0:
            return r + ([],)
        else:
            return r + (self.all,)
        
    def came_in(self, d, blob, begin, slice):
        c = d.connection
        c.current -= 1
        if c.current == 0:
            return (blob, self.all)
        else:
            return (None, [])
        
    def has_blobs(self, d, blobs):
        return true

    def connected(self, d):
        pass

    def disconnected(self, d):
        d.connection.disconnected = true
        return self.all

def test_choke():
    # unchoked, interested, want
    dd = DummyData()
    yyy = DummyConnection()
    yyn = DummyConnection()
    yny = DummyConnection()
    ynn = DummyConnection()
    nyy = DummyConnection()
    nyn = DummyConnection()
    nny = DummyConnection()
    nnn = DummyConnection()
    extra = DummyConnection()
    
    yyyd = Download(yyy, dd, 2, 15)
    yynd = Download(yyn, dd, 2, 15)
    ynyd = Download(yny, dd, 2, 15)
    ynnd = Download(ynn, dd, 2, 15)
    nyyd = Download(nyy, dd, 2, 15)
    nynd = Download(nyn, dd, 2, 15)
    nnyd = Download(nny, dd, 2, 15)
    nnnd = Download(nnn, dd, 2, 15)
    extrad = Download(extra, dd, 2, 15)
    
    yyy.more.append(('a', 0, 2))
    yny.more.append(('a', 0, 2))
    nyy.more.append(('a', 0, 2))
    nny.more.append(('a', 0, 2))

    nyyd.got_choke()
    nynd.got_choke()
    nnyd.got_choke()
    nnnd.got_choke()

    dd.all = [yyyd, yynd, ynyd, ynnd, nyyd, nynd, nnyd, nnnd, extrad]

    yyyd.got_I_have({'type': 'I have', 'blobs': ['a']})
    yynd.got_I_have({'type': 'I have', 'blobs': ['a']})
    nyyd.got_I_have({'type': 'I have', 'blobs': ['a']})
    nynd.got_I_have({'type': 'I have', 'blobs': ['a']})

    assert yyy.m == [{'type': 'send', 'blob': 'a', 'begin': 0, 'length': 2}]
    del yyy.m[:]
    assert yyn.m == []
    del yyn.m[:]
    assert nyy.m == [{'type': 'interested'}]
    del nyy.m[:]
    assert nyn.m == []
    del nyn.m[:]
    
    extrad.disconnected()
    assert extra.disconnected
    assert not yyy.disconnected
    assert not yyn.disconnected
    assert not yny.disconnected
    assert not ynn.disconnected
    assert not nyy.disconnected
    assert not nyn.disconnected
    assert not nny.disconnected
    assert not nnn.disconnected

    assert yyy.m == []
    assert yyn.m == []
    assert yny.m == [{'type': 'send', 'blob': 'a', 'begin': 0, 'length': 2}]
    assert ynn.m == []
    assert nyy.m == []
    assert nyn.m == []
    assert nny.m == [{'type': 'interested'}]
    assert nnn.m == []

def test_halts_at_backlog():
    dd = DummyData()
    c = DummyConnection()
    c.more.append(('a', 0, 2))
    c.more.append(('a', 2, 2))
    c.more.append(('a', 4, 2))
    c.more.append(('a', 6, 2))
    c.more.append(('a', 8, 2))
    c.more.append(('a', 10, 2))
    d = Download(c, dd, 2, 15)
    dd.all.append(d)
    
    d.got_I_have({'type': 'I have', 'blobs': ['a']})
    assert d.interested
    
    assert c.m == [{'type': 'send', 'blob': 'a', 'begin': 0, 'length': 2},
        {'type': 'send', 'blob': 'a', 'begin': 2, 'length': 2}]
    del c.m[:]
    assert c.current == 2
    assert d.interested

    d.got_choke()
    assert d.interested
    assert c.current == 0
    d.got_unchoke()

    assert c.m == [{'type': 'send', 'blob': 'a', 'begin': 4, 'length': 2},
        {'type': 'send', 'blob': 'a', 'begin': 6, 'length': 2}]
    del c.m[:]
    assert c.current == 2
    assert d.interested

    d.got_slice({'type': 'slice', 'blob': 'a', 'begin': 4, 'slice': 'pq'})
    assert c.m == [{'type': 'send', 'blob': 'a', 'begin': 8, 'length': 2}]
    del c.m[:]
    assert c.current == 2

    d.got_slice({'type': 'slice', 'blob': 'a', 'begin': 6, 'slice': 'pq'})
    assert c.m == [{'type': 'send', 'blob': 'a', 'begin': 10, 'length': 2}]
    del c.m[:]
    assert c.current == 2

    assert d.got_slice({'type': 'slice', 'blob': 'a', 
        'begin': 8, 'slice': 'pq'}) == None
    assert c.m == []
    assert c.current == 1
    assert d.interested

    assert d.got_slice({'type': 'slice', 'blob': 'a', 
        'begin': 10, 'slice': 'pq'}) == 'a'
    assert c.m == [{'type': 'done'}]
    assert c.current == 0
