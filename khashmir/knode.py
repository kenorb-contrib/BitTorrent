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
    def checkSender(self, dict):
        try:
            senderid = dict['rsp']['id']
        except KeyError:
            raise KRPCProtocolError, "No peer id in response."
        else:
            if self.id != NULL_ID and senderid != self.id:
                self.table.table.invalidateNode(self)
                
        return dict

    def errBack(self, err):
        return err
        
    def ping(self, id):
        df = self.conn.sendRequest('ping', {"id":id})
        df.addErrback(self.errBack)
        df.addCallback(self.checkSender)
        return df

    def findNode(self, target, id):
        df = self.conn.sendRequest('find_node', {"target" : target, "id": id})
        df.addErrback(self.errBack)
        df.addCallback(self.checkSender)
        return df

class KNodeRead(KNodeBase):
    def findValue(self, key, id):
        df =  self.conn.sendRequest('find_value', {"key" : key, "id" : id})
        df.addErrback(self.errBack)
        df.addCallback(self.checkSender)
        return df

class KNodeWrite(KNodeRead):
    def storeValue(self, key, value, id):
        df = self.conn.sendRequest('store_value', {"key" : key, "value" : value, "id": id})
        df.addErrback(self.errBack)
        df.addCallback(self.checkSender)
        return df
    def storeValues(self, key, value, id):
        df = self.conn.sendRequest('store_values', {"key" : key, "values" : value, "id": id})
        df.addErrback(self.errBack)
        df.addCallback(self.checkSender)
        return df
