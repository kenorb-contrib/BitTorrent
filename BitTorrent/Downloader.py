# Written by Bram Cohen
# see LICENSE.txt for license information

from CurrentRateMeasure import Measure
from random import shuffle
from time import time
true = 1
false = 0

EXPIRE_TIME = 60 * 60

class PerIPStats: 	 
    def __init__(self, ip): 	 
        self.numgood = 0
        self.bad = {}
        self.numconnections = 0
        self.lastdownload = None
        self.peerid = None

class BadDataGuard:
    def __init__(self, download):
        self.download = download
        self.ip = download.ip
        self.downloader = download.downloader
        self.stats = self.downloader.perip[self.ip]
        self.lastindex = None

    def failed(self, index, bump = false):
        self.stats.bad.setdefault(index, 0)
        self.downloader.gotbaddata[self.ip] = 1
        self.stats.bad[index] += 1
        if len(self.stats.bad) > 1:
            if self.download is not None:
                self.downloader.try_kick(self.download)
            elif self.stats.numconnections == 1 and self.stats.lastdownload is not None:
                self.downloader.try_kick(self.stats.lastdownload)
        if len(self.stats.bad) >= 3 and len(self.stats.bad) > int(self.stats.numgood/30):
            self.downloader.try_ban(self.ip)
        elif bump:
            self.downloader.picker.bump(index)

    def good(self, index):
        # lastindex is a hack to only increase numgood by one for each good
        # piece, however many chunks come from the connection(s) from this IP
        if index != self.lastindex:
            self.stats.numgood += 1
            self.lastindex = index

