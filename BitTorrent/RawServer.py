# Written by Bram Cohen
# see LICENSE.txt for license information

from bisect import insort
import socket
from cStringIO import StringIO
from traceback import print_exc
from errno import EWOULDBLOCK, EINTR
try:
    from select import poll, error, POLLIN, POLLOUT, POLLERR, POLLHUP
    timemult = 1000
except ImportError:
    from selectpoll import poll, error, POLLIN, POLLOUT, POLLERR, POLLHUP
    timemult = 1
from threading import Thread, Event
from time import time, sleep
import sys
true = 1
false = 0

all = POLLIN | POLLOUT

class SingleSocket:
    def __init__(self, raw_server, sock, handler):
        self.raw_server = raw_server
        self.socket = sock
        self.handler = handler
        self.buffer = []
        self.last_hit = time()
        self.connected = false
        
    def get_ip(self):
        try:
            return self.socket.getpeername()[0]
        except socket.error:
            return 'no connection'
        
    def close(self):
        sock = self.socket
        self.socket = None
        self.buffer = []
        del self.raw_server.single_sockets[sock.fileno()]
        self.raw_server.poll.unregister(sock)
        sock.close()

    def shutdown(self, val):
        self.socket.shutdown(val)

    def is_flushed(self):
        return len(self.buffer) == 0

    def write(self, s):
        assert self.socket is not None
        self.buffer.append(s)
        if len(self.buffer) == 1:
            self.try_write()

    def try_write(self):
        if self.connected:
            try:
                while self.buffer != []:
                    amount = self.socket.send(self.buffer[0])
                    if amount != len(self.buffer[0]):
                        if amount != 0:
                            self.buffer[0] = self.buffer[0][amount:]
                        break
                    del self.buffer[0]
            except socket.error, e:
                code, msg = e
                if code != EWOULDBLOCK:
                    self.raw_server.dead_from_write.append(self)
                    return
        if self.buffer == []:
            self.raw_server.poll.register(self.socket, POLLIN)
        else:
            self.raw_server.poll.register(self.socket, all)

class RawServer:
    def __init__(self, doneflag, timeout_check_interval, timeout, noisy = true):
        self.timeout_check_interval = timeout_check_interval
        self.timeout = timeout
        self.poll = poll()
        # {socket: SingleSocket}
        self.single_sockets = {}
        self.dead_from_write = []
        self.doneflag = doneflag
        self.noisy = noisy
        self.funcs = []
        self.externally_added = []
        self.add_task(self.scan_for_timeouts, timeout_check_interval)

    def add_task(self, func, delay):
        insort(self.funcs, (time() + delay, func))

    def external_add_task(self, func, delay = 0):
        self.externally_added.append((func, delay))

    def scan_for_timeouts(self):
        self.add_task(self.scan_for_timeouts, self.timeout_check_interval)
        t = time() - self.timeout
        tokill = []
        for s in self.single_sockets.values():
            if s.last_hit < t:
                tokill.append(s)
        for k in tokill:
            if k.socket is not None:
                self._close_socket(k)

    def bind(self, port, bind = '', reuse = false):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if reuse:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.setblocking(0)
        server.bind((bind, port))
        server.listen(5)
        self.poll.register(server, POLLIN)
        self.server = server

    def start_connection(self, dns, handler = None):
        if handler is None:
            handler = self.handler
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(0)
        sock.connect_ex(dns)
        self.poll.register(sock, POLLIN)
        s = SingleSocket(self, sock, handler)
        self.single_sockets[sock.fileno()] = s
        return s
        
    def handle_events(self, events):
        for sock, event in events:
            if sock == self.server.fileno():
                if event & (POLLHUP | POLLERR) != 0:
                    self.server.close()
                    self.poll.unregister(self.server)
                    print "lost server socket"
                else:
                    newsock, addr = self.server.accept()
                    newsock.setblocking(0)
                    nss = SingleSocket(self, newsock, self.handler)
                    self.single_sockets[newsock.fileno()] = nss
                    self.poll.register(newsock, POLLIN)
                    self.handler.external_connection_made(nss)
            else:
                s = self.single_sockets.get(sock)
                if s is None:
                    continue
                s.connected = true
                if (event & (POLLHUP | POLLERR)) != 0:
                    self._close_socket(s)
                    continue
                if (event & POLLIN) != 0:
                    try:
                        s.last_hit = time()
                        data = s.socket.recv(100000)
                        if data == '':
                            self._close_socket(s)
                        else:
                            s.handler.data_came_in(s, data)
                    except socket.error, e:
                        code, msg = e
                        if code != EWOULDBLOCK:
                            self._close_socket(s)
                            continue
                if (event & POLLOUT) != 0 and s.socket is not None and not s.is_flushed():
                    s.try_write()
                    if s.is_flushed():
                        s.handler.connection_flushed(s)

    def pop_external(self):
        try:
            while true:
                (a, b) = self.externally_added.pop()
                self.add_task(a, b)
        except IndexError:
            pass

    def listen_forever(self, handler):
        self.handler = handler
        try:
            while not self.doneflag.isSet():
                try:
                    self.pop_external()
                    if len(self.funcs) == 0:
                        period = 2 ** 30
                    else:
                        period = self.funcs[0][0] - time()
                    if period < 0:
                        period = 0
                    events = self.poll.poll(period * timemult)
                    if self.doneflag.isSet():
                        return
                    while len(self.funcs) > 0 and self.funcs[0][0] <= time():
                        garbage, func = self.funcs[0]
                        del self.funcs[0]
                        try:
                            func()
                        except KeyboardInterrupt:
                            print_exc()
                            return
                        except:
                            if self.noisy:
                                print_exc()
                    self._close_dead()
                    self.handle_events(events)
                    if self.doneflag.isSet():
                        return
                    self._close_dead()
                except error:
                    if self.doneflag.isSet():
                        return
                    else:
                        print_exc()
                except KeyboardInterrupt:
                    print_exc()
                    return
                except:
                    print_exc()
        finally:
            for ss in self.single_sockets.values():
                ss.close()
            self.server.close()

    def _close_dead(self):
        while len(self.dead_from_write) > 0:
            old = self.dead_from_write
            self.dead_from_write = []
            for s in old:
                if s.socket is not None:
                    self._close_socket(s)

    def _close_socket(self, s):
        sock = s.socket.fileno()
        s.socket.close()
        self.poll.unregister(sock)
        del self.single_sockets[sock]
        s.socket = None
        s.handler.connection_lost(s)

