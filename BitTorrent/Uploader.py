# Written by Bram Cohen
# see LICENSE.txt for license information

from time import time

true = 1
false = 0

class Upload:
    def __init__(self, connection, choker, storage, 
            max_slice_length, max_rate_period, total_up = [0l]):
        self.connection = connection
        self.choker = choker
        self.storage = storage
        self.max_slice_length = max_slice_length
        self.max_rate_period = max_rate_period
        self.total_up = total_up
        self.choked = true
        self.interested = false
        self.buffer = []
        self.ratesince = time() - 5.0
        self.lastout = self.ratesince
        self.rate = 0.0
        if storage.do_I_have_anything():
            connection.send_bitfield(storage.get_have_list)

    def got_done(self):
        if self.interested:
            self.interested = false
            del self.buffer[:]
            self.choker.not_interested(self.connection)

    def got_interested(self):
        if not self.interested:
            self.interested = true
            self.choker.interested(self.connection)

    def update_rate(self, amount):
        self.total_up[0] += amount
        t = time()
        self.rate = (self.rate * (self.lastout - self.ratesince) + 
            amount) / (t - self.ratesince)
        self.lastout = t
        if self.ratesince < t - self.max_rate_period:
            self.ratesince = t - self.max_rate_period

    def flushed(self):
        while len(self.buffer) > 0 and self.connection.is_flushed():
            index, begin, length = self.buffer[0]
            del self.buffer[0]
            piece = self.storage.get_piece(index, begin, length)
            if piece is None:
                self.connection.close()
                return
            self.update_rate(len(piece))
            self.connection.send_piece(index, begin, piece)

    def got_send(self, index, begin, length):
        if not self.interested or length > self.max_slice_length:
            self.connection.close()
            return
        if not self.choked:
            self.buffer.append((index, begin, length))
            self.flushed()

    def choke(self):
        if not self.choked:
            self.choked = true
            del self.buffer[:]
            self.connection.send_choke()
        
    def unchoke(self):
        if self.choked:
            self.choked = false
            self.connection.send_unchoke()
        
    def is_choked(self):
        return self.choked
        
    def is_interested(self):
        return self.interested

class DummyConnection:
    def __init__(self, events):
        self.events = events
        self.flushed = true

    def send_message(self, message):
        self.events.append(message)
    
    def is_flushed(self):
        return self.flushed

class DummyChoker:
    def __init__(self, events):
        self.events = events

    def interested(self, connection):
        self.events.append('interested')
    
    def not_interested(self, connection):
        self.events.append('not interested')

class DummyBlobs:
    def __init__(self, blobs):
        self.blobs = blobs

    def get_list_of_blobs_I_have(self):
        return self.blobs.keys()
    
    def get_slice(self, blob, begin, length):
        if not self.blobs.has_key(blob):
            return None
        return self.blobs[blob][begin : begin + length]

def test_skip_over_choke():
    events = []
    connection = DummyConnection(events)
    choker = DummyChoker(events)
    blobs = DummyBlobs({'a' * 20: 'abcd'})
    upload = Upload(connection, choker, blobs, 100, 15)
    assert upload.is_choked()
    assert not upload.is_interested()
    
    upload.unchoke()
    upload.send_intro()
    assert events == [{'type': 'unchoke'}, {'type': 'I have', 'blobs': ['a' * 20]}]
    del events[:]

    connection.flushed = false
    upload.got_send({'type': 'send', 'blob': 'a' * 20, 'begin': 1, 'length': 2})
    assert events == ['interested']
    del events[:]
    assert not upload.is_choked()
    assert upload.is_interested()

    upload.choke()
    assert events == []
    assert upload.is_choked()
    assert upload.is_interested()
    
    upload.unchoke()
    assert events == []
    assert not upload.is_choked()
    assert upload.is_interested()

    connection.flushed = true
    upload.flushed()
    assert events == [{'type': 'slice', 'blob': 'a' * 20, 'slice': 'bc', 'begin': 1}]
    del events[:]
    assert not upload.is_choked()
    assert upload.is_interested()

    upload.got_send({'type': 'send', 'blob': 'a' * 20, 'begin': 1, 'length': 2})
    assert events == [{'type': 'slice', 'blob': 'a' * 20, 'slice': 'bc', 'begin': 1}]
    del events[:]
    assert not upload.is_choked()
    assert upload.is_interested()

