# Written by Bram Cohen
# see LICENSE.txt for license information

from RawServer import RawServer
from HTTPHandler import HTTPHandler
from threading import Event
from btemplate import compile_template, ListMarker, string_template, OptionMarker, exact_length, ValuesMarker
from bencode import bencode, bdecode
from urllib import urlopen, quote, unquote
from os.path import exists
from cStringIO import StringIO
from traceback import print_exc
from copy import deepcopy
true = 1
false = 0

infotemplate = compile_template([{'type': 'single', 
    'pieces': ListMarker(exact_length(20)),
    'piece length': 1, 'length': 0, 'name': string_template}, 
    {'type': 'multiple', 'pieces': ListMarker(exact_length(20)), 
    'piece length': 1, 'files': ListMarker({'path': ListMarker(string_template), 
    'length': 0}), 'name': string_template}])

contact = {'ip': string_template, 
    'port': 1}

infofiletemplate = compile_template(ValuesMarker(infotemplate))

peerlist = ListMarker({'myid': string_template, 'contact': contact})

downloaderfiletemplate = compile_template(ValuesMarker(
    {'permanent': peerlist, 'temporary': peerlist}))

announcetemplate = compile_template([
    {'type': 'announce', 'id': string_template, 'myid': string_template, 
    'contact': contact, 'left': OptionMarker(0)},
    {'type': 'finished', 'myid': string_template, 
    'uploaded': 0, 'downloaded': 0, 
    'result': ['success', 'failure']}])

alas = 'your file may exist elsewhere in the universe\n\nbut alas, not here'

class Tracker:
    def __init__(self, ip, port, statefile, dfile, logfile):
        self.urlprefix = 'http://' + ip + ':' + str(port)
        self.statefile = statefile
        self.dfile = dfile
        self.loghandle = open(logfile, 'ab')
        self.published = {}
        if exists(statefile):
            h = open(statefile, 'rb')
            r = h.read()
            h.close()
            self.published = bdecode(r)
            infofiletemplate(self.published)
        self.loghandle = open(logfile, 'ab')
        self.downloaders = {}
        self.myid_to_id = {}
        if exists(dfile):
            h = open(dfile, 'rb')
            ds = h.read()
            h.close()
            self.downloads = bdecode(ds)
            downloaderfiletemplate(self.downloads)
            for key, value in self.downloads.items():
                for j in value['permanent'] + value['temporary']:
                    self.myid_to_id[j['myid']] = id

    def get(self, connection, path, headers):
        try:
            return self.realget(connection, path, headers)
        except ValueError, e:
            return (400, 'Bad Request', {'Content-Type': 'text/plain'}, 
                'you sent me garbage - ' + `e`)

    def realget(self, connection, path, headers):
        published = self.published
        path = unquote(path)[1:]
        if path == '' or path == 'index.html':
            s = StringIO()
            s.write('<head><title>Published BitTorrent files</title></head>Published BitTorrent files<p>\n')
            names = published.keys()
            if names == []:
                s.write('(no files published yet)')
            names.sort()
            for name in names:
                s.write('<a href="' + name + '">' + name + '</a><p>\n\n')
            return (200, 'OK', {'Content-Type': 'text/html'}, s.getvalue())
        if not published.has_key(path):
            return (404, 'Not Found', {'Content-Type': 'text/plain'}, alas)
        p = self.downloaders.get(path)
        peers = []
        if p is not None:
            for x in (p['permanent'] + p['temporary']):
                y = deepcopy(x['contact'])
                y['id'] = x['myid']
                peers.append(y)
        data = bencode({'info': published[path], 'id': path, 
            'url': self.urlprefix + path, 'protocol': 'plaintext',
            'announce': self.urlprefix + '/announce/',
            'your ip': connection.get_ip(), 'peers': peers})
        return (200, 'OK', {'Content-Type': 'application/x-bittorrent', 
            'Pragma': 'no-cache'}, data)

    def put(self, connection, path, headers, data):
        try:
            return self.realput(connection, path, headers, data)
        except ValueError, e:
            return (400, 'Bad Request', {'Content-Type': 'text/plain'}, 
                'you sent me garbage - ' + `e`)

    def realput(self, connection, path, headers, data):
        path = unquote(path)[1:]
        message = bdecode(data)
        self.loghandle.write(str(message) + '\n')
        if path == 'announce/':
            announcetemplate(message)
            downloaders = self.downloaders
            myid = message['myid']
            if message['type'] == 'announce':
                id = message['id']
                contact = message['contact']
                peers = downloaders.setdefault(id, 
                    {'permanent': [], 'temporary': []})
                perm = peers['permanent']
                temp = peers['temporary']
                for i in xrange(len(perm)):
                    if perm[i]['contact'] == contact:
                        del self.myid_to_id[perm[i]['myid']]
                        del perm[i]
                        break
                else:
                    for i in xrange(len(temp)):
                        if temp[i]['contact'] == contact:
                            del self.myid_to_id[temp[i]['myid']]
                            del temp[i]
                            break
                if not message.has_key('permanent'):
                    temp.append({'myid': myid, 'contact': contact})
                    if len(temp) > 25:
                        del temp[0]
                else:
                    perm.append({'myid': myid, 'contact': contact})
                self.myid_to_id[myid] = id
            else:
                if self.myid_to_id.has_key(myid):
                    id = self.myid_to_id[myid]
                    del self.myid_to_id[myid]
                    peers = downloaders.setdefault(id, 
                        {'permanent': [], 'temporary': []})
                    perm = peers['permanent']
                    temp = peers['temporary']
                    for i in xrange(len(perm)):
                        if perm[i]['myid'] == myid:
                            del perm[i]
                            break
                    else:
                        for i in xrange(len(temp)):
                            if temp[i]['myid'] == myid:
                                del temp[i]
                                break
                    if perm == [] and temp == []:
                        del downloaders[id]
            h = open(self.dfile, 'wb')
            h.write(bencode(downloaders))
            h.close()
        else:
            if headers.get('content-type') != 'application/x-bittorrent':
                return (403, 'forbidden', {'Content-Type': 'text/plain'},
                    'only accepting puts of content-type application/x-bittorrent')
            infotemplate(message)
            published = self.published
            if published.has_key(path):
                if published[path] != message:
                    return (403, 'forbidden', {'Content-Type': 'text/plain'},
                        'incompatible existing information')
            else:
                published[path] = message
                h = open(self.statefile, 'wb')
                h.write(bencode(published))
                h.close()
        return (200, 'OK', {'Content-Type': 'text/plain'}, 
            'Thanks! Love, Kerensa.')

def track(ip, port, statefile, dfile, logfile, bind):
    try:
        h = urlopen('http://bitconjurer.org/BitTorrent/status-tracker-02-07-02.txt')
        status = h.read().strip()
        h.close()
        if status != 'current':
            print 'No longer the latest version - see http://bitconjurer.org/BitTorrent/download.html'
            return
    except IOError, e:
        print "Couldn't check version number - " + str(e)
    t = Tracker(ip, port, statefile, dfile, logfile)
    r = RawServer(100, Event(), 30)
    r.bind(port, bind)
    r.listen_forever(HTTPHandler(t.get, t.put))