# everything below is for testing

class DummyHandler:
    def __init__(self):
        self.external_made = []
        self.data_in = []
        self.lost = []

    def external_connection_made(self, s):
        self.external_made.append(s)
    
    def data_came_in(self, s, data):
        self.data_in.append((s, data))
    
    def connection_lost(self, s):
        self.lost.append(s)

    def connection_flushed(self, s):
        pass

def sl(rs, handler, port):
    rs.bind(port)
    Thread(target = rs.listen_forever, args = [handler]).start()

def loop(rs):
    x = []
    def r(rs = rs, x = x):
        rs.add_task(x[0], .1)
    x.append(r)
    rs.add_task(r, .1)

def test_starting_side_close():
    try:
        da = DummyHandler()
        fa = Event()
        sa = RawServer(fa, 100, 100)
        loop(sa)
        sl(sa, da, 5000)
        db = DummyHandler()
        fb = Event()
        sb = RawServer(fb, 100, 100)
        loop(sb)
        sl(sb, db, 5001)

        sleep(.5)
        ca = sa.start_connection(('', 5001))
        sleep(1)
        
        assert da.external_made == []
        assert da.data_in == []
        assert da.lost == []
        assert len(db.external_made) == 1
        cb = db.external_made[0]
        del db.external_made[:]
        assert db.data_in == []
        assert db.lost == []

        ca.write('aaa')
        cb.write('bbb')
        sleep(1)
        
        assert da.external_made == []
        assert da.data_in == [(ca, 'bbb')]
        del da.data_in[:]
        assert da.lost == []
        assert db.external_made == []
        assert db.data_in == [(cb, 'aaa')]
        del db.data_in[:]
        assert db.lost == []

        ca.write('ccc')
        cb.write('ddd')
        sleep(1)
        
        assert da.external_made == []
        assert da.data_in == [(ca, 'ddd')]
        del da.data_in[:]
        assert da.lost == []
        assert db.external_made == []
        assert db.data_in == [(cb, 'ccc')]
        del db.data_in[:]
        assert db.lost == []

        ca.close()
        sleep(1)

        assert da.external_made == []
        assert da.data_in == []
        assert da.lost == []
        assert db.external_made == []
        assert db.data_in == []
        assert db.lost == [cb]
        del db.lost[:]
    finally:
        fa.set()
        fb.set()

def test_receiving_side_close():
    try:
        da = DummyHandler()
        fa = Event()
        sa = RawServer(fa, 100, 100)
        loop(sa)
        sl(sa, da, 5002)
        db = DummyHandler()
        fb = Event()
        sb = RawServer(fb, 100, 100)
        loop(sb)
        sl(sb, db, 5003)
        
        sleep(.5)
        ca = sa.start_connection(('', 5003))
        sleep(1)
        
        assert da.external_made == []
        assert da.data_in == []
        assert da.lost == []
        assert len(db.external_made) == 1
        cb = db.external_made[0]
        del db.external_made[:]
        assert db.data_in == []
        assert db.lost == []

        ca.write('aaa')
        cb.write('bbb')
        sleep(1)
        
        assert da.external_made == []
        assert da.data_in == [(ca, 'bbb')]
        del da.data_in[:]
        assert da.lost == []
        assert db.external_made == []
        assert db.data_in == [(cb, 'aaa')]
        del db.data_in[:]
        assert db.lost == []

        ca.write('ccc')
        cb.write('ddd')
        sleep(1)
        
        assert da.external_made == []
        assert da.data_in == [(ca, 'ddd')]
        del da.data_in[:]
        assert da.lost == []
        assert db.external_made == []
        assert db.data_in == [(cb, 'ccc')]
        del db.data_in[:]
        assert db.lost == []

        cb.close()
        sleep(1)

        assert da.external_made == []
        assert da.data_in == []
        assert da.lost == [ca]
        del da.lost[:]
        assert db.external_made == []
        assert db.data_in == []
        assert db.lost == []
    finally:
        fa.set()
        fb.set()

