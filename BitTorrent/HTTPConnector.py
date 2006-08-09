# by Greg Hazel

from __future__ import generators

from struct import pack, unpack

import urllib
import logging

from BitTorrent.obsoletepythonsupport import *
from BitTorrent.DictWithLists import OrderedDict
from BitTorrent.Connector import Connection
from bisect import bisect_right
from urlparse import urlparse

# package management sucks!
# it encourages code duplication because it can't keep up
# with packages that have been out for over a year.
# as a result, this is copy'n'pasted twisted 2.0 code
#from twisted.web.http import parseContentRange
def parseContentRange(header):
    """Parse a content-range header into (start, end, realLength).

    realLength might be None if real length is not known ('*').
    """
    kind, other = header.strip().split()
    if kind.lower() != "bytes":
        raise ValueError, "a range of type %r is not supported"
    startend, realLength = other.split("/")
    start, end = map(int, startend.split("-"))
    if realLength == "*":
        realLength = None
    else:
        realLength = int(realLength)
    return (start, end, realLength)

  
noisy = True
if noisy:
    connection_logger = logging.getLogger("BitTorrent.HTTPConnector")
    def log(s):
        print s
    #log = connection_logger.debug


def protocol_violation(s, c=None):
    a = ''
    if noisy:
        if c is not None:
            a = (c.ip, c.port)
        log( "FAUX PAS: %s %s" % ( s, a ))

class BatchRequests(object):

    def __init__(self):
        self.requests = {}

    # you should add from the perspective of a BatchRequest
    def _add_request(self, filename, begin, length, br):
        r = (filename, begin, length)
        assert r not in self.requests
        self.requests[r] = br

    def got_request(self, filename, begin, data):
        length = len(data)
        r = (filename, begin, length)
        br = self.requests.pop(r)
        br.got_request(filename, begin, length, data)
        return br
        

class BatchRequest(object):
    
    def __init__(self, parent, start):
        self.parent = parent
        self.numactive = 0
        self.start = start
        self.requests = OrderedDict()

    def add_request(self, filename, begin, length):
        r = (filename, begin, length)
        assert r not in self.requests
        self.parent._add_request(filename, begin, length, self)
        self.requests[r] = None
        self.numactive += 1

    def got_request(self, filename, begin, length, data):
        self.requests[(filename, begin, length)] = data
        self.numactive -= 1

    def get_result(self):
        if self.numactive > 0:
            return None
        chunks = []
        for k in self.requests.itervalues():
            chunks.append(k)
        return ''.join(chunks)
        

# kind of like storage wrapper for webserver interaction
class URLage(object):

    def __init__(self, files):
        # a list of bytes ranges and filenames for window-based IO
        self.ranges = []
        self._build_url_structs(files)
        
    def _build_url_structs(self, files):
        total = 0
        for filename, length in files:
            if length > 0:
                self.ranges.append((total, total + length, filename))
            total += length
        self.total_length = total

    def _intervals(self, pos, amount):
        r = []
        stop = pos + amount
        p = max(bisect_right(self.ranges, (pos, )) - 1, 0)
        for begin, end, filename in self.ranges[p:]:
            if begin >= stop:
                break
            r.append((filename, max(pos, begin) - begin, min(end, stop) - begin))
        return r

    def _request(self, host, filename, pos, amount, prefix, append):
        b = pos
        e = b + amount - 1
        f = prefix
        if append:
            f += filename
        s = '\r\n'.join([
            "GET /%s HTTP/1.1" % (urllib.quote(f)),
            "Host: %s" % host,
            "Connection: Keep-Alive",
            "Range: bytes=%s-%s" % (b, e),
            "", ""])
        return s    

    def build_requests(self, brs, host, pos, amount, prefix, append):
        r = []
        br = BatchRequest(brs, pos)
        for filename, pos, end in self._intervals(pos, amount):
            s = self._request(host, filename, pos, end - pos, prefix, append)
            br.add_request(filename, pos, end - pos)
            r.append((filename, s))
        return r
        

