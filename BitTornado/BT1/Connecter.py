# Written by Bram Cohen
# see LICENSE.txt for license information

from BitTornado.bitfield import Bitfield
from traceback import print_exc
from binascii import b2a_hex
from BitTornado.CurrentRateMeasure import Measure
from time import time
from cStringIO import StringIO

try:
    True
except:
    True = 1
    False = 0

def toint(s):
    return long(b2a_hex(s), 16)

def tobinary(i):
    return (chr(i >> 24) + chr((i >> 16) & 0xFF) + 
        chr((i >> 8) & 0xFF) + chr(i & 0xFF))

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

class Connection:
    def __init__(self, connection, connecter):
        self.connection = connection
        self.connecter = connecter
        self.got_anything = False
        self.next_upload = None
        self.outqueue = []
        self.partial_message = None
        self.download = None

    def get_ip(self, real=False):
        return self.connection.get_ip(real)

    def get_id(self):
        return self.connection.get_id()

    def get_readable_id(self):
        return self.connection.get_readable_id()

    def close(self):
        self.connection.close()

    def is_locally_initiated(self):
        return self.connection.is_locally_initiated()

    def send_interested(self):
        self._send_message(INTERESTED)

    def send_not_interested(self):
        self._send_message(NOT_INTERESTED)

    def send_choke(self):
        self._send_message(CHOKE)

    def send_unchoke(self):
        self._send_message(UNCHOKE)

    def send_request(self, index, begin, length):
        self._send_message(REQUEST + tobinary(index) + 
            tobinary(begin) + tobinary(length))

    def send_cancel(self, index, begin, length):
        self._send_message(CANCEL + tobinary(index) + 
            tobinary(begin) + tobinary(length))

    def send_bitfield(self, bitfield):
        self._send_message(BITFIELD + bitfield)

    def send_have(self, index):
        self._send_message(HAVE + tobinary(index))

    def _send_message(self, s):
        s = tobinary(len(s))+s
        if not self.partial_message:
            self.connection.send_message(s)
        else:
            self.outqueue.append(s)

    def send_partial(self, bytes):
        if self.connection.closed:
            return 0
        if self.partial_message is None:
            s = self.upload.get_upload_chunk()
            if s is None:
                return 0
            index, begin, piece = s
            self.partial_message = ''.join((
                            tobinary(len(piece) + 9), PIECE,
                            tobinary(index), tobinary(begin), piece ))

        if bytes < len(self.partial_message):
            self.connection.send_message(self.partial_message[:bytes])
            self.partial_message = self.partial_message[bytes:]
            return bytes

        q = [self.partial_message]
        q.extend(self.outqueue)
        q = ''.join(q)
        self.connection.send_message(q)
        self.partial_message = None
        self.outqueue = []
        return len(q)

    def get_upload(self):
        return self.upload

    def get_download(self):
        return self.download

    def set_download(self, download):
        self.download = download

    def backlogged(self):
        return not self.connection.is_flushed()



class Connecter:
    def __init__(self, make_upload, downloader, choker, numpieces,
            totalup, config, ratelimiter, sched = None):
        self.downloader = downloader
        self.make_upload = make_upload
        self.choker = choker
        self.numpieces = numpieces
        self.config = config
        self.ratelimiter = ratelimiter
        self.rate_capped = False
        self.sched = sched
        self.totalup = totalup
        self.rate_capped = False
        self.connections = {}
        self.external_connection_made = 0

    def how_many_connections(self):
        return len(self.connections)

    def connection_made(self, connection):
        c = Connection(connection, self)
        self.connections[connection] = c
        c.upload = self.make_upload(c, self.ratelimiter, self.totalup)
        c.download = self.downloader.make_download(c)
        self.choker.connection_made(c)

    def connection_lost(self, connection):
        c = self.connections[connection]
        del self.connections[connection]
        if c.download:
            c.download.disconnected()
        self.choker.connection_lost(c)

    def connection_flushed(self, connection):
        conn = self.connections[connection]
        if conn.next_upload is None and (conn.partial_message is not None
               or len(conn.upload.buffer) > 0):
            self.ratelimiter.queue(conn)
            
    def got_piece(self, i):
        for co in self.connections.values():
            co.send_have(i)

    def got_message(self, connection, message):
        c = self.connections[connection]
        t = message[0]
        if t == BITFIELD and c.got_anything:
            connection.close()
            return
        c.got_anything = True
        if (t in [CHOKE, UNCHOKE, INTERESTED, NOT_INTERESTED] and 
                len(message) != 1):
            connection.close()
            return
        if t == CHOKE:
            c.download.got_choke()
        elif t == UNCHOKE:
            c.download.got_unchoke()
        elif t == INTERESTED:
            c.upload.got_interested()
        elif t == NOT_INTERESTED:
            c.upload.got_not_interested()
        elif t == HAVE:
            if len(message) != 5:
                connection.close()
                return
            i = toint(message[1:])
            if i >= self.numpieces:
                connection.close()
                return
            c.download.got_have(i)
        elif t == BITFIELD:
            try:
                b = Bitfield(self.numpieces, message[1:])
            except ValueError:
                connection.close()
                return
            c.download.got_have_bitfield(b)
        elif t == REQUEST:
            if len(message) != 13:
                connection.close()
                return
            i = toint(message[1:5])
            if i >= self.numpieces:
                connection.close()
                return
            c.upload.got_request(i, toint(message[5:9]), 
                toint(message[9:]))
        elif t == CANCEL:
            if len(message) != 13:
                connection.close()
                return
            i = toint(message[1:5])
            if i >= self.numpieces:
                connection.close()
                return
            c.upload.got_cancel(i, toint(message[5:9]), 
                toint(message[9:]))
        elif t == PIECE:
            if len(message) <= 9:
                connection.close()
                return
            i = toint(message[1:5])
            if i >= self.numpieces:
                connection.close()
                return
            if c.download.got_piece(i, toint(message[5:9]), message[9:]):
                self.got_piece(i)
        else:
            connection.close()

