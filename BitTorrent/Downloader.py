# Written by Bram Cohen
# this file is public domain

from types import StringType, DictType
from btemplate import compile_template, ListMarker, string_template
from bencode import bencode, bdecode
from binascii import b2a_hex
from traceback import print_exc
true = 1
false = 0

def len20(s, verbose):
    if type(s) != StringType or len(s) != 20:
        raise ValueError

have_files_template = compile_template({'type': 'I have files', 
    'files': ListMarker(len20)})

do_not_have_files_template = compile_template({'type': "I don't have files", 
    'files': ListMarker(len20)})

here_is_a_slice_template = compile_template({'type': 'here is a slice', 
    'file': len20, 'begin': 0, 'slice': string_template})

done_message = bencode({'type': 'done downloading'})

class SingleDownload:
    def __init__(self, downloader, connection):
        self.downloader = downloader
        self.connection = connection
        self.id = connection.get_id()
        self.throttled = false
        self.active_requests = []
        self.peer_has = {}
        self.total = 0
        self.last = None
        self.rate = 0
        self.received_since_checkpoint = 0

    def get_ip(self):
        return self.connection.get_ip()

    def get_id(self):
        return self.id

    def is_downloading(self):
        return len(self.active_requests) != 0

    def is_throttled(self):
        return self.throttled

    def start_new_downloads(self):
        if len(self.active_requests) >= self.downloader.backlog:
            return
        all_requests = []
        for s in self.downloader.downloads.values():
            all_requests.extend(s.active_requests)
        chunk_size = self.downloader.chunk_size
        database = self.downloader.database
        for file in database.get_list_of_files_I_want():
            if not self.peer_has.has_key(file):
                continue
            begin = database.get_amount_have(file)
            size = database.get_size(file)
            while begin < size:
                if not self.downloader.got_already.get(file, {}).has_key(begin):
                    amount = min(begin + chunk_size, size) - begin
                    next = (file, begin, amount)
                    if next not in all_requests:
                        self.active_requests.append(next)
                        self.connection.send_message(bencode({'type': 'send slice',
                            'file': file, 'begin': begin, 'length': amount}))
                        if len(self.active_requests) >= self.downloader.backlog:
                            return
                begin += chunk_size

    def start_downloading(self):
        if self.throttled or len(self.active_requests) > 0:
            return false
        self.start_new_downloads()
        return len(self.active_requests) > 0

    def got_message(self, message):
        try:
            m = bdecode(message)
            if type(m) != DictType:
                raise ValueError
            mtype = m.get('type')
            if mtype == 'here is a slice':
                self.got_slice_message(m)
            elif mtype == "you're throttled":
                self.got_throttled_message(m)
            elif mtype == "you're not throttled":
                if self.throttled:
                    self.throttled = false
                    self.downloader.throttler.download_unthrottled(self)
            elif mtype == 'I have files':
                self.got_files_message(m)
            elif mtype == "I don't have files":
                self.got_no_files_message(m)
        except ValueError:
            print_exc()

    def got_throttled_message(self, message):
        if self.throttled:
            return 
        self.throttled = true
        del self.active_requests[:]
        self.downloader.throttler.download_throttled(self)

    def got_slice_message(self, message):
        here_is_a_slice_template(message)
        if len(self.active_requests) == 0:
            self.connection.send_message(done_message)
            return
        slice = message['slice']
        file, begin, length = message['file'], message['begin'], len(slice)
        for i in xrange(len(self.active_requests)):
            if self.active_requests[i] == (file, begin, length):
                break
        else:
            return
        del self.active_requests[i]
        database = self.downloader.database
        completed = false
        have = self.downloader.got_already.setdefault(file, {})
        have[begin] = slice
        while have.has_key(database.get_amount_have(file)):
            a = database.get_amount_have(file)
            s = have[a]
            del have[a]
            if database.save_slice(file, a, s):
                completed = true
                del self.downloader.got_already[file]
                break
        self.start_new_downloads()
        self.last = file
        self.received_since_checkpoint += len(slice)
        self.total += len(slice)
        if len(self.active_requests) == 0:
            self.connection.send_message(done_message)
            self.downloader.throttler.data_came_in(self, len(slice), true)
        else:
            self.downloader.throttler.data_came_in(self, len(slice), false)
        if completed:
            self.downloader.uploader.received_file(file)

    def got_files_message(self, message):
        have_files_template(message)
        for f in message['files']:
            self.peer_has[f] = 1
        self.downloader.throttler.download_possible(self)

    def got_no_files_message(self, message):
        do_not_have_files_template(message)
        for f in message['files']:
            if self.peer_has.has_key(f):
                del self.peer_has[f]
        new_active = [x for x in self.active_requests if self.peer_has.has_key(x[0])]
        if len(new_active) == len(self.active_requests):
            return
        self.active_requests = new_active
        self.start_new_downloads()
        if len(self.active_requests) == 0:
            self.connection.send_message(done_message)
            self.downloader.throttler.download_hiccuped(self, true)
        else:
            self.downloader.throttler.download_hiccuped(self, false)

