# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bram Cohen and Greg Hazel

from socket import error as socketerror

# for crypto
from sha import sha

from BitTorrent.translation import _

from BitTorrent import BTFailure
from BitTorrent.obsoletepythonsupport import *
from BitTorrent.RawServer_twisted import Handler
from BitTorrent.NatTraversal import UPNPError
from BitTorrent.Connector import Connection
from BitTorrent.platform import is_frozen_exe
from BitTorrent.ClientIdentifier import identify_client
from BitTorrent.LocalDiscovery import LocalDiscovery
from twisted.internet import task

# header, reserved, download id, my id, [length, message]

class InitialConnectionHandler(Handler):
    
    def __init__(self, parent, id, encrypt=False):
        self.parent = parent
        self.id = id
        self.accept = True
        self.encrypt = encrypt
        
    def connection_made(self, s):
        del self.parent.pending_connections[(s.ip, s.port)]

        # prevents conenctions we no longer care about from being accepted
        if not self.accept:
            return

        con = Connection(self.parent, s, self.id, True, self.encrypt)
        self.parent._add_connection(con)

        # it might not be obvious why this is here.
        # if the pending queue filled and put the remaining connections
        # into the spare list, this will push more connections in to pending
        self.parent.replace_connection()
        
    def connection_failed(self, addr, exception):
        
        del self.parent.pending_connections[addr]

        if not self.accept:
            # we don't need to rotate the spares with replace_connection()
            # if the ConnectionManager object has stopped all connections
            return

        self.parent.replace_connection()


class ConnectionManager(object):

    def __init__(self, make_upload, downloader, choker, numpieces, ratelimiter,
                 rawserver, config, my_id, schedulefunc, download_id, context,
                 addcontactfunc, reported_port):
        self.make_upload = make_upload
        self.downloader = downloader
        self.choker = choker
        self.numpieces = numpieces
        self.ratelimiter = ratelimiter
        self.rawserver = rawserver
        self.my_id = my_id
        self.config = config
        self.schedulefunc = schedulefunc
        self.download_id = download_id
        self.context = context
        self.addcontact = addcontactfunc
        self.reported_port = reported_port
        self.everinc = False
        #self.throttle_task = None

        # submitted
        self.pending_connections = {}
        # transport connected
        self.connections = {}
        # protocol active
        self.complete_connections = set()
        
        self.spares = set()

        self.banned = set()
        self.schedulefunc(config['keepalive_interval'],
                          self.send_keepalives)

        self.throttled = False
        self.downloader.postpone_func = self.throttle_connections
        self.downloader.resume_func = self.unthrottle_connections

        self.cruise_control = task.LoopingCall(self._check_throttle)
        self.cruise_control.start(0.5)

    def send_keepalives(self):
        self.schedulefunc(self.config['keepalive_interval'],
                          self.send_keepalives)
        for c in self.complete_connections:
            c.send_keepalive()

    def hashcheck_succeeded(self, i):
        for c in self.complete_connections:
            # should we not send have messages to peers that already have the piece?
            #if not c.download.have[i]:
            c.send_have(i)

    # returns False if the connection has been pushed on to self.spares
    # other filters and a successful connection return True
    def start_connection(self, dns, id, encrypt=False):
        """@param dns: domain name/ip address and port pair.
           @param id: peer id.
           """
        if dns[0] in self.banned:
            return True
        if id == self.my_id:
            return True
        for v in self.connections.itervalues():
            if id and v.id == id:
                return True
            if self.config['one_connection_per_ip'] and v.ip == dns[0]:
                return True

        #print "start", len(self.pending_connections), len(self.spares), len(self.connections)

        total_outstanding = len(self.connections)
        # it's possible the pending connections could eventually complete,
        # so we have to account for those when enforcing max_initiate
        total_outstanding += len(self.pending_connections)
        
        if total_outstanding >= self.config['max_initiate']:
            self.spares.add(dns)
            return False

        # if these fail, I'm getting a very weird dns object        
        assert isinstance(dns, tuple)
        assert isinstance(dns[0], str)
        assert isinstance(dns[1], int)

        # sometimes we try to connect to a peer we're already trying to 
        # connect to 
        #assert dns not in self.pending_connections
        if dns in self.pending_connections:
            return True

        handler = InitialConnectionHandler(self, id, encrypt)
        self.pending_connections[dns] = handler
        new_connection = self.rawserver.start_connection(dns, handler, 
                                                         self.context)

        if not new_connection:
            del self.pending_connections[dns]
            self.spares.add(dns)
            return False

        return True

    def connection_completed(self, c):
        self.complete_connections.add(c)
        c.upload = self.make_upload(c)
        c.download = self.downloader.make_download(c)
        self.choker.connection_made(c)
        if c.uses_dht:
            c.send_port(self.reported_port)

    def got_port(self, c):
        if self.addcontact and c.uses_dht and c.dht_port != None:
            self.addcontact(c.connection.ip, c.dht_port)

    def ever_got_incoming(self):
        return self.everinc

    def how_many_connections(self):
        return len(self.complete_connections)

    def replace_connection(self):
        while self.spares:
            started = self.start_connection(self.spares.pop(), None)
            if not started:
                # start_connection decided to push this connection back on to
                # self.spares because a limit was hit. break now or loop
                # forever
                break

    def throttle_connections(self, t):
        self.throttled = True

        for c in self.connections.itervalues():
            c.connection.pause_reading()

    def _check_throttle(self):
        if not self.context.is_context_valid():
            self.cruise_control.stop()
            return
            
        self.downloader.check_rate()
    
        # TODO: this is a little lazy. it loops over all the connections every
        # half second for every torrent, even if there's no need to throttle.
        if not self.throttled:
            for c in self.connections.itervalues():
                c.connection.resume_reading()
                # arg. resume actually flushes the buffers in iocpreactor, so we
                # have to check the state constantly
                if self.throttled:
                    break

        # TODO: this is totally redundant (notice the assert) but I'm too lazy
        # to test that right now.
        if self.throttled:
            for c in self.connections.itervalues():
                assert c.connection.paused
                c.connection.pause_reading()

    def unthrottle_connections(self):
        self.throttled = False        

    def close_connections(self):
        # drop connections which could be made after we're not interested
        for c in self.pending_connections.itervalues():
            c.accept = False
            
        for c in self.connections.itervalues():
            if not c.closed:
                c.connection.close()
                c.closed = True

    def singleport_connection(self, con):
        if con.ip in self.banned:
            return False
        m = self.config['max_allow_in']
        if m and len(self.connections) >= m:
            return False
        self._add_connection(con)
        con.set_parent(self)
        con.connection.context = self.context
        return True

    def _add_connection(self, con):
        if self.throttled:
            con.connection.pause_reading()
        self.connections[con.connection] = con

    def ban(self, ip):
        self.banned.add(ip)