class SingleDownload:
    def __init__(self, downloader, connection):
        self.downloader = downloader
        self.unhave = downloader.numpieces
        self.connection = connection
        self.choked = true
        self.interested = false
        self.active_requests = []
        self.measure = Measure(downloader.max_rate_period)
        self.peermeasure = Measure(downloader.max_rate_period)
        self.have = [false] * downloader.numpieces
        self.last = 0
        self.example_interest = None
        self.backlog = 2
        self.ip = connection.get_ip()
        self.guard = BadDataGuard(self)

    def _backlog(self):
        self.backlog = min(2+int(self.measure.get_rate()/self.downloader.chunksize),
                                                        self.downloader.backlog)
        return self.backlog
    
    def disconnected(self):
        self.downloader.lost_peer(self)
        for i in xrange(len(self.have)):
            if self.have[i]:
                self.downloader.picker.lost_have(i)
        if self.unhave == 0 and self.downloader.storage.is_endgame():
            self.downloader.add_disconnected_seed(self.connection.get_id())
        self._letgo()
        self.guard.download = None

    def _letgo(self):
        if not self.active_requests:
            return
        if self.downloader.endgamemode:
            self.active_requests = []
            return
        lost = []
        for index, begin, length in self.active_requests:
            self.downloader.storage.request_lost(index, begin, length)
            if index not in lost:
                lost.append(index)
        self.active_requests = []
        ds = [d for d in self.downloader.downloads if not d.choked]
        shuffle(ds)
        for d in ds:
            d._request_more(lost)
        for d in self.downloader.downloads:
            if d.choked and not d.interested:
                for l in lost:
                    if d.have[l] and self.downloader.storage.do_I_have_requests(l):
                        d.interested = true
                        d.connection.send_interested()
                        break

    def got_choke(self):
        if not self.choked:
            self.choked = true
            self._letgo()

    def got_unchoke(self):
        if self.choked:
            self.choked = false
            if self.interested:
                self._request_more()

    def is_choked(self):
        return self.choked

    def is_interested(self):
        return self.interested

    def got_piece(self, index, begin, piece):
        try:
            self.active_requests.remove((index, begin, len(piece)))
        except ValueError:
            return false
        if self.downloader.endgamemode:
            self.downloader.all_requests.remove((index, begin, len(piece)))
        self.last = time()
        self.measure.update_rate(len(piece))
        self.downloader.measurefunc(len(piece))
        self.downloader.downmeasure.update_rate(len(piece))
        if not self.downloader.storage.piece_came_in(index, begin, piece, self.guard):
            self.downloader.piece_flunked(index)
            return false
        if self.downloader.storage.do_I_have(index):
            self.downloader.picker.complete(index)
        if self.downloader.endgamemode:
            for d in self.downloader.downloads:
                if d is not self and d.interested:
                    if d.choked:
                        d.fix_download_endgame()
                    else:
                        try:
                            d.active_requests.remove((index, begin, len(piece)))
                        except ValueError:
                            continue
                        d.connection.send_cancel(index, begin, len(piece))
                        d.fix_download_endgame()
        self._request_more()
        self.downloader.check_complete(index)
        return self.downloader.storage.do_I_have(index)

    def _want(self, index):
        return self.have[index] and self.downloader.storage.do_I_have_requests(index)

    def _request_more(self, indices = None):
        assert not self.choked
        if len(self.active_requests) >= self._backlog():
            return
        if self.downloader.endgamemode:
            self.fix_download_endgame()
            return
        lost_interests = []
        while len(self.active_requests) < self.backlog:
            if indices is None:
                interest = self.downloader.picker.next(self._want)
            else:
                interest = None
                for i in indices:
                    if self.have[i] and self.downloader.storage.do_I_have_requests(i):
                        interest = i
                        break
            if interest is None:
                break
            if not self.interested:
                self.interested = true
                self.connection.send_interested()
            self.example_interest = interest
            begin, length = self.downloader.storage.new_request(interest)
            self.downloader.picker.requested(interest)
            self.active_requests.append((interest, begin, length))
            self.connection.send_request(interest, begin, length)
            if not self.downloader.storage.do_I_have_requests(interest):
                lost_interests.append(interest)
        if not self.active_requests and self.interested:
            self.interested = false
            self.connection.send_not_interested()
        if lost_interests:
            for d in self.downloader.downloads:
                if d.active_requests or not d.interested:
                    continue
                if d.example_interest is not None and self.downloader.storage.do_I_have_requests(d.example_interest):
                    continue
                for lost in lost_interests:
                    if d.have[lost]:
                        break
                else:
                    continue
                interest = self.downloader.picker.next(d._want)
                if interest is None:
                    d.interested = false
                    d.connection.send_not_interested()
                else:
                    d.example_interest = interest
        if self.downloader.storage.is_endgame():
            self.downloader.endgamemode = true
            self.downloader.all_requests = []
            for d in self.downloader.downloads:
                self.downloader.all_requests.extend(d.active_requests)
            for d in self.downloader.downloads:
                d.fix_download_endgame()

    def fix_download_endgame(self):
        want = [a for a in self.downloader.all_requests if self.have[a[0]] and a not in self.active_requests]
        if self.interested and not self.active_requests and not want:
            self.interested = false
            self.connection.send_not_interested()
            return
        if not self.interested and want:
            self.interested = true
            self.connection.send_interested()
        if self.choked or len(self.active_requests) >= self._backlog():
            return
        shuffle(want)
        del want[self.backlog - len(self.active_requests):]
        self.active_requests.extend(want)
        for piece, begin, length in want:
            self.connection.send_request(piece, begin, length)

    def got_have(self, index):
        if index == self.downloader.numpieces-1:
            self.downloader.totalmeasure.update_rate(self.downloader.storage.total_length-(self.downloader.numpieces-1)*self.downloader.storage.piece_length)
            self.peermeasure.update_rate(self.downloader.storage.total_length-(self.downloader.numpieces-1)*self.downloader.storage.piece_length)
        else:
            self.downloader.totalmeasure.update_rate(self.downloader.storage.piece_length)
            self.peermeasure.update_rate(self.downloader.storage.piece_length)
        if self.have[index]:
            return
        self.have[index] = true
        self.unhave -= 1
        self.downloader.picker.got_have(index)
        if self.downloader.picker.am_I_complete() and self.unhave == 0:
            self.downloader.add_disconnected_seed(self.connection.get_id())
            self.connection.close()
            return
        if self.downloader.endgamemode:
            self.fix_download_endgame()
        elif self.downloader.storage.do_I_have_requests(index):
            if not self.choked:
                self._request_more([index])
            else:
                if not self.interested:
                    self.interested = true
                    self.connection.send_interested()

    def got_have_bitfield(self, have):
        self.have = have
        for i in xrange(len(have)):
            if have[i]:
                self.unhave -= 1
                self.downloader.picker.got_have(i)
        if self.downloader.picker.am_I_complete() and self.unhave == 0:
            if self.downloader.super_seeding:
                self.connection.send_bitfield(have)     # be nice, show you're a seed too
            self.connection.close()
            self.downloader.add_disconnected_seed(self.connection.get_id())
            return
        if self.downloader.endgamemode:
            for piece, begin, length in self.downloader.all_requests:
                if self.have[piece]:
                    self.interested = true
                    self.connection.send_interested()
                    return
        for i in xrange(len(have)):
            if have[i] and self.downloader.storage.do_I_have_requests(i):
                self.interested = true
                self.connection.send_interested()
                return

    def get_rate(self):
        return self.measure.get_rate()

    def is_snubbed(self):
        return time() - self.last > self.downloader.snub_time