class Downloader:
    def __init__(self, throttler, database, uploader, chunk_size, backlog):
        self.throttler = throttler
        self.database = database
        self.uploader = uploader
        self.chunk_size = chunk_size
        self.backlog = backlog
        self.downloads = {}
        # {file: {begin: slice}}
        self.got_already = {}

    def connection_made(self, connection):
        down = SingleDownload(self, connection)
        self.downloads[down.get_id()] = down
        connection.send_message(bencode({'type': 'list all files'}))
        self.throttler.download_connected(down)

    def connection_lost(self, connection):
        down = self.downloads[connection.get_id()]
        del down.connection
        del self.downloads[down.get_id()]
        self.throttler.download_disconnected(down)

    def got_message(self, connection, message):
        self.downloads[connection.get_id()].got_message(message)

# everything below is just for testing

from sha import sha

class DummyUploader:
    def __init__(self):
        self.received = []

    def received_file(self, file):
        self.received.append(file)

class DummyThrottler:
    def __init__(self):
        self.downloads = []
        self.events = []

    def download_throttled(self, download):
        self.events.append('throttled')

    def download_unthrottled(self, download):
        self.events.append('unthrottled')

    def download_possible(self, download):
        self.events.append('possible')

    def download_connected(self, download):
        self.events.append('connected')
        self.downloads.append(download)

    def download_disconnected(self, download):
        self.events.append('disconnected')

    def data_came_in(self, download, amount, exhausted):
        self.events.append(('in', amount, exhausted))

    def download_hiccuped(self, download, exhausted):
        self.events.append(('hiccup', exhausted))

class DummyConnection:
    def __init__(self, myid):
        self.id = myid
        self.messages = []

    def send_message(self, message):
        self.messages.append(message)

    def get_id(self):
        return self.id

class DummyDatabase:
    def __init__(self, sizes, want = None):
        self.files = {}
        self.sizes = sizes
        if want is None:
            self.want = sizes.keys()
        else:
            self.want = want

    def get_amount_have(self, file):
        return len(self.files.get(file, ''))

    def get_size(self, file):
        return self.sizes[file]

    def save_slice(self, file, begin, slice):
        old = self.files.get(file, '')
        assert len(old) == begin
        self.files[file] = old + slice
        return sha(self.files[file]).digest() == file

    def get_list_of_files_I_want(self):
        return self.want

