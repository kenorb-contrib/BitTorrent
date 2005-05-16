## Copyright 2002-2004 Andrew Loewenstern, All Rights Reserved
# see LICENSE.txt for license information

import const

import time

from sha import sha

from BitTorrent.defaultargs import common_options, rare_options
from BitTorrent.RawServer import RawServer

from ktable import KTable, K
from knode import *
from kstore import KStore

from khash import newID, newIDInRange

from util import packNodes
from actions import FindNode, GetValue, KeyExpirer, StoreValue
import krpc

import sys
import os
import traceback

from BitTorrent.bencode import bencode, bdecode

from defer import Deferred
from random import randrange

from threading import Event

class KhashmirDBExcept(Exception):
    pass

# this is the base class, has base functionality and find node, no key-value mappings
class KhashmirBase:
    __slots__ = ('listener', 'node', 'table', 'store', 'app', 'last', 'protocol')
    _Node = KNodeBase
    def __init__(self, host, port, data_dir, rawserver=None, config=None):
        if rawserver:
            self.rawserver = rawserver
        else:
            self.flag = Event()
            d = dict([(x[0],x[1]) for x in common_options + rare_options])            
            self.rawserver = RawServer(self.flag, d)
        self.setup(host, port, data_dir)
        
    def setup(self, host, port, data_dir):
        self.host = host
        self.port = port
        self.ddir = data_dir
        self.store = KStore()
        self.socket = self.rawserver.create_udpsocket(self.port, self.host, True)
        self.udp = krpc.hostbroker(self, (self.host, self.port), self.socket, self.rawserver.add_task)
        self._load()
        self.rawserver.start_listening_udp(self.socket, self.udp)
        self.last = time.time()
        KeyExpirer(self.store, self.rawserver.add_task)
        self.refreshTable(force=1)
        self.rawserver.add_task(self.checkpoint, 60, (1,))

    def Node(self):
        n = self._Node()
        n.table = self
        return n
    
    def __del__(self):
        self.socket.close()
        
    def _load(self):
        do_load = False
        try:
            s = open(os.path.join(self.ddir, "routing_table"), 'r').read()
            dict = bdecode(s)
        except:
            id = newID()
        else:
            id = dict['id']
            do_load = True
            
        self.node = self._Node().init(id, self.host, self.port)
        self.table = KTable(self.node)
        if do_load:
            self._loadRoutingTable(dict['rt'])
            
        
    def checkpoint(self, auto=0):
        d = {}
        d['id'] = self.node.id
        d['rt'] = self._dumpRoutingTable()
        self.findCloseNodes()
        self.refreshTable()
        try:
            f = open(os.path.join(self.ddir, "routing_table"), 'wb')
            f.write(bencode(d))
            f.close()
        except:
            #print ">>> unable to dump routing table!"
            pass
        
        
        if auto:
            self.rawserver.add_task(self.checkpoint,
                                    randrange(int(const.CHECKPOINT_INTERVAL * .9),
                                              int(const.CHECKPOINT_INTERVAL * 1.1)),
                                    (1,))
        
    def _loadRoutingTable(self, nodes):
        """
            load routing table nodes from database
            it's usually a good idea to call refreshTable(force=1) after loading the table
        """
        for rec in nodes:
            n = self.Node().initWithDict(rec)
            n.conn = self.udp.connectionForAddr((n.host, n.port))
            self.table.insertNode(n, contacted=0)

    def _dumpRoutingTable(self):
        """
            save routing table nodes to the database
        """
        l = []
        for bucket in self.table.buckets:
            for node in bucket.l:
                l.append({'id':node.id, 'host':node.host, 'port':node.port})
        return l
        
            

    #######
    #######  LOCAL INTERFACE    - use these methods!
    def addContact(self, host, port, callback=None):
        """
            ping this node and add the contact info to the table on pong!
        """
        n =self.Node().init(const.NULL_ID, host, port)
        try:
            n.conn = self.udp.connectionForAddr((n.host, n.port))
        except krpc.KRPCSelfNodeError:
            # our own node
            pass
        else:
            self.sendPing(n, callback=callback)

    ## this call is async!
    def findNode(self, id, callback, errback=None):
        """ returns the contact info for node, or the k closest nodes, from the global table """
        # get K nodes out of local table/cache, or the node we want
        nodes = self.table.findNodes(id)
        d = Deferred()
        if errback:
            d.addCallbacks(callback, errback)
        else:
            d.addCallback(callback)
        if len(nodes) == 1 and nodes[0].id == id :
            d.callback(nodes)
        else:
            # create our search state
            state = FindNode(self, id, d.callback, self.rawserver.add_task)
            self.rawserver.external_add_task(state.goWithNodes, 0, (nodes,))
    
    def insertNode(self, n, contacted=1):
        """
        insert a node in our local table, pinging oldest contact in bucket, if necessary
        
        If all you have is a host/port, then use addContact, which calls this method after
        receiving the PONG from the remote node.  The reason for the seperation is we can't insert
        a node into the table without it's peer-ID.  That means of course the node passed into this
        method needs to be a properly formed Node object with a valid ID.
        """
        old = self.table.insertNode(n, contacted=contacted)
        if old and (time.time() - old.lastSeen) > const.MIN_PING_INTERVAL and old.id != self.node.id:
            # the bucket is full, check to see if old node is still around and if so, replace it
            
            ## these are the callbacks used when we ping the oldest node in a bucket
            def _staleNodeHandler(oldnode=old, newnode = n):
                """ called if the pinged node never responds """
                self.table.replaceStaleNode(old, newnode)
            
            def _notStaleNodeHandler(dict, old=old):
                """ called when we get a pong from the old node """
                dict = dict['rsp']
                if dict['id'] == old.id:
                    self.table.justSeenNode(old.id)
            
            df = old.ping(self.node.id)
            df.addCallbacks(_notStaleNodeHandler, _staleNodeHandler)

    def sendPing(self, node, callback=None):
        """
            ping a node
        """
        df = node.ping(self.node.id)
        ## these are the callbacks we use when we issue a PING
        def _pongHandler(dict, node=node, table=self.table, callback=callback):
            _krpc_sender = dict['_krpc_sender']
            dict = dict['rsp']
            sender = {'id' : dict['id']}
            sender['host'] = _krpc_sender[0]
            sender['port'] = _krpc_sender[1]
            n = self.Node().initWithDict(sender)
            n.conn = self.udp.connectionForAddr((n.host, n.port))
            table.insertNode(n)
            if callback:
                callback()
        def _defaultPong(err, node=node, table=self.table, callback=callback):
            table.nodeFailed(node)
            if callback:
                callback()
        
        df.addCallbacks(_pongHandler,_defaultPong)

    def findCloseNodes(self, callback=lambda a: None):
        """
            This does a findNode on the ID one away from our own.  
            This will allow us to populate our table with nodes on our network closest to our own.
            This is called as soon as we start up with an empty table
        """
        id = self.node.id[:-1] + chr((ord(self.node.id[-1]) + 1) % 256)
        self.findNode(id, callback)

    def refreshTable(self, force=0):
        """
            force=1 will refresh table regardless of last bucket access time
        """
        def callback(nodes):
            pass
    
        for bucket in self.table.buckets:
            if force or (time.time() - bucket.lastAccessed >= const.BUCKET_STALENESS):
                id = newIDInRange(bucket.min, bucket.max)
                self.findNode(id, callback)

    def stats(self):
        """
        Returns (num_contacts, num_nodes)
        num_contacts: number contacts in our routing table
        num_nodes: number of nodes estimated in the entire dht
        """
        num_contacts = reduce(lambda a, b: a + len(b.l), self.table.buckets, 0)
        num_nodes = const.K * (2**(len(self.table.buckets) - 1))
        return {'num_contacts':num_contacts, 'num_nodes':num_nodes}

    def krpc_ping(self, id, _krpc_sender):
        sender = {'id' : id}
        sender['host'] = _krpc_sender[0]
        sender['port'] = _krpc_sender[1]        
        n = self.Node().initWithDict(sender)
        n.conn = self.udp.connectionForAddr((n.host, n.port))
        self.insertNode(n, contacted=0)
        return {"id" : self.node.id}
        
    def krpc_find_node(self, target, id, _krpc_sender):
        nodes = self.table.findNodes(target, invalid=False)
        nodes = map(lambda node: node.senderDict(), nodes)
        sender = {'id' : id}
        sender['host'] = _krpc_sender[0]
        sender['port'] = _krpc_sender[1]        
        n = self.Node().initWithDict(sender)
        n.conn = self.udp.connectionForAddr((n.host, n.port))
        self.insertNode(n, contacted=0)
        return {"nodes" : packNodes(nodes), "id" : self.node.id}


