# usage:
#
# from twisted.internet import reactor
# from ConnectionRateLimitReactor import connectionRateLimitReactor
# connectionRateLimitReactor(reactor, max_incomplete=10)
#
# by Greg Hazel

import threading
from twisted.python import threadable
from twisted.internet import interfaces

try:
    from zope.interface import implements
    zope = True
except ImportError:
    zope = False

class HookedFactory(object):
    def __init__(self, reactor, factory, host):
        self.reactor = reactor
        self.factory = factory
        self.host = host

    def clientConnectionFailed(self, *a, **kw):
        self.reactor._remove_pending_connection(self.host)
        return self.factory.clientConnectionFailed(*a, **kw)

    def buildProtocol(self, *a, **kw):
        p = self.factory.buildProtocol(*a, **kw)
        old_connectionMade = p.connectionMade
        def connectionMade(*a2, **kw2):
            self.reactor._remove_pending_connection(self.host)
            return old_connectionMade(*a2, **kw2)
        p.connectionMade = connectionMade
        return p

    def __getattr__(self, attr):
        return getattr(self.factory, attr)
    

class IRobotConnector(object):
    if zope:
        try:
            implements(interfaces.IConnector)
        except:
            # stupid zope verisons!
            pass

    def __init__(self, reactor, host, port, factory, timeout, bindAddress):
        self.reactor = reactor
        self.host = host
        self.port = port
        self.factory = factory
        self.timeout = timeout
        self.connector = None
        self.bindAddress = bindAddress
        self.do_not_connect = False

        self.factory = HookedFactory(self.reactor, self.factory, self.host)

    def disconnect(self):
        if self.connector:
            self.connector.disconnect()
        else:
            self.do_not_connect = True
    stopConnecting = disconnect

    def connect(self):
        #print 'connecting', self.host, self.port
        self.reactor.add_pending_connection(self.host)
        self.connector = self.reactor.old_connectTCP(self.host, self.port,
                                                     self.factory, self.timeout,
                                                     self.bindAddress)
        # hm, this might briefly connect, but at least it fires the callback
        if self.do_not_connect:
            self.connector.disconnect()
        return self.connector

    def getDestination(self):
        return address.IPv4Address('TCP', self.host, self.port, 'INET')


class ConnectionRateLimiter(object):
    def __init__(self, reactor, max_incomplete):
        self.reactor = reactor
        self.pending_starters = []
        self.max_incomplete = max_incomplete
        # this can go away when urllib does
        self.pending_sockets_lock = threading.RLock()
        self.pending_sockets = {}
        self.old_connectTCP = self.reactor.connectTCP

    # safe from any thread    
    def add_pending_connection(self, host):
        #print 'adding', host, 'iot', threadable.isInIOThread()
        self.pending_sockets_lock.acquire()
        self.pending_sockets.setdefault(host, 0)
        self.pending_sockets[host] += 1
        self.pending_sockets_lock.release()

    # thread footwork, because _remove actually starts new connections
    def remove_pending_connection(self, host):
        if not threadable.isInIOThread():
            self.reactor.callFromThread(self._remove_pending_connection, host)
        else:
            self._remove_pending_connection(host)

    def _remove_pending_connection(self, host):
        #print 'removing', host
        self.pending_sockets_lock.acquire()
        self.pending_sockets[host] -= 1
        if self.pending_sockets[host] <= 0:
            del self.pending_sockets[host]
            self._push_new_connections()
        self.pending_sockets_lock.release()

    def _push_new_connections(self):
        if not self.pending_starters:
            return
        c = self.pending_starters.pop(0)
        c.connect()

    def connectTCP(self, host, port, factory, timeout=30, bindAddress=None):
        c = IRobotConnector(self, host, port, factory, timeout, bindAddress)
        
        # the XP connection rate limiting is unique at the IP level
        if (len(self.pending_sockets) >= self.max_incomplete and
            host not in self.pending_sockets):
            #print 'postponing', host, port
            self.pending_starters.append(c)
        else:
            c.connect()
            
        return c


def connectionRateLimitReactor(reactor, max_incomplete):
    limiter = ConnectionRateLimiter(reactor, max_incomplete)
    assert not hasattr(reactor, 'crl_installed'), \
           "reactor already has conncetion rate limiter installed"
    reactor.connectTCP = limiter.connectTCP
    reactor.add_pending_connection = limiter.add_pending_connection
    reactor.remove_pending_connection = limiter.remove_pending_connection
    reactor.crl_installed = True