def test_even():
    file = 'abcdef'
    fid = sha(file).digest()
    database = DummyDatabase({fid: len(file)})
    throttler = DummyThrottler()
    uploader = DummyUploader()
    downloader = Downloader(throttler, database, uploader, 3, 3)
    connection = DummyConnection('a' * 20)
    
    downloader.connection_made(connection)
    assert uploader.received == []
    assert throttler.events == ['connected']
    del throttler.events[:]
    assert len(throttler.downloads) == 1
    sd = throttler.downloads[0]
    del throttler.downloads[:]
    assert sd.get_id() == 'a' * 20
    assert not sd.is_downloading()
    assert not sd.is_throttled()
    assert database.files == {}
    assert connection.messages == [bencode({'type': 'list all files'})]
    del connection.messages[:]
    
    assert not sd.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert not sd.is_throttled()

    downloader.got_message(connection, bencode({'type': 'I have files', 'files': [fid]}))
    assert uploader.received == []
    assert throttler.events == ['possible']
    del throttler.events[:]
    assert database.files == {}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert not sd.is_throttled()

    assert sd.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection.messages == [bencode({'type': 'send slice', 'file': fid, 
        'begin': 0, 'length': 3}), bencode({'type': 'send slice', 'file': fid, 
        'begin': 3, 'length': 3})]
    del connection.messages[:]
    assert sd.is_downloading()
    assert not sd.is_throttled()

    assert not sd.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection.messages == []
    assert sd.is_downloading()
    assert not sd.is_throttled()

    downloader.got_message(connection, bencode({'type': 'here is a slice', 
        'file': fid, 'begin': 0, 'slice': 'abc'}))
    assert uploader.received == []
    assert throttler.events == [('in', 3, false)]
    del throttler.events[:]
    assert database.files == {fid: 'abc'}
    assert connection.messages == []
    assert sd.is_downloading()
    assert not sd.is_throttled()

    assert not sd.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {fid: 'abc'}
    assert connection.messages == []
    assert sd.is_downloading()
    assert not sd.is_throttled()

    downloader.got_message(connection, bencode({'type': 'here is a slice', 
        'file': fid, 'begin': 3, 'slice': 'def'}))
    assert uploader.received == [fid]
    del uploader.received[:]
    assert throttler.events == [('in', 3, true)]
    del throttler.events[:]
    assert database.files == {fid: 'abcdef'}
    assert connection.messages == [done_message]
    del connection.messages[:]
    assert not sd.is_downloading()
    assert not sd.is_throttled()

    assert not sd.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {fid: 'abcdef'}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert not sd.is_throttled()

def test_out_of_order():
    file = 'abcde'
    fid = sha(file).digest()
    database = DummyDatabase({fid: len(file)})
    throttler = DummyThrottler()
    uploader = DummyUploader()
    downloader = Downloader(throttler, database, uploader, 3, 1)
    connection1 = DummyConnection('a' * 20)
    connection2 = DummyConnection('b' * 20)

    downloader.connection_made(connection1)
    assert uploader.received == []
    assert throttler.events == ['connected']
    del throttler.events[:]
    assert len(throttler.downloads) == 1
    sd1 = throttler.downloads[0]
    del throttler.downloads[:]
    assert sd1.get_id() == 'a' * 20
    assert not sd1.is_downloading()
    assert not sd1.is_throttled()
    assert database.files == {}
    assert connection1.messages == [bencode({'type': 'list all files'})]
    del connection1.messages[:]
    
    downloader.connection_made(connection2)
    assert uploader.received == []
    assert throttler.events == ['connected']
    del throttler.events[:]
    assert len(throttler.downloads) == 1
    sd2 = throttler.downloads[0]
    del throttler.downloads[:]
    assert sd2.get_id() == 'b' * 20
    assert not sd2.is_downloading()
    assert not sd2.is_throttled()
    assert database.files == {}
    assert connection2.messages == [bencode({'type': 'list all files'})]
    del connection2.messages[:]
    
    downloader.got_message(connection1, bencode({'type': 'I have files', 'files': [fid]}))
    assert uploader.received == []
    assert throttler.events == ['possible']
    del throttler.events[:]
    assert database.files == {}
    assert connection1.messages == []
    assert not sd1.is_downloading()
    assert not sd1.is_throttled()

    assert sd1.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection1.messages == [bencode({'type': 'send slice', 'file': fid, 
        'begin': 0, 'length': 3})]
    del connection1.messages[:]
    assert sd1.is_downloading()
    assert not sd1.is_throttled()

    downloader.got_message(connection2, bencode({'type': 'I have files', 'files': [fid]}))
    assert uploader.received == []
    assert throttler.events == ['possible']
    del throttler.events[:]
    assert database.files == {}
    assert connection2.messages == []
    assert not sd2.is_downloading()
    assert not sd2.is_throttled()

    assert sd2.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection2.messages == [bencode({'type': 'send slice', 'file': fid, 
        'begin': 3, 'length': 2})]
    del connection2.messages[:]
    assert sd2.is_downloading()
    assert not sd2.is_throttled()

    downloader.got_message(connection2, bencode({'type': 'here is a slice', 
        'file': fid, 'begin': 3, 'slice': 'de'}))
    assert uploader.received == []
    del uploader.received[:]
    assert throttler.events == [('in', 2, true)]
    del throttler.events[:]
    assert database.files == {}
    assert connection2.messages == [done_message]
    del connection2.messages[:]
    assert not sd2.is_downloading()
    assert not sd2.is_throttled()

    downloader.got_message(connection1, bencode({'type': 'here is a slice', 
        'file': fid, 'begin': 0, 'slice': 'abc'}))
    assert uploader.received == [fid]
    del uploader.received[:]
    assert throttler.events == [('in', 3, true)]
    del throttler.events[:]
    assert database.files == {fid: 'abcde'}
    assert connection1.messages == [done_message]
    del connection1.messages[:]
    assert not sd1.is_downloading()
    assert not sd1.is_throttled()

