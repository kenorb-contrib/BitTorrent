# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Written by Bram Cohen

from BitTorrent.CurrentRateMeasure import Measure


class Upload(object):

    def __init__(self, connection, ratelimiter, totalup, totalup2, choker,
                 storage, max_slice_length, max_rate_period):
        self.connection = connection
        self.ratelimiter = ratelimiter
        self.totalup = totalup
        self.totalup2 = totalup2
        self.choker = choker
        self.storage = storage
        self.max_slice_length = max_slice_length
        self.max_rate_period = max_rate_period
        self.choked = True
        self.unchoke_time = None
        self.interested = False
        self.buffer = []
        self.measure = Measure(max_rate_period)
        if storage.do_I_have_anything():
            connection.send_bitfield(storage.get_have_list())

    def got_not_interested(self):
        if self.interested:
            self.interested = False
            del self.buffer[:]
            self.choker.not_interested(self.connection)

    def got_interested(self):
        if not self.interested:
            self.interested = True
            self.choker.interested(self.connection)

    def get_upload_chunk(self):
        if not self.buffer:
            return None
        index, begin, length = self.buffer.pop(0)
        piece = self.storage.get_piece(index, begin, length)
        if piece is None:
            self.connection.close()
            return None
        self.measure.update_rate(len(piece))
        self.totalup.update_rate(len(piece))
        self.totalup2.update_rate(len(piece))
        return (index, begin, piece)

    def got_request(self, index, begin, length):
        if not self.interested or length > self.max_slice_length:
            self.connection.close()
            return
        if not self.connection.choke_sent:
            self.buffer.append((index, begin, length))
            if self.connection.next_upload is None and \
                   self.connection.connection.is_flushed():
                self.ratelimiter.queue(self.connection)

    def got_cancel(self, index, begin, length):
        try:
            self.buffer.remove((index, begin, length))
        except ValueError:
            pass

    def choke(self):
        if not self.choked:
            self.choked = True
            self.connection.send_choke()

    def sent_choke(self):
        assert self.choked
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