def test_connection_refused():
    try:
        da = DummyHandler()
        fa = Event()
        sa = RawServer(fa, 100, 100)
        loop(sa)
        sl(sa, da, 5006)

        sleep(.5)
        ca = sa.start_connection(('', 5007))
        sleep(1)
        
        assert da.external_made == []
        assert da.data_in == []
        assert da.lost == [ca]
        del da.lost[:]
    finally:
        fa.set()

def test_both_close():
    try:
        da = DummyHandler()
        fa = Event()
        sa = RawServer(fa, 100, 100)
        loop(sa)
        sl(sa, da, 5004)

        sleep(1)
        db = DummyHandler()
        fb = Event()
        sb = RawServer(fb, 100, 100)
        loop(sb)
        sl(sb, db, 5005)

        sleep(.5)
        ca = sa.start_connection(('', 5005))
        sleep(1)
        
        assert da.external_made == []
        assert da.data_in == []
        assert da.lost == []
        assert len(db.external_made) == 1
        cb = db.external_made[0]
        del db.external_made[:]
        assert db.data_in == []
        assert db.lost == []

        ca.write('aaa')
        cb.write('bbb')
        sleep(1)
        
        assert da.external_made == []
        assert da.data_in == [(ca, 'bbb')]
        del da.data_in[:]
        assert da.lost == []
        assert db.external_made == []
        assert db.data_in == [(cb, 'aaa')]
        del db.data_in[:]
        assert db.lost == []

        ca.write('ccc')
        cb.write('ddd')
        sleep(1)
        
        assert da.external_made == []
        assert da.data_in == [(ca, 'ddd')]
        del da.data_in[:]
        assert da.lost == []
        assert db.external_made == []
        assert db.data_in == [(cb, 'ccc')]
        del db.data_in[:]
        assert db.lost == []

        ca.close()
        cb.close()
        sleep(1)

        assert da.external_made == []
        assert da.data_in == []
        assert da.lost == []
        assert db.external_made == []
        assert db.data_in == []
        assert db.lost == []
    finally:
        fa.set()
        fb.set()

def test_normal():
    l = []
    f = Event()
    s = RawServer(f, 100, 100)
    loop(s)
    sl(s, DummyHandler(), 5007)
    s.add_task(lambda l = l: l.append('b'), 2)
    s.add_task(lambda l = l: l.append('a'), 1)
    s.add_task(lambda l = l: l.append('d'), 4)
    sleep(1.5)
    s.add_task(lambda l = l: l.append('c'), 1.5)
    sleep(3)
    assert l == ['a', 'b', 'c', 'd']
    f.set()

def test_catch_exception():
    l = []
    f = Event()
    s = RawServer(f, 100, 100, false)
    loop(s)
    sl(s, DummyHandler(), 5009)
    s.add_task(lambda l = l: l.append('b'), 2)
    s.add_task(lambda: 4/0, 1)
    sleep(3)
    assert l == ['b']
    f.set()

def test_closes_if_not_hit():
    try:
        da = DummyHandler()
        fa = Event()
        sa = RawServer(fa, 2, 2)
        loop(sa)
        sl(sa, da, 5012)

        sleep(1)
        db = DummyHandler()
        fb = Event()
        sb = RawServer(fb, 100, 100)
        loop(sb)
        sl(sb, db, 5013)
        
        sleep(.5)
        sa.start_connection(('', 5013))
        sleep(1)
        
        assert da.external_made == []
        assert da.data_in == []
        assert da.lost == []
        assert len(db.external_made) == 1
        del db.external_made[:]
        assert db.data_in == []
        assert db.lost == []

        sleep(3.1)
        
        assert len(da.lost) == 1
        assert len(db.lost) == 1
    finally:
        fa.set()
        fb.set()

def test_does_not_close_if_hit():
    try:
        da = DummyHandler()
        fa = Event()
        sa = RawServer(fa, 2, 2)
        loop(sa)
        sl(sa, da, 5012)

        sleep(1)
        db = DummyHandler()
        fb = Event()
        sb = RawServer(fb, 100, 100)
        loop(sb)
        sl(sb, db, 5013)
        
        sleep(.5)
        sa.start_connection(('', 5013))
        sleep(1)
        
        assert da.external_made == []
        assert da.data_in == []
        assert da.lost == []
        assert len(db.external_made) == 1
        cb = db.external_made[0]
        del db.external_made[:]
        assert db.data_in == []
        assert db.lost == []

        cb.write('bbb')
        sleep(2)
        
        assert da.lost == []
        assert db.lost == []
    finally:
        fa.set()
        fb.set()
