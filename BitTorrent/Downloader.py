# Written by Bram Cohen
# see LICENSE.txt for license information

from CurrentRateMeasure import Measure
true = 1
false = 0

class SingleDownload:
    def __init__(self, downloader, connection):
        self.downloader = downloader
        self.connection = connection
        self.choked = true
        self.interested = false
        self.active_requests = []
        self.measure = Measure(downloader.max_rate_period)
        self.have = [false] * downloader.numpieces

    def disconnected(self):
        self.downloader.downloads.remove(self)
        for i in xrange(len(self.have)):
            if self.have[i]:
                self.downloader.picker.lost_have(i)
        self._letgo()

    def _letgo(self):
        hits = []
        for index, begin, length in self.active_requests:
            before = self.downloader.storage.do_I_have_requests(index)
            self.downloader.storage.request_lost(index, begin, length)
            if not before:
                hits.append(index)
        self.active_requests = []
        if len(hits) > 0:
            for d in self.downloader.downloads:
                d._check_interest(hits)
                d.download_more(hits)

    def got_choke(self):
        if not self.choked:
            self.choked = true
            self._letgo()

    def got_unchoke(self):
        if self.choked:
            self.choked = false
            self.download_more()

    def is_choked(self):
        return self.choked

    def is_interested(self):
        return self.interested

    def got_piece(self, index, begin, piece):
        try:
            self.active_requests.remove((index, begin, len(piece)))
        except ValueError:
            return false
        self.measure.update_rate(len(piece))
        self.downloader.measurefunc(len(piece))
        self.downloader.downmeasure.update_rate(len(piece))
        self.downloader.picker.came_in(index)
        self.downloader.storage.piece_came_in(index, begin, piece)
        if self.downloader.storage.do_I_have(index):
            self.downloader.picker.complete(index)
        self.download_more()
        if len(self.active_requests) == 0:
            self.interested = false
            self.connection.send_not_interested()
        return self.downloader.storage.do_I_have(index)

    def download_more(self, pieces = None):
        if self.choked or len(self.active_requests) == self.downloader.backlog:
            return
        if pieces is None:
            pieces = self.downloader.picker
        hit = []
        self._d(pieces, hit)
        if len(hit) > 0:
            for d in self.downloader.downloads:
                d._lost_interest(hit)

    def _d(self, pieces, hit):
        for piece in pieces:
            if self.have[piece]:
                while self.downloader.storage.do_I_have_requests(piece):
                    begin, length = self.downloader.storage.new_request(piece)
                    self.active_requests.append((piece, begin, length))
                    self.connection.send_request(piece, begin, length)
                    if not self.downloader.storage.do_I_have_requests(piece):
                        hit.append(piece)
                    if len(self.active_requests) == self.downloader.backlog:
                        return

    def _lost_interest(self, pieces):
        if not self.interested or len(self.active_requests) > 0:
            return
        for piece in pieces:
            if self.have[piece]:
                break
        else:
            return
        for i in xrange(len(self.have)):
            if self.have[i] and self.downloader.storage.do_I_have_requests(i):
                return
        self.interested = false
        self.connection.send_not_interested()

    def _check_interest(self, pieces):
        if self.interested:
            return
        for i in pieces:
            if self.have[i] and self.downloader.storage.do_I_have_requests(i):
                self.interested = true
                self.connection.send_interested()
                return

    def got_have(self, index):
        if self.have[index]:
            return
        self.have[index] = true
        self.downloader.picker.got_have(index)
        self._check_interest([index])
        self.download_more([index])

    def got_have_bitfield(self, have):
        self.have = have
        for i in xrange(len(have)):
            if have[i]:
                self.downloader.picker.got_have(i)
        self._check_interest([i for i in xrange(len(have)) if have[i]])
        self.download_more()

