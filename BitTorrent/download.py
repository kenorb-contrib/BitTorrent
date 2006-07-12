# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bram Cohen, Uoti Urpala, David Harrison, and Greg Hazel

import random
import logging

from BitTorrent.obsoletepythonsupport import *
from BitTorrent.platform import bttime
from BitTorrent.CurrentRateMeasure import Measure
from BitTorrent.bitfield import Bitfield
from BitTorrent.defer import Deferred

logger = logging.getLogger("BitTorrent.Download")
log = logger.debug

class BadDataGuard(object):

    def __init__(self, download):
        self.download = download
        self.ip = download.connection.ip
        self.multidownload = download.multidownload
        self.stats = self.multidownload.perip[self.ip]
        self.lastindex = None

    def bad(self, index, bump = False):
        self.stats.bad.setdefault(index, 0)
        self.stats.bad[index] += 1
        if self.ip not in self.multidownload.bad_peers:
            self.multidownload.bad_peers[self.ip] = (False, self.stats)
        if self.download is not None:
            self.multidownload.kick(self.download)
            self.download = None
        elif len(self.stats.bad) > 1 and self.stats.numconnections == 1 and \
             self.stats.lastdownload is not None:
            # kick new connection from same IP if previous one sent bad data,
            # mainly to give the algorithm time to find other bad pieces
            # in case the peer is sending a lot of bad data
            self.multidownload.kick(self.stats.lastdownload)
        if len(self.stats.bad) >= 3 and len(self.stats.bad) > \
           self.stats.numgood // 30:
            self.multidownload.ban(self.ip)
        elif bump:
            self.multidownload.active_requests.remove(index)
            self.multidownload.picker.bump(index)

    def good(self, index):
        # lastindex is a hack to only increase numgood for by one for each good
        # piece, however many chunks came from the connection(s) from this IP
        if index != self.lastindex:
            self.stats.numgood += 1
            self.lastindex = index


