# Written by Bram Cohen
# see LICENSE.txt for license information

from BitTornado.CurrentRateMeasure import Measure
from BitTornado.bitfield import Bitfield
from random import shuffle
from time import time
try:
    True
except:
    True = 1
    False = 0

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

    def failed(self, index, bump = False):
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
        self.connection = connection
        self.choked = True
        self.interested = False
        self.active_requests = []
        self.measure = Measure(downloader.max_rate_period)
        self.peermeasure = Measure(downloader.max_rate_period)
        self.have = Bitfield(downloader.numpieces)
        self.last = 0
        self.example_interest = None
        self.backlog = 2
        self.ip = connection.get_ip()
        self.guard = BadDataGuard(self)

    def _backlog(self):
        self.backlog = 2+int(4*self.measure.get_rate()/self.downloader.chunksize)
        return self.backlog
    
    def disconnected(self):
        self.downloader.lost_peer(self)
        if self.have.complete():
            self.downloader.picker.lost_seed()
        else:
            for i in xrange(len(self.have)):
                if self.have[i]:
                    self.downloader.picker.lost_have(i)
        if self.have.complete() and self.downloader.storage.is_endgame():
            self.downloader.add_disconnected_seed(self.connection.get_readable_id())
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
                        d.send_interested()
                        break

    def got_choke(self):
        if not self.choked:
            self.choked = True
            self._letgo()

    def got_unchoke(self):
        if self.choked:
            self.choked = False
            if self.interested:
                self._request_more()

    def is_choked(self):
        return self.choked

    def is_interested(self):
        return self.interested

    def send_interested(self):
        if not self.interested:
            self.interested = True
            self.connection.send_interested()

    def send_not_interested(self):
        if self.interested:
            self.interested = False
            self.connection.send_not_interested()

    def got_piece(self, index, begin, piece):
        length = len(piece)
        try:
            self.active_requests.remove((index, begin, length))
        except ValueError:
            self.downloader.discarded += length
            return False
        if self.downloader.endgamemode:
            self.downloader.all_requests.remove((index, begin, length))
        self.last = time()
        self.measure.update_rate(length)
        self.downloader.measurefunc(length)
        self.downloader.downmeasure.update_rate(length)
        if not self.downloader.storage.piece_came_in(index, begin, piece, self.guard):
            self.downloader.piece_flunked(index)
            return False
        if self.downloader.storage.do_I_have(index):
            self.downloader.picker.complete(index)
        if self.downloader.endgamemode:
            for d in self.downloader.downloads:
                if d is not self:
                  if d.interested:
                    if d.choked:
                        assert not d.active_requests
                        d.fix_download_endgame()
                    else:
                        try:
                            d.active_requests.remove((index, begin, length))
                        except ValueError:
                            continue
                        d.connection.send_cancel(index, begin, length)
                        d.fix_download_endgame()
                  else:
                      assert not d.active_requests
        self._request_more()
        self.downloader.check_complete(index)
        return self.downloader.storage.do_I_have(index)

