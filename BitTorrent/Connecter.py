# written by Bram Cohen
# this file is public domain

true = 1
false = 0

class TransferConnection:
    def __init__(self, connection, dict):
        self.connection = connection
        self.dict = dict
        self.id = connection.get_id()
        self.is_local = connection.is_locally_initiated()

    def is_locally_initiated(self):
        return self.is_local

    def get_ip(self):
        return self.connection.get_ip()

    def send_message(self, message):
        self.connection.send_message(message)

    def get_id(self):
        return self.id
        
    def close(self):
        connection = self.connection
        del self.connection
        del self.dict[self.id]
        del self.dict
        connection.close()

class Connecter:
    def __init__(self, uploader, downloader):
        self.uploader = uploader
        self.downloader = downloader
        # {id: TransferConnection}
        self.uploads = {}
        # {id: TransferConnection}
        self.downloads = {}
        self.encrypter = None

    def set_encrypter(self, encrypter):
        self.encrypter = encrypter

    def start_connecting(self, dnss):
        for d in dnss:
            self.encrypter.start_connection(d)

    def locally_initiated_connection_completed(self, connection):
        k = connection.get_id()
        if not self.downloads.has_key(k):
            down = TransferConnection(connection, self.downloads)
            self.downloads[k] = down
            connection.send_message('download')
            if not self.uploads.has_key(k):
                self.encrypter.start_connection(connection.get_dns())
            self.downloader.connection_made(down)
        elif not self.uploads.has_key(k):
            up = TransferConnection(connection, self.uploads)
            self.uploads[k] = up
            connection.send_message('upload')
            self.uploader.connection_made(up)
        else:
            connection.close()

    def connection_lost(self, connection):
        k = connection.get_id()
        up = self.uploads.get(k, None)
        if up is not None and up.connection == connection:
            del self.uploads[k]
            del up.dict
            del up.connection
            self.uploader.connection_lost(up)
            return
        down = self.downloads.get(k, None)
        if down is not None and down.connection == connection:
            del self.downloads[k]
            del down.dict
            del down.connection
            self.downloader.connection_lost(down)
            return

    def got_message(self, connection, message):
        k = connection.get_id()
        up = self.uploads.get(k, None)
        if up is not None and up.connection == connection:
            self.uploader.got_message(up, message)
            return
        down = self.downloads.get(k, None)
        if down is not None and down.connection == connection:
            self.downloader.got_message(down, message)
            return
        if message == 'download':
            if up is None:
                up = TransferConnection(connection, self.uploads)
                self.uploads[k] = up
                self.uploader.connection_made(up)
            else:
                up.connection.close()
                del up.dict
                del up.connection
                newup = TransferConnection(connection, self.uploads)
                self.uploads[k] = newup
                self.uploader.connection_lost(up)
                self.uploader.connection_made(newup)
        elif message == 'upload':
            if down is None:
                down = TransferConnection(connection, self.downloads)
                self.downloads[k] = down
                self.downloader.connection_made(down)
            else:
                down.connection.close()
                del down.dict
                del down.connection
                newdown = TransferConnection(connection, self.downloads)
                self.downloads[k] = newdown
                self.downloader.connection_lost(down)
                self.downloader.connection_made(newdown)
        else:
            connection.close()

# everything below is for testing

class DummyEncrypter:
    def __init__(self):
        self.c = []
        
    def start_connection(self, ip):
        self.c.append(ip)

class DummyScheduler:
    def __init__(self):
        self.c = []
    
    def __call__(self, func, delay, args = []):
        self.c.append((func, delay, args))

class DummyConnection:
    def __init__(self, mid, dns = None):
        self.closed = false
        self.m = []
        self.mid = mid
        self.dns = dns

    def get_ip(self):
        return 'fake.ip'

    def close(self):
        self.closed = true
        
    def send_message(self, message):
        self.m.append(message)
        
    def get_id(self):
        return self.mid
        
    def get_dns(self):
        return self.dns
        
    def is_locally_initiated(self):
        return self.dns != None