def test_disconnect():
    file = 'ab'
    fid = sha(file).digest()
    database = DummyDatabase({fid: len(file)})
    throttler = DummyThrottler()
    uploader = DummyUploader()
    downloader = Downloader(throttler, database, uploader, 3, 1)
    connection1 = DummyConnection('a' * 20)
    connection2 = DummyConnection('b' * 20)

    downloader.connection_made(connection1)
    assert uploader.received == []
    assert throttler.events == ['connected']
    del throttler.events[:]
    assert len(throttler.downloads) == 1
    sd1 = throttler.downloads[0]
    del throttler.downloads[:]
    assert sd1.get_id() == 'a' * 20
    assert not sd1.is_downloading()
    assert not sd1.is_throttled()
    assert database.files == {}
    assert connection1.messages == [bencode({'type': 'list all files'})]
    del connection1.messages[:]
    
    downloader.connection_made(connection2)
    assert uploader.received == []
    assert throttler.events == ['connected']
    del throttler.events[:]
    assert len(throttler.downloads) == 1
    sd2 = throttler.downloads[0]
    del throttler.downloads[:]
    assert sd2.get_id() == 'b' * 20
    assert not sd2.is_downloading()
    assert not sd2.is_throttled()
    assert database.files == {}
    assert connection2.messages == [bencode({'type': 'list all files'})]
    del connection2.messages[:]
    
    downloader.got_message(connection1, bencode({'type': 'I have files', 'files': [fid]}))
    assert uploader.received == []
    assert throttler.events == ['possible']
    del throttler.events[:]
    assert database.files == {}
    assert connection1.messages == []
    assert not sd1.is_downloading()
    assert not sd1.is_throttled()

    assert sd1.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection1.messages == [bencode({'type': 'send slice', 'file': fid, 
        'begin': 0, 'length': 2})]
    del connection1.messages[:]
    assert sd1.is_downloading()
    assert not sd1.is_throttled()

    downloader.got_message(connection2, bencode({'type': 'I have files', 'files': [fid]}))
    assert uploader.received == []
    assert throttler.events == ['possible']
    del throttler.events[:]
    assert database.files == {}
    assert connection2.messages == []
    assert not sd2.is_downloading()
    assert not sd2.is_throttled()

    assert not sd2.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection2.messages == []
    assert not sd2.is_downloading()
    assert not sd2.is_throttled()

    downloader.connection_lost(connection1)
    assert uploader.received == []
    assert throttler.events == ['disconnected']
    del throttler.events[:]
    assert database.files == {}
    assert connection1.messages == []

    assert sd2.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection2.messages == [bencode({'type': 'send slice', 'file': fid, 
        'begin': 0, 'length': 2})]
    del connection2.messages[:]
    assert sd2.is_downloading()
    assert not sd2.is_throttled()

