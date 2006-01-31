# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Originally written by Bram Cohen, heavily modified by Uoti Urpala

# required for python 2.2
from __future__ import generators

from binascii import b2a_hex
from struct import pack, unpack

from BitTorrent.RawServer_magic import Handler
from BitTorrent.bitfield import Bitfield
from BitTorrent.obsoletepythonsupport import *

def toint(s):
    return unpack("!i", s)[0]

def tobinary(i):
    return pack("!i", i)

CHOKE = chr(0)
UNCHOKE = chr(1)
INTERESTED = chr(2)
NOT_INTERESTED = chr(3)
# index
HAVE = chr(4)
# index, bitfield
BITFIELD = chr(5)
# index, begin, length
REQUEST = chr(6)
# index, begin, piece
PIECE = chr(7)
# index, begin, piece
CANCEL = chr(8)

# 2-byte port message
PORT = chr(9)

# reserved flags
DHT = 1
FLAGS = '\0' * 7 + '\1'
protocol_name = 'BitTorrent protocol'


class Connection(Handler):

    def __init__(self, encoder, connection, id, is_local):
        self.encoder = encoder
        self.connection = connection
        self.connection.handler = self
        self.id = id
        self.ip = connection.ip
        self.locally_initiated = is_local
        self.complete = False
        self.closed = False
        self.got_anything = False
        self.next_upload = None
        self.upload = None
        self.download = None
        self._buffer = []
        self._buffer_len = 0
        self._reader = self._read_messages()
        self._next_len = self._reader.next()
        self._partial_message = None
        self._outqueue = []
        self.choke_sent = True
        self.uses_dht = False
        self.dht_port = None
        if self.locally_initiated:
            connection.write(chr(len(protocol_name)) + protocol_name +
                FLAGS + self.encoder.download_id)
            if self.id is not None:
                connection.write(self.encoder.my_id)

    def close(self):
        if not self.closed:
            self.connection.close()
            self._sever()

    def send_interested(self):
        self._send_message(INTERESTED)

    def send_not_interested(self):
        self._send_message(NOT_INTERESTED)

    def send_choke(self):
        if self._partial_message is None:
            self._send_message(CHOKE)
            self.choke_sent = True
            self.upload.sent_choke()

    def send_unchoke(self):
        if self._partial_message is None:
            self._send_message(UNCHOKE)
            self.choke_sent = False

    def send_port(self, port):
        self._send_message(PORT+pack('!H', port))
        
    def send_request(self, index, begin, length):
        self._send_message(pack("!ciii", REQUEST, index, begin, length))

    def send_cancel(self, index, begin, length):
        self._send_message(pack("!ciii", CANCEL,index, begin, length))

    def send_bitfield(self, bitfield):
        self._send_message(BITFIELD + bitfield)

    def send_have(self, index):
        self._send_message(pack("!ci", HAVE, index))

    def send_keepalive(self):
        self._send_message('')

    def send_partial(self, bytes):
        if self.closed:
            return 0
        if self._partial_message is None:
            s = self.upload.get_upload_chunk()
            if s is None:
                return 0
            index, begin, piece = s
            self._partial_message = pack("!icii%ss" % len(piece), len(piece) + 9, PIECE,
                                    index, begin, piece)
        if bytes < len(self._partial_message):
            self.upload.update_rate(bytes)
            self.connection.write(buffer(self._partial_message, 0, bytes))
            self._partial_message = buffer(self._partial_message, bytes)
            return bytes

        queue = [str(self._partial_message)]
        self._partial_message = None
        if self.choke_sent != self.upload.choked:
            if self.upload.choked:
                self._outqueue.append(pack("!ic", 1, CHOKE))
                self.upload.sent_choke()
            else:
                self._outqueue.append(pack("!ic", 1, UNCHOKE))
            self.choke_sent = self.upload.choked
        queue.extend(self._outqueue)
        self._outqueue = []
        queue = ''.join(queue)
        self.upload.update_rate(len(queue))
        self.connection.write(queue)
        return len(queue)

    # yields the number of bytes it wants next, gets those in self._message
    def _read_messages(self):
        yield 1   # header length
        if ord(self._message) != len(protocol_name):
            return

        yield len(protocol_name)
        if self._message != protocol_name:
            return

        yield 8  # reserved
        # dht is on last reserved byte
        if ord(self._message[7]) & DHT:
            self.uses_dht = True
        
        yield 20 # download id
        if self.encoder.download_id is None:  # incoming connection
            # modifies self.encoder if successful
            self.encoder.select_torrent(self, self._message)
            if self.encoder.download_id is None:
                return
        elif self._message != self.encoder.download_id:
            return
        if not self.locally_initiated:
            self.connection.write(chr(len(protocol_name)) + protocol_name +
                FLAGS + self.encoder.download_id + self.encoder.my_id)

        yield 20  # peer id
        if not self.id:
            self.id = self._message
            if self.id == self.encoder.my_id:
                return
            for v in self.encoder.connections.itervalues():
                if v is not self:
                    if v.id == self.id:
                        return
                    if self.encoder.config['one_connection_per_ip'] and \
                           v.ip == self.ip:
                        return
            if self.locally_initiated:
                self.connection.write(self.encoder.my_id)
            else:
                self.encoder.everinc = True
        else:
            if self._message != self.id:
                return
        self.complete = True
        self.encoder.connection_completed(self)

        while True:
            yield 4   # message length
            l = toint(self._message)
            if l > self.encoder.config['max_message_length']:
                return
            if l > 0:
                yield l
                self._got_message(self._message)

    def _got_message(self, message):
        t = message[0]
        if t == BITFIELD and self.got_anything:
            self.close()
            return
        self.got_anything = True
        if (t in [CHOKE, UNCHOKE, INTERESTED, NOT_INTERESTED] and
                len(message) != 1):
            self.close()
            return
        if t == CHOKE:
            self.download.got_choke()
        elif t == UNCHOKE:
            self.download.got_unchoke()
        elif t == INTERESTED:
            self.upload.got_interested()
        elif t == NOT_INTERESTED:
            self.upload.got_not_interested()
        elif t == HAVE:
            if len(message) != 5:
                self.close()
                return
            i = unpack("!xi", message)[0]
            if i >= self.encoder.numpieces:
                self.close()
                return
            self.download.got_have(i)
        elif t == BITFIELD:
            try:
                b = Bitfield(self.encoder.numpieces, message[1:])
            except ValueError:
                self.close()
                return
            self.download.got_have_bitfield(b)
        elif t == REQUEST:
            if len(message) != 13:
                self.close()
                return
            i, a, b = unpack("!xiii", message)
            if i >= self.encoder.numpieces:
                self.close()
                return
            self.upload.got_request(i, a, b)
        elif t == CANCEL:
            if len(message) != 13:
                self.close()
                return
            i, a, b = unpack("!xiii", message)
            if i >= self.encoder.numpieces:
                self.close()
                return
            self.upload.got_cancel(i, a, b)
        elif t == PIECE:
            if len(message) <= 9:
                self.close()
                return
            n = len(message) - 9
            i, a, b = unpack("!xii%ss" % n, message)
            if i >= self.encoder.numpieces:
                self.close()
                return
            if self.download.got_piece(i, a, b):
                for co in self.encoder.complete_connections:
                    co.send_have(i)
        elif t == PORT:
            if len(message) != 3:
                self.close()
                return
            self.dht_port = unpack('!H', message[1:3])[0]
            self.encoder.got_port(self)
        else:
            self.close()

    def _sever(self):
        self.closed = True
        self._reader = None
        del self.encoder.connections[self.connection]
        self.connection = None
        self.encoder.replace_connection()
        if self.complete:
            del self.encoder.complete_connections[self]
            self.download.disconnected()
            self.encoder.choker.connection_lost(self)
            self.upload = self.download = None

    def _send_message(self, message):
        s = tobinary(len(message)) + message
        if self._partial_message is not None:
            self._outqueue.append(s)
        else:
            self.connection.write(s)

    def data_came_in(self, conn, s):
        while True:
            if self.closed:
                return
            i = self._next_len - self._buffer_len
            if i > len(s):
                self._buffer.append(s)
                self._buffer_len += len(s)
                return
            m = s[:i]
            if self._buffer_len > 0:
                self._buffer.append(m)
                m = ''.join(self._buffer)
                self._buffer = []
                self._buffer_len = 0
            s = s[i:]
            self._message = m
            try:
                self._next_len = self._reader.next()
            except StopIteration:
                self.close()
                return

    def connection_lost(self, conn):
        if self.connection is None:
            assert self.closed
        else:
            assert conn is self.connection
            self._sever()

    def connection_flushed(self, connection):
        if self.complete and self.next_upload is None and (self._partial_message is not None
                                             or (self.upload and self.upload.buffer)):
                self.encoder.ratelimiter.queue(self, self.encoder.context.rlgroup)