class HTTPConnection(Connection):
    """Implements the HTTP syntax with a BitTorrent Connection interface. 
       Connection-level semantics are as normal, but the download is always
       unchoked after it's connected."""

    MAX_LINE_LENGTH = 16384

    def __init__(self, parent, piece_size, urlage, connection, id, outgoing):
        self.piece_size = piece_size
        self._header_lines = []
        self.manual_close = False
        self.urlage = urlage
        self.batch_requests = BatchRequests()
        # pipeline tracker
        self.request_paths = []
        scheme, host, path, params, query, fragment = urlparse(id)
        if path and path[0] == '/':
            path = path[1:]
        self.host = host
        self.prefix = path
        self.append = not(len(self.urlage.ranges) == 1 and path and path[-1] != '/')
        Connection.__init__(self, parent, connection, id, outgoing)

    def close(self):
        self.manual_close = True
        Connection.close(self)

    def send_handshake(self):
        self.send_request(0, 0, 1)

    def send_request(self, index, begin, length):
        if noisy:
            log( "SEND %s %d %d %d" % ('GET', index, begin, length) )
        b = (index * self.piece_size) + begin
        r = self.urlage.build_requests(self.batch_requests, self.host, b, length, self.prefix, self.append)
        for filename, s in r:
            self.request_paths.append(filename)
            if self._partial_message is not None:
                self._outqueue.append(s)
            else:
                self.connection.write(s)

    def send_interested(self):
        pass

    def send_not_interested(self):
        pass

    def send_choke(self):
        self.choke_sent = self.upload.choked

    def send_unchoke(self):
        self.choke_sent = self.upload.choked

    def send_cancel(self, index, begin, length):
        pass

    def send_have(self, index):
        pass

    def send_bitfield(self, bitfield):
        pass
    
    def send_keepalive(self):
        # is there something I can do here?
        pass

    # yields the number of bytes it wants next, gets those in self._message
    def _read_messages(self):
        completing = False
        
        while True:
            self._header_lines = []

            yield None
            if not self._message.upper().startswith('HTTP/1.1 206'):
                protocol_violation('Bad status message: %s' % self._message,
                                   self.connection)
                return

            if not self.complete:
                completing = True

            headers = {}
            while True:
                yield None
                if len(self._message) == 0:
                    break
                if ':' not in self._message:
                    protocol_violation('Bad header: %s' % self._message,
                                       self.connection)
                    return
                header, value = self._message.split(':', 1)
                headers[header] = value.strip()
            # reset the header buffer so we can loop
            self._header_lines = []

            filename = self.request_paths.pop(0)
            
            start, end, realLength = parseContentRange(headers['content-range'])
            length = (end - start) + 1
            cl = int(headers.get('content-length', length))
            assert (cl == length,
                    'Got c-l:%d bytes instead of l:%d' % (cl, length))
            yield length
            assert (len(self._message) == length,
                    'Got m:%d bytes instead of l:%d' % (len(self._message), length))
            
            if completing:
                self.complete = True
                completing = False
                self.parent.connection_handshake_completed(self)
                # prefer full pieces to reduce http overhead
                self.download.prefer_full = True
                self.download._got_have_all()
                self.download.got_unchoke()
            elif self.complete:
                self.got_anything = True
                br = self.batch_requests.got_request(filename, start, self._message)
                data = br.get_result()
                if data:
                    index = br.start // self.piece_size
                    if index >= self.parent.numpieces:
                        return
                    begin = br.start - (index * self.piece_size)
                    self.download.got_piece(index, begin, data)

    def data_came_in(self, conn, s):
        self.received_data = True
        if not self.download:
            # this is really annoying.
            self.sloppy_pre_connection_counter += len(s)
        else:
            l = self.sloppy_pre_connection_counter + len(s)
            self.sloppy_pre_connection_counter = 0

        self._buffer.append(s)
        self._buffer_len += len(s)
        # not my favorite loop.
        # the goal is: read self._next_len bytes, or if it's None return all
        # data up to a \r\n
        while True:
            if self.closed:
                return
            if self._next_len == None:
                if self._header_lines:
                    d = ''.join(self._buffer)
                    m = self._header_lines.pop(0).lower()
                else:
                    if '\r\n' not in s:
                        return
                    d = ''.join(self._buffer)
                    headers = d.split('\r\n')
                    # the last one is always trash
                    headers.pop(-1)
                    self._header_lines.extend(headers)
                    m = self._header_lines.pop(0).lower()
                if len(m) > self.MAX_LINE_LENGTH:
                    protocol_violation('Line length exceeded.',
                                       self.connection)
                    self.close()
                    return
                self._next_len = len(m) + len('\r\n')
            else:
                if self._next_len > self._buffer_len:
                    return
                d = ''.join(self._buffer)
                m = d[:self._next_len]
            s = d[self._next_len:]
            self._buffer = [s]
            self._buffer_len = len(s)
            self._message = m
            try:
                self._next_len = self._reader.next()
            except StopIteration:
                self.close()
                return

    def _optional_restart(self):            
        if self.complete and not self.manual_close:
            # http keep-alive has a per-connection limit on the number of requests
            # also, it times out. both result it a dropped connection, so re-make it.
            # idealistically, the connection would hang around even if dropped, and
            # reconnect if we needed to make a new request (that way we don't thrash
            # the piece picker everytime we reconnect)
            dns = (self.connection.ip, self.connection.port)
            self.parent.start_http_connection(dns, id=self.id)
