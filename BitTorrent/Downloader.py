# Written by Bram Cohen
# see LICENSE.txt for license information

from time import time
from PriorityBitField import PriorityBitField
from random import shuffle
from copy import copy
true = 1
false = 0

class SingleDownload:
    def __init__(self, downloader, connection):
        self.downloader = downloader
        self.connection = connection
        self.choked = true
        self.interested = false
        self.active_requests = []
        self.want_priorities = PriorityBitField(downloader.numpieces)
        self.ratesince = time()
        self.lastin = self.ratesince
        self.rate = 0.0
        self.have = [false] * downloader.numpieces

    def disconnected(self):
        self.downloader.downloads.remove(self)
        self.letgo()

    def letgo(self):
        hit = false
        for index, begin, length in self.active_requests:
            before = self.downloader.storage.do_I_have_requests(index)
            self.downloader.storage.request_lost(index, begin, length)
            if self.downloader.change_interest(index, before):
                hit = true
        del self.active_requests[:]
        if hit:
            self.downloader.adjust()

    def got_choke(self):
        if self.choked:
            return
        self.choked = true
        self.letgo()

    def got_unchoke(self):
        if not self.choked:
            return
        self.choked = false
        self.downloader.adjust(self)

    def is_choked(self):
        return self.choked

    def is_interested(self):
        return self.interested

    def update_rate(self, amount):
        self.downloader.measurefunc(amount)
        self.downloader.total_down[0] += amount
        t = time()
        self.rate = (self.rate * (self.lastin - self.ratesince) + 
            amount) / (t - self.ratesince)
        self.lastin = t
        if self.ratesince < t - self.downloader.max_rate_period:
            self.ratesince = t - self.downloader.max_rate_period

    def got_piece(self, index, begin, piece):
        try:
            self.active_requests.remove((index, begin, len(piece)))
        except ValueError:
            return false
        self.update_rate(len(piece))
        wanted_before = self.downloader.storage.do_I_have_requests(index)
        self.downloader.storage.piece_came_in(index, begin, piece)
        if self.downloader.change_interest(index, wanted_before):
            self.downloader.adjust()
        else:
            self.downloader.adjust(self)
        return self.downloader.storage.do_I_have(index)

    def adjust(self):
        if self.want_priorities.is_empty() and self.active_requests == []:
            if self.interested:
                self.interested = false
                self.connection.send_not_interested()
        else:
            if not self.interested:
                self.interested = true
                self.connection.send_interested()
        if self.choked:
            return false
        hit = false
        while (not self.want_priorities.is_empty() and 
                len(self.active_requests) < self.downloader.backlog):
            i = self.downloader.priority_to_index[self.want_priorities.get_first()]
            begin, length = self.downloader.storage.new_request(i)
            self.active_requests.append((i, begin, length))
            if self.downloader.change_interest(i, true):
                hit = true
            self.connection.send_request(i, begin, length)
        return hit

    def got_have(self, index):
        if self.have[index]:
            return
        self.have[index] = true
        if self.downloader.storage.do_I_have_requests(index):
            self.want_priorities.insert_strict(
                self.downloader.index_to_priority[index])
            self.downloader.adjust(self)

    def got_have_bitfield(self, have):
        self.have = have
        for i in xrange(len(have)):
            if have[i] and self.downloader.storage.do_I_have_requests(i):
                self.want_priorities.insert_strict(
                    self.downloader.index_to_priority[i])
        self.downloader.adjust(self)

class Downloader:
    def __init__(self, storage, backlog, max_rate_period, numpieces, 
            total_down = [0l], measurefunc = lambda x: None):
        self.storage = storage
        self.backlog = backlog
        self.max_rate_period = max_rate_period
        self.total_down = total_down
        self.numpieces = numpieces
        self.measurefunc = measurefunc
        self.index_to_priority = range(numpieces)
        shuffle(self.index_to_priority)
        self.priority_to_index = [None] * numpieces
        for i in xrange(numpieces):
            self.priority_to_index[self.index_to_priority[i]] = i
        self.downloads = []

    def change_interest(self, index, before):
        assert before in [0, 1]
        after = self.storage.do_I_have_requests(index)
        p = self.index_to_priority[index]
        r = false
        if not before and after:
            for c in self.downloads:
                if c.have[index]:
                    r = true
                    c.want_priorities.insert_strict(p)
        elif before and not after:
            for c in self.downloads:
                if c.have[index]:
                    r = true
                    c.want_priorities.remove_strict(p)
        return r

    def adjust(self, c = None):
        if c is None:
            d = self.downloads
        else:
            d = [c]
        while true in [c.adjust() for c in d]:
            d = self.downloads

    def make_download(self, connection):
        self.downloads.insert(0, SingleDownload(self, connection))
        return self.downloads[0]

