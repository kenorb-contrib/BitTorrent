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

from cStringIO import StringIO
from socket import error as socketerror
from BitTorrent.RawServer_twisted import Handler

protocol_name = 'BitTorrent protocol'

# header, reserved, download id, my id, [length, message]


class NatCheck(Handler):

    def __init__(self, resultfunc, downloadid, peerid, ip, port, rawserver):
        self.resultfunc = resultfunc
        self.downloadid = downloadid
        self.peerid = peerid
        self.ip = ip
        self.port = port
        self.closed = False
        self.buffer = StringIO()
        self.next_len = 1
        self.next_func = self.read_header_len
        rawserver.start_connection((ip, port), self)

    def connection_made(self, s):
        self.connection = s
        self.connection.write(chr(len(protocol_name)) + protocol_name +
                              (chr(0) * 8) + self.downloadid)

    def connection_failed(self, s, exception):
        self.answer(False)

    def answer(self, result):
        self.closed = True
        try:
            self.connection.close()
        except AttributeError:
            pass
        self.resultfunc(result, self.downloadid, self.peerid, self.ip, self.port)

    def read_header_len(self, s):
        if ord(s) != len(protocol_name):
            return None
        return len(protocol_name), self.read_header

    def read_header(self, s):
        if s != protocol_name:
            return None
        return 8, self.read_reserved

    def read_reserved(self, s):
        return 20, self.read_download_id

    def read_download_id(self, s):
        if s != self.downloadid:
            return None
        return 20, self.read_peer_id

    def read_peer_id(self, s):
        if s != self.peerid:
            return None
        self.answer(True)
        return None

    def data_came_in(self, connection, s):
        while True:
            if self.closed:
                return
            i = self.next_len - self.buffer.tell()
            if i > len(s):
                self.buffer.write(s)
                return
            self.buffer.write(s[:i])
            s = s[i:]
            m = self.buffer.getvalue()
            self.buffer.reset()
            self.buffer.truncate()
            x = self.next_func(m)
            if x is None:
                if not self.closed:
                    self.answer(False)
                return
            self.next_len, self.next_func = x

    def connection_lost(self, connection):
        if not self.closed:
            self.closed = True
            self.resultfunc(False, self.downloadid, self.peerid, self.ip, self.port)

    def connection_flushed(self, connection):
        pass
