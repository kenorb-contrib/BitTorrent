# Written by Bram Cohen
# see LICENSE.txt for license information

from bitfield import bitfield_to_booleans, booleans_to_bitfield
from traceback import print_exc
from binascii import b2a_hex
true = 1
false = 0

def toint(s):
    return long(b2a_hex(s), 16)

def tobinary(i):
    return (chr(i >> 24) + chr((i >> 16) & 0xFF) + 
        chr((i >> 8) & 0xFF) + chr(i & 0xFF))

CHOKE = 0
UNCHOKE = 1
INTERESTED = 2
NOT_INTERESTED = 3
# index
HAVE = 4
# index, bitfield
BITFIELD = 5
# index, begin, length
REQUEST = 6
# index, begin, piece
PIECE = 7

class Connection:
    def __init__(self, connection):
        self.connection = connection
        self.got_have = false

    def get_ip(self):
        return self.connection.get_ip()

    def is_flushed(self):
        return self.connection.is_flushed()

    def send_interested(self):
        self.connection.send_message(INTERESTED)

    def send_not_interested(self):
        self.connection.send_message(NOT_INTERESTED)

    def send_choke(self):
        self.connection.send_message(CHOKE)

    def send_unchoke(self):
        self.connection.send_message(UNCHOKE)

    def send_request(self, index, begin, length):
        self.connection.send_message(REQUEST + toint(index) + 
            toint(begin) + toint(length))

    def send_piece(self, index, begin, piece):
        self.connection.send_message(PIECE + toint(index) + 
            toint(begin) + piece)

    def send_bitfield(self, bitfield):
        b = booleans_to_bitfield(bitfield)
        self.connection.send_message(BITFIELD + b)

    def send_have(self, index):
        self.connection.send_message(HAVE + toint(index))

    def get_upload(self):
        return self.upload

    def get_download(self):
        return self.download

class Connecter:
    def __init__(self, make_upload, make_download, choker, numpieces):
        self.make_download = make_download
        self.make_upload = make_upload
        self.choker = choker
        self.numpieces = numpieces
        self.connections = {}

    def connection_made(self, connection):
        c = Connection(connection)
        self.connections[connection] = c
        c.upload = self.make_upload(c)
        c.download = self.make_download(c)
        self.choker.connection_made(c)

    def connection_lost(self, connection):
        c = self.connections[connection]
        u = c.upload
        d = c.download
        del c.upload
        del c.download
        del self.connections[connection]
        u.disconnected()
        d.disconnected()
        self.choker.connection_lost(c)

    def connection_flushed(self, connection):
        self.connections[connection].upload.flushed()

    def got_message(self, connection, message):
        c = self.connections[connection]
        if len(message) == 0:
            connection.close()
            return
        t = chr(message[0])
        if t == CHOKE:
            if len(message) != 1:
                connection.close()
                return
            c.download.got_choke()
        elif t == UNCHOKE:
            if len(message) != 1:
                connection.close()
                return
            c.download.got_unchoke()
        elif t == INTERESTED:
            if len(message) != 1:
                connection.close()
                return
            c.upload.got_interested()
        elif t == NOT_INTERESTED:
            if len(message) != 1:
                connection.close()
                return
            c.upload.got_not_interested()
        elif t == HAVE:
            if len(message) != 5:
                connection.close()
                return
            c.got_have = true
            i = tobinary(message[1:])
            if i >= self.numpieces:
                connection.close()
                return
            c.download.got_have(i)
        elif t == BITFIELD:
            b = bitfield_to_booleans(t[1:], self.numpieces)
            if b is None or c.got_have:
                connection.close()
                return
            c.got_have = true
            c.download.got_bitfield(b)
        elif t == REQUEST:
            if len(message) != 13:
                connection.close()
                return
            i = tobinary(message[1:5])
            if i >= self.numpieces:
                connection.close()
                return
            c.upload.got_request(i, tobinary(message[5:9]), 
                tobinary(message[9:]))
        elif t == PIECE:
            if len(message) <= 9:
                connection.close()
                return
            i = tobinary(message[1:5])
            if i >= self.numpieces:
                connection.close()
                return
            if c.download.got_piece(i, tobinary(message[5:9]), message[9:]):
                for co in self.connections.values():
                    co.send_have(i)
        else:
            connection.close()

