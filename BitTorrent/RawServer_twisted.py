# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Greg Hazel

import os
import sys
import socket
import signal
import struct
import thread
from cStringIO import StringIO
from traceback import print_exc, print_stack

from BitTorrent import BTFailure, WARNING, CRITICAL, FAQ_URL
    
noSignals = True

if os.name == 'nt':
    try:
        from twisted.internet import iocpreactor
        iocpreactor.proactor.install()
        noSignals = False
    except:
        # just as limited (if not more) as select, and also (supposedly) buggy
        #try:
        #    from twisted.internet import win32eventreactor
        #    win32eventreactor.install()
        #except:
        #    pass
        pass
else:
    try:
        from twisted.internet import kqreactor
        kqreactor.install()
    except:
        try:
            from twisted.internet import pollreactor
            pollreactor.install()
        except:
            pass

#the default reactor is select-based, and will be install()ed if another has not    
from twisted.internet import reactor, task, error

import twisted.copyright
if int(twisted.copyright.version.split('.')[0]) < 2:
    raise ImportError("RawServer_twisted requires twisted 2.0.0 or greater")

from twisted.internet.protocol import DatagramProtocol, Protocol, Factory, ClientFactory
from twisted.protocols.policies import TimeoutMixin

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

class ConnectionWrapper(object):
    def __init__(self, rawserver, handler, context, tos=0):
        self.dying = 0
        self.ip = None
        self.port = None
        self.transport = None
        self.reset_timeout = None

        self.post_init(rawserver, handler, context)

        self.tos = tos

        self.buffer = OutputBuffer(self)        

    def post_init(self, rawserver, handler, context):
        self.rawserver = rawserver
        self.handler = handler
        self.context = context
        if self.rawserver:
            self.rawserver.single_sockets[self] = self

    def get_socket(self):
        s = None
        try:
            s = self.transport.getHandle()
        except:
            try:
                # iocpreactor doesn't implement ISystemHandle like it should
                s = self.transport.socket
            except:
                pass
        return s            

    def attach_transport(self, transport, reset_timeout):
        self.transport = transport
        self.reset_timeout = reset_timeout

        try:        
            address = self.transport.getPeer()
        except:
            try:
                # udp, for example
                address = self.transport.getHost()
            except:
                if not self.transport.__dict__.has_key("state"):
                    self.transport.state = "NO STATE!"
                sys.stderr.write("UNKNOWN HOST/PEER: " + str(self.transport) + ":" + str(self.transport.state)+ ":" + str(self.handler) + "\n")
                print_stack()
                # fallback incase the unknown happens,
                # there's no use raising an exception
                address = ("unknown", -1)
                pass

        try:            
            self.ip = address.host
            self.port = address.port
        except:
            #unix sockets, for example
            pass

        if self.tos != 0:
            s = self.get_socket()
            
            try:
                s.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, self.tos)
            except:
                pass

    def sendto(self, packet, flags, addr):
        return self.transport.write(packet, addr)

    def write(self, b):
        self.buffer.add(b)

    def _flushed(self):
        s = self        
        #why do you tease me so?
        if s.handler is not None:
            #calling flushed from the write is bad form
            self.rawserver.add_task(s.handler.connection_flushed, 0, (s,))

    def is_flushed(self):
        return self.buffer.is_flushed()

    def shutdown(self, how):
        if how == socket.SHUT_WR:
            self.transport.loseWriteConnection()
            self.buffer.stopWriting()
        elif how == socket.SHUT_RD:
            self.transport.stopListening()
        else:
            self.close()
            
    def close(self):
        self.buffer.stopWriting()
        
        # opt for no "connection_lost" callback since we know that
        self.dying = 1

        if self.rawserver.config['close_with_rst']:
            try:
                s = self.get_socket()
                s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, NOLINGER)
            except:
                pass

        if self.rawserver.udp_sockets.has_key(self):
            # udp connections should only call stopListening
            self.transport.stopListening()
        else:
            self.transport.loseConnection()