def test_received_blob():
    events = []
    connection = DummyConnection(events)
    choker = DummyChoker(events)
    blobs = DummyBlobs({'a' * 20: 'abcd'})
    upload = Upload(connection, choker, blobs, 100, 15)
    assert not upload.is_interested()
    
    upload.unchoke()
    upload.received_blob('a' * 20)
    assert events == [{'type': 'unchoke'}, {'type': 'I have', 'blobs': ['a' * 20]}]

def test_get_bad_slice():
    events = []
    connection = DummyConnection(events)
    choker = DummyChoker(events)
    blobs = DummyBlobs({})
    upload = Upload(connection, choker, blobs, 100, 15)
    assert upload.is_choked()
    assert not upload.is_interested()

    upload.unchoke()
    upload.got_send({'type': 'send', 'blob': 'a' * 20, 'begin': 0, 'length': 2})
    assert events == [{'type': 'unchoke'}, 'interested']
    assert not upload.is_choked()
    assert upload.is_interested()

def test_transitions_clockwise():
    events = []
    connection = DummyConnection(events)
    choker = DummyChoker(events)
    blobs = DummyBlobs({'a' * 20: 'abcd'})
    upload = Upload(connection, choker, blobs, 100, 15)
    assert not upload.is_interested()

    upload.unchoke()
    upload.got_interested()
    assert events == [{'type': 'unchoke'}, 'interested']
    del events[:]
    assert not upload.is_choked()
    assert upload.is_interested()

    upload.choke()
    assert events == [{'type': 'choke'}]
    del events[:]
    assert upload.is_choked()
    assert upload.is_interested()

    upload.got_send({'type': 'send', 'blob': 'a' * 20, 'begin': 1, 'length': 2})
    assert events == []
    assert upload.is_choked()
    assert upload.is_interested()

    upload.got_done()
    assert events == ['not interested']
    del events[:]
    assert upload.is_choked()
    assert not upload.is_interested()

    upload.unchoke()
    assert events == [{'type': 'unchoke'}]
    del events[:]
    assert not upload.is_choked()
    assert not upload.is_interested()

    upload.got_send({'type': 'send', 'blob': 'a' * 20, 'begin': 1, 'length': 2})
    assert events == [{'type': 'slice', 'blob': 'a' * 20, 'slice': 'bc', 'begin': 1}, 'interested']
    del events[:]
    assert not upload.is_choked()
    assert upload.is_interested()

def test_transitions_counterclockwise():
    events = []
    connection = DummyConnection(events)
    choker = DummyChoker(events)
    blobs = DummyBlobs({'a' * 20: 'abcd'})
    upload = Upload(connection, choker, blobs, 100, 15)
    assert upload.is_choked()
    assert not upload.is_interested()

    upload.got_send({'type': 'send', 'blob': 'a' * 20, 'begin': 1, 'length': 2})
    assert events == ['interested']
    del events[:]
    assert upload.is_choked()
    assert upload.is_interested()

    upload.got_interested()
    assert events == []
    assert upload.is_choked()
    assert upload.is_interested()

    upload.unchoke()
    assert events == [{'type': 'unchoke'}]
    del events[:]
    assert not upload.is_choked()
    assert upload.is_interested()

    upload.got_done()
    assert events == ['not interested']
    del events[:]
    assert not upload.is_choked()
    assert not upload.is_interested()

    upload.got_done()
    assert events == []
    assert not upload.is_choked()
    assert not upload.is_interested()

    upload.got_interested()
    assert events == ['interested']
    assert not upload.is_choked()
    assert upload.is_interested()
