from httplib import HTTP
from bencode import bencode, bdecode
from urlparse import urlparse

def readput(url, data):
    data = bencode(data)
    protocol, host, path, g1, g2, g3 = urlparse(url)
    if protocol != 'http':
        raise ValueError, "can't handle protocol '" + protocol + "'"
    h = HTTP(host)
    h.putrequest('PUT', path)
    h.putheader('content-length', str(len(data)))
    h.endheaders()
    h.send(data)
    reply, message, headers = h.getreply()
    if reply != 200:
        raise ValueError, 'unexpected response - ' + str(reply)
    f = h.getfile()
    r = f.read(int(headers.getheader('content-length')))
    f.close()
    return bdecode(r)