class DummyTransfer:
    def __init__(self):
        self.cs_made = []
        self.cs_lost = []
        self.m = []
        
    def connection_made(self, connection):
        self.cs_made.append(connection)
        
    def connection_lost(self, connection):
        self.cs_lost.append(connection)
        
    def got_message(self, connection, message):
        self.m.append((connection, message))

def test_close_local_of_local_start():
    up = DummyTransfer()
    down = DummyTransfer()
    s = DummyScheduler()
    c = Connecter(up, down, s, 5, 6)
    e = DummyEncrypter()
    c.set_encrypter(e)
    c.start_connecting(['testcode.com'])
    assert s.c == []
    assert e.c == ['testcode.com']
    del e.c[:]

    dc = DummyConnection('a' * 20, 'testcode.com')
    c.locally_initiated_connection_completed(dc)
    assert len(down.cs_made) == 1 and down.cs_made[0].get_id() == 'a' * 20
    assert len(up.cs_made) == 0
    assert s.c == []
    assert dc.m == ['download']
    del dc.m[:]

    down.cs_made[0].send_message('a')
    assert dc.m == ['a']
    
    c.got_message(dc, 'b')
    assert down.m == [(down.cs_made[0], 'b')]

    assert not dc.closed
    down.cs_made[0].close()
    assert dc.closed
    assert s.c == []

def test_close_remote_of_local_start():
    up = DummyTransfer()
    down = DummyTransfer()
    s = DummyScheduler()
    c = Connecter(up, down, s, 5, 6)
    e = DummyEncrypter()
    c.set_encrypter(e)
    c.start_connecting(['testcode.com'])
    assert s.c == []
    assert e.c == ['testcode.com']
    del e.c[:]
    assert s.c == []
    
    dc = DummyConnection('a' * 20, 'testcode.com')
    c.locally_initiated_connection_completed(dc)
    assert len(down.cs_made) == 1 and down.cs_made[0].get_id() == 'a' * 20
    assert len(up.cs_made) == 0
    assert s.c == []
    assert e.c == ['testcode.com']
    del e.c[:]
    assert dc.m == ['download']
    del dc.m[:]

    down.cs_made[0].send_message('a')
    assert dc.m == ['a']
    
    c.got_message(dc, 'b')
    assert down.m == [(down.cs_made[0], 'b')]

    assert not dc.closed
    c.connection_lost(dc)
    assert down.cs_lost == down.cs_made
    assert len(s.c) == 1 and s.c[0][1] == 5 and s.c[0][2] == ['testcode.com']

def test_close_remote_of_remote_start():
    up = DummyTransfer()
    down = DummyTransfer()
    s = DummyScheduler()
    c = Connecter(up, down, s, 5, 6)
    e = DummyEncrypter()
    c.set_encrypter(e)
    
    dc = DummyConnection('a' * 20)
    c.got_message(dc, 'upload')
    assert len(down.cs_made) == 1 and down.cs_made[0].get_id() == 'a' * 20

    c.got_message(dc, 'booga')
    assert down.m == [(down.cs_made[0], 'booga')]

    down.cs_made[0].send_message('booga 2')
    assert dc.m == ['booga 2']

    c.connection_lost(dc)
    assert down.cs_lost == down.cs_made
    
def test_close_local_of_remote_start():
    up = DummyTransfer()
    down = DummyTransfer()
    s = DummyScheduler()
    c = Connecter(up, down, s, 5, 6)
    e = DummyEncrypter()
    c.set_encrypter(e)
    
    dc = DummyConnection('a' * 20)
    c.got_message(dc, 'upload')
    assert len(down.cs_made) == 1 and down.cs_made[0].get_id() == 'a' * 20

    c.got_message(dc, 'booga')
    assert down.m == [(down.cs_made[0], 'booga')]

    down.cs_made[0].send_message('booga 2')
    assert dc.m == ['booga 2']

    down.cs_made[0].close()
    assert down.cs_lost == []
    assert dc.closed

