# written by Bram Cohen
# this file is public domain

from btemplate import compile_template, exact_length
true = 1
false = 0

send_template = compile_template({'type': 'send',
    'blob': exact_length(20), 'begin': 0, 'length': 0})

class Upload:
    def __init__(self, connection, choker, blobs):
        self.connection = connection
        self.choker = choker
        self.blobs = blobs
        self.choked = false
        self.reported_choked = false
        self.interested = false
        self.buffer = []
        connection.send_message({'type': 'I have', 
            'blobs': blobs.get_list_of_blobs_I_have()})

    def got_done(self, message):
        if self.interested:
            self.interested = false
            del self.buffer[:]
            self.choker.not_interested(self.connection)

    def got_interested(self, message):
        if not self.interested:
            self.interested = true
            self.choker.interested(self.connection)

    def flushed(self):
        self.fix_choke()
        while len(self.buffer) > 0 and self.connection.is_flushed():
            blob, begin, length = self.buffer[0]
            del self.buffer[0]
            slice = self.blobs.get_slice(blob, begin, length)
            if slice is not None:
                self.connection.send_message({'type': 'slice', 
                    'blob': blob, 'begin': begin, 'slice': slice})

    def got_send(self, m):
        send_template(m)
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
        self.fix_choke
        
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

"""

def test_skip_over_choke():
    queue requests, choke and unchoke, flush
    assert requests still sent
    send another, asserts gets through immediately

def test_transitions_clockwise():
    make thing
    transition to interested, choked, uninterested, unchoked

def test_transitions_counterclockwise():
    make thing
    transition to choked, interested, unchoked, uninterested

def test_received_blob():
    call received_blob

"""