class DummyUpload:
    def __init__(self, events):
        self.events = events

    def send_intro(self):
        self.events.append('intro')
        
    def disconnected(self):
        self.events.append('disconnected')
        
    def flushed(self):
        self.events.append('flushed')

    def got_interested(self):
        self.events.append('interested')
        
    def got_done(self):
        self.events.append('done')

    def got_send(self, m):
        self.events.append('send')

    def received_blob(self, blob):
        self.events.append(('received', blob))

class DummyUploadMaker:
    def __init__(self, events):
        self.events = events
    
    def make(self, connection):
        self.events.append(('made upload', DummyUpload(self.events)))
        return self.events[-1][1]

class DummyDownload:
    def __init__(self, events):
        self.events = events
        self.received = None

    def disconnected(self):
        self.events.append('disconnected')
        
    def got_choke(self):
        self.events.append('choke')
        
    def got_unchoke(self):
        self.events.append('unchoke')

    def got_I_have(self, m):
        self.events.append('I have')
        
    def got_slice(self, m):
        self.events.append('slice')
        return self.received

class DummyDownloadMaker:
    def __init__(self, events):
        self.events = events
        
    def make(self, connection):
        self.events.append(('made download', DummyDownload(self.events)))
        return self.events[-1][1]

class DummyConnection:
    def __init__(self, ident, events):
        self.events = events
        self.ident = ident

    def send_message(self, message):
        self.events.append(('m', message))
    
    def get_id(self):
        return self.ident
    
    def close(self):
        self.events.append('close')

class DummyChoker:
    def __init__(self, events):
        self.events = events

    def connection_made(self, c):
        self.events.append(('made', c))
        
    def connection_lost(self, c):
        self.events.append(('lost', c))

def test_connect_and_disconnect():
    events = []
    downloadMaker = DummyDownloadMaker(events)
    uploadMaker = DummyUploadMaker(events)
    choker = DummyChoker(events)
    connecter = Connecter(uploadMaker.make, downloadMaker.make, choker)
    connection = DummyConnection('a' * 20, events)
    connecter.connection_made(connection)

    assert events[0][0] == 'made upload'
    up = events[0][1]
    assert events[1][0] == 'made download'
    down = events[1][1]
    assert events[2][0] == 'made'
    c = events[2][1]
    assert events[3] == 'intro'
    del events[:]

    c.send_message('test')
    assert events == [('m', bencode('test'))]
    del events[:]

    connecter.connection_flushed(connection)
    assert events == ['flushed']
    del events[:]

    connecter.connection_lost(connection)
    assert events == ['disconnected', 'disconnected', ('lost', c)]
    del events[:]

def test_bifurcation():
    events = []
    downloadMaker = DummyDownloadMaker(events)
    uploadMaker = DummyUploadMaker(events)
    choker = DummyChoker(events)
    connecter = Connecter(uploadMaker.make, downloadMaker.make, choker)
    connection = DummyConnection('a' * 20, events)
    connecter.connection_made(connection)

    assert events[0][0] == 'made upload'
    up = events[0][1]
    assert events[1][0] == 'made download'
    down = events[1][1]
    assert events[2][0] == 'made'
    c = events[2][1]
    assert events[3] == 'intro'
    del events[:]

    connecter.got_message(connection, bencode({'type': 'choke'}))
    assert events == ['choke']
    del events[:]

    connecter.got_message(connection, bencode({'type': 'unchoke'}))
    assert events == ['unchoke']
    del events[:]

    connecter.got_message(connection, bencode({'type': 'I have', 
        'blobs': ['c' * 20]}))
    assert events == ['I have']
    del events[:]

    connecter.got_message(connection, bencode({'type': 'slice', 
        'blob': 'c' * 20, 'begin': 0, 'slice': 'abc'}))
    assert events == ['slice']
    del events[:]

    connecter.got_message(connection, bencode({'type': 'interested'}))
    assert events == ['interested']
    del events[:]

    connecter.got_message(connection, bencode({'type': 'done'}))
    assert events == ['done']
    del events[:]

    connecter.got_message(connection, bencode({'type': 'send', 
        'blob': 'c' * 20, 'begin': 0, 'length': 3}))
    assert events == ['send']
    del events[:]

    down.received = 'b' * 20
    connecter.got_message(connection, bencode({'type': 'slice', 
        'blob': 'c' * 20, 'begin': 0, 'slice': 'abc'}))
    assert events == ['slice', ('received', 'b' * 20)]
    del events[:]

