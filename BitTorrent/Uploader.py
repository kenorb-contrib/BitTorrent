# written by Bram Cohen
# this file is public domain

from bencode import bencode, bdecode
from btemplate import compile_template
from types import *
from traceback import print_exc
from binascii import b2a_hex
true = 1
false = 0

def len20(s, verbose):
    if type(s) != StringType or len(s) != 20:
        raise ValueError

choke_message = bencode({'type': "you're choked"})
    
unchoke_message = bencode({'type': "you're not choked"})

send_slice_template = compile_template({'type': 'send slice',
    'file': len20, 'begin': 0, 'length': 0})

class SingleUpload:
    def __init__(self, connection, uploader):
        self.connection = connection
        self.uploader = uploader
        self.choked = false
        self.uploading = false
        self.id = connection.get_id()
        self.last_sent = None
        self.sent_since_checkpoint = 0
        self.rate = 0
        self.total = 0
        connection.send_message(bencode({'type': 'I have files', 
            'files': uploader.database.get_list_of_files_I_have()}))

    def get_ip(self):
        return self.connection.get_ip()

    def got_message(self, message):
        try:
            m = bdecode(message)
            if type(m) != DictType:
                raise ValueError
            mtype = m.get('type')
            if mtype == 'send slice':
                self.got_send_slice(m)
            elif mtype == 'done downloading':
                if self.uploading:
                    self.uploading = false
                    self.uploader.choker.upload_stopped(self)
        except ValueError:
            print_exc()

    def got_send_slice(self, m):
        send_slice_template(m)
        if self.choked:
            self.connection.send_message(choke_message)
            return
        file = m['file']
        begin = m['begin']
        slice = self.uploader.database.get_slice(file, begin, m['length'])
        if slice is None:
            return
        self.connection.send_message(bencode({'type': 'here is a slice', 
            'file': file, 'begin': begin, 'slice': slice}))
        self.total += len(slice)
        self.last_sent = file
        self.sent_since_checkpoint += len(slice)
        begin = m['begin']
        end = begin + len(slice)
        if not self.uploading:
            self.uploading = true
            self.uploader.choker.upload_started(self)
        self.uploader.choker.data_sent_out(self, len(slice))

    def choke(self):
        self.choked = true
        self.uploading = false
        self.connection.send_message(choke_message)
        
    def unchoke(self):
        self.choked = false
        self.connection.send_message(unchoke_message)
        
    def get_id(self):
        return self.id
        
    def is_choked(self):
        return self.choked
        
    def is_uploading(self):
        return self.uploading

class Uploader:
    def __init__(self, choker, database):
        self.choker = choker
        self.database = database
        # {id: SingleUploader}
        self.uploads = {}
    
    def connection_made(self, connection):
        s = SingleUpload(connection, self)
        assert not self.uploads.has_key(s.get_id())
        self.uploads[s.get_id()] = s
        self.choker.upload_connected(s)
        
    def connection_lost(self, connection):
        s = self.uploads[connection.get_id()]
        del s.connection
        del self.uploads[connection.get_id()]
        self.choker.upload_disconnected(s)
        
    def got_message(self, connection, message):
        self.uploads[connection.get_id()].got_message(message)

    def received_file(self, file):
        m = bencode({'type': 'I have files', 'files': [file]})
        for up in self.uploads.values():
            up.connection.send_message(m)
        
# everything below is for testing

from sha import sha

class DummyDatabase:
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
        
    def get_id(self):
        return self.id

def test():
    th = DummyChoker()
    val = 'a' * 20 + 'z' * 10
    key = sha(val).digest()
    dd = DummyDatabase({key: val})
    up = Uploader(th, dd)
    
    c = DummyConnection('b' * 20)
    up.connection_made(c)
    assert c.m == [bencode({'type': 'I have files', 'files': [key]})]
    del c.m[:]
    assert th.events == ['connected']
    del th.events[:]

    up.received_file('c' * 20)
    assert c.m == [bencode({'type': 'I have files', 'files': ['c' * 20]})]
    del c.m[:]
    assert th.events == []
    
    th.up[0].choke()
    assert c.m == [bencode({'type': "you're choked"})]
    del c.m[:]
    assert th.events == []
    
    up.got_message(c, bencode({'type': 'send slice', 'file': key, 'begin': 0, 'length': 20}))
    assert c.m == [bencode({'type': "you're choked"})]
    del c.m[:]
    assert th.events == []

    th.up[0].unchoke()
    assert c.m == [bencode({'type': "you're not choked"})]
    del c.m[:]
    assert th.events == []
    
    up.got_message(c, bencode({'type': 'send slice', 'file': key, 'begin': 0, 'length': 20}))
    assert c.m == [bencode({'type': 'here is a slice', 'file': key, 
        'slice': 'a' * 20, 'begin': 0})]
    del c.m[:]
    assert th.events == ['started', 20]
    del th.events[:]

    up.got_message(c, bencode({'type': 'send slice', 'file': key, 'begin': 20, 'length': 20}))
    assert c.m == [bencode({'type': 'here is a slice', 'file': key, 
        'slice': 'z' * 10, 'begin': 20})]
    del c.m[:]
    assert th.events == [10]
    del th.events[:]

    up.got_message(c, bencode({'type': 'send slice', 'file': 'd' * 20, 'begin': 0, 'length': 20}))
    assert c.m == []
    assert th.events == []

    up.got_message(c, bencode({'type': 'done downloading'}))
    assert c.m == []
    assert th.events == ['stopped']
    del th.events[:]


