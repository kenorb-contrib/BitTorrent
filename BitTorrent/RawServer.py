# Written by Bram Cohen
# this file is public domain

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
from threading import Thread
from time import time, sleep
import sys
true = 1
false = 0

all = POLLIN | POLLOUT

class SingleSocket:
    def __init__(self, raw_server, sock):
        self.raw_server = raw_server
        self.socket = sock
        self.buffer = []
        
    def get_ip(self):
        try:
            return self.socket.getpeername()[0]
        except socket.error, e:
            return 'no connection'
        
    def close(self):
        sock = self.socket
        self.socket = None
        self.buffer = []
        del self.raw_server.single_sockets[sock.fileno()]
        self.raw_server.poll.unregister(sock)
        sock.close()

    def write(self, s):
        assert self.socket is not None
        self.buffer.append(s)
        if len(self.buffer) == 1:
            self.try_write()

    def try_write(self):
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
        if self.buffer == []:
            self.raw_server.poll.register(self.socket, POLLIN)
        else:
            self.raw_server.poll.register(self.socket, all)

class RawServer:
    def __init__(self, max_poll_period, noisy = true):
        self.max_poll_period = max_poll_period
        self.poll = poll()
        # {socket: SingleSocket}
        self.single_sockets = {}
        self.dead_from_write = []
        self.running = true
        self.noisy = noisy
        self.funcs = []

    def shutdown(self):
        self.running = false

    def add_task(self, func, delay):
        insort(self.funcs, (time() + delay, func))

    def start_listening(self, handler, port, ret = true):
        self.handler = handler
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.setblocking(0)
        self.server.bind(('', port))
        self.server.listen(5)
        self.poll.register(self.server, POLLIN)
        if ret:
            Thread(target = self.listen_forever).start()
        else:
            self.listen_forever()
    
    def start_connection(self, dns):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(0)
        sock.connect_ex(dns)
        self.poll.register(sock, all)
        s = SingleSocket(self, sock)
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
                    nss = SingleSocket(self, newsock)
                    self.single_sockets[newsock.fileno()] = nss
                    self.poll.register(newsock, POLLIN)
                    self.handler.external_connection_made(nss)
            else:
                if sock == self.server.fileno():
                    continue
                s = self.single_sockets.get(sock)
                if s is None:
                    continue
                if (event & (POLLHUP | POLLERR)) != 0:
                    self.close_socket(s)
                    continue
                if (event & POLLIN) != 0:
                    try:
                        hit = false
                        data = s.socket.recv(100000)
                        if data == '':
                            self.close_socket(s)
                            hit = true
                        else:
                            self.handler.data_came_in(s, data)
                    except socket.error, e:
                        code, msg = e
                        if code != EWOULDBLOCK:
                            self.close_socket(s)
                            continue
                    if hit:
                        continue
                if (event & POLLOUT) != 0 and s.socket is not None:
                    s.try_write()

    def listen_forever(self):
        try:
            while self.running:
                try:
                    if len(self.funcs) == 0:
                        period = self.max_poll_period
                    else:
                        period = self.funcs[0][0] - time()
                        if period > self.max_poll_period:
                            period = self.max_poll_period
                    if period < 0:
                        period = 0
                    events = self.poll.poll(period * timemult)
                    if not self.running:
                        return
                    while len(self.funcs) > 0 and self.funcs[0][0] <= time():
                        garbage, func = self.funcs[0]
                        del self.funcs[0]
                        try:
                            func()
                        except KeyboardInterrupt:
                            raise
                        except:
                            if self.noisy:
                                print_exc()
                    self.close_dead()
                    self.handle_events(events)
                    self.close_dead()
                except error, e:
                    if not self.running:
                        return
                    else:
                        print_exc()
                except KeyboardInterrupt:
                    return
                except:
                    print_exc()
        finally:
            self.server.close()
            for ss in self.single_sockets.values():
                ss.close()

    def close_dead(self):
        while len(self.dead_from_write) > 0:
            old = self.dead_from_write
            self.dead_from_write = []
            for s in old:
                if self.single_sockets.has_key(s):
                    self.close_socket(s)

    def close_socket(self, s):
        sock = s.socket.fileno()
        s.socket.close()
        self.poll.unregister(sock)
        del self.single_sockets[sock]
        s.socket = None
        self.handler.connection_lost(s)

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

def test_starting_side_close():
    try:
        da = DummyHandler()
        sa = RawServer(.1)
        sa.start_listening(da, 5000)
        db = DummyHandler()
        sb = RawServer(.1)
        sb.start_listening(db, 5001)

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
        sa.shutdown()
        sb.shutdown()

def test_receiving_side_close():
    try:
        da = DummyHandler()
        sa = RawServer(.1)
        sa.start_listening(da, 5002)
        db = DummyHandler()
        sb = RawServer(.1)
        sb.start_listening(db, 5003)
        
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
        sa.shutdown()
        sb.shutdown()

def test_connection_refused():
    try:
        da = DummyHandler()
        sa = RawServer(.1)
        sa.start_listening(da, 5006)
        
        ca = sa.start_connection(('', 5007))
        sleep(1)
        
        assert da.external_made == []
        assert da.data_in == []
        assert da.lost == [ca]
        del da.lost[:]
    finally:
        sa.shutdown()

def test_both_close():
    try:
        da = DummyHandler()
        sa = RawServer(.1)
        sa.start_listening(da, 5004)

        sleep(1)
        db = DummyHandler()
        sb = RawServer(.1)
        sb.start_listening(db, 5005)
        
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
        sa.shutdown()
        sb.shutdown()

def test_normal():
    l = []
    s = RawServer(5)
    s.start_listening(DummyHandler(), 5007)
    s.add_task(lambda l = l: l.append('b'), 2)
    s.add_task(lambda l = l: l.append('a'), 1)
    s.add_task(lambda l = l: l.append('d'), 4)
    sleep(1.5)
    s.add_task(lambda l = l: l.append('c'), 1.5)
    sleep(3)
    assert l == ['a', 'b', 'c', 'd']
    s.shutdown()

def test_catch_exception():
    l = []
    s = RawServer(5, false)
    s.start_listening(DummyHandler(), 5009)
    s.add_task(lambda l = l: l.append('b'), 2)
    s.add_task(lambda: 4/0, 1)
    sleep(3)
    assert l == ['b']
    s.shutdown()
