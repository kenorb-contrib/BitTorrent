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
        self.interested = false
        connection.send_message({'type': 'I have', 
            'blobs': blobs.get_list_of_blobs_I_have()})

    def got_done(self, message):
        if self.interested:
            self.interested = false
            self.choker.not_interested(self.connection)

    def got_interested(self, message):
        if not self.interested:
            self.interested = true
            self.choker.interested(self.connection)

    def got_send(self, m):
        send_template(m)
        if not self.choked:
            blob = m['blob']
            begin = m['begin']
            slice = self.blobs.get_slice(blob, begin, m['length'])
            if slice is not None:
                self.connection.send_message({'type': 'slice', 
                    'blob': blob, 'begin': begin, 'slice': slice})
        if not self.interested:
            self.interested = true
            self.choker.interested(self.connection)

    def choke(self):
        self.choked = true
        self.connection.send_message({'type': 'choke'})
        
    def unchoke(self):
        self.choked = false
        self.connection.send_message({'type': 'unchoke'})
        
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

# everything below is for testing

from sha import sha

class Dummyblobs:
    def __init__(self, files):
        # {hash: file}
        self.files = files
    
    def get_slice(self, file, begin, length):
        assert len(file) == 20
        if not self.files.has_key(file):
            return None
        return self.files[file][begin:begin + length]

    def get_list_of_files_I_have(self):
        return self.files.keys()

class DummyChoker:
    def __init__(self):
        self.up = []
        self.events = []
        
    def upload_stopped(self, up):
        self.events.append('stopped')

    def upload_started(self, up):
        self.events.append('started')

    def upload_connected(self, up):
        self.events.append('connected')
        self.up.append(up)
        
    def upload_disconnected(self, up):
        self.events.append('disconnected')
        
    def data_sent_out(self, up, amount):
        self.events.append(amount)

class DummyConnection:
    def __init__(self, myid):
        self.id = myid
        self.m = []
        
    def send_message(self, m):
        self.m.append(m)

def test():
    th = DummyChoker()
    val = 'a' * 20 + 'z' * 10
    key = sha(val).digest()
    dd = Dummyblobs({key: val})
    up = Uploader(th, dd)
    
    c = DummyConnection('b' * 20)
    up.connection_made(c)
    assert c.m == [bencode({'type': 'I have', 'files': [key]})]
    del c.m[:]
    assert th.events == ['connected']
    del th.events[:]

    up.received_file('c' * 20)
    assert c.m == [bencode({'type': 'I have', 'files': ['c' * 20]})]
    del c.m[:]
    assert th.events == []
    
    th.up[0].choke()
    assert c.m == [bencode({'type': "choke"})]
    del c.m[:]
    assert th.events == []
    
    up.got_message(c, bencode({'type': 'send slice', 'blob': key, 'begin': 0, 'length': 20}))
    assert c.m == [bencode({'type': "choke"})]
    del c.m[:]
    assert th.events == []

    th.up[0].unchoke()
    assert c.m == [bencode({'type': "unchoke"})]
    del c.m[:]
    assert th.events == []
    
    up.got_message(c, bencode({'type': 'send slice', 'blob': key, 'begin': 0, 'length': 20}))
    assert c.m == [bencode({'type': 'slice', 'blob': key, 
        'slice': 'a' * 20, 'begin': 0})]
    del c.m[:]
    assert th.events == ['started', 20]
    del th.events[:]

    up.got_message(c, bencode({'type': 'send slice', 'blob': key, 'begin': 20, 'length': 20}))
    assert c.m == [bencode({'type': 'slice', 'blob': key, 
        'slice': 'z' * 10, 'begin': 20})]
    del c.m[:]
    assert th.events == [10]
    del th.events[:]

    up.got_message(c, bencode({'type': 'send slice', 'blob': 'd' * 20, 'begin': 0, 'length': 20}))
    assert c.m == []
    assert th.events == []

    up.got_message(c, bencode({'type': 'done'}))
    assert c.m == []
    assert th.events == ['stopped']
    del th.events[:]