class OutputBuffer(object):

    def __init__(self, connection):
        self.connection = connection
        self.consumer = None
        self.buffer = StringIO()

    def is_flushed(self):
        return (self.buffer.tell() == 0)

    def add(self, b):
        # sometimes we get strings, sometimes we get buffers. ugg.
        if (isinstance(b, buffer)):
            b = str(b)
        self.buffer.write(b)

        if self.consumer is None:
            self.beginWriting()
        
    def beginWriting(self):
        self.stopWriting()
        self.consumer = self.connection.transport
        self.consumer.registerProducer(self, False)

    def stopWriting(self):
        if self.consumer is not None:
            self.consumer.unregisterProducer()
        self.consumer = None

    def resumeProducing(self):
        if self.consumer is not None:
            if self.buffer.tell() > 0:
                self.consumer.write(self.buffer.getvalue())
                self.buffer.seek(0)
                self.buffer.truncate(0)
                self.connection._flushed()
            else:
                self.stopWriting()


    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass
            
class CallbackConnection(object):

    def attachTransport(self, transport, connection, *args):
        s = connection
        if s is None:
            s = ConnectionWrapper(*args)

        s.attach_transport(transport, self.optionalResetTimeout)
        self.connection = s

    def connectionMade(self):
        s = self.connection
        s.handler.connection_started(s)
        self.optionalResetTimeout()

    def connectionLost(self, reason):
        reactor.callLater(0, self.post_connectionLost, reason)
        
    #twisted api inconsistancy workaround
    #sometimes connectionLost is called (not fired) from inside write()
    def post_connectionLost(self, reason):
        #hack to try and dig up the connection if one was ever made
        if not self.__dict__.has_key("connection"):
            self.connection = self.factory.connection
        if self.connection is not None:
            self.factory.rawserver._remove_socket(self.connection)

    def dataReceived(self, data):
        self.optionalResetTimeout()

        s = self.connection
        s.rawserver._make_wrapped_call(s.handler.data_came_in,
                                       (s, data), s)

    def datagramReceived(self, data, (host, port)):
        s = self.connection
        s.rawserver._make_wrapped_call(s.handler.data_came_in,
                                       ((host, port), data), s)
        
    def connectionRefused(self):
        s = self.connection
        dns = (s.ip, s.port)
        reason = "connection refused"
        
        if not s.dying:
            # this might not work - reason is not an exception
            s.handler.connection_failed(dns, reason)

            #so we don't get failed then closed
            s.dying = 1
        
        s.rawserver._remove_socket(s)

    def optionalResetTimeout(self):
        if self.can_timeout:
            self.resetTimeout()

class CallbackProtocol(CallbackConnection, TimeoutMixin, Protocol):

    def makeConnection(self, transport):
        self.can_timeout = 1
        self.setTimeout(self.factory.rawserver.config['socket_timeout'])
        self.attachTransport(transport, self.factory.connection, *self.factory.connection_args)
        Protocol.makeConnection(self, transport)

class CallbackDatagramProtocol(CallbackConnection, DatagramProtocol):

    def startProtocol(self):
        self.can_timeout = 0
        self.attachTransport(self.transport, self.connection, ())
        DatagramProtocol.startProtocol(self)

    def connectionRefused(self):
        # we don't use these at all for udp, so skip the CallbackConnection
        DatagramProtocol.connectionRefused(self)
        
class OutgoingConnectionFactory(ClientFactory):
        
    def clientConnectionFailed(self, connector, reason):
        peer = connector.getDestination()
        dns = (peer.host, peer.port)
        # opt-out        
        if not self.connection.dying:
            # this might not work - reason is not an exception
            self.connection.handler.connection_failed(dns, reason)

            #so we don't get failed then closed
            self.connection.dying = 1
            
        self.rawserver._remove_socket(self.connection)

def UnimplementedWarning(msg):
    #ok, I think people get the message
    #print "UnimplementedWarning: " + str(msg)
    pass

#Encoder calls stop_listening(socket) then socket.close()
#to us they mean the same thing, so swallow the second call
class CloseSwallower:
    def close(self):
        pass

