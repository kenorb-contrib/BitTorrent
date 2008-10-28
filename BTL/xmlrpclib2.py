# by Greg Hazel

import xml
import xmlrpclib
from connection_cache import PyCURL_Cache, cache_set
import pycurllib
pycurllib.set_use_compression(True)

class PyCurlTransport(xmlrpclib.Transport):
    def __init__(self, cache, max_connects=None, timeout=None):
        self.host = None
        self.cache = cache
        self.max_connects = max_connects
        self.timeout = timeout

    def request(self, host, handler, request_body, verbose=0):
        for i in xrange(0):
            try:
                return self._request(host, handler, request_body, verbose)
            except:
                pass
        return self._request(host, handler, request_body, verbose)

    def _set_connection_params(self, h):
        h.add_header('User-Agent', "xmlrpclib2.py/2.0")
        h.add_header('Connection', "Keep-Alive")
        h.add_header('Content-Type', "application/octet-stream")
        # this timeout is intended to save us from tomcat not responding
        # and locking the site
        if None != self.timeout:
            h.set_timeout(self.timeout)
        else:
            h.set_timeout(2000) # for backwards compatibility, keep old default
        if None != self.max_connects:
            h.set_max_connects(self.max_connects)

    def _request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request
        h = self.cache.get_connection()
        try:
            self._set_connection_params(h)
            h.add_data(request_body)
            response = pycurllib.urlopen(h, close=False)
        except:
            # connection may no longer be valid
            self.cache.destroy_connection(h)
            raise
        self.cache.put_connection(h)
        if response.code != 200:
            raise xmlrpclib.ProtocolError(
                host + handler,
                response.code, response.msg,
                'N/A',
            )
        self.verbose = verbose
        return self._parse_response(response)

    def _parse_response(self, response):
        # read response from input file/socket, and parse it
        p, u = self.getparser()
        d = response.getvalue()
        try:
            p.feed(d)
        except xml.parsers.expat.ExpatError, e:
            n = xml.parsers.expat.ExpatError("%s : %s" % (e, d))
            try:
                n.code = e.code
                n.lineno = e.lineno
                n.offset = e.offset
            except:
                pass
            raise n
        p.close()
        return u.close()

def new_server_proxy(url, max_connects=None, timeout=None):
    c = cache_set.get_cache(PyCURL_Cache, url, max_per_cache=max_connects)
    t = PyCurlTransport(c, max_connects=max_connects, timeout=timeout)
    return xmlrpclib.ServerProxy(url, transport=t)

ServerProxy = new_server_proxy
