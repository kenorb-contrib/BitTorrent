# Written by Bram Cohen
# see LICENSE.txt for license information

from time import time
from random import shuffle
from copy import copy
true = 1
false = 0

class SingleDownload:
    def __init__(self, downloader, connection = None, old = None):
        self.downloader = downloader
        self.unhave = downloader.numpieces
        if old is None:
            self.connection = connection
            self.choked = true
            self.interested = false
            self.have = [false] * downloader.numpieces
            self.ratesince = time()
            self.lastin = self.ratesince
            self.rate = 0.0
        else:
            self.connection = old.connection
            self.connection.set_download(self)
            self.choked = old.choked
            self.have = old.have
            self.ratesince = old.ratesince
            self.lastin = old.lastin
            self.rate = old.rate
            self.interested = old.interested
            shuffle(downloader.requests)
            for h in self.have:
                if h:
                    self.unhave -= 1
            if not self.choked:
                for info in downloader.requests:
                    if info not in old.active_requests:
                        (index, begin, length) = info
                        if self.have[index]:
                            self.send_request(index, begin, length)

    def disconnected(self):
        self.downloader.downloads.remove(self)

    def got_choke(self):
        self.choked = true

    def got_unchoke(self):
        if not self.choked or not self.interested:
            return
        shuffle(self.downloader.requests)
        for (index, begin, length) in self.downloader.requests:
            if self.have[index]:
                self.connection.send_request(index, begin, length)

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

    def send_request(self, index, begin, length):
        if not self.interested:
            self.interested = true
            self.connection.send_interested()
        self.connection.send_request(index, begin, length)

    def got_piece(self, index, begin, piece):
        try:
            self.downloader.requests.remove((index, begin, len(piece)))
        except ValueError:
            return false
        self.update_rate(len(piece))
        storage = self.downloader.storage
        storage.piece_came_in(index, begin, piece)
        if storage.do_I_have_requests(index):
            n = []
            while storage.do_I_have_requests(index):
                (a, b) = storage.new_request(index)
                n.append((a, b))
                self.downloader.requests.append((index, a, b))
            for d in self.downloader.downloads:
                if not d.choked and d.have[index]:
                    shuffle(n)
                    for (a, b) in n:
                        if a != begin or d is self:
                            d.send_request(index, a, b)
            return false
        for d in self.downloader.downloads:
            if d.have[index] and d is not self and not d.choked:
                d.connection.send_cancel(index, begin, len(piece))
        for (a, b, c) in self.downloader.requests:
            if a == index:
                return true
        for d in self.downloader.downloads:
            if d.have[index]:
                for (a, b, c) in self.downloader.requests:
                    if d.have[a]:
                        break
                else:
                    d.interested = false
                    d.connection.send_not_interested()
        if self.downloader.requests == []:
            for d in copy(self.downloader.downloads):
                if d.unhave == 0:
                    d.connection.close()
        return true

    def got_have(self, index):
        if self.have[index]:
            return
        self.have[index] = true
        self.unhave -= 1
        if self.downloader.storage.do_I_have(index):
            return
        shuffle(self.downloader.requests)
        for i, begin, length in self.downloader.requests:
            if i == index:
                self.send_request(i, begin, length)
        if self.downloader.requests == [] and self.unhave == 0:
            self.connection.close()

    def got_have_bitfield(self, have):
        self.have = have
        for h in self.have:
            if h:
                self.unhave -= 1
        shuffle(self.downloader.requests)
        for i, begin, length in self.downloader.requests:
            if self.have[i]:
                self.send_request(i, begin, length)
        if self.downloader.requests == [] and self.unhave == 0:
            self.connection.close()

class EndgameDownloader:
    def __init__(self, old):
        self.storage = old.storage
        self.backlog = old.backlog
        self.max_rate_period = old.max_rate_period
        self.numpieces = old.numpieces
        self.total_down = old.total_down
        self.measurefunc = old.measurefunc
        self.requests = []
        for d in old.downloads:
            self.requests.extend(d.active_requests)
        self.downloads = []
        for d in old.downloads:
            self.downloads.append(SingleDownload(self, old = d))

    def make_download(self, connection):
        self.downloads.append(SingleDownload(self, connection))
        return self.downloads[-1]

class DummyConnection:
    def __init__(self, events):
        self.events = events

    def set_download(self, download):
        self.download = download

    def send_request(self, index, begin, length):
        self.events.append((self, 'request', index, begin, length))

    def send_cancel(self, index, begin, length):
        self.events.append((self, 'cancel', index, begin, length))

    def send_interested(self):
        self.events.append((self, 'interested'))

    def send_not_interested(self):
        self.events.append((self, 'not interested'))

    def close(self):
        self.events.append((self, 'close'))

