## Copyright 2002-2004 Andrew Loewenstern, All Rights Reserved
# see LICENSE.txt for license information

from node import Node
from defer import Deferred
from const import NULL_ID
from krpc import KRPCProtocolError

class IDChecker:
    def __init__(self, id):
        self.id = id

class KNodeBase(Node):
    def __init__(self, cfa):
        Node.__init__(self)
        self.pinging = False
        self.cfa = cfa

    def conn(self):
        return self.cfa((self.host, self.port))
    
    def checkSender(self, dict):
        try:
            senderid = dict['rsp']['id']
        except KeyError:
            raise KRPCProtocolError, "No peer id in response."
        else:
            if self.id != NULL_ID and senderid != self.id:
                self.table.table.invalidateNode(self)
            else:
                self.table.insertNode(self, contacted=1)
        return dict

    def errBack(self, err):
        self.table.table.nodeFailed(self)
        return err
        
    def ping(self, id):
        df = self.conn().sendRequest('ping', {"id":id})
        self.pinging = True
        def endping(x):
            self.pinging = False
            return x
        df.addCallbacks(endping, endping)
        df.addCallbacks(self.checkSender, self.errBack)
        return df

    def findNode(self, target, id):
        df = self.conn().sendRequest('find_node', {"target" : target, "id": id})
        df.addErrback(self.errBack)
        df.addCallback(self.checkSender)
        return df

class KNodeRead(KNodeBase):
    def findValue(self, key, id):
        df =  self.conn().sendRequest('find_value', {"key" : key, "id" : id})
        df.addErrback(self.errBack)
        df.addCallback(self.checkSender)
        return df

class KNodeWrite(KNodeRead):
    def storeValue(self, key, value, id):
        df = self.conn().sendRequest('store_value', {"key" : key, "value" : value, "id": id})
        df.addErrback(self.errBack)
        df.addCallback(self.checkSender)
        return df
    def storeValues(self, key, value, id):
        df = self.conn().sendRequest('store_values', {"key" : key, "values" : value, "id": id})
        df.addErrback(self.errBack)
        df.addCallback(self.checkSender)
        return df
