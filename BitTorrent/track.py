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
from time import time
from random import shuffle
true = 1
false = 0

def mult20(thing, verbose):
    if type(thing) != type(''):
        raise ValueError, 'must be a string'
    if len(thing) % 20 != 0:
        raise ValueError, 'must be multiple of 20'

infotemplate = compile_template({'pieces': mult20, 
    'piece length': 1, 'files': OptionMarker(ListMarker({
    'path': ListMarker(string_template), 'length': 0})), 
    'name': string_template, 'length': OptionMarker(0)})

infofiletemplate = compile_template(ValuesMarker(infotemplate))

downloaderfiletemplate = compile_template(ValuesMarker(
    ValuesMarker({'ip': string_template, 'port': 1}, 
    exact_length(20))))

announcetemplate = compile_template({'file id': string_template, 
    'peer id': exact_length(20), 'ip': string_template, 'port': 1, 
    'uploaded': 0, 'downloaded': 0, 'left': 0,
    'event': OptionMarker(['started', 'completed', 'stopped'])})

alas = 'your file may exist elsewhere in the universe\n\nbut alas, not here'

thanks = (200, 'OK', {'Content-Type': 'text/plain'}, 
    'Thanks! Love, Kerensa.')

class Tracker:
    def __init__(self, ip, port, statefile, dfile, logfile, rawserver):
        self.urlprefix = 'http://' + ip + ':' + str(port)
        self.statefile = statefile
        self.dfile = dfile
        self.rawserver = rawserver
        self.loghandle = open(logfile, 'ab')
        self.cached = {}
        self.published = {}
        if exists(statefile):
            h = open(statefile, 'rb')
            r = h.read()
            h.close()
            self.published = bdecode(r)
            infofiletemplate(self.published)
        self.loghandle = open(logfile, 'ab')
        self.downloads = {}
        self.times = {}
        if exists(dfile):
            h = open(dfile, 'rb')
            ds = h.read()
            h.close()
            self.downloads = bdecode(ds)
            downloaderfiletemplate(self.downloads)
            for x in self.downloads.keys():
                self.times[x] = {}
                for y in self.downloads[x].keys():
                    self.times[x][y] = 0
        rawserver.add_task(self.save_dfile, 5 * 60)
        self.prevtime = time()
        rawserver.add_task(self.expire_downloaders, 45 * 60)

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
        data = {'info': self.published[path], 'file id': path, 
            'url': self.urlprefix + path, 'protocol': 'plaintext',
            'announce': self.urlprefix + '/announce/', 'junk': None,
            'your ip': connection.get_ip(), 'interval': 30 * 60}
        if len(self.cached.get(path, [])) < 25:
            self.cached[path] = [{'peer id': key, 'ip': value['ip'], 
                'port': value['port']} for key, value in 
                self.downloads.setdefault(path, {}).items()]
            shuffle(self.cached[path])
        data['peers'] = self.cached[path][-25:]
        del self.cached[path][-25:]
        return (200, 'OK', {'Content-Type': 'application/x-bittorrent', 
            'Pragma': 'no-cache'}, bencode(data))

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
        self.loghandle.flush()
        if path == 'announce/':
            announcetemplate(message)
            peers = self.downloads.setdefault(message['file id'], {})
            myid = message['peer id']
            if message.get('event') != 'stopped':
                self.times.setdefault(message['file id'], {})[myid] = time()
                if not peers.has_key(myid):
                    peers[myid] = {'ip': message['ip'], 'port': message['port']}
            else:
                if peers.has_key(myid):
                    del peers[myid]
                    del self.times[message['file id']][myid]
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

    def save_dfile(self):
        self.rawserver.add_task(self.save_dfile, 5 * 60)
        h = open(self.dfile, 'wb')
        h.write(bencode(self.downloads))
        h.close()

    def expire_downloaders(self):
        for x in self.times.keys():
            for myid, t in self.times[x].items():
                if t < self.prevtime:
                    del self.times[x][myid]
                    del self.downloads[x][myid]
        self.prevtime = time()
        self.rawserver.add_task(self.expire_downloaders, 45 * 60)

def track(ip, port, statefile, dfile, logfile, bind):
    try:
        h = urlopen('http://bitconjurer.org/BitTorrent/status-tracker-02-08-00.txt')
        status = h.read().strip()
        h.close()
        if status != 'current':
            print 'No longer the latest version - see http://bitconjurer.org/BitTorrent/download.html'
            return
    except IOError, e:
        print "Couldn't check version number - " + str(e)
    r = RawServer(100, Event(), 30)
    t = Tracker(ip, port, statefile, dfile, logfile, r)
    r.bind(port, bind)
    r.listen_forever(HTTPHandler(t.get, t.put))