#storage for socket creation requestions, and proxy once the connection is made
class SocketProxy(object):
    def __init__(self, port, bind, reuse, tos, protocol):
        self.port = port
        self.bind = bind
        self.reuse = reuse
        self.tos = tos
        self.protocol = protocol
        self.connection = None

    def __getattr__(self, name):
        try:
            return getattr(self.connection, name)
        except:
            raise AttributeError, name

def default_error_handler(level, message):
    print message

class RawServerMixin(object):

    def __init__(self, doneflag, config, noisy=True,
                 errorfunc=default_error_handler, tos=0):
        self.doneflag = doneflag
        self.noisy = noisy
        self.errorfunc = errorfunc
        self.config = config
        self.tos = tos
        self.ident = thread.get_ident()

    def _make_wrapped_call(self, function, args, wrapper=None, context=None):
        try:
            function(*args)
        except KeyboardInterrupt:
            raise
        except Exception, e:         # hopefully nothing raises strings
            # Incoming sockets can be assigned to a particular torrent during
            # a data_came_in call, and it's possible (though not likely) that
            # there could be a torrent-specific exception during the same call.
            # Therefore read the context after the call.
            if wrapper is not None:
                context = wrapper.context
            if self.noisy and context is None:
                data = StringIO()
                print_exc(file=data)
                data.seek(-1)
                self.errorfunc(CRITICAL, data.read())
            if context is not None:
                context.got_exception(e)

    # must be called from the main thread
    def install_sigint_handler(self):
        signal.signal(signal.SIGINT, self._handler)

    def _handler(self, signum, frame):
        self.external_add_task(self.doneflag.set, 0)
        # Allow pressing ctrl-c multiple times to raise KeyboardInterrupt,
        # in case the program is in an infinite loop
        signal.signal(signal.SIGINT, signal.default_int_handler)

