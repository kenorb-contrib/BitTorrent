# Written by Bram Cohen
# see LICENSE.txt for license information

from bisect import insort
import socket
from cStringIO import StringIO
from traceback import print_exc
from errno import EWOULDBLOCK, ECONNREFUSED, EHOSTUNREACH
try:
    from select import poll, error, POLLIN, POLLOUT, POLLERR, POLLHUP
    timemult = 1000
except ImportError:
    from selectpoll import poll, error, POLLIN, POLLOUT, POLLERR, POLLHUP
    timemult = 1
from threading import Thread, Event
from time import time, sleep
import sys
from random import randrange, shuffle
true = 1
false = 0

all = POLLIN | POLLOUT

def autodetect_ipv6():
    try:
        assert sys.version_info >= (2,3)
        assert socket.has_ipv6
        socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    except:
        return 0
    return 1

def autodetect_socket_style():
	if sys.platform.find('linux') < 0:
		return 1
	else:
		try:
			f = open('/proc/sys/net/ipv6/bindv6only','r')
			dual_socket_style = int(f.read())
			f.close()
			return int(not dual_socket_style)
		except:
			return 0

class SingleSocket:
    def __init__(self, raw_server, sock, handler, ip = None):
        self.raw_server = raw_server
        self.socket = sock
        self.handler = handler
        self.buffer = []
        self.last_hit = time()
        self.fileno = sock.fileno()
        self.connected = false
        try:
            self.ip = self.socket.getpeername()[0]
        except:
            if ip is None:
                self.ip = 'unknown'
            else:
                self.ip = ip
        
    def get_ip(self):
        return self.ip
        
    def close(self):
        sock = self.socket
        self.socket = None
        self.buffer = []
        del self.raw_server.single_sockets[self.fileno]
        self.raw_server.poll.unregister(sock)
        sock.close()

    def shutdown(self, val):
        self.socket.shutdown(val)

    def is_flushed(self):
        return not self.buffer

    def write(self, s):
        assert self.socket is not None
        self.buffer.append(s)
        if len(self.buffer) == 1:
            self.try_write()

    def try_write(self):
        if self.connected:
            try:
                while self.buffer:
                    buf = self.buffer[0]
                    amount = self.socket.send(buf)
                    if amount != len(buf):
                        if amount != 0:
                            self.buffer[0] = buf[amount:]
                        break
                    del self.buffer[0]
            except socket.error, e:
                try:
                    if e[0] != EWOULDBLOCK:
                        self.raw_server.dead_from_write.append(self)
                        return
                except:
                    raise TypeError, "cannot decode "+str(e)
        if self.buffer:
            self.raw_server.poll.register(self.socket, all)
        else:
            self.raw_server.poll.register(self.socket, POLLIN)

    def set_handler(self, handler):
        self.handler = handler