class DummyStorage:
    def __init__(self, events):
        self.events = events
        self.expect_flunk = []
        self.requests = []

    def piece_came_in(self, index, begin, piece):
        self.events.append((self, 'came in', index, begin, piece))
        if self.expect_flunk != []:
            self.requests = self.expect_flunk
        self.expect_flunk = []

    def do_I_have_requests(self, index):
        return len(self.requests) != 0

    def new_request(self, index):
        return self.requests.pop()

    def do_I_have(self, index):
        return false

class DummyDownload:
    def __init__(self, connection, choked, interested, have, active_requests):
        self.connection = connection
        self.choked = choked
        self.interested = interested
        self.have = have
        self.active_requests = active_requests
        self.ratesince = 0
        self.lastin = 0
        self.rate = 0

class DummyDownloader:
    def __init__(self, storage, numpieces, downloads):
        self.storage = storage
        self.backlog = 5
        self.max_rate_period = 50
        self.numpieces = numpieces
        self.total_down = [0]
        self.measurefunc = lambda x: None
        self.downloads = downloads

def test_piece_came_in_no_interest_lost():
    events = []
    c1 = DummyConnection(events)
    c2 = DummyConnection(events)
    d1 = DummyDownload(c1, false, true, [true], [(0, 0, 2)])
    d2 = DummyDownload(c2, false, true, [true], [(0, 4, 1)])
    s = DummyStorage(events)
    d = DummyDownloader(s, 1, [d1, d2])
    ed = EndgameDownloader(d)
    d1 = c1.download
    d2 = c2.download
    assert events == [(c1, 'request', 0, 4, 1), (c2, 'request', 0, 0, 2)]
    del events[:]
    assert d1.got_piece(0, 4, 'a')
    assert events == [(s, 'came in', 0, 4, 'a'), (c2, 'cancel', 0, 4, 1)]
    del events[:]
    c3 = DummyConnection(events)
    d3 = ed.make_download(c3)
    assert events == []
    d3.got_have(0)
    assert events == [(c3, 'interested'), (c3, 'request', 0, 0, 2)]
    del events[:]
    c4 = DummyConnection(events)
    d4 = ed.make_download(c4)
    assert events == []
    d4.got_have_bitfield([true])
    assert events == [(c4, 'interested'), (c4, 'request', 0, 0, 2)]

def test_piece_came_in_lost_interest():
    events = []
    c1 = DummyConnection(events)
    c2 = DummyConnection(events)
    c3 = DummyConnection(events)
    c4 = DummyConnection(events)
    d1 = DummyDownload(c1, false, true, [true], [(0, 0, 2)])
    d2 = DummyDownload(c2, false, true, [true], [])
    d3 = DummyDownload(c3, false, false, [false], [])
    d4 = DummyDownload(c4, true, true, [true], [])
    s = DummyStorage(events)
    d = DummyDownloader(s, 1, [d1, d2, d3, d4])
    ed = EndgameDownloader(d)
    d1 = c1.download
    d2 = c2.download
    d3 = c3.download
    d4 = c4.download
    assert events == [(c2, 'request', 0, 0, 2)]
    del events[:]
    assert d1.got_piece(0, 0, 'aa')
    assert events == [(s, 'came in', 0, 0, 'aa'),(c2, 'cancel', 0, 0, 2), 
        (c1, 'not interested'), (c2, 'not interested'), (c4, 'not interested'),
        (c1, 'close'), (c2, 'close'), (c4, 'close')]
    del events[:]
    c5 = DummyConnection(events)
    d5 = ed.make_download(c5)
    assert events == []
    d5.got_have(0)
    assert events == [(c5, 'close')]
    del events[:]
    c6 = DummyConnection(events)
    d6 = ed.make_download(c6)
    assert events == []
    d6.got_have_bitfield([true])
    assert events == [(c6, 'close')]

def test_hash_fail():
    events = []
    c1 = DummyConnection(events)
    c2 = DummyConnection(events)
    c3 = DummyConnection(events)
    c4 = DummyConnection(events)
    d1 = DummyDownload(c1, false, true, [true], [(0, 0, 2)])
    d2 = DummyDownload(c2, false, true, [true], [])
    d3 = DummyDownload(c3, false, false, [false], [])
    d4 = DummyDownload(c4, true, true, [true], [])
    s = DummyStorage(events)
    s.expect_flunk = [(0, 4)]
    d = DummyDownloader(s, 1, [d1, d2, d3, d4])
    EndgameDownloader(d)
    d1 = c1.download
    d2 = c2.download
    d3 = c3.download
    d4 = c4.download
    assert events == [(c2, 'request', 0, 0, 2)]
    del events[:]
    assert not d1.got_piece(0, 0, 'aa')
    assert events == [(s, 'came in', 0, 0, 'aa'), (c1, 'request', 0, 0, 4)]
    del events[:]
    d4.got_unchoke()
    assert events == [(c4, 'request', 0, 0, 4)]