class RawServer(RawServerMixin):

    def __init__(self, doneflag, config, noisy=True,
                 errorfunc=default_error_handler, tos=0):
        RawServerMixin.__init__(self, doneflag, config, noisy, errorfunc, tos)

        self.listening_handlers = {}
        self.single_sockets = {}
        self.udp_sockets = {}
        self.live_contexts = {None : 1}
        self.listened = 0
        
    def add_context(self, context):
        self.live_contexts[context] = 1

    def remove_context(self, context):
        del self.live_contexts[context]

    def autoprune(self, f, *a, **kw):
        if self.live_contexts.has_key(kw['context']):
            f(*a, **kw)

    def add_task(self, func, delay, args=(), context=None):
        assert thread.get_ident() == self.ident
        assert type(args) == list or type(args) == tuple

        #we're going to check again later anyway
        #if self.live_contexts.has_key(context):
        reactor.callLater(delay, self.autoprune, self._make_wrapped_call,
                          func, args, context=context)
        
    def external_add_task(self, func, delay, args=(), context=None):
        assert type(args) == list or type(args) == tuple
        reactor.callFromThread(self.add_task, func, delay, args, context)

    def create_unixserversocket(filename):
        s = SocketProxy(0, filename, True, 0, 'tcp')
        s.factory = Factory()
        
        if s.reuse == False:
            UnimplementedWarning("You asked for reuse to be off when binding. Sorry, I can't do that.")

        listening_port = reactor.listenUNIX(s.bind, s.factory)
        listening_port.listening = 1
        s.listening_port = listening_port
        
        return s
    create_unixserversocket = staticmethod(create_unixserversocket)

    def create_serversocket(port, bind='', reuse=False, tos=0):
        s = SocketProxy(port, bind, reuse, tos, 'tcp')
        s.factory = Factory()
        
        if s.reuse == False:
            UnimplementedWarning("You asked for reuse to be off when binding. Sorry, I can't do that.")

        try:        
            listening_port = reactor.listenTCP(s.port, s.factory, interface=s.bind)
        except error.CannotListenError, e:
            if e[0] != 0:
                raise e.socketError
            else:
                raise
        listening_port.listening = 1
        s.listening_port = listening_port
        
        return s
    create_serversocket = staticmethod(create_serversocket)

    def create_udpsocket(port, bind='', reuse=False, tos=0):
        s = SocketProxy(port, bind, reuse, tos, 'udp')
        s.protocol = CallbackDatagramProtocol()
        c = ConnectionWrapper(None, None, None, tos)
        s.connection = c
        s.protocol.connection = c

        if s.reuse == False:
            UnimplementedWarning("You asked for reuse to be off when binding. Sorry, I can't do that.")
                         
        try:        
            listening_port = reactor.listenUDP(s.port, s.protocol, interface=s.bind)
        except error.CannotListenError, e:
            raise e.socketError       
        listening_port.listening = 1
        s.listening_port = listening_port
        
        return s
    create_udpsocket = staticmethod(create_udpsocket)

    def start_listening(self, serversocket, handler, context=None):
        s = serversocket
        s.factory.rawserver = self
        s.factory.protocol = CallbackProtocol
        s.factory.connection = None
        s.factory.connection_args = (self, handler, context, serversocket.tos)

        if not s.listening_port.listening:
            s.listening_port.startListening()
            s.listening_port.listening = 1

        self.listening_handlers[s] = s.listening_port

        #provides a harmless close() method
        s.connection = CloseSwallower()        

    def start_listening_udp(self, serversocket, handler, context=None):
        s = serversocket
        
        c = s.connection
        c.post_init(self, handler, context)

        if not s.listening_port.listening:
            s.listening_port.startListening()
            s.listening_port.listening = 1

        self.listening_handlers[serversocket] = s.listening_port
            
        self.udp_sockets[c] = c

    def stop_listening(self, serversocket):
        listening_port = self.listening_handlers[serversocket]
        try:
            listening_port.stopListening()
            listening_port.listening = 0
        except error.NotListeningError:
            pass
        del self.listening_handlers[serversocket]

    def stop_listening_udp(self, serversocket):
        listening_port = self.listening_handlers[serversocket]
        listening_port.stopListening()
        del self.listening_handlers[serversocket]
        del self.udp_sockets[serversocket.connection]
        del self.single_sockets[serversocket.connection]
        
    def start_connection(self, dns, handler, context=None, do_bind=True):
        addr = dns[0]
        port = int(dns[1])

        bindaddr = None
        if do_bind:
            bindaddr = self.config['bind']
            if bindaddr and len(bindaddr) >= 0:
                bindaddr = (bindaddr, 0)
            else:
                bindaddr = None

        factory = OutgoingConnectionFactory()
        factory.protocol = CallbackProtocol
        factory.rawserver = self

        c = ConnectionWrapper(self, handler, context, self.tos)
        
        factory.connection = c
        factory.connection_args = ()

        connector = reactor.connectTCP(addr, port, factory, bindAddress=bindaddr)

        self.single_sockets[c] = c
        return c

    def async_start_connection(self, dns, handler, context=None, do_bind=True):
        self.start_connection(dns, handler, context, do_bind)

    def wrap_socket(self, sock, handler, context=None, ip=None):
        raise Unimplemented("wrap_socket")

    def listen_forever(self):
        self.ident = thread.get_ident()
        if self.listened:
            UnimplementedWarning("listen_forever() should only be called once per reactor.")
        self.listened = 1
        
        l = task.LoopingCall(self.stop)
        l.start(1, now = False)
        
        if noSignals:
            reactor.run(installSignalHandlers=False)
        else:
            reactor.run()
            
    def listen_once(self, period=1e9):
        UnimplementedWarning("listen_once() Might not return until there is activity, and might not process the event you want. Use listen_forever().")
        reactor.iterate(period)
    
    def stop(self):
        if (self.doneflag.isSet()):

            for connection in self.single_sockets.values():
                try:
                    #I think this still sends all the data
                    connection.close()
                except:
                    pass
                
            reactor.suggestThreadPoolSize(0)
            reactor.stop()

    def _remove_socket(self, s):
        # opt-out        
        if not s.dying:
            self._make_wrapped_call(s.handler.connection_lost, (s,), s)
            s.handler = None

        del self.single_sockets[s]
        