class Downloader:
    def __init__(self, storage, picker, backlog, max_rate_period, numpieces, 
            downmeasure, measurefunc = lambda x: None):
        self.storage = storage
        self.picker = picker
        self.backlog = backlog
        self.max_rate_period = max_rate_period
        self.downmeasure = downmeasure
        self.numpieces = numpieces
        self.measurefunc = measurefunc
        self.downloads = []

    def make_download(self, connection):
        self.downloads.insert(0, SingleDownload(self, connection))
        return self.downloads[0]

class DummyPicker:
    def __init__(self, num, r):
        self.stuff = range(num)
        self.r = r

    def __getitem__(self, key):
        return self.stuff[key]

    def __iter__(self):
        return iter(self.stuff)

    def lost_have(self, pos):
        self.r.append('lost have')

    def got_have(self, pos):
        self.r.append('got have')

    def came_in(self, pos):
        self.r.append('came in')

    def complete(self, pos):
        self.stuff.remove(pos)
        self.r.append('complete')

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
    events = []
    d = Downloader(ds, DummyPicker(len(ds.active), events), 2, 15, 1, Measure(15))
    sd = d.make_download(DummyConnection(events))
    assert events == []
    assert ds.remaining == [[(0, 2), (2, 2), (4, 2), (6, 2)]]
    assert ds.active == [[]]
    sd.got_have_bitfield([true])
    assert events == ['got have', 'interested']
    del events[:]
    assert ds.remaining == [[(0, 2), (2, 2), (4, 2), (6, 2)]]
    assert ds.active == [[]]
    sd.got_unchoke()
    assert events == [('request', 0, 6, 2), ('request', 0, 4, 2)]
    del events[:]
    assert ds.remaining == [[(0, 2), (2, 2)]]
    assert ds.active == [[(4, 2), (6, 2)]]
    sd.got_piece(0, 4, 'ab')
    assert events == ['came in', ('request', 0, 2, 2)]
    del events[:]
    assert ds.remaining == [[(0, 2)]]
    assert ds.active == [[(2, 2), (6, 2)]]

def test_got_have_single():
    ds = DummyStorage([[(0, 2)]])
    events = []
    d = Downloader(ds, DummyPicker(len(ds.active), events), 2, 15, 1, Measure(15))
    sd = d.make_download(DummyConnection(events))
    assert events == []
    assert ds.remaining == [[(0, 2)]]
    assert ds.active == [[]]
    sd.got_unchoke()
    assert events == []
    assert ds.remaining == [[(0, 2)]]
    assert ds.active == [[]]
    sd.got_have(0)
    assert events == ['got have', 'interested', ('request', 0, 0, 2)]
    del events[:]
    assert ds.remaining == [[]]
    assert ds.active == [[(0, 2)]]
    sd.disconnected()
    assert events == ['lost have']

def test_choke_clears_active():
    ds = DummyStorage([[(0, 2)]])
    events = []
    d = Downloader(ds, DummyPicker(len(ds.active), events), 2, 15, 1, Measure(15))
    sd1 = d.make_download(DummyConnection(events))
    sd2 = d.make_download(DummyConnection(events))
    assert events == []
    assert ds.remaining == [[(0, 2)]]
    assert ds.active == [[]]
    sd1.got_unchoke()
    sd1.got_have(0)
    assert events == ['got have', 'interested', ('request', 0, 0, 2)]
    del events[:]
    assert ds.remaining == [[]]
    assert ds.active == [[(0, 2)]]
    sd2.got_unchoke()
    sd2.got_have(0)
    assert events == ['got have']
    del events[:]
    assert ds.remaining == [[]]
    assert ds.active == [[(0, 2)]]
    sd1.got_choke()
    assert events == ['interested', ('request', 0, 0, 2), 'not interested']
    del events[:]
    assert ds.remaining == [[]]
    assert ds.active == [[(0, 2)]]
    sd2.got_piece(0, 0, 'ab')
    assert events == ['came in', 'complete', 'not interested']
    del events[:]
    assert ds.remaining == [[]]
    assert ds.active == [[]]
