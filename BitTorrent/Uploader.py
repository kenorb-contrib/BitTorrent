# written by Bram Cohen
# this file is public domain

from time import time

true = 1
false = 0

class Upload:
    def __init__(self, connection, choker, blobs, max_slice_length):
        self.connection = connection
        self.choker = choker
        self.blobs = blobs
        self.max_slice_length = max_slice_length
        self.choked = false
        self.reported_choked = false
        self.interested = false
        self.buffer = []
        self.ratesince = time()
        self.lastout = self.ratesince
        self.rate = 0.0

    def send_intro(self):
        self.connection.send_message({'type': 'I have', 
            'blobs': self.blobs.get_list_of_blobs_I_have()})

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
        t = time()
        self.rate = (self.rate * (self.lastout - self.ratesince) + 
            amount) / (t - self.ratesince)
        self.lastout = t
        if self.ratesince < t - 20:
            self.ratesince = t - 20

    def flushed(self):
        self.fix_choke()
        while len(self.buffer) > 0 and self.connection.is_flushed():
            blob, begin, length = self.buffer[0]
            del self.buffer[0]
            slice = self.blobs.get_slice(blob, begin, length)
            if slice is not None:
                self.connection.send_message({'type': 'slice', 
                    'blob': blob, 'begin': begin, 'slice': slice})
                self.update_rate(len(slice))

    def got_send(self, m):
        if m['length'] > self.max_slice_length:
            return
        if not self.reported_choked:
            self.buffer.append((m['blob'], m['begin'], m['length']))
            self.flushed()
        if not self.interested:
            self.interested = true
            self.choker.interested(self.connection)

    def fix_choke(self):
        if self.choked == self.reported_choked:
            return
        if not self.connection.is_flushed():
            return
        if self.choked:
            self.connection.send_message({'type': 'choke'})
            self.reported_choked = true
            del self.buffer[:]
        else:
            self.connection.send_message({'type': 'unchoke'})
            self.reported_choked = false

    def choke(self):
        self.choked = true
        self.fix_choke()
        
    def unchoke(self):
        self.choked = false
        self.fix_choke()
        
    def is_choked(self):
        return self.choked
        
    def is_interested(self):
        return self.interested

    def received_blob(self, blob):
        self.connection.send_message({'type': 'I have', 
            'blobs': [blob]})

    def disconnected(self):
        del self.connection
        del self.choker
        del self.blobs

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
    upload = Upload(connection, choker, blobs, 100)
    assert not upload.is_choked()
    assert not upload.is_interested()
    
    upload.send_intro()
    assert events == [{'type': 'I have', 'blobs': ['a' * 20]}]
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
    upload = Upload(connection, choker, blobs, 100)
    assert not upload.is_choked()
    assert not upload.is_interested()
    
    upload.received_blob('a' * 20)
    assert events == [{'type': 'I have', 'blobs': ['a' * 20]}]

def test_get_bad_slice():
    events = []
    connection = DummyConnection(events)
    choker = DummyChoker(events)
    blobs = DummyBlobs({})
    upload = Upload(connection, choker, blobs, 100)
    assert not upload.is_choked()
    assert not upload.is_interested()

    upload.got_send({'type': 'send', 'blob': 'a' * 20, 'begin': 0, 'length': 2})
    assert events == ['interested']
    assert not upload.is_choked()
    assert upload.is_interested()

def test_transitions_clockwise():
    events = []
    connection = DummyConnection(events)
    choker = DummyChoker(events)
    blobs = DummyBlobs({'a' * 20: 'abcd'})
    upload = Upload(connection, choker, blobs, 100)
    assert not upload.is_choked()
    assert not upload.is_interested()

    upload.got_interested()
    assert events == ['interested']
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
    upload = Upload(connection, choker, blobs, 100)
    assert not upload.is_choked()
    assert not upload.is_interested()

    upload.choke()
    assert events == [{'type': 'choke'}]
    del events[:]
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