## This class provides read-only access to the DHT, valueForKey
## you probably want to use this mixin and provide your own write methods
class KhashmirRead(KhashmirBase):
    _Node = KNodeRead
    def retrieveValues(self, key):
        try:
            l = self.store[key]
        except KeyError:
            l = []
        return l
    ## also async
    def valueForKey(self, key, callback, searchlocal = 1):
        """ returns the values found for key in global table
            callback will be called with a list of values for each peer that returns unique values
            final callback will be an empty list - probably should change to 'more coming' arg
        """
        nodes = self.table.findNodes(key)
        
        # get locals
        if searchlocal:
            l = self.retrieveValues(key)
            if len(l) > 0:
                self.rawserver.add_task(callback, 0, (l,))
        else:
            l = []
        
        # create our search state
        state = GetValue(self, key, callback, self.rawserver.add_task)
        self.rawserver.add_task(state.goWithNodes, 0, (nodes, l))

    def krpc_find_value(self, key, id, _krpc_sender):
        sender = {'id' : id}
        sender['host'] = _krpc_sender[0]
        sender['port'] = _krpc_sender[1]        
        n = self.Node().initWithDict(sender)
        n.conn = self.udp.connectionForAddr((n.host, n.port))
        self.insertNode(n, contacted=0)
    
        l = self.retrieveValues(key)
        if len(l) > 0:
            return {'values' : l, "id": self.node.id}
        else:
            nodes = self.table.findNodes(key, invalid=False)
            nodes = map(lambda node: node.senderDict(), nodes)
            return {'nodes' : packNodes(nodes), "id": self.node.id}