class Downloader:
    def __init__(self, storage, picker, backlog, max_rate_period, numpieces, chunksize,
                 downmeasure, snub_time,
                 kickbans_ok, kickfunc, banfunc, measurefunc = lambda x: None):
        self.storage = storage
        self.picker = picker
        self.backlog = backlog
        self.max_rate_period = max_rate_period
        self.downmeasure = downmeasure
        self.totalmeasure = Measure(max_rate_period*storage.piece_length/storage.request_size)
        self.numpieces = numpieces
        self.chunksize = chunksize
        self.snub_time = snub_time
        self.kickfunc = kickfunc
        self.banfunc = banfunc
        self.measurefunc = measurefunc
        self.disconnectedseeds = {}
        self.downloads = []
        self.perip = {}
        self.gotbaddata = {}
        self.kicked = {}
        self.banned = {}
        self.kickbans_ok = kickbans_ok
        self.kickbans_halted = false
        self.super_seeding = false
        self.endgamemode = false

    def make_download(self, connection):
        ip = connection.get_ip()
        if self.perip.has_key(ip):
            perip = self.perip[ip]
        else:
            perip = self.perip.setdefault(ip, PerIPStats(ip))
        perip.peerid = connection.get_id()
        perip.numconnections += 1
        d = SingleDownload(self, connection)
        perip.lastdownload = d
        self.downloads.append(d)
        return d

    def piece_flunked(self, index):
        if self.endgamemode:
            if not self.downloads:  # must've been called externally
                self.storage.reset_endgame()
                self.endgamemode = false
                return
            while self.storage.do_I_have_requests(index):
                nb, nl = self.storage.new_request(index)
                self.all_requests.append((index, nb, nl))
            for d in self.downloads:
                d.fix_download_endgame()
            return
        ds = [d for d in self.downloads if not d.choked]
        shuffle(ds)
        for d in ds:
            d._request_more([index])

    def has_downloaders(self):
        return len(self.downloads)

    def lost_peer(self, download):
        ip = download.ip
        self.perip[ip].numconnections -= 1
        if self.perip[ip].lastdownload == download:
            self.perip[ip].lastdownload = None
        self.downloads.remove(download)
        if self.storage.is_endgame() and not self.downloads and self.all_requests: # all peers gone
            for index, begin, length in self.all_requests:
                self.storage.request_lost(index, begin, length)
            self.all_requests = []
            download.active_requests = []
            self.storage.reset_endgame()


    def add_disconnected_seed(self, id):
#        if not self.disconnectedseeds.has_key(id):
#            self.picker.seed_seen_recently()
        self.disconnectedseeds[id]=time()

#	def expire_disconnected_seeds(self):

    def num_disconnected_seeds(self):
        # first expire old ones
        expired = []
        for id,t in self.disconnectedseeds.items():
            if time() - t > EXPIRE_TIME:     #Expire old seeds after so long
                expired.append(id)
        for id in expired:
#            self.picker.seed_disappeared()
            del self.disconnectedseeds[id]
        return len(self.disconnectedseeds)
        # if this isn't called by a stats-gathering function
        # it should be scheduled to run every minute or two.

    def _check_kicks_ok(self):
        if len(self.gotbaddata) > 10:
            self.kickbans_ok = false
            self.kickbans_halted = true
        return self.kickbans_ok and len(self.downloads) > 2

    def try_kick(self, download):
        if self._check_kicks_ok():
            download.guard.download = None
            ip = download.ip
            id = download.connection.get_id()
            self.kicked[ip] = id
            self.perip[ip].peerid = id
            self.kickfunc(download.connection)
        
    def try_ban(self, ip):
        if self._check_kicks_ok():
            self.banfunc(ip)
            self.banned[ip] = self.perip[ip].peerid
            if self.kicked.has_key(ip):
                del self.kicked[ip]

    def set_super_seed(self):
        self.super_seeding = true

    def check_complete(self, index):
        if self.picker.am_I_complete():
            for d in [i for i in self.downloads if i.unhave == 0]:
                d.connection.send_have(index)   # be nice, tell the other seed you completed
                self.add_disconnected_seed(d.connection.get_id())
                d.connection.close()
            return true
        return false