class SingleportListener(Handler):
    """Manages a server socket common to all torrents.  When a remote
       peer opens a connection to the local peer, the SingleportListener
       maps that peer on to the appropriate torrent's connection manager
       (see SingleportListener.select_torrent).

       See Connector.Connection which upcalls to select_torrent after
       the infohash is received in the opening handshake."""

    def __init__(self, rawserver, nattraverser):
        self.rawserver = rawserver
        self.nattraverser = nattraverser
        self.port = 0
        self.ports = {}
        self.port_change_notification = None
        self.torrents = {}
        self.obfuscated_torrents = {}
        self.connections = {}
        self.download_id = None
        self.local_discovery = None
        self._creating_local_discorvery = False

    def _close(self, port):        
        serversocket = self.ports[port][0]
        self.nattraverser.unregister_port(port, "TCP")
        self.rawserver.stop_listening(serversocket)
        serversocket.close()
        if self.local_discovery:
            self.local_discovery.stop()

    def _check_close(self, port):
        if not port or self.port == port or len(self.ports[port][1]) > 0:
            return
        self._close(port)
        del self.ports[port]

    def open_port(self, port, config):
        if port in self.ports:
            self.port = port
            return
        serversocket = self.rawserver.create_serversocket(
            port, config['bind'], tos=config['peer_socket_tos'])
        try:
            d = self.nattraverser.register_port(port, port, "TCP", config['bind'])
            def change(*a):
                self.rawserver.external_add_task(0, self._change_port, *a)
            d.addCallback(change)
            def silent(*e):
                pass
            d.addErrback(silent)
        except Exception, e:
            # blanket, just incase - we don't want to interrupt things
            # maybe we should log it, maybe not
            #print "UPnP registration error", e
            pass
        self.rawserver.start_listening(serversocket, self)
        oldport = self.port
        self.port = port
        self.ports[port] = [serversocket, {}]        
        self._check_close(oldport)

        if self.local_discovery:
            self.local_discovery.stop()
        self._create_local_discovery()

    def _create_local_discovery(self):
        self._creating_local_discorvery = True
        try:
            self.local_discovery = LocalDiscovery(self.rawserver, self.port,
                                                  self._start_connection)
            self._creating_local_discorvery = False
        except:
            self.rawserver.add_task(5, self._create_local_discovery)

    def _start_connection(self, addr, infohash):
        infohash = infohash.decode('hex')
        if infohash not in self.torrents:
            return
        connection_manager = self.torrents[infohash]
        # TODO: peer id?
        connection_manager.start_connection(addr, None)
        
    def _change_port(self, port):
        if self.port == port:
            return
        [serversocket, callbacks] = self.ports[self.port]
        self.ports[port] = [serversocket, callbacks]
        del self.ports[self.port]
        self.port = port
        for callback in callbacks:
            if callback:
                callback(port)

    def get_port(self, callback = None):
        if self.port:
            callbacks = self.ports[self.port][1]
            if callback not in callbacks:
                callbacks[callback] = 1
            else:
                callbacks[callback] += 1
        return self.port

    def release_port(self, port, callback = None):
        callbacks = self.ports[port][1]
        callbacks[callback] -= 1
        if callbacks[callback] == 0:
            del callbacks[callback]
        self._check_close(port)

    def close_sockets(self):
        for port in self.ports.iterkeys():
            self._close(port)

    def add_torrent(self, infohash, connection_manager):
        if infohash in self.torrents:
            raise BTFailure(_("Can't start two separate instances of the same "
                              "torrent"))
        self.torrents[infohash] = connection_manager
        self.obfuscated_torrents[sha('req2' + infohash).digest()] = connection_manager
        if self.local_discovery:
            self.local_discovery.announce(infohash.encode('hex'),
                                          connection_manager.my_id.encode('hex'))

    def remove_torrent(self, infohash):
        del self.torrents[infohash]
        del self.obfuscated_torrents[sha('req2' + infohash).digest()]

    def select_torrent(self, conn, infohash):
        if infohash in self.torrents:
            accepted = self.torrents[infohash].singleport_connection(conn)
            # the connection manager may refuse the connection, in which
            # case keep the connection in our list until it is dropped
            if accepted:
                del self.connections[conn.connection]

    def select_torrent_obfuscated(self, conn, streamid):
        if streamid not in self.obfuscated_torrents:
            return
        self.obfuscated_torrents[streamid].singleport_connection(conn)

    def connection_made(self, connection):
        con = Connection(self, connection, None, False)
        self.connections[connection] = con

    def replace_connection(self):
        pass