def test_remote_connect_down():
    up = DummyTransfer()
    down = DummyTransfer()
    s = DummyScheduler()
    c = Connecter(up, down, s, 5, 6)
    e = DummyEncrypter()
    c.set_encrypter(e)
    
    dc = DummyConnection('a' * 20)
    c.got_message(dc, 'upload')
    assert len(down.cs_made) == 1 and down.cs_made[0].get_id() == 'a' * 20

    c.got_message(dc, 'booga')
    assert down.m == [(down.cs_made[0], 'booga')]
    del down.m[:]

    down.cs_made[0].send_message('booga 2')
    assert dc.m == ['booga 2']

    dc2 = DummyConnection('a' * 20)
    c.got_message(dc2, 'upload')
    assert len(down.cs_made) == 1
    assert dc.closed

    c.got_message(dc2, 'booga 3')
    assert down.m == [(down.cs_made[0], 'booga 3')]

    down.cs_made[0].send_message('booga 4')
    assert dc2.m == ['booga 4']
    
def test_remote_connect_up():
    up = DummyTransfer()
    down = DummyTransfer()
    s = DummyScheduler()
    c = Connecter(up, down, s, 5, 6)
    e = DummyEncrypter()
    c.set_encrypter(e)
    
    dc = DummyConnection('a' * 20)
    c.got_message(dc, 'download')
    assert len(up.cs_made) == 1 and up.cs_made[0].get_id() == 'a' * 20

    c.got_message(dc, 'booga')
    assert up.m == [(up.cs_made[0], 'booga')]
    del up.m[:]

    up.cs_made[0].send_message('booga 2')
    assert dc.m == ['booga 2']

    dc2 = DummyConnection('a' * 20)
    c.got_message(dc2, 'download')
    assert len(up.cs_made) == 1
    assert dc.closed

    c.got_message(dc2, 'booga 3')
    assert up.m == [(up.cs_made[0], 'booga 3')]

    up.cs_made[0].send_message('booga 4')
    assert dc2.m == ['booga 4']
    
def test_local_connect():
    up = DummyTransfer()
    down = DummyTransfer()
    s = DummyScheduler()
    c = Connecter(up, down, s, 5, 6)
    e = DummyEncrypter()
    c.set_encrypter(e)
    c.start_connecting(['testcode.com'])
    assert s.c == []
    assert e.c == ['testcode.com']
    del e.c[:]
    assert s.c == []
    
    dc = DummyConnection('a' * 20, 'testcode.com')
    c.locally_initiated_connection_completed(dc)
    assert len(down.cs_made) == 1 and down.cs_made[0].get_id() == 'a' * 20
    assert len(up.cs_made) == 0
    assert s.c == []
    assert e.c == ['testcode.com']
    del e.c[:]
    assert dc.m == ['download']
    del dc.m[:]

    down.cs_made[0].send_message('a')
    assert dc.m == ['a']
    
    c.got_message(dc, 'b')
    assert down.m == [(down.cs_made[0], 'b')]

    assert s.c == []

    dc2 = DummyConnection('a' * 20, 'testcode.com')
    c.locally_initiated_connection_completed(dc2)
    assert len(up.cs_made) == 1 and up.cs_made[0].get_id() == 'a' * 20
    assert s.c == []
    assert dc2.m == ['upload']
    del dc2.m[:]

    up.cs_made[0].send_message('c')
    assert dc2.m == ['c']
    
    c.got_message(dc2, 'd')
    assert up.m == [(up.cs_made[0], 'd')]

    assert s.c == []

    dc3 = DummyConnection('a' * 20, 'testcode.com')
    c.locally_initiated_connection_completed(dc3)
    assert dc3.closed