def test_throttle():
    file = 'abc'
    fid = sha(file).digest()
    database = DummyDatabase({fid: len(file)})
    throttler = DummyThrottler()
    uploader = DummyUploader()
    downloader = Downloader(throttler, database, uploader, 3, 3)
    connection = DummyConnection('a' * 20)
    
    downloader.connection_made(connection)
    assert uploader.received == []
    assert throttler.events == ['connected']
    del throttler.events[:]
    assert len(throttler.downloads) == 1
    sd = throttler.downloads[0]
    del throttler.downloads[:]
    assert sd.get_id() == 'a' * 20
    assert not sd.is_downloading()
    assert not sd.is_throttled()
    assert database.files == {}
    assert connection.messages == [bencode({'type': 'list all files'})]
    del connection.messages[:]
    
    assert not sd.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert not sd.is_throttled()

    downloader.got_message(connection, bencode({'type': 'I have files', 'files': [fid]}))
    assert uploader.received == []
    assert throttler.events == ['possible']
    del throttler.events[:]
    assert database.files == {}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert not sd.is_throttled()

    assert sd.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection.messages == [bencode({'type': 'send slice', 'file': fid, 
        'begin': 0, 'length': 3})]
    del connection.messages[:]
    assert sd.is_downloading()
    assert not sd.is_throttled()

    downloader.got_message(connection, bencode({'type': "you're throttled"}))
    assert uploader.received == []
    assert throttler.events == ['throttled']
    del throttler.events[:]
    assert database.files == {}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert sd.is_throttled()

    assert not sd.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert sd.is_throttled()

    downloader.got_message(connection, bencode({'type': "you're throttled"}))
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert sd.is_throttled()

    downloader.got_message(connection, bencode({'type': "you're not throttled"}))
    assert uploader.received == []
    assert throttler.events == ['unthrottled']
    del throttler.events[:]
    assert database.files == {}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert not sd.is_throttled()

    downloader.got_message(connection, bencode({'type': "you're not throttled"}))
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert not sd.is_throttled()

    assert sd.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection.messages == [bencode({'type': 'send slice', 'file': fid, 
        'begin': 0, 'length': 3})]
    del connection.messages[:]
    assert sd.is_downloading()
    assert not sd.is_throttled()

def test_hiccup():
    file = 'abc'
    fid = sha(file).digest()
    database = DummyDatabase({fid: len(file)})
    throttler = DummyThrottler()
    uploader = DummyUploader()
    downloader = Downloader(throttler, database, uploader, 3, 3)
    connection = DummyConnection('a' * 20)
    
    downloader.connection_made(connection)
    assert uploader.received == []
    assert throttler.events == ['connected']
    del throttler.events[:]
    assert len(throttler.downloads) == 1
    sd = throttler.downloads[0]
    del throttler.downloads[:]
    assert sd.get_id() == 'a' * 20
    assert not sd.is_downloading()
    assert not sd.is_throttled()
    assert database.files == {}
    assert connection.messages == [bencode({'type': 'list all files'})]
    del connection.messages[:]
    
    assert not sd.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert not sd.is_throttled()

    downloader.got_message(connection, bencode({'type': 'I have files', 'files': [fid]}))
    assert uploader.received == []
    assert throttler.events == ['possible']
    del throttler.events[:]
    assert database.files == {}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert not sd.is_throttled()

    assert sd.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection.messages == [bencode({'type': 'send slice', 'file': fid, 
        'begin': 0, 'length': 3})]
    del connection.messages[:]
    assert sd.is_downloading()
    assert not sd.is_throttled()

    downloader.got_message(connection, bencode({'type': "I don't have files", 
        'files': [fid]}))
    assert uploader.received == []
    assert throttler.events == [('hiccup', true)]
    del throttler.events[:]
    assert database.files == {}
    assert connection.messages == [bencode({'type': 'done downloading'})]
    del connection.messages[:]
    assert not sd.is_downloading()
    assert not sd.is_throttled()

    downloader.got_message(connection, bencode({'type': "I don't have files", 
        'files': [fid]}))
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert not sd.is_throttled()

    downloader.got_message(connection, bencode({'type': 'I have files', 'files': [fid]}))
    assert uploader.received == []
    assert throttler.events == ['possible']
    del throttler.events[:]
    assert database.files == {}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert not sd.is_throttled()

    assert sd.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection.messages == [bencode({'type': 'send slice', 'file': fid, 
        'begin': 0, 'length': 3})]
    del connection.messages[:]
    assert sd.is_downloading()
    assert not sd.is_throttled()

