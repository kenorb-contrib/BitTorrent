# Written by Bram Cohen
# see LICENSE.txt for license information

import socket
from errno import EWOULDBLOCK, ECONNREFUSED, EHOSTUNREACH
try:
    from select import poll, error, POLLIN, POLLOUT, POLLERR, POLLHUP
    timemult = 1000
except ImportError:
    from selectpoll import poll, error, POLLIN, POLLOUT, POLLERR, POLLHUP
    timemult = 1
from time import time, sleep
import sys
from random import shuffle
try:
    True
except:
    True = 1
    False = 0

all = POLLIN | POLLOUT

class SingleSocket:
    def __init__(self, socket_handler, sock, handler, ip = None):
        self.socket_handler = socket_handler
        self.socket = sock
        self.handler = handler
        self.buffer = []
        self.last_hit = time()
        self.fileno = sock.fileno()
        self.connected = False
        try:
            self.ip = self.socket.getpeername()[0]
        except:
            if ip is None:
                self.ip = 'unknown'
            else:
                self.ip = ip
        
    def get_ip(self, real=False):
        if real:
            try:
                self.ip = self.socket.getpeername()[0]
            except:
                pass
        return self.ip
        
    def close(self):
        sock = self.socket
        self.socket = None
        self.buffer = []
        del self.socket_handler.single_sockets[self.fileno]
        self.socket_handler.poll.unregister(sock)
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
                    dead = e[0] != EWOULDBLOCK
                except:
                    dead = True
                if dead:
                    self.socket_handler.dead_from_write.append(self)
                    return
        if self.buffer:
            self.socket_handler.poll.register(self.socket, all)
        else:
            self.socket_handler.poll.register(self.socket, POLLIN)

    def set_handler(self, handler):
        self.handler = handler

class SocketHandler:
    def __init__(self, timeout, ipv6_enable, readsize = 100000):
        self.timeout = timeout
        self.ipv6_enable = ipv6_enable
        self.readsize = readsize
        self.poll = poll()
        # {socket: SingleSocket}
        self.single_sockets = {}
        self.dead_from_write = []
        self.max_connects = 1000

    def scan_for_timeouts(self):
        t = time() - self.timeout
        tokill = []
        for s in self.single_sockets.values():
            if s.last_hit < t:
                tokill.append(s)
        for k in tokill:
            if k.socket is not None:
                self._close_socket(k)

    def bind(self, port, bind = '', reuse = False, ipv6_socket_style = 1, upnp = 0):
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

    def find_and_bind(self, minport, maxport, bind = '', reuse = False,
                                          ipv6_socket_style = 1, upnp = 0):
        e = 'maxport less than minport - no ports to check'
        for listen_port in xrange(minport, maxport+1):
            try:
                self.bind(listen_port, bind,
                               ipv6_socket_style = ipv6_socket_style, upnp = upnp)
                return listen_port
            except socket.error, e:
                pass
        raise socket.error(str(e))
        return


    def set_handler(self, handler):
        self.handler = handler


    def start_connection_raw(self, dns, socktype = socket.AF_INET, handler = None):
        if handler is None:
            handler = self.handler
        sock = socket.socket(socktype, socket.SOCK_STREAM)
        sock.setblocking(0)
        try:
            sock.connect_ex(dns)
        except socket.error:
            raise
        except Exception, e:
            raise socket.error(str(e))
        self.poll.register(sock, POLLIN)
        s = SingleSocket(self, sock, handler, dns[0])
        self.single_sockets[sock.fileno()] = s
        return s


    def start_connection(self, dns, handler = None, randomize = False):
        if handler is None:
            handler = self.handler
        if sys.version_info < (2,2):
            s = self.start_connection_raw(dns,socket.AF_INET,handler)
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
                    s = self.start_connection_raw(addrinfo[4],addrinfo[0],handler)
                    break
                except:
                    pass
            else:
                raise socket.error('unable to connect')
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
                elif len(self.single_sockets) < self.max_connects:
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
                s.connected = True
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

    def close_dead(self):
        while self.dead_from_write:
            old = self.dead_from_write
            self.dead_from_write = []
            for s in old:
                if s.socket:
                    self._close_socket(s)

    def _close_socket(self, s):
        s.close()
        s.handler.connection_lost(s)

    def do_poll(self, t):
        r = self.poll.poll(t*timemult)
        if r is None:
            connects = len(self.single_sockets)
            to_close = int(connects*0.05)+1 # close 5% of sockets
            self.max_connects = connects-to_close
            closelist = self.single_sockets.keys()
            shuffle(closelist)
            closelist = closelist[:to_close]
            for sock in closelist:
                self._close_socket(sock)
            return []
        return r
            

    def shutdown(self):
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