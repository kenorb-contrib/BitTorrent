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

throttle_message = bencode({'type': "you're throttled"})
    
unthrottle_message = bencode({'type': "you're not throttled"})

support_message = bencode({'type': 'I support', 
    'list all files': None, 'send slice': None})

send_slice_template = compile_template({'type': 'send slice',
    'file': len20, 'begin': 0, 'length': 0})

class SingleUpload:
    def __init__(self, connection, uploader):
        self.connection = connection
        self.uploader = uploader
        self.throttled = false
        self.uploading = false
        self.id = connection.get_id()
        self.listing_all_files = false
        self.connection.send_message(support_message)
        self.last_sent = None
        self.sent_since_checkpoint = 0
        self.rate = 0
        self.total = 0

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
                    self.uploader.throttler.upload_stopped(self)
            elif mtype == 'list all files':
                self.listing_all_files = true
                self.connection.send_message(bencode({'type': 'I have files', 
                    'files': self.uploader.database.get_list_of_files_I_have()}))
        except ValueError:
            print_exc()

    def got_send_slice(self, m):
        send_slice_template(m)
        if self.throttled:
            self.connection.send_message(throttle_message)
            return
        file = m['file']
        begin = m['begin']
        slice = self.uploader.database.get_slice(file, begin, m['length'])
        if slice is None:
            self.connection.send_message(bencode({'type': "I don't have files", 
                'files': [file]}))
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
            self.uploader.throttler.upload_started(self)
        self.uploader.throttler.data_sent_out(self, len(slice))

    def throttle(self):
        self.throttled = true
        self.uploading = false
        self.connection.send_message(throttle_message)
        
    def unthrottle(self):
        self.throttled = false
        self.connection.send_message(unthrottle_message)
        
    def get_id(self):
        return self.id
        
    def is_throttled(self):
        return self.throttled
        
    def is_uploading(self):
        return self.uploading

class Uploader:
    def __init__(self, throttler, database):
        self.throttler = throttler
        self.database = database
        # {id: SingleUploader}
        self.uploads = {}
    
    def connection_made(self, connection):
        s = SingleUpload(connection, self)
        assert not self.uploads.has_key(s.get_id())
        self.uploads[s.get_id()] = s
        self.throttler.upload_connected(s)
        
    def connection_lost(self, connection):
        s = self.uploads[connection.get_id()]
        del s.connection
        del self.uploads[connection.get_id()]
        self.throttler.upload_disconnected(s)
        
    def got_message(self, connection, message):
        self.uploads[connection.get_id()].got_message(message)

    def received_file(self, file):
        m = bencode({'type': 'I have files', 'files': [file]})
        for up in self.uploads.values():
            if up.listing_all_files:
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

class DummyThrottler:
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
    th = DummyThrottler()
    val = 'a' * 20 + 'z' * 10
    key = sha(val).digest()
    dd = DummyDatabase({key: val})
    up = Uploader(th, dd)
    
    c = DummyConnection('b' * 20)
    up.connection_made(c)
    assert c.m == [support_message]
    del c.m[:]
    assert th.events == ['connected']
    del th.events[:]

    up.got_message(c, bencode({'type': 'list all files'}))
    assert c.m == [bencode({'type': 'I have files', 'files': [key]})]
    del c.m[:]
    assert th.events == []
    
    up.received_file('c' * 20)
    assert c.m == [bencode({'type': 'I have files', 'files': ['c' * 20]})]
    del c.m[:]
    assert th.events == []
    
    th.up[0].throttle()
    assert c.m == [bencode({'type': "you're throttled"})]
    del c.m[:]
    assert th.events == []
    
    up.got_message(c, bencode({'type': 'send slice', 'file': key, 'begin': 0, 'length': 20}))
    assert c.m == [bencode({'type': "you're throttled"})]
    del c.m[:]
    assert th.events == []

    th.up[0].unthrottle()
    assert c.m == [bencode({'type': "you're not throttled"})]
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
    assert c.m == [bencode({'type': "I don't have files", 'files': ['d' * 20]})]
    del c.m[:]
    assert th.events == []

    up.got_message(c, bencode({'type': 'done downloading'}))
    assert c.m == []
    assert th.events == ['stopped']
    del th.events[:]


