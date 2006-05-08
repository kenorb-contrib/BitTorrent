# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bram Cohen

from BitTorrent.CurrentRateMeasure import Measure
from BitTorrent.Connector import Connection
import BitTorrent.Torrent
import BitTorrent.Connector
from sha import sha
import logging
logger = logging.getLogger("BitTorrent.Upload")
log = logger.debug

class Upload(object):
    """Upload over a single connection."""
    
    def __init__(self, connection, ratelimiter, totalup,choker,
                 storage, max_slice_length, max_rate_period, num_fast,
                 torrent):
        assert isinstance(connection, BitTorrent.Connector.Connection)
        assert isinstance(torrent, BitTorrent.Torrent.Torrent)
        self.connection = connection
        self.ratelimiter = ratelimiter
        self.totalup = totalup
        self.torrent = torrent
        self.choker = choker
        self.num_fast = num_fast
        self.storage = storage
        self.max_slice_length = max_slice_length
        self.max_rate_period = max_rate_period
        self.choked = True
        self.unchoke_time = None
        self.interested = False
        self.buffer = []    # contains piece data about to be sent.
        self.measure = Measure(max_rate_period)
        self.allowed_fast_pieces = []
        if connection.uses_fast_extension:
            if storage.get_amount_left() == 0:
                connection.send_have_all();
            elif storage.do_I_have_anything():
                connection.send_bitfield(storage.get_have_list())
            else:
                connection.send_have_none();
            self._send_allowed_fast_list()
        elif storage.do_I_have_anything():
                connection.send_bitfield(storage.get_have_list())


    def _send_allowed_fast_list(self):
        """Computes and sends the 'allowed fast' set.  """

        self.allowed_fast_pieces = self._compute_allowed_fast_list(
                        self.torrent.infohash,
                        self.connection.ip, self.num_fast,
                        self.storage.get_num_pieces())

        #log( "Upload: fast_list=%s" % str(self.allowed_fast_pieces))
        for index in self.allowed_fast_pieces:
            self.connection.send_allowed_fast(index)

    def _compute_allowed_fast_list(self,infohash,ip, num_fast, num_pieces):
        
        #log( "compute_allowed_fast_list ip=%s, num_fast=%s, num_pieces=%s" %
        #    ( ip, num_fast, num_pieces ) ) 

        # if ipv4 then  (for now assume IPv4)
        iplist = [int(x) for x in ip.split(".")]

        # classful heuristic.
        if iplist[0] | 0x7F==0xFF or iplist[0] & 0xC0==0x80: # class A or B
            iplist = [chr(iplist[0]),chr(iplist[1]),chr(0),chr(0)]
        else:
            iplist = [chr(iplist[0]),chr(iplist[1]),chr(iplist[2]),chr(0)]
        h = "".join(iplist)
        h = "".join([h,infohash])
        fastlist = []
        assert num_pieces < 2**32
        if num_pieces <= num_fast:
            return range(num_pieces) # <---- this would be bizarre
        while True:
            h = sha(h).digest() # rehash hash to generate new random string.
            #log( "infohash=%s" % h.encode('hex' ) )
            for i in xrange(5):
                j = i*4
                y = [ord(x) for x in h[j:j+4]]
                z = (y[0] << 24) + (y[1]<<16) + (y[2]<<8) + y[3]
                index = int(z % num_pieces)
                #log("z=%s=%d, index=%d" % ( hex(z), z, index ))
                if index not in fastlist:
                    fastlist.append(index)
                    if len(fastlist) >= num_fast:
                        return fastlist

    def got_not_interested(self):
        if self.interested:
            self.interested = False
            self.choker.not_interested(self.connection)

    def got_interested(self):
        if not self.interested:
            self.interested = True
            self.choker.interested(self.connection)

    def get_upload_chunk(self, index, begin, length):
        df = self.storage.read(index, begin, length)
        def fail(e):
            log( "get_upload_chunk failed: %s" % str(e[1]) )
            self.connection.close()
            return None
        def update_rate(piece):  # piece is actual data.
            if piece is None:
                return fail("Piece is None")
            return (index, begin, piece)
        df.addCallback(update_rate)
        df.addErrback(fail)
        return df

    def update_rate(self, bytes):
        self.measure.update_rate(bytes)
        self.totalup.update_rate(bytes)

    def got_request(self, index, begin, length):
        if not self.interested or length > self.max_slice_length:
            self.connection.close()
            return
        if index in self.allowed_fast_pieces or not self.connection.choke_sent:
            df = self.get_upload_chunk(index, begin, length)
            def got_piece(piece):  # 3rd elem in tuple is piece data.
                if self.connection.closed or piece is None:
                    return
                index, begin, piece = piece # piece changes from tuple to data.
                if self.choked:
                    if not self.connection.uses_fast_extension:
                        return
                    if index not in self.allowed_fast_pieces:
                        self.connection.send_reject_request(
                            index, begin, len(piece))
                        return
                self.buffer.append(((index, begin, len(piece)), piece))
                if self.connection.next_upload is None and \
                       self.connection.connection.is_flushed():
                    self.ratelimiter.queue(self.connection)
            df.addCallback(got_piece)
        elif self.connection.uses_fast_extension:
            self.connection.send_reject_request( index, begin, length )
            
    def got_cancel(self, index, begin, length):
        req = (index, begin, length)
        for pos, (r, p) in enumerate(self.buffer):
            if r == req:
                del self.buffer[pos]
                if self.connection.uses_fast_extension:
                    self.connection.send_reject_request(*req)
                break

    def choke(self):
        if not self.choked:
            self.choked = True
            self.connection.send_choke()

    def sent_choke(self):
        assert self.choked
        if self.connection.uses_fast_extension:
            b2 = []
            for r in self.buffer:
                ((index,begin,length),piecedata) = r
                if index not in self.allowed_fast_pieces:
                    self.connection.send_reject_request( index, begin, length )
                else:
                    b2.append(r)
            self.buffer = b2
        else:
            del self.buffer[:]

    def unchoke(self, time):
        if self.choked:
            self.choked = False
            self.unchoke_time = time
            self.connection.send_unchoke()

    def has_queries(self):
        return len(self.buffer) > 0

    def get_rate(self):
        return self.measure.get_rate()