class RawServer:
    def __init__(self, doneflag, timeout_check_interval, timeout, noisy = true,
                 ipv6_enable = true, failfunc = lambda x: None, errorfunc = None):
        self.timeout_check_interval = timeout_check_interval
        self.timeout = timeout
        self.poll = poll()
        # {socket: SingleSocket}
        self.servers = {}
        self.single_sockets = {}
        self.dead_from_write = []
        self.doneflag = doneflag
        self.noisy = noisy
        self.ipv6_enable = ipv6_enable
        self.failfunc = failfunc
        self.errorfunc = errorfunc
        self.exccount = 0
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

    def bind(self, port, bind = '', reuse = false, ipv6_socket_style = 1):
        port = int(port)
        addrinfos = []
        self.servers = {}
        # if bind != "" thread it as a comma seperated list and bind to all
        # addresses (can be ips or hostnames) else bind to default ipv6 and
        # ipv4 address
        if bind:
            if self.ipv6_enable:
                socktype = socket.AF_UNSPEC
            else:
                socktype = socket.AF_INET
            bind = bind.split(',')
            for addr in bind:
                if sys.version_info < (2,2):
                    addrinfos.append((socket.AF_INET, None, None, None, (addr, port)))
                else:
                    addrinfos.extend(socket.getaddrinfo(addr, port,
                                               socktype, socket.SOCK_STREAM))
        else:
            if self.ipv6_enable:
                addrinfos.append([socket.AF_INET6, None, None, None, ('', port)])
            if not addrinfos or ipv6_socket_style == 0:
                addrinfos.append([socket.AF_INET, None, None, None, ('', port)])
        for addrinfo in addrinfos:
            try:
                server = socket.socket(addrinfo[0], socket.SOCK_STREAM)
                if reuse:
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.setblocking(0)
                server.bind(addrinfo[4])
                self.servers[server.fileno()] = server
                server.listen(5)
                self.poll.register(server, POLLIN)
            except socket.error, e:
                for server in self.servers.values():
                    try:
                        server.close()
                    except:
                        pass
                if self.ipv6_enable and ipv6_socket_style == 0 and self.servers:
                    raise socket.error('blocked port (may require ipv6_binds_v4 to be set)')
                raise socket.error(str(e))
        if not self.servers:
            raise socket.error('unable to open server port')


    def start_connection(self, dns, handler = None, randomize = false):
        if handler is None:
            handler = self.handler
        if sys.version_info < (2,2):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(0)
            try:
                sock.connect_ex(dns)
            except socket.error:
                raise
            except Exception, e:
                raise socket.error(str(e))
        else:
            if self.ipv6_enable:
                socktype = socket.AF_UNSPEC
            else:
                socktype = socket.AF_INET
            try:
                addrinfos = socket.getaddrinfo(dns[0], int(dns[1]),
                                               socktype, socket.SOCK_STREAM)
            except socket.error, e:
                raise
            except Exception, e:
                raise socket.error(str(e))
            if randomize:
                shuffle(addrinfos)
            for addrinfo in addrinfos:
                try:
                    sock = socket.socket(addrinfo[0], socket.SOCK_STREAM)
                    sock.setblocking(0)
                    sock.connect_ex(addrinfo[4])
                    break
                except:
                    pass
            else:
                raise socket.error('unable to connect')
        self.poll.register(sock, POLLIN)
        s = SingleSocket(self, sock, handler, dns[0])
        self.single_sockets[sock.fileno()] = s
        return s

    def _sleep(self):
        sleep(1)
        
    def handle_events(self, events):
        for sock, event in events:
            s = self.servers.get(sock)
            if s:
                if event & (POLLHUP | POLLERR) != 0:
                    self.poll.unregister(s)
                    s.close()
                    del self.servers[sock]
                    print "lost server socket"
                else:
                    try:
                        newsock, addr = s.accept()
                        newsock.setblocking(0)
                        nss = SingleSocket(self, newsock, self.handler)
                        self.single_sockets[newsock.fileno()] = nss
                        self.poll.register(newsock, POLLIN)
                        self.handler.external_connection_made(nss)
                    except socket.error:
                        self._sleep()
            else:
                s = self.single_sockets.get(sock)
                if not s:
                    continue
                s.connected = true
                if (event & (POLLHUP | POLLERR)):
                    self._close_socket(s)
                    continue
                if (event & POLLIN):
                    try:
                        s.last_hit = time()
                        data = s.socket.recv(100000)
                        if not data:
                            self._close_socket(s)
                        else:
                            s.handler.data_came_in(s, data)
                    except socket.error, e:
                        code, msg = e
                        if code != EWOULDBLOCK:
                            self._close_socket(s)
                            continue
                if (event & POLLOUT) and s.socket and not s.is_flushed():
                    s.try_write()
                    if s.is_flushed():
                        s.handler.connection_flushed(s)

    def pop_external(self):
        while self.externally_added:
            (a, b) = self.externally_added.pop(0)
            self.add_task(a, b)

    def listen_forever(self, handler):
        self.handler = handler
        try:
            while not self.doneflag.isSet():
                try:
                    self.pop_external()
                    if self.funcs:
                        period = self.funcs[0][0] - time()
                    else:
                        period = 2 ** 30
                    if period < 0:
                        period = 0
                    events = self.poll.poll(period * timemult)
                    if self.doneflag.isSet():
                        return
                    while self.funcs and self.funcs[0][0] <= time():
                        garbage, func = self.funcs.pop(0)
                        try:
                            func()
                        except (SystemError, MemoryError), e:
                            self.failfunc(str(e))
                            return
                        except KeyboardInterrupt:
                            self.exception(true)
                            return
                        except:
                            if self.noisy:
                                self.exception()
                    self._close_dead()
                    self.handle_events(events)
                    if self.doneflag.isSet():
                        return
                    self._close_dead()
                except (SystemError, MemoryError), e:
                    self.failfunc(str(e))
                    return
                except error:
                    if self.doneflag.isSet():
                        return
                except KeyboardInterrupt:
                    self.exception(true)
                    return
                except:
                    self.exception()
                if self.exccount > 10:
                    return
        finally:
            for ss in self.single_sockets.values():
                try:
                    ss.close()
                except:
                    pass
            for server in self.servers.values():
                try:
                    server.close()
                except:
                    pass

    def exception(self, kbint = false):
        self.exccount += 1
        if self.errorfunc is None:
            print_exc()
        else:
            data = StringIO()
            print_exc(file = data)
            print data.getvalue()   # report exception here too
            if not kbint:           # don't report here if it's a keyboard interrupt
                self.errorfunc(data.getvalue())

    def _close_dead(self):
        if self.dead_from_write:
            old = self.dead_from_write
            self.dead_from_write = []
            for s in old:
                if s.socket:
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