#    def _want(self, index):
#        return self.have[index] and self.downloader.storage.do_I_have_requests(index)

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
                interest = self.downloader.picker.next(self.have,
                                   self.downloader.storage.do_I_have_requests,
                                   self.downloader.too_many_partials())
            else:
                interest = None
                for i in indices:
                    if self.have[i] and self.downloader.storage.do_I_have_requests(i):
                        interest = i
                        break
            if interest is None:
                break
            self.example_interest = interest
            self.send_interested()
            loop = True
            while len(self.active_requests) < self.backlog and loop:
                begin, length = self.downloader.storage.new_request(interest)
                self.downloader.picker.requested(interest)
                self.active_requests.append((interest, begin, length))
                self.connection.send_request(interest, begin, length)
                if not self.downloader.storage.do_I_have_requests(interest):
                    loop = False
                    lost_interests.append(interest)
        if not self.active_requests:
            self.send_not_interested()
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
                interest = self.downloader.picker.next(d.have,
                                   self.downloader.storage.do_I_have_requests,
                                   self.downloader.too_many_partials())
                if interest is None:
                    d.send_not_interested()
                else:
                    d.example_interest = interest
        if self.downloader.storage.is_endgame():
            self.downloader.endgamemode = True
            assert not self.downloader.all_requests
            for d in self.downloader.downloads:
                if d.active_requests:
                    assert d.interested and not d.choked
                self.downloader.all_requests.extend(d.active_requests)
            for d in self.downloader.downloads:
                d.fix_download_endgame()

    def fix_download_endgame(self):
        if len(self.active_requests) >= self._backlog():
            return
        want = [a for a in self.downloader.all_requests if self.have[a[0]] and a not in self.active_requests]
        if not (self.active_requests or want):
            self.send_not_interested()
            return
        if want:
            self.send_interested()
        if self.choked:
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
        self.have[index] = True
        self.downloader.picker.got_have(index)
        if self.have.complete():
            self.downloader.picker.became_seed()
            if self.downloader.picker.am_I_complete():
                self.downloader.add_disconnected_seed(self.connection.get_readable_id())
                self.connection.close()
                return
        if self.downloader.endgamemode:
            self.fix_download_endgame()
        elif self.downloader.storage.do_I_have_requests(index):
            if not self.choked:
                self._request_more([index])
            else:
                self.send_interested()

    def got_have_bitfield(self, have):
        if self.downloader.picker.am_I_complete() and have.complete():
            if self.downloader.super_seeding:
                self.connection.send_bitfield(have.tostring()) # be nice, show you're a seed too
            self.connection.close()
            self.downloader.add_disconnected_seed(self.connection.get_readable_id())
            return
        self.have = have
        if have.complete():
            self.downloader.picker.got_seed()
        else:
            for i in xrange(len(have)):
                if have[i]:
                    self.downloader.picker.got_have(i)
        if self.downloader.endgamemode:
            for piece, begin, length in self.downloader.all_requests:
                if self.have[piece]:
                    self.send_interested()
                    break
            return
        for i in xrange(len(have)):
            if have[i] and self.downloader.storage.do_I_have_requests(i):
                self.send_interested()
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
        self.kickbans_halted = False
        self.super_seeding = False
        self.endgamemode = False
        self.all_requests = []
        self.discarded = 0L

    def make_download(self, connection):
        ip = connection.get_ip()
        if self.perip.has_key(ip):
            perip = self.perip[ip]
        else:
            perip = self.perip.setdefault(ip, PerIPStats(ip))
        perip.peerid = connection.get_readable_id()
        perip.numconnections += 1
        d = SingleDownload(self, connection)
        perip.lastdownload = d
        self.downloads.append(d)
        return d

    def piece_flunked(self, index):
        if self.endgamemode:
            assert self.downloads
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
        ds = [d for d in self.downloads if not d.interested and d.have[index]]
        for d in ds:
            d.example_interest = index
            d.send_interested()

    def has_downloaders(self):
        return len(self.downloads)

    def lost_peer(self, download):
        ip = download.ip
        self.perip[ip].numconnections -= 1
        if self.perip[ip].lastdownload == download:
            self.perip[ip].lastdownload = None
        self.downloads.remove(download)
        if self.endgamemode and not self.downloads: # all peers gone
            self.storage.reset_endgame(self.all_requests)
            self.endgamemode = False
            self.all_requests = []


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
            self.kickbans_ok = False
            self.kickbans_halted = True
        return self.kickbans_ok and len(self.downloads) > 2

    def try_kick(self, download):
        if self._check_kicks_ok():
            download.guard.download = None
            ip = download.ip
            id = download.connection.get_readable_id()
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
        self.super_seeding = True

    def check_complete(self, index):
        if self.picker.am_I_complete():
            assert not self.all_requests
            for d in [i for i in self.downloads if i.have.complete()]:
                d.connection.send_have(index)   # be nice, tell the other seed you completed
                self.add_disconnected_seed(d.connection.get_readable_id())
                d.connection.close()
            return True
        return False

    def too_many_partials(self):
        return len(self.storage.dirty) > (len(self.downloads)/2)
