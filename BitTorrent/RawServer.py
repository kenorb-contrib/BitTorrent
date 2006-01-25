# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bram Cohen, Uoti Urpala

import os
import sys
import socket
import signal
import struct
import thread
from bisect import insort
from cStringIO import StringIO
from traceback import print_exc
from errno import EWOULDBLOCK, ENOBUFS, EINTR

from BitTorrent.platform import bttime
from BitTorrent import WARNING, CRITICAL, FAQ_URL
from BitTorrent.defer import Deferred

try:
    from select import poll, error, POLLIN, POLLOUT, POLLERR, POLLHUP
    timemult = 1000
except ImportError:
    from BitTorrent.selectpoll import poll, error, POLLIN, POLLOUT, POLLERR, POLLHUP
    timemult = 1

NOLINGER = struct.pack('ii', 1, 0)


class Handler(object):

    # there is only a semantic difference between "made" and "started".
    # I prefer "started"
    def connection_started(self, s):
        self.connection_made(s)
    def connection_made(self, s):
        pass

    def connection_lost(self, s):
        pass

    # Maybe connection_lost should just have a default 'None' exception parameter
    def connection_failed(self, addr, exception):
        pass
    
    def connection_flushed(self, s):
        pass
    def data_came_in(self, addr, datagram):
        pass

    
class SingleSocket(object):

    def __init__(self, rawserver, sock, handler, context, addr=None):
        self.rawserver = rawserver
        self.socket = sock
        self.handler = handler
        self.buffer = []
        self.last_hit = bttime()
        self.fileno = sock.fileno()
        self.connected = False
        self.context = context
        self.ip = None
        self.port = None


        if isinstance(addr, basestring):
            # UNIX socket, not really ip
            self.ip = addr
        else:
            peername = (None, None)
            try:
                peername = self.socket.getpeername()
            except socket.error, e:
                # UDP raises (107, 'Transport endpoint is not connected')
                # but so can a TCP socket we just got from start_connection,
                # in which case addr is set and we use it later.
                if (e[0] == 107) and (addr == None):
                    # lies.
                    # the peer endpoint should be gathered from the
                    # tuple passed to data_came_in
                    try:
                        peername = self.socket.getsockname()
                    except socket.error, e:
                        pass

            # this is awesome!
            # max prefers a value over None, so this is a common case:
            # max(('ip', None), ('ip', 1234)) => ('ip', 1234)
            # or the default case:
            # max(('ip', None), None) => ('ip', None)
            self.ip, self.port = max(peername, addr)
            
                    
    def close(self):
        sock = self.socket
        self.socket = None
        self.buffer = []
        del self.rawserver.single_sockets[self.fileno]
        self.rawserver.poll.unregister(sock)
        self.handler = None
        if self.rawserver.config['close_with_rst']:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, NOLINGER)
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
                    self.rawserver.dead_from_write.append(self)
                    return
        if self.buffer == []:
            self.rawserver.poll.register(self.socket, POLLIN)
        else:
            self.rawserver.poll.register(self.socket, POLLIN | POLLOUT)


def default_error_handler(level, message):
    print message