class DummyStorage:
    def __init__(self, remaining):
        self.remaining = remaining
        self.active = [[]]

    def do_I_have_requests(self, index):
        return self.remaining[index] != []
        
    def request_lost(self, index, begin, length):
        x = (begin, length)
        self.active[index].remove(x)
        self.remaining[index].append(x)
        self.remaining[index].sort()
        
    def piece_came_in(self, index, begin, piece):
        self.active[index].remove((begin, len(piece)))
        
    def do_I_have(self, index):
        return (self.remaining[index] == [] and 
            self.active[index] == [])
        
    def new_request(self, index):
        x = self.remaining[index].pop()
        self.active[index].append(x)
        self.active[index].sort()
        return x

class DummyConnection:
    def __init__(self, events):
        self.events = events

    def send_interested(self):
        self.events.append('interested')
        
    def send_not_interested(self):
        self.events.append('not interested')
        
    def send_request(self, index, begin, length):
        self.events.append(('request', index, begin, length))

def test_stops_at_backlog():
    ds = DummyStorage([[(0, 2), (2, 2), (4, 2), (6, 2)]])
    d = Downloader(ds, 2, 15, 1, [0])
    events = []
    sd = d.make_download(DummyConnection(events))
    assert events == []
    assert ds.remaining == [[(0, 2), (2, 2), (4, 2), (6, 2)]]
    assert ds.active == [[]]
    sd.got_have_bitfield([true])
    assert events == ['interested']
    del events[:]
    assert ds.remaining == [[(0, 2), (2, 2), (4, 2), (6, 2)]]
    assert ds.active == [[]]
    sd.got_unchoke()
    assert events == [('request', 0, 6, 2), ('request', 0, 4, 2)]
    del events[:]
    assert ds.remaining == [[(0, 2), (2, 2)]]
    assert ds.active == [[(4, 2), (6, 2)]]
    sd.got_piece(0, 4, 'ab')
    assert events == [('request', 0, 2, 2)]
    del events[:]
    assert ds.remaining == [[(0, 2)]]
    assert ds.active == [[(2, 2), (6, 2)]]

def test_got_have_single():
    ds = DummyStorage([[(0, 2)]])
    d = Downloader(ds, 2, 15, 1, [0])
    events = []
    sd = d.make_download(DummyConnection(events))
    assert events == []
    assert ds.remaining == [[(0, 2)]]
    assert ds.active == [[]]
    sd.got_unchoke()
    assert events == []
    assert ds.remaining == [[(0, 2)]]
    assert ds.active == [[]]
    sd.got_have(0)
    assert events == ['interested', ('request', 0, 0, 2)]
    del events[:]
    assert ds.remaining == [[]]
    assert ds.active == [[(0, 2)]]

def test_choke_clears_active():
    ds = DummyStorage([[(0, 2)]])
    d = Downloader(ds, 2, 15, 1, [0])
    events = []
    sd1 = d.make_download(DummyConnection(events))
    sd2 = d.make_download(DummyConnection(events))
    assert events == []
    assert ds.remaining == [[(0, 2)]]
    assert ds.active == [[]]
    sd1.got_unchoke()
    sd1.got_have(0)
    assert events == ['interested', ('request', 0, 0, 2)]
    del events[:]
    assert ds.remaining == [[]]
    assert ds.active == [[(0, 2)]]
    sd2.got_unchoke()
    sd2.got_have(0)
    assert events == []
    assert ds.remaining == [[]]
    assert ds.active == [[(0, 2)]]
    sd1.got_choke()
    assert events == ['interested', ('request', 0, 0, 2), 'not interested']
    del events[:]
    assert ds.remaining == [[]]
    assert ds.active == [[(0, 2)]]
    sd2.got_piece(0, 0, 'ab')
    assert events == ['not interested']
    del events[:]
    assert ds.remaining == [[]]
    assert ds.active == [[]]

def test_introspect_priority_list():
    d = Downloader(None, 2, 15, 10, [0])
    for i in xrange(10):
        for j in xrange(i):
            assert d.index_to_priority[i] != d.index_to_priority[j]
            assert d.priority_to_index[i] != d.priority_to_index[j]
    for i in xrange(10):
        assert d.index_to_priority[d.priority_to_index[i]] == i
