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
true = 1
false = 0

infotemplate = compile_template([{'type': 'single', 
    'pieces': ListMarker(exact_length(20)),
    'piece length': 1, 'length': 0, 'name': string_template}, 
    {'type': 'multiple', 'pieces': ListMarker(exact_length(20)), 
    'piece length': 1, 'files': ListMarker({'path': ListMarker(string_template), 
    'length': 0}), 'name': string_template}])

infofiletemplate = compile_template(ValuesMarker(infotemplate))

downloaderfiletemplate = compile_template(ValuesMarker(
    ListMarker({'id': exact_length(20), 'ip': string_template,
    'port': 1})))

announcetemplate = compile_template({'id': string_template, 
    'myid': exact_length(20), 'ip': string_template, 'port': 1, 
    'uploaded': 0, 'downloaded': 0, 'left': 0,
    'event': OptionMarker(['started', 'completed', 'stopped'])})

alas = 'your file may exist elsewhere in the universe\n\nbut alas, not here'

thanks = (200, 'OK', {'Content-Type': 'text/plain'}, 
    'Thanks! Love, Kerensa.')

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

    def get(self, connection, path, headers):
        path = unquote(path)[1:]
        if path == '' or path == 'index.html':
            s = StringIO()
            s.write('<head><title>Published BitTorrent files</title></head>Published BitTorrent files<p>\n')
            names = self.published.keys()
            if names == []:
                s.write('(no files published yet)')
            names.sort()
            for name in names:
                s.write('<a href="' + name + '">' + name + '</a><p>\n\n')
            return (200, 'OK', {'Content-Type': 'text/html'}, s.getvalue())
        if not self.published.has_key(path):
            return (404, 'Not Found', {'Content-Type': 'text/plain'}, alas)
        data = bencode({'info': self.published[path], 'id': path, 
            'url': self.urlprefix + path, 'protocol': 'plaintext',
            'announce': self.urlprefix + '/announce/',
            'your ip': connection.get_ip(), 'peers': self.downloaders.get(path, [])})
        return (200, 'OK', {'Content-Type': 'application/x-bittorrent', 
            'Pragma': 'no-cache'}, data)

    def put(self, connection, path, headers, data):
        try:
            return self.realput(connection, path, headers, data)
        except ValueError, e:
            print_exc()
            return (400, 'Bad Request', {'Content-Type': 'text/plain'}, 
                'you sent me garbage - ' + `e`)

    def realput(self, connection, path, headers, data):
        path = unquote(path)[1:]
        message = bdecode(data)
        self.loghandle.write(str(message) + '\n')
        if path == 'announce/':
            announcetemplate(message)
            peers = self.downloaders.setdefault(message['id'], [])
            if message.get('event') != 'stopped':
                for p in peers:
                    if p['id'] == message['myid']:
                        return thanks
                peers.append({'ip': message['ip'], 'port': message['port'],
                    'id': message['myid']})
                if len(peers) > 25:
                    del peers[0]
            else:
                for i in xrange(len(peers)):
                    if peers[i]['id'] == message['myid']:
                        del peers[i]
                        break
                else:
                    return thanks
            h = open(self.dfile, 'wb')
            h.write(bencode(self.downloaders))
            h.close()
        else:
            infotemplate(message)
            if headers.get('content-type') != 'application/x-bittorrent':
                return (403, 'forbidden', {'Content-Type': 'text/plain'},
                    'only accepting puts of content-type application/x-bittorrent')
            if self.published.has_key(path):
                if self.published[path] != message:
                    return (403, 'forbidden', {'Content-Type': 'text/plain'},
                        'incompatible existing information')
            else:
                self.published[path] = message
                h = open(self.statefile, 'wb')
                h.write(bencode(self.published))
                h.close()
        return thanks

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


