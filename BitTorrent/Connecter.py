# Written by Bram Cohen
# see LICENSE.txt for license information

from bencode import bencode, bdecode
from btemplate import compile_template, exact_length, string_template, ListMarker
from traceback import print_exc
true = 1
false = 0

message_template = compile_template([{'type': 'choke'}, 
    {'type': 'unchoke'}, {'type': 'interested'}, {'type': 'done'}, 
    {'type': 'I have', 'blobs': ListMarker(exact_length(20))}, 
    {'type': 'slice', 'blob': exact_length(20), 
        'begin': 0, 'slice': string_template}, 
    {'type': 'send', 'blob': exact_length(20), 'begin': 0, 'length': 1}])

class Connection:
    def __init__(self, connection):
        self.connection = connection

    def is_locally_initiated(self):
        return self.connection.is_locally_initiated()

    def get_ip(self):
        return self.connection.get_ip()

    def is_flushed(self):
        return self.connection.is_flushed()

    def send_message(self, message):
        self.connection.send_message(bencode(message))

    def get_upload(self):
        return self.upload

    def get_download(self):
        return self.download

class Connecter:
    def __init__(self, make_upload, make_download, choker):
        self.make_download = make_download
        self.make_upload = make_upload
        self.choker = choker
        self.connections = {}

    def locally_initiated_connection_completed(self, connection):
        for c in self.connections.keys():
            if c.get_id() == connection.get_id():
                connection.close()
                return
        connection.send_message('transfer')
        self._make_connection(connection)

    def _make_connection(self, connection):
        c = Connection(connection)
        upload = self.make_upload(c)
        download = self.make_download(c)
        c.upload = upload
        c.download = download
        self.connections[connection] = c
        self.choker.connection_made(c)
        upload.send_intro()

    def connection_lost(self, connection):
        c = self.connections[connection]
        del self.connections[connection]
        c.upload.disconnected()
        c.download.disconnected()
        del c.connection
        self.choker.connection_lost(c)

    def connection_flushed(self, connection):
        self.connections[connection].upload.flushed()

    def got_message(self, connection, message):
        if not self.connections.has_key(connection):
            if message != 'transfer':
                connection.close()
                return
            self._make_connection(connection)
            return
        c = self.connections[connection]
        try:
            m = bdecode(message)
            message_template(m)
            mtype = m['type']
            if mtype == 'send':
                c.upload.got_send(m)
            elif mtype == 'interested':
                c.upload.got_interested()
            elif mtype == 'done':
                c.upload.got_done()
            elif mtype == 'choke':
                c.download.got_choke()
            elif mtype == 'unchoke':
                c.download.got_unchoke()
            elif mtype == 'I have':
                c.download.got_I_have(m)
            else:
                blob = c.download.got_slice(m)
                if blob is not None:
                    for c in self.connections.values():
                        c.upload.received_blob(blob)
        except ValueError:
            print_exc()

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
    connecter.got_message(connection, 'transfer')

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

def test_flunk_not_transfer():
    events = []
    downloadMaker = DummyDownloadMaker(events)
    uploadMaker = DummyUploadMaker(events)
    choker = DummyChoker(events)
    connecter = Connecter(uploadMaker.make, downloadMaker.make, choker)
    connection = DummyConnection('a' * 20, events)
    connecter.got_message(connection, 'garbage')

    assert events == ['close']

def test_bifurcation():
    events = []
    downloadMaker = DummyDownloadMaker(events)
    uploadMaker = DummyUploadMaker(events)
    choker = DummyChoker(events)
    connecter = Connecter(uploadMaker.make, downloadMaker.make, choker)
    connection = DummyConnection('a' * 20, events)
    connecter.got_message(connection, 'transfer')

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

def test_close_duplicate():
    events = []
    downloadMaker = DummyDownloadMaker(events)
    uploadMaker = DummyUploadMaker(events)
    choker = DummyChoker(events)
    connecter = Connecter(uploadMaker.make, downloadMaker.make, choker)
    connection = DummyConnection('a' * 20, events)
    connecter.locally_initiated_connection_completed(connection)

    assert events[0] == ('m', 'transfer')
    assert events[1][0] == 'made upload'
    up = events[1][1]
    assert events[2][0] == 'made download'
    down = events[2][1]
    assert events[3][0] == 'made'
    c = events[3][1]
    assert events[4] == 'intro'
    del events[:]

    connection2 = DummyConnection('a' * 20, events)
    connecter.locally_initiated_connection_completed(connection2)
    assert events == ['close']
