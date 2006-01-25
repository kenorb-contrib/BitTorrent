# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bram Cohen

from socket import error as socketerror

from BitTorrent import BTFailure
from BitTorrent.RawServer_magic import Handler
from BitTorrent.NatTraversal import UPNPError
from BitTorrent.Connecter import Connection
from BitTorrent.platform import is_frozen_exe
from BitTorrent.ClientIdentifier import identify_client

# header, reserved, download id, my id, [length, message]

class InitialConnectionHandler(Handler):
    def __init__(self, parent, id):
        self.parent = parent
        self.id = id
        self.accept = True
        
    def connection_started(self, s):

        del self.parent.pending_connections[(s.ip, s.port)]

        # prevents conenctions we no longer care about from being accepted
        if not self.accept:
            return

        con = Connection(self.parent, s, self.id, True)
        self.parent.connections[s] = con
            
        # it might not be obvious why this is here.
        # if the pending queue filled and put the remaining connections
        # into the spare list, this will push more connections in to pending
        self.parent.replace_connection()
        
    def connection_failed(self, addr, exception):
        del self.parent.pending_connections[addr]

        if not self.accept:
            # we don't need to rotate the spares with replace_connection()
            # if the Encoder object has stopped all connections
            return

        self.parent.replace_connection()


class Encoder(object):

    def __init__(self, make_upload, downloader, choker, numpieces, ratelimiter,
                 rawserver, config, my_id, schedulefunc, download_id, context, addcontactfunc, reported_port):
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

        # submitted
        self.pending_connections = {}
        # transport connected
        self.connections = {}
        # protocol active
        self.complete_connections = {}
        
        self.spares = {}

        self.banned = {}
        schedulefunc(self.send_keepalives, config['keepalive_interval'])

    def send_keepalives(self):
        self.schedulefunc(self.send_keepalives,
                          self.config['keepalive_interval'])
        for c in self.complete_connections:
            c.send_keepalive()

    # returns False if the connection has been pushed on to self.spares
    # other filters and a successful connection return True
    def start_connection(self, dns, id):
        if dns[0] in self.banned:
            return True
        if id == self.my_id:
            return True
        for v in self.connections.values():
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
            self.spares[dns] = 1
            return False

        # if these fail, I'm getting a very weird dns object        
        assert isinstance(dns, tuple)
        assert isinstance(dns[0], str)
        assert isinstance(dns[1], int)

        # looks like we connect to the same peer several times in a row.
        # we should probably stop doing that, but this prevents it from crashing
        if dns in self.pending_connections:
            # uncomment this if you want to debug the multi-connect problem
            #print "Double Add on", dns
            #traceback.print_stack()
            return True

        handler = InitialConnectionHandler(self, id)
        self.pending_connections[dns] = handler
        started = self.rawserver.async_start_connection(dns, handler, self.context)

        if not started:
            del self.pending_connections[dns]
            self.spares[dns] = 1
            return False

        return True

    def connection_completed(self, c):
        self.complete_connections[c] = 1
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
            started = self.start_connection(self.spares.popitem()[0], None)
            if not started:
                # start_connection decided to push this connection back on to
                # self.spares because a limit was hit. break now or loop forever
                break

    def close_connections(self):
        # drop connections which could be made after we're not interested
        for c in self.pending_connections.itervalues():
            c.accept = False
            
        for c in self.connections.itervalues():
            if not c.closed:
                c.connection.close()
                c.closed = True

    def singleport_connection(self, listener, con):
        if con.ip in self.banned:
            return
        m = self.config['max_allow_in']
        if m and len(self.connections) >= m:
            return
        self.connections[con.connection] = con
        del listener.connections[con.connection]
        con.encoder = self
        con.connection.context = self.context

    def ban(self, ip):
        self.banned[ip] = None


class SingleportListener(Handler):

    def __init__(self, rawserver, nattraverser):
        self.rawserver = rawserver
        self.nattraverser = nattraverser
        self.port = 0
        self.ports = {}
        self.port_change_notification = None
        self.torrents = {}
        self.connections = {}
        self.download_id = None

    def _close(self, port):        
        serversocket = self.ports[port][0]
        self.nattraverser.unregister_port(port, "TCP")
        self.rawserver.stop_listening(serversocket)
        serversocket.close()

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
            port, config['bind'], reuse=True, tos=config['peer_socket_tos'])
        try:
            d = self.nattraverser.register_port(port, port, "TCP", config['bind'])
            d.addCallback(self._change_port)
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
            if not callbacks.has_key(callback):
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

    def add_torrent(self, infohash, encoder):
        if infohash in self.torrents:
            raise BTFailure(_("Can't start two separate instances of the same "
                              "torrent"))
        self.torrents[infohash] = encoder

    def remove_torrent(self, infohash):
        del self.torrents[infohash]

    def select_torrent(self, conn, infohash):
        if infohash in self.torrents:
            self.torrents[infohash].singleport_connection(self, conn)

    def connection_made(self, connection):
        con = Connection(self, connection, None, False)
        self.connections[connection] = con

    def replace_connection(self):
        pass
