# Written by Bram Cohen
# see LICENSE.txt for license information

from time import time
from PriorityBitField import PriorityBitField
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
        self.downloader.downloaders.remove(self)
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
                len(self.active_requests) < self.downloader.max_requests):
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
        if self.connecter.storage.do_I_have_requests(index):
            self.want_priorities.insert(
                self.downloader.index_to_priority[index])
            self.downloader.adjust(self)

    def got_have_bitfield(self, have):
        self.have = have
        for i in xrange(len(have)):
            if have[i] and self.connecter.storage.do_I_have_requests(i):
                self.want_priorities.insert(
                    self.downloader.index_to_priority[i])
        self.downloader.adjust(self)

class Downloader:
    def __init__(self, storage, backlog, 
            max_rate_period, numpieces, total_down = [0l]):
        self.backlog = backlog
        self.max_rate_period = max_rate_period
        self.total_down = total_down
        self.numpieces = numpieces
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
            for c in self.d:
                if c.have[index]:
                    r = true
                    c.want_priorities.insert(p)
        elif before and not after:
            for c in self.d:
                if c.have[index]:
                    r = true
                    c.want_priorities.remove(p)
        return r

    def adjust(self, c = None):
        if c is None:
            d = self.d
        else:
            d = [c]
        while true in [c.adjust() for c in d]:
            d = self.d

    def make_download(self, connection):
        self.downloads.insert(0, SingleDownload(self, connection))
        return self.downloads[0]

def test_stops_at_backlog():
    assert false
    #booga make multiple available, assert stops querying at max
    #booga make one come in, assert queries for exactly one more

def test_got_have_single():
    assert false
    #booga have a have single come in, assert gains interest

def test_download_after_unchoke():
    assert false
    #booga make thing which is interested, unchoke after bitfield

def test_choke_clears_active():
    assert false
    #booga start two things, both of which want the same thing
    #booga assert downloads for second connected
    #booga choke second, assert downloads first
    #booga receive on first, completing
    #booga assert loses interest on both

def test_introspect_priority_list():
    assert false
    #booga manually verify index_to_priority and priority_to_index