class DummyPicker:
    def __init__(self, num, r):
        self.stuff = range(num)
        self.r = r

    def next(self, wantfunc):
        for i in self.stuff:
            if wantfunc(i):
                return i
        return None

    def lost_have(self, pos):
        self.r.append('lost have')

    def got_have(self, pos):
        self.r.append('got have')

    def requested(self, pos):
        self.r.append('requested')

    def complete(self, pos):
        self.stuff.remove(pos)
        self.r.append('complete')

    def am_I_complete(self):
        return false

class DummyStorage:
    def __init__(self, remaining, have_endgame = false, numpieces = 1):
        self.remaining = remaining
        self.active = [[] for i in xrange(numpieces)]
        self.endgame = false
        self.have_endgame = have_endgame

    def do_I_have_requests(self, index):
        return self.remaining[index] != []
        
    def request_lost(self, index, begin, length):
        x = (begin, length)
        self.active[index].remove(x)
        self.remaining[index].append(x)
        self.remaining[index].sort()
        
    def piece_came_in(self, index, begin, piece):
        self.active[index].remove((begin, len(piece)))
        return true
        
    def do_I_have(self, index):
        return (self.remaining[index] == [] and 
            self.active[index] == [])
        
    def new_request(self, index):
        x = self.remaining[index].pop()
        for i in self.remaining:
            if i:
                break
        else:
            self.endgame = true
        self.active[index].append(x)
        self.active[index].sort()
        return x

    def is_endgame(self):
        return self.have_endgame and self.endgame

class DummyConnection:
    def __init__(self, events):
        self.events = events

    def send_interested(self):
        self.events.append('interested')
        
    def send_not_interested(self):
        self.events.append('not interested')
        
    def send_request(self, index, begin, length):
        self.events.append(('request', index, begin, length))

    def send_cancel(self, index, begin, length):
        self.events.append(('cancel', index, begin, length))

def test_stops_at_backlog():
    ds = DummyStorage([[(0, 2), (2, 2), (4, 2), (6, 2)]])
    events = []
    d = Downloader(ds, DummyPicker(len(ds.remaining), events), 2, 15, 1, Measure(15), 10)
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
    assert events == ['requested', ('request', 0, 6, 2), 'requested', ('request', 0, 4, 2)]
    del events[:]
    assert ds.remaining == [[(0, 2), (2, 2)]]
    assert ds.active == [[(4, 2), (6, 2)]]
    sd.got_piece(0, 4, 'ab')
    assert events == ['requested', ('request', 0, 2, 2)]
    del events[:]
    assert ds.remaining == [[(0, 2)]]
    assert ds.active == [[(2, 2), (6, 2)]]

def test_got_have_single():
    ds = DummyStorage([[(0, 2)]])
    events = []
    d = Downloader(ds, DummyPicker(len(ds.remaining), events), 2, 15, 1, Measure(15), 10)
    sd = d.make_download(DummyConnection(events))
    assert events == []
    assert ds.remaining == [[(0, 2)]]
    assert ds.active == [[]]
    sd.got_unchoke()
    assert events == []
    assert ds.remaining == [[(0, 2)]]
    assert ds.active == [[]]
    sd.got_have(0)
    assert events == ['got have', 'interested', 'requested', ('request', 0, 0, 2)]
    del events[:]
    assert ds.remaining == [[]]
    assert ds.active == [[(0, 2)]]
    sd.disconnected()
    assert events == ['lost have']

def test_choke_clears_active():
    ds = DummyStorage([[(0, 2)]])
    events = []
    d = Downloader(ds, DummyPicker(len(ds.remaining), events), 2, 15, 1, Measure(15), 10)
    sd1 = d.make_download(DummyConnection(events))
    sd2 = d.make_download(DummyConnection(events))
    assert events == []
    assert ds.remaining == [[(0, 2)]]
    assert ds.active == [[]]
    sd1.got_unchoke()
    sd1.got_have(0)
    assert events == ['got have', 'interested', 'requested', ('request', 0, 0, 2)]
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
    assert events == ['interested', 'requested', ('request', 0, 0, 2), 'not interested']
    del events[:]
    assert ds.remaining == [[]]
    assert ds.active == [[(0, 2)]]
    sd2.got_piece(0, 0, 'ab')
    assert events == ['complete', 'not interested']
    del events[:]
    assert ds.remaining == [[]]
    assert ds.active == [[]]