class RawServer(object):

    def __init__(self, doneflag, config, noisy=True,
                 errorfunc=default_error_handler, tos=0):
        self.config = config
        self.tos = tos
        self.poll = poll()
        # {socket: SingleSocket}
        self.single_sockets = {}
        self.udp_sockets = {}
        self.dead_from_write = []
        self.doneflag = doneflag
        self.noisy = noisy
        self.errorfunc = errorfunc
        self.funcs = []
        self.externally_added_tasks = []
        self.listening_handlers = {}
        self.serversockets = {}
        self.live_contexts = {None : True}
        self.ident = thread.get_ident()
        self.to_start = []
        self.add_task(self.scan_for_timeouts, config['timeout_check_interval'])
        if sys.platform.startswith('win'):
            # Windows doesn't support pipes with select(). Just prevent sleeps
            # longer than a second instead of proper wakeup for now.
            self.wakeupfds = (None, None)
            self._wakeup()
        else:
            self.wakeupfds = os.pipe()
            self.poll.register(self.wakeupfds[0], POLLIN)

    def _wakeup(self):
        self.add_task(self._wakeup, 1)

    def add_context(self, context):
        self.live_contexts[context] = True

    def remove_context(self, context):
        del self.live_contexts[context]
        self.funcs = [x for x in self.funcs if x[3] != context]

    def add_task(self, func, delay, args=(), context=None):
        assert thread.get_ident() == self.ident
        assert type(args) == list or type(args) == tuple
        if context in self.live_contexts:
            insort(self.funcs, (bttime() + delay, func, args, context))

    def external_add_task(self, func, delay, args=(), context=None):
        assert type(args) == list or type(args) == tuple
        self.externally_added_tasks.append((func, delay, args, context))
        # Wake up the RawServer thread in case it's sleeping in poll()
        if self.wakeupfds[1] is not None:
            os.write(self.wakeupfds[1], 'X')

    def scan_for_timeouts(self):
        self.add_task(self.scan_for_timeouts,
                      self.config['timeout_check_interval'])
        t = bttime() - self.config['socket_timeout']
        tokill = []
        for s in [s for s in self.single_sockets.values() if s not in self.udp_sockets.keys()]:
            if s.last_hit < t:
                tokill.append(s)
        for k in tokill:
            if k.socket is not None:
                self._close_socket(k)

    def create_unixserversocket(filename):
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.setblocking(0)
        server.bind(filename)
        server.listen(5)
        return server
    create_unixserversocket = staticmethod(create_unixserversocket)

    def create_serversocket(port, bind='', reuse=False, tos=0):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if reuse and os.name != 'nt':
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.setblocking(0)
        if tos != 0:
            try:
                server.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, tos)
            except:
                pass
        server.bind((bind, port))
        server.listen(5)
        return server
    create_serversocket = staticmethod(create_serversocket)

    def create_udpsocket(port, bind='', reuse=False, tos=0):
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if reuse and os.name != 'nt':
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.setblocking(0)
        if tos != 0:
            try:
                server.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, tos)
            except:
                pass
        server.bind((bind, port))
        return server
    create_udpsocket = staticmethod(create_udpsocket)

    def start_listening(self, serversocket, handler, context=None):
        self.listening_handlers[serversocket.fileno()] = (handler, context)
        self.serversockets[serversocket.fileno()] = serversocket
        self.poll.register(serversocket, POLLIN)

    def start_listening_udp(self, serversocket, handler, context=None):
        self.listening_handlers[serversocket.fileno()] = (handler, context)
        nss = SingleSocket(self, serversocket, handler, context)
        self.single_sockets[serversocket.fileno()] = nss
        self.udp_sockets[nss] = 1
        self.poll.register(serversocket, POLLIN)

    def stop_listening(self, serversocket):
        del self.listening_handlers[serversocket.fileno()]
        del self.serversockets[serversocket.fileno()]
        self.poll.unregister(serversocket)

    def stop_listening_udp(self, serversocket):
        del self.listening_handlers[serversocket.fileno()]
        del self.single_sockets[serversocket.fileno()]
        l = [s for s in self.udp_sockets.keys() if s.socket == serversocket]
        del self.udp_sockets[l[0]]
        self.poll.unregister(serversocket)

    def start_connection(self, dns, handler=None, context=None, do_bind=True):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(0)
        bindaddr = do_bind and self.config['bind']
        if bindaddr:
            sock.bind((bindaddr, 0))
        if self.tos != 0:
            try:
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, self.tos)
            except:
                pass
        try:
            sock.connect_ex(dns)
        except socket.error:
            sock.close()
            raise
        except Exception, e:
            sock.close()
            raise socket.error(str(e))
        self.poll.register(sock, POLLIN)
        s = SingleSocket(self, sock, handler, context, dns)
        self.single_sockets[sock.fileno()] = s
        return s

    def _add_pending_connection(self, addr):
        pass

    def _remove_pending_connection(self, addr):
        pass

    def async_start_connection(self, dns, handler=None, context=None, do_bind=True):
        self.to_start.insert(0, (dns, handler, context, do_bind))
        self._start_connection()
        return True
    
    def _start_connection(self):
        dns, handler, context, do_bind = self.to_start.pop()
        try:
            s = self.start_connection(dns, handler, context, do_bind)
        except Exception, e:
            handler.connection_failed(dns, e)
        else:
            handler.connection_started(s)
        
    def wrap_socket(self, sock, handler, context=None, ip=None, port=None):
        sock.setblocking(0)
        self.poll.register(sock, POLLIN)
        s = SingleSocket(self, sock, handler, context, (ip, port))
        self.single_sockets[sock.fileno()] = s
        return s

    # must be called from the main thread
    def install_sigint_handler(self):
        signal.signal(signal.SIGINT, self._handler)

    def _handler(self, signum, frame):
        self.external_add_task(self.doneflag.set, 0)
        # Allow pressing ctrl-c multiple times to raise KeyboardInterrupt,
        # in case the program is in an infinite loop
        signal.signal(signal.SIGINT, signal.default_int_handler)

    def _handle_events(self, events):
        for sock, event in events:
            if sock in self.serversockets:
                s = self.serversockets[sock]
                if event & (POLLHUP | POLLERR) != 0:
                    try:
                        self.poll.unregister(s)
                        s.close()
                    except socket.error, e:
                        self.errorfunc(WARNING, _("failed to unregister or close server socket: %s") % str(e))
                    self.errorfunc(CRITICAL, _("lost server socket"))
                else:
                    handler, context = self.listening_handlers[sock]
                    try:
                        newsock, addr = s.accept()
                    except socket.error, e:
                        continue
                    try:
                        newsock.setblocking(0)
                        nss = SingleSocket(self, newsock, handler, context, addr)
                        self.single_sockets[newsock.fileno()] = nss
                        self.poll.register(newsock, POLLIN)
                        self._make_wrapped_call(handler. \
                           connection_made, (nss,), context=context)
                    except socket.error, e:
                        self.errorfunc(WARNING,
                                       _("Error handling accepted connection: ") +
                                       str(e))
            else:
                s = self.single_sockets.get(sock)
                if s is None:
                    if sock == self.wakeupfds[0]:
                        # Another thread wrote this just to wake us up.
                        os.read(sock, 1)
                    continue
                s.connected = True
                if event & POLLERR:
                    self._close_socket(s)
                    continue
                if event & (POLLIN | POLLHUP):
                    s.last_hit = bttime()
                    try:
                        data, addr = s.socket.recvfrom(100000)
                    except socket.error, e:
                        code, msg = e
                        if code != EWOULDBLOCK:
                            self._close_socket(s)
                        continue
                    if data == '' and not self.udp_sockets.has_key(s):
                        self._close_socket(s)
                    else:
                        if not self.udp_sockets.has_key(s):
                            self._make_wrapped_call(s.handler.data_came_in,
                                                    (s, data), s)
                        else:
                            self._make_wrapped_call(s.handler.data_came_in,
                                                    (addr, data), s)
                            
                # data_came_in could have closed the socket (s.socket = None)
                if event & POLLOUT and s.socket is not None:
                    s.try_write()
                    if s.is_flushed():
                        self._make_wrapped_call(s.handler.connection_flushed,
                                                (s,), s)

    def _pop_externally_added(self):
        while self.externally_added_tasks:
            task = self.externally_added_tasks.pop(0)
            self.add_task(*task)

    def listen_forever(self):
        ret = 0
        self.ident = thread.get_ident()
        while not self.doneflag.isSet() and not ret:
            ret = self.listen_once()
            
    def listen_once(self, period=1e9):
        try:
            self._pop_externally_added()
            if self.funcs:
                period = self.funcs[0][0] - bttime()
            if period < 0:
                period = 0
            events = self.poll.poll(period * timemult)
            if self.doneflag.isSet():
                return 0
            while self.funcs and self.funcs[0][0] <= bttime():
                garbage, func, args, context = self.funcs.pop(0)
                self._make_wrapped_call(func, args, context=context)
            self._close_dead()
            self._handle_events(events)
            if self.doneflag.isSet():
                return 0
            self._close_dead()
        except error, e:
            if self.doneflag.isSet():
                return 0
            # I can't find a coherent explanation for what the behavior
            # should be here, and people report conflicting behavior,
            # so I'll just try all the possibilities
            code = None
            if hasattr(e, '__getitem__'):
                code = e[0]
            else:
                code = e
            if code == ENOBUFS:
                # log the traceback so we can see where the exception is coming from
                print_exc(file = sys.stderr)
                self.errorfunc(CRITICAL,
                               _("Have to exit due to the TCP stack flaking "
                                 "out. Please see the FAQ at %s") % FAQ_URL)
                return -1
            elif code in (EINTR,):
                # add other ignorable error codes here
                pass
            else:
                self.errorfunc(CRITICAL, str(e))
            return 0
        except KeyboardInterrupt:
            print_exc()
            return -1
        except:
            data = StringIO()
            print_exc(file=data)
            self.errorfunc(CRITICAL, data.getvalue())
            return 0

    def _make_wrapped_call(self, function, args, socket=None, context=None):
        try:
            function(*args)
        except KeyboardInterrupt:
            raise
        except Exception, e:         # hopefully nothing raises strings
            # Incoming sockets can be assigned to a particular torrent during
            # a data_came_in call, and it's possible (though not likely) that
            # there could be a torrent-specific exception during the same call.
            # Therefore read the context after the call.
            if socket is not None:
                context = socket.context
            if self.noisy and context is None:
                data = StringIO()
                print_exc(file=data)
                self.errorfunc(CRITICAL, data.getvalue())
            if context is not None:
                context.got_exception(e)

    def _close_dead(self):
        while len(self.dead_from_write) > 0:
            old = self.dead_from_write
            self.dead_from_write = []
            for s in old:
                if s.socket is not None:
                    self._close_socket(s)

    def _close_socket(self, s):
        sock = s.socket.fileno()
        if self.config['close_with_rst']:
            s.socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, NOLINGER)
        s.socket.close()
        self.poll.unregister(sock)
        del self.single_sockets[sock]
        s.socket = None
        self._make_wrapped_call(s.handler.connection_lost, (s,), s)
        s.handler = None