def test_hiccup2():
    file1 = 'ab'
    fid1 = sha(file1).digest()
    file2 = 'cd'
    fid2 = sha(file2).digest()
    database = DummyDatabase({fid1: len(file1), fid2: len(file2)}, [fid1, fid2])
    throttler = DummyThrottler()
    uploader = DummyUploader()
    downloader = Downloader(throttler, database, uploader, 3, 1)
    connection = DummyConnection('a' * 20)
    
    downloader.connection_made(connection)
    assert uploader.received == []
    assert throttler.events == ['connected']
    del throttler.events[:]
    assert len(throttler.downloads) == 1
    sd = throttler.downloads[0]
    del throttler.downloads[:]
    assert sd.get_id() == 'a' * 20
    assert not sd.is_downloading()
    assert not sd.is_throttled()
    assert database.files == {}
    assert connection.messages == [bencode({'type': 'list all files'})]
    del connection.messages[:]
    
    assert not sd.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert not sd.is_throttled()

    downloader.got_message(connection, bencode({'type': 'I have files', 'files': [fid1, fid2]}))
    assert uploader.received == []
    assert throttler.events == ['possible']
    del throttler.events[:]
    assert database.files == {}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert not sd.is_throttled()

    assert sd.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection.messages == [bencode({'type': 'send slice', 'file': fid1, 
        'begin': 0, 'length': 2})]
    del connection.messages[:]
    assert sd.is_downloading()
    assert not sd.is_throttled()

    downloader.got_message(connection, bencode({'type': "I don't have files", 
        'files': [fid1]}))
    assert uploader.received == []
    assert throttler.events == [('hiccup', false)]
    del throttler.events[:]
    assert database.files == {}
    assert connection.messages == [bencode({'type': 'send slice', 'file': fid2, 
        'begin': 0, 'length': 2})]
    del connection.messages[:]
    assert sd.is_downloading()
    assert not sd.is_throttled()

    downloader.got_message(connection, bencode({'type': "I don't have files", 
        'files': [fid2]}))
    assert uploader.received == []
    assert throttler.events == [('hiccup', true)]
    del throttler.events[:]
    assert database.files == {}
    assert connection.messages == [bencode({'type': 'done downloading'})]
    del connection.messages[:]
    assert not sd.is_downloading()
    assert not sd.is_throttled()

    downloader.got_message(connection, bencode({'type': 'I have files', 'files': [fid1, fid2]}))
    assert uploader.received == []
    assert throttler.events == ['possible']
    del throttler.events[:]
    assert database.files == {}
    assert connection.messages == []
    assert not sd.is_downloading()
    assert not sd.is_throttled()

    assert sd.start_downloading()
    assert uploader.received == []
    assert throttler.events == []
    assert database.files == {}
    assert connection.messages == [bencode({'type': 'send slice', 'file': fid1, 
        'begin': 0, 'length': 2})]
    del connection.messages[:]
    assert sd.is_downloading()
    assert not sd.is_throttled()



