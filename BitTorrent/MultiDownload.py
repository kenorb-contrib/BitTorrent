# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bram Cohen, Uoti Urpala

import array
import random

from BTL.sparse_set import SparseSet
from BTL.obsoletepythonsupport import set
from BitTorrent.Download import Download

SPARSE_SET = True
if SPARSE_SET:
    from BitTorrent.PieceSetBuckets import PieceSetBuckets
else:
    from BitTorrent.PieceSetBuckets import SortedPieceBuckets, resolve_typecode

RENDER = False

class PerIPStats(object):

    def __init__(self):
        self.numgood = 0
        self.bad = {}
        self.numconnections = 0
        self.lastdownload = None
        self.peerid = None

class MultiDownload(object):

    def __init__(self, config, storage, urlage, picker, numpieces,
                 finished, kickfunc, banfunc):
        self.config = config
        self.storage = storage
        self.urlage = urlage
        self.picker = picker
        self.rerequester = None
        self.connection_manager = None
        self.chunksize = config['download_chunk_size']
        self.numpieces = numpieces
        self.finished = finished
        self.snub_time = config['snub_time']
        self.kickfunc = kickfunc
        self.banfunc = banfunc
        self.downloads = []
        self.perip = {}
        self.bad_peers = {}
        self.discarded_bytes = 0
        self.useful_received_listeners = set()
        
        if SPARSE_SET:
            self.piece_states = PieceSetBuckets()
            nothing = SparseSet(xrange(self.numpieces))
            self.piece_states.buckets.append(nothing)

            # I hate this
            nowhere = [(i, 0) for i in xrange(self.numpieces)]
            self.piece_states.place_in_buckets = dict(nowhere)
        else:
            typecode = resolve_typecode(self.numpieces)
            self.piece_states = SortedPieceBuckets(typecode)
            nothing = array.array(typecode, range(self.numpieces))
            self.piece_states.buckets.append(nothing)

            # I hate this
            nowhere = [(i, (0, i)) for i in xrange(self.numpieces)]
            self.piece_states.place_in_buckets = dict(nowhere)
        
        self.last_update = 0
        self.active_requests = set(self.storage.inactive_requests.iterkeys())
        self.all_requests = set()


    def attach_connection_manager(self, connection_manager):
        self.connection_manager = connection_manager

    def aggregate_piece_states(self):
        d = {}
        d['h'] = self.storage.have_set
        d['t'] = self.active_requests

        for i, bucket in enumerate(self.piece_states.buckets):
            d[i] = bucket

        r = (self.numpieces, self.last_update, d)
        return r

    def get_adjusted_distributed_copies(self):
        # compensate for the fact that piece picker does no
        # contain all the pieces
        num = self.picker.get_distributed_copies()
        percent_have = (float(len(self.storage.have_set)) /
                        float(self.numpieces))
        num += percent_have
        if self.rerequester and self.rerequester.tracker_num_seeds:
            num += self.rerequester.tracker_num_seeds
        return num

    def active_requests_add(self, r):
        self.last_update += 1
        self.active_requests.add(r)
        
    def active_requests_remove(self, r):
        self.last_update += 1
        # wtf! this is so ridiculous. is it active or not?
        self.active_requests.discard(r)

    def got_have(self, piece):
        self.picker.got_have(piece)
        self.last_update += 1
        p = self.piece_states
        p.add(piece, p.remove(piece) + 1)

    def got_have_all(self):
        self.picker.got_have_all()
        self.last_update += 1
        self.piece_states.prepend_bucket()

    def lost_have(self, piece):
        self.picker.lost_have(piece)
        self.last_update += 1
        p = self.piece_states
        p.add(piece, p.remove(piece) - 1)

    def lost_have_all(self):
        self.picker.lost_have_all()
        self.last_update += 1
        self.piece_states.popleft_bucket()

    def hashchecked(self, index):
        if not self.storage.do_I_have(index):
            if self.storage.endgame:
                while self.storage.want_requests(index):
                    nb, nl = self.storage.new_request(index)
                    self.all_requests.add((index, nb, nl))
                for d in self.downloads:
                    d.fix_download_endgame()
            else:
                ds = [d for d in self.downloads if not d.choked]
                random.shuffle(ds)
                for d in ds:
                    d._request_more([index])
            return

        self.picker.complete(index)
        self.active_requests_remove(index)

        self.connection_manager.hashcheck_succeeded(index)

        if self.storage.have.numfalse == 0:
            for d in self.downloads:
                if d.have.numfalse == 0:
                    d.connection.close()

            self.finished()

    def time_until_rate(self):
        rate = self.config['max_download_rate']

        # obey "no max" setting
        if rate == -1:
            return 0

        possible_burst = self.burst_avg
        # substract the possible burst so that the download rate is a maximum
        adjusted_rate = rate - possible_burst
        # don't let it go to 0, just because the burst is greater than the
        # desired rate. this could be improved by no throttling and unthrottling
        # all connections at once.
        adjusted_rate = max(adjusted_rate, possible_burst)
        # don't let it go above the explicit max either.
        adjusted_rate = min(adjusted_rate, rate)

        # we need to call this because the rate measure is dumb
        self.total_downmeasure.get_rate()
        t = self.total_downmeasure.time_until_rate(adjusted_rate)
        #print "DOWNLOAD: burst_size:", possible_burst, "rate:", self.total_downmeasure.get_rate(), "rate_limit:", rate, "new_rate:", adjusted_rate, t
        return t

    def check_rate(self):
        t = self.time_until_rate()
        if t > 0:
            self.postpone_func()
        else:
            self.resume_func()

    def update_rate(self, amount):
        self.burst_avg = (self.burst_avg/2.0 + float(amount)/2.0)
        self.measurefunc(amount)
        self.total_downmeasure.update_rate(amount)
        self.downmeasure.update_rate(amount)
        self.check_rate()

    def get_rate(self):
        return self.downmeasure.get_rate()

    def make_download(self, connection):
        ip = connection.ip
        perip = self.perip.setdefault(ip, PerIPStats())
        perip.numconnections += 1
        d = Download(self, connection)
        d.add_useful_received_listener(self.fire_useful_received_listeners) 
        perip.lastdownload = d
        perip.peerid = connection.id
        self.downloads.append(d)
        return d

    def add_useful_received_listener(self,listener):
        """Listeners are called for useful arrivals to any of the downloaders
           managed by this MultiDownload object.
           (see Download.add_useful_received_listener for which listeners are
           called for bytes received by that particular Download."""
        self.useful_received_listeners.add(listener)

    def remove_useful_received_listener(self,listener):
        self.useful_received_listeners.remove(listener)

    def fire_useful_received_listeners(self,bytes):
        for f in self.useful_received_listeners:
            f(bytes)
            
    def lost_peer(self, download):
        self.downloads.remove(download)
        ip = download.connection.ip
        self.perip[ip].numconnections -= 1
        if self.perip[ip].lastdownload == download:
            self.perip[ip].lastdownload = None

    def kick(self, download):
        if not self.config['retaliate_to_garbled_data']:
            return
        ip = download.connection.ip
        peerid = download.connection.id
        # kickfunc will schedule connection.close() to be executed later; we
        # might now be inside RawServer event loop with events from that
        # connection already queued, and trying to handle them after doing
        # close() now could cause problems.
        self.kickfunc(download.connection)

    def ban(self, ip):
        if not self.config['retaliate_to_garbled_data']:
            return
        self.banfunc(ip)
        self.bad_peers[ip] = (True, self.perip[ip])