###  provides a generic write method, you probably don't want to deploy something that allows
###  arbitrary value storage
class KhashmirWrite(KhashmirRead):
    _Node = KNodeWrite
    ## async, callback indicates nodes we got a response from (but no guarantee they didn't drop it on the floor)
    def storeValueForKey(self, key, value, callback=None):
        """ stores the value for key in the global table, returns immediately, no status 
            in this implementation, peers respond but don't indicate status to storing values
            a key can have many values
        """
        def _storeValueForKey(nodes, key=key, value=value, response=callback , table=self.table):
            if not response:
                # default callback
                def _storedValueHandler(sender):
                    pass
                response=_storedValueHandler
            action = StoreValue(self, key, value, response, self.rawserver.add_task)
            self.rawserver.external_add_task(action.goWithNodes, 0, (nodes,))
            
        # this call is asynch
        self.findNode(key, _storeValueForKey)
                    
    def krpc_store_value(self, key, value, id, _krpc_sender):
        t = "%0.6f" % time.time()
        self.store[key] = value
        sender = {'id' : id}
        sender['host'] = _krpc_sender[0]
        sender['port'] = _krpc_sender[1]        
        n = self.Node().initWithDict(sender)
        n.conn = self.udp.connectionForAddr((n.host, n.port))
        self.insertNode(n, contacted=0)
        return {"id" : self.node.id}

# the whole shebang, for testing
class Khashmir(KhashmirWrite):
    _Node = KNodeWrite
