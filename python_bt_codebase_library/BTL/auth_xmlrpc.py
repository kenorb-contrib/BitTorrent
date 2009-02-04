# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Copyright 2006 BitTorrent, Inc. All Rights Reserved.
#
# XML-RPC that supports public key encryption and authentication.
# Author: David Harrison

from BTL.reactor_magic import reactor
from twisted.web import xmlrpc
from twisted.internet.ssl import SSL
from twisted.internet import ssl

debug = False

## Keep these next two commented out classes.  They can be useful for
## spying on calls.
class AuthQueryProtocol(xmlrpc.QueryProtocol):
    def connectionMade(self):
        if debug:
            print "connectionMade"
        xmlrpc.QueryProtocol.connectionMade(self)

    def handleStatus(self, version, status, message):
        if debug:
            print "version=%s\nstats=%s\nmessage=%s" % (version,status,message)
        xmlrpc.QueryProtocol.handleStatus(self,version,status,message)

    def handleResponse(self, contents):
        if debug:
            print "contents=%s" % str(contents)
        xmlrpc.QueryProtocol.handleResponse(self, contents)

class AuthQueryFactory(xmlrpc.QueryFactory):
    #protocol = xmlrpc.QueryProtocol
    protocol = AuthQueryProtocol

    def __init__( self, path, host, method, user=None, password=None, *args):
        xmlrpc.QueryFactory.__init__(self, path, host, method, user, password, *args)
## End Comment

class AuthContextFactory(ssl.ClientContextFactory):
    def __init__(self, certificate_file_name, private_key_file_name):
        self.certificate_file_name = certificate_file_name
        self.private_key_file_name = private_key_file_name
        
    def getContext(self):
        ctx = SSL.Context(self.method)
        ctx.use_certificate_file(self.certificate_file_name)
        if self.private_key_file_name:
            ctx.use_privatekey_file(self.private_key_file_name)
        return ctx

class AuthProxy(xmlrpc.Proxy):
    def __init__(self, url, certificate_file_name, private_key_file_name = None,
                 user=None, password=None):
        xmlrpc.Proxy.__init__(self, url, user, password)
        self.certificate_file_name = certificate_file_name
        self.private_key_file_name = private_key_file_name
        
    def callRemote(self, method, *args):
        factory = AuthQueryFactory(self.path, self.host, method,
                                   self.user, self.password, *args)
        #factory = xmlrpc.QueryFactory(self.path, self.host, method,
        #                           self.user, self.password, *args)
        if self.secure:
            from twisted.internet import ssl
            #print "Connecting using ssl to host", self.host, "port", (self.port or 443)
            reactor.connectSSL(self.host, self.port or 443, factory, 
                               AuthContextFactory(self.certificate_file_name,
                                                  self.private_key_file_name))
            #reactor.connectSSL(self.host, self.port or 443, factory, 
            #    ssl.DefaultOpenSSLContextFactory("", self.certificate_file_name))

        else:
            reactor.connectTCP(self.host, self.port or 80, factory)
        return factory.deferred