class Download(object):
    """Implements BitTorrent protocol semantics for downloading over a single
       connection.  See Upload for the protocol semantics in the upload
       direction.  See Connector.Connection for the protocol syntax
       implementation."""

    def __init__(self, multidownload, connection):
        self.multidownload = multidownload
        self.connection = connection
        self.choked = True
        self.interested = False
        self.prefer_full = False
        self.active_requests = set()
        self.measure = Measure(multidownload.config['max_rate_period'])
        self.peermeasure = Measure(
            max(multidownload.storage.piece_size / 10000, 20))
        self.have = Bitfield(multidownload.numpieces)
        self.last = 0
        self.example_interest = None
        self.guard = BadDataGuard(self)
        self.suggested_pieces = []
        self.allowed_fast_pieces = []
        
    def _backlog(self):
        backlog = 2 + int(4 * self.measure.get_rate() /
                          self.multidownload.chunksize)
        if backlog > 50:
            backlog = max(50, int(.075 * backlog))
        return backlog

    def disconnected(self):
        self.multidownload.lost_peer(self)
        if self.have.numfalse == 0:
            self.multidownload.lost_have_all()
        else:
            # arg, slow
            count = 0
            target = len(self.have) - self.have.numfalse
            for i in xrange(len(self.have)):
                if count == target:
                    break
                if self.have[i]:
                    self.multidownload.lost_have(i)
                    count += 1
        self._letgo()
        self.guard.download = None
        
    def _letgo(self):
        if not self.active_requests:
            return
        if self.multidownload.storage.endgame:
            self.active_requests.clear()
            return
        lost = []
        for index, begin, length in self.active_requests:
            self.multidownload.storage.request_lost(index, begin, length)
            self.multidownload.active_requests.remove(index)
            if index not in lost:
                lost.append(index)
        self.active_requests.clear()
        ds = [d for d in self.multidownload.downloads if not d.choked]
        random.shuffle(ds)
        for d in ds:
            d._request_more(lost)
        for d in self.multidownload.downloads:
            if d.choked and not d.interested:
                for l in lost:
                    if d.have[l] and \
                      self.multidownload.storage.want_requests(l):
                        d.interested = True
                        d.connection.send_interested()
                        break
        
    def got_choke(self):
        if not self.choked:
            self.choked = True
            if not self.connection.uses_fast_extension:
                self._letgo()
        
    def got_unchoke(self):
        if self.choked:
            self.choked = False
            if self.interested:
                self._request_more()

    def got_piece(self, index, begin, piece):
        req = (index, begin, len(piece))

        if req not in self.active_requests:
            self.multidownload.discarded_bytes += len(piece)
            if self.connection.uses_fast_extension:
                self.connection.close()
            return
        
        self.active_requests.remove(req)
        
        if self.multidownload.storage.endgame:
            if req not in self.multidownload.all_requests:
                self.multidownload.discarded_bytes += len(piece)
                return
            
            self.multidownload.all_requests.remove(req)

            for d in self.multidownload.downloads:
                if d.interested:
                    if not d.choked:
                        if req in d.active_requests:
                            d.connection.send_cancel(*req)
                            if not self.connection.uses_fast_extension:
                                d.active_requests.remove(req)
                    d.fix_download_endgame()
        else:
            self._request_more()
            
        self.last = bttime()
        self.update_rate(len(piece))
        df = self.multidownload.storage.write(index, begin, piece, self.guard)
        df.addCallback(self._got_piece, index)

    def _got_piece(self, hashchecked, index):
        if hashchecked:
            self.multidownload.hashchecked(index)
        
    def _want(self, index):
        return self.have[index] and \
               self.multidownload.storage.want_requests(index)

    def _request_more(self, indices = []):
        
        if self.choked:
            self._request_when_choked()
            return
        #log( "_request_more.active_requests=%s" % self.active_requests )
        b = self._backlog()
        if len(self.active_requests) >= b:
            return
        if self.multidownload.storage.endgame:
            self.fix_download_endgame()
            return

        self.suggested_pieces = [i for i in self.suggested_pieces 
            if not self.multidownload.storage.do_I_have(i)]
        lost_interests = []
        while len(self.active_requests) < b:
            if not indices:
                interest = self.multidownload.picker.next(self.have,
                                    self.multidownload.active_requests,
                                    self.multidownload.storage.full_pieces,
                                    self.suggested_pieces)
            else:
                interest = None
                for i in indices:
                    if self.have[i] and \
                            self.multidownload.storage.want_requests(i):
                        interest = i
                        break
            if interest is None:
                break
            if not self.interested:
                self.interested = True
                self.connection.send_interested()
            # an example interest created by from_behind is preferable
            if self.example_interest is None:
                self.example_interest = interest

            # request as many chunks of interesting piece as fit in backlog.
            while len(self.active_requests) < b:
                begin, length = self.multidownload.storage.new_request(interest,
                                                                       self.prefer_full)
                self.multidownload.active_requests_add(interest)
                self.active_requests.add((interest, begin, length))
                self.connection.send_request(interest, begin, length)
                if not self.multidownload.storage.want_requests(interest):
                    lost_interests.append(interest)
                    break
        if not self.active_requests and self.interested:
            self.interested = False
            self.connection.send_not_interested()
        self._check_lost_interests(lost_interests)
        if self.multidownload.storage.endgame:
            self.multidownload.all_requests = set()
            for d in self.multidownload.downloads:
                self.multidownload.all_requests.update(d.active_requests)
            for d in self.multidownload.downloads:
                d.fix_download_endgame()

    def _check_lost_interests(self, lost_interests):
        """
           Notify other downloads that these pieces are no longer interesting.

           @param lost_interests: list of pieces that have been fully 
               requested.
        """
        if not lost_interests:
            return
        for d in self.multidownload.downloads:
            if d.active_requests or not d.interested:
                continue
            if d.example_interest is not None and not \
                    self.multidownload.storage.have[d.example_interest] and \
                    self.multidownload.storage.want_requests(d.example_interest):
                continue
            # any() does not exist until python 2.5
            #if not any([d.have[lost] for lost in lost_interests]):
            #    continue
            for lost in lost_interests:
                if d.have[lost]:
                    break
            else:
                continue
            interest = self.multidownload.picker.from_behind(self.have,
                            self.multidownload.storage.full_pieces)
            if interest is None:
                d.interested = False
                d.connection.send_not_interested()
            else:
                d.example_interest = interest

    def _request_when_choked(self):
        self.allowed_fast_pieces = [i for i in self.allowed_fast_pieces
            if not self.multidownload.storage.do_I_have(i)]
        if not self.allowed_fast_pieces:
            return
        fast = list(self.allowed_fast_pieces)

        b = self._backlog()
        lost_interests = []
        while len(self.active_requests) < b:

            while fast:
                piece = fast.pop()
                if self.have[piece] \
                   and self.multidownload.storage.want_requests(piece):
                    break
            else:
                break # no unrequested pieces among allowed fast.

            # request chunks until no more chunks or no more room in backlog.
            while len(self.active_requests) < b:
                begin, length = self.multidownload.storage.new_request(piece,
                                                                       self.prefer_full)
                self.multidownload.active_requests_add(piece)
                self.active_requests.add((piece, begin, length))
                self.connection.send_request(piece, begin, length)
                if not self.multidownload.storage.want_requests(piece):
                    lost_interests.append(piece)
                    break
        self._check_lost_interests(lost_interests)
        if self.multidownload.storage.endgame:
            self.multidownload.all_requests = set()
            for d in self.multidownload.downloads:
                self.multidownload.all_requests.update(d.active_requests)
            for d in self.multidownload.downloads:
                d.fix_download_endgame()
                
    def fix_download_endgame(self):
        want = []
        for a in self.multidownload.all_requests:
            if not self.have[a[0]]:
                continue
            if a in self.active_requests:
                continue
            want.append(a)

        if self.interested and not self.active_requests and not want:
            self.interested = False
            self.connection.send_not_interested()
            return
        if not self.interested and want:
            self.interested = True
            self.connection.send_interested()
        if self.choked:
            return
        random.shuffle(want)
        for req in want[:self._backlog() - len(self.active_requests)]:
            self.active_requests.add(req)
            self.connection.send_request(*req)
        
    def got_have(self, index):
        if self.have[index]:
            return
        if index == self.multidownload.numpieces-1:
            self.peermeasure.update_rate(self.multidownload.storage.total_length-
              (self.multidownload.numpieces-1)*self.multidownload.storage.piece_size)
        else:
            self.peermeasure.update_rate(self.multidownload.storage.piece_size)
        self.have[index] = True
        self.multidownload.got_have(index)
        if self.multidownload.storage.get_amount_left() == 0 and self.have.numfalse == 0:
            self.connection.close()
            return
        if self.multidownload.storage.endgame:
            self.fix_download_endgame()
        elif self.multidownload.storage.want_requests(index):
            self._request_more([index]) # call _request_more whether choked.
            if self.choked:
                if not self.interested:
                    self.interested = True
                    self.connection.send_interested()
        
    def got_have_bitfield(self, have):
        if have.numfalse == 0:
            self._got_have_all(have)
            return
        self.have = have
        # arg, slow
        count = 0
        target = len(self.have) - self.have.numfalse
        for i in xrange(len(self.have)):
            if count == target:
                break
            if self.have[i]:
                self.multidownload.got_have(i)
                count += 1
        if self.multidownload.storage.endgame:
            for piece, begin, length in self.multidownload.all_requests:
                if self.have[piece]:
                    self.interested = True
                    self.connection.send_interested()
                    return
        for piece in self.multidownload.storage.iter_want():
            if self.have[piece]:
                self.interested = True
                self.connection.send_interested()
                return

    def _got_have_all(self, have=None):
        if self.multidownload.storage.get_amount_left() == 0:
            self.connection.close()
            return
        if have is None:
            # bleh
            n = self.multidownload.numpieces
            rlen, extra = divmod(n, 8)
            if extra:
                extra = chr((0xFF << (8 - extra)) & 0xFF)
            else:
                extra = ''
            s = (chr(0xFF) * rlen) + extra
            have = Bitfield(n, s)
        self.have = have
        self.multidownload.got_have_all()
        if self.multidownload.storage.endgame:
            for piece, begin, length in self.multidownload.all_requests:
                self.interested = True
                self.connection.send_interested()
                return
        for i in self.multidownload.storage.iter_want():
            self.interested = True
            self.connection.send_interested()
            return
        
    def update_rate(self, amount):
        self.measure.update_rate(amount)
        self.multidownload.update_rate(amount)

    def get_rate(self):
        return self.measure.get_rate()

    def is_snubbed(self):
        return bttime() - self.last > self.multidownload.snub_time

    def got_have_none(self):
        pass  # currently no action is taken when have_none is received.
              # The picker already assumes the local peer has none of the
              # pieces until got_have is called.

    def got_have_all(self):
        assert self.connection.uses_fast_extension
        self._got_have_all()

    def got_suggest_piece(self, piece):
        assert self.connection.uses_fast_extension
        if not self.multidownload.storage.do_I_have(piece): 
          self.suggested_pieces.append(piece)
        self._request_more() # try to request more. Just returns if choked.

    def got_allowed_fast(self,piece):
        """Upon receiving this message, the multidownload knows that it is
           allowed to download the specified piece even when choked."""
        #log( "got_allowed_fast %d" % piece )
        assert self.connection.uses_fast_extension

        if not self.multidownload.storage.do_I_have(piece): 
            if piece not in self.allowed_fast_pieces:
                self.allowed_fast_pieces.append(piece)
                random.shuffle(self.allowed_fast_pieces)  # O(n) but n is small.
        self._request_more()  # will try to request.  Handles cases like
                              # whether neighbor has "allowed fast" piece.

    def got_reject_request(self, piece, begin, length):
        if not self.connection.uses_fast_extension:
            self.connection.close()
            return
        req = (piece, begin, length) 

        if req not in self.active_requests:
            self.connection.close()
            return
        self.active_requests.remove(req)

        if self.multidownload.storage.endgame:
            return

        self.multidownload.storage.request_lost(*req)
        if not self.choked:
            self._request_more()
        ds = [d for d in self.multidownload.downloads if not d.choked]
        random.shuffle(ds)
        for d in ds:
            d._request_more([piece])
            
        for d in self.multidownload.downloads:
            if d.choked and not d.interested:
                if d.have[piece] and \
                  self.multidownload.storage.want_requests(piece):
                    d.interested = True
                    d.connection.send_interested()
                    break

