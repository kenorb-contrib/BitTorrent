# Written by Bram Cohen
# see LICENSE.txt for license information

from cStringIO import StringIO
from socket import error as socketerror
from traceback import print_exc
true = 1
false = 0

protocol_name = 'BitTorrent protocol'

# header, reserved, download id, my id, [length, message]

class NatCheck:
    def __init__(self, resultfunc, downloadid, peerid, ip, port, rawserver):
        self.resultfunc = resultfunc
        self.downloadid = downloadid
        self.peerid = peerid
        self.ip = ip
        self.closed = false
        self.buffer = StringIO()
        self.next_len = 1
        self.next_func = self.read_header_len
        try:
            self.connection = rawserver.start_connection((ip, port), self)
            self.connection.write(chr(len(protocol_name)) + protocol_name +
                (chr(0) * 8) + downloadid)
        except socketerror:
            self.answer(false)
        except IOError:
            self.answer(false)

    def answer(self, result):
        self.closed = true
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
        self.answer(true)
        return None

    def data_came_in(self, connection, s):
        while true:
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
                    self.answer(false)
                return
            self.next_len, self.next_func = x

    def connection_lost(self, connection):
        if not self.closed:
            self.closed = true
            self.resultfunc(false)

    def connection_flushed(self, connection):
        pass