def test_endgame():
    ds = DummyStorage([[(0, 2)], [(0, 2)], [(0, 2)]], true, 3)
    events = []
    d = Downloader(ds, DummyPicker(len(ds.remaining), events), 10, 15, 3, Measure(15), 10)
    ev1 = []
    ev2 = []
    ev3 = []
    ev4 = []
    sd1 = d.make_download(DummyConnection(ev1))
    sd2 = d.make_download(DummyConnection(ev2))
    sd3 = d.make_download(DummyConnection(ev3))
    sd1.got_unchoke()
    sd1.got_have(0)
    assert ev1 == ['interested', ('request', 0, 0, 2)]
    del ev1[:]
    
    sd2.got_unchoke()
    sd2.got_have(0)
    sd2.got_have(1)
    assert ev2 == ['interested', ('request', 1, 0, 2)]
    del ev2[:]
    
    sd3.got_unchoke()
    sd3.got_have(0)
    sd3.got_have(1)
    sd3.got_have(2)
    assert (ev3 == ['interested', ('request', 2, 0, 2), ('request', 0, 0, 2), ('request', 1, 0, 2)] or 
        ev3 == ['interested', ('request', 2, 0, 2), ('request', 1, 0, 2), ('request', 0, 0, 2)])
    del ev3[:]
    assert ev2 == [('request', 0, 0, 2)]
    del ev2[:]

    sd2.got_piece(0, 0, 'ab')
    assert ev1 == [('cancel', 0, 0, 2), 'not interested']
    del ev1[:]
    assert ev2 == []
    assert ev3 == [('cancel', 0, 0, 2)]
    del ev3[:]

    sd3.got_choke()
    assert ev1 == []
    assert ev2 == []
    assert ev3 == []

    sd3.got_unchoke()
    assert (ev3 == [('request', 2, 0, 2), ('request', 1, 0, 2)] or 
        ev3 == [('request', 1, 0, 2), ('request', 2, 0, 2)])
    del ev3[:]
    assert ev1 == []
    assert ev2 == []

    sd4 = d.make_download(DummyConnection(ev4))
    sd4.got_have_bitfield([true, true, true])
    assert ev4 == ['interested']
    del ev4[:]
    sd4.got_unchoke()
    assert (ev4 == [('request', 2, 0, 2), ('request', 1, 0, 2)] or 
        ev4 == [('request', 1, 0, 2), ('request', 2, 0, 2)])
    assert ev1 == []
    assert ev2 == []
    assert ev3 == []

def test_stops_at_backlog_endgame():
    ds = DummyStorage([[(2, 2), (0, 2)], [(2, 2), (0, 2)], [(0, 2)]], true, 3)
    events = []
    d = Downloader(ds, DummyPicker(len(ds.remaining), events), 3, 15, 3, Measure(15), 10)
    ev1 = []
    ev2 = []
    ev3 = []
    sd1 = d.make_download(DummyConnection(ev1))
    sd2 = d.make_download(DummyConnection(ev2))
    sd3 = d.make_download(DummyConnection(ev3))

    sd1.got_unchoke()
    sd1.got_have(0)
    assert ev1 == ['interested', ('request', 0, 0, 2), ('request', 0, 2, 2)]
    del ev1[:]

    sd2.got_unchoke()
    sd2.got_have(0)
    assert ev2 == []
    sd2.got_have(1)
    assert ev2 == ['interested', ('request', 1, 0, 2), ('request', 1, 2, 2)]
    del ev2[:]

    sd3.got_unchoke()
    sd3.got_have(2)
    assert (ev2 == [('request', 0, 0, 2)] or 
        ev2 == [('request', 0, 2, 2)])
    n = ev2[0][2]
    del ev2[:]

    sd1.got_piece(0, n, 'ab')
    assert ev1 == []
    assert ev2 == [('cancel', 0, n, 2), ('request', 0, 2-n, 2)]

# test piece flunking behavior
# make backlog of 1, one piece with two subpieces
# first connects, requests and gets part 1, requests part 2
# second connects, does nothing
# first gets part 2, flunks check, first requests part 1 and second requests part 2

# test piece flunking behavior endgame
# one piece, two sub-pieces, two peers
# second sub-piece comes in, assert gets request for both sub-pieces from both peers