class DummyUpload:
    def __init__(self, events):
        self.events = events
        events.append('made upload')

    def flushed(self):
        self.events.append('flushed')

    def got_interested(self):
        self.events.append('interested')
        
    def got_not_interested(self):
        self.events.append('not interested')

    def got_request(self, index, begin, length):
        self.events.append(('request', index, begin, length))

    def got_cancel(self, index, begin, length):
        self.events.append(('cancel', index, begin, length))

class DummyDownload:
    def __init__(self, events):
        self.events = events
        events.append('made download')
        self.hit = 0

    def disconnected(self):
        self.events.append('disconnected')

    def got_choke(self):
        self.events.append('choke')

    def got_unchoke(self):
        self.events.append('unchoke')

    def got_have(self, i):
        self.events.append(('have', i))

    def got_have_bitfield(self, bitfield):
        self.events.append(('bitfield', bitfield.tostring()))

    def got_piece(self, index, begin, piece):
        self.events.append(('piece', index, begin, piece))
        self.hit += 1
        return self.hit > 1

class DummyDownloader:
    def __init__(self, events):
        self.events = events

    def make_download(self, connection):
        return DummyDownload(self.events)

class DummyConnection:
    def __init__(self, events):
        self.events = events

    def send_message(self, message):
        self.events.append(('m', message))

class DummyChoker:
    def __init__(self, events, cs):
        self.events = events
        self.cs = cs

    def connection_made(self, c):
        self.events.append('made')
        self.cs.append(c)

    def connection_lost(self, c):
        self.events.append('lost')

def test_operation():
    events = []
    cs = []
    co = Connecter(lambda c, events = events: DummyUpload(events), 
        DummyDownloader(events), DummyChoker(events, cs), 3, 
        Measure(10))
    assert events == []
    assert cs == []
    
    dc = DummyConnection(events)
    co.connection_made(dc)
    assert len(cs) == 1
    cc = cs[0]
    co.got_message(dc, BITFIELD + chr(0xc0))
    co.got_message(dc, CHOKE)
    co.got_message(dc, UNCHOKE)
    co.got_message(dc, INTERESTED)
    co.got_message(dc, NOT_INTERESTED)
    co.got_message(dc, HAVE + tobinary(2))
    co.got_message(dc, REQUEST + tobinary(1) + tobinary(5) + tobinary(6))
    co.got_message(dc, CANCEL + tobinary(2) + tobinary(3) + tobinary(4))
    co.got_message(dc, PIECE + tobinary(1) + tobinary(0) + 'abc')
    co.got_message(dc, PIECE + tobinary(1) + tobinary(3) + 'def')
    co.connection_flushed(dc)
    cc.send_bitfield([False, True, True])
    cc.send_interested()
    cc.send_not_interested()
    cc.send_choke()
    cc.send_unchoke()
    cc.send_have(4)
    cc.send_request(0, 2, 1)
    cc.send_cancel(1, 2, 3)
    cc.send_piece(1, 2, 'abc')
    co.connection_lost(dc)
    x = ['made upload', 'made download', 'made', 
        ('bitfield', [True, True, False]), 'choke', 'unchoke',
        'interested', 'not interested', ('have', 2), 
        ('request', 1, 5, 6), ('cancel', 2, 3, 4),
        ('piece', 1, 0, 'abc'), ('piece', 1, 3, 'def'), 
        ('m', HAVE + tobinary(1)),
        'flushed', ('m', BITFIELD + chr(0x60)), ('m', INTERESTED), 
        ('m', NOT_INTERESTED), ('m', CHOKE), ('m', UNCHOKE), 
        ('m', HAVE + tobinary(4)), ('m', REQUEST + tobinary(0) + 
        tobinary(2) + tobinary(1)), ('m', CANCEL + tobinary(1) + 
        tobinary(2) + tobinary(3)), ('m', PIECE + tobinary(1) + 
        tobinary(2) + 'abc'), 'disconnected', 'lost']
    for a, b in zip (events, x):
        assert a == b, repr((a, b))

def test_conversion():
    assert toint(tobinary(50000)) == 50000
