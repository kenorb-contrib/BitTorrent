# Written by Bram Cohen
# see LICENSE.txt for license information

from parseargs import parseargs, formatDefinitions
from RawServer import RawServer
from HTTPHandler import HTTPHandler
from threading import Event
from btemplate import compile_template, ListMarker, string_template, OptionMarker, exact_length, ValuesMarker
from bencode import bencode, bdecode
from urllib import urlopen, quote, unquote
from urlparse import urlparse
from os.path import exists
from cStringIO import StringIO
from traceback import print_exc
from time import time
from random import shuffle
true = 1
false = 0

defaults = [
    ('port', 'p', 80, "Port to listen on."),
    ('ip', 'i', None, "ip to report you have to downloaders."),
    ('file', 's', None, 'file to store state in'),
    ('dfile', 'd', None, 'file to store recent downloader info in'),
    ('bind', None, '', 'ip to bind to locally'),
    ('socket_timeout', None, 30, 'timeout for closing connections'),
    ('save_dfile_interval', None, 5 * 60, 'seconds between saving dfile'),
    ('timeout_downloaders_interval', None, 45 * 60, 'seconds between expiring downloaders'),
    ('reannounce_interval', None, 30 * 60, 'seconds downloaders should wait between reannouncements'),
    ('response_size', None, 25, 'number of peers to send in an info message'),
    ]

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
    ValuesMarker({'ip': string_template, 'port': 1}, exact_length(20))))

alas = 'your file may exist elsewhere in the universe\n\nbut alas, not here'

thanks = (200, 'OK', {'Content-Type': 'text/plain'}, 
    'Thanks! Love, Kerensa.')

class Tracker:
    def __init__(self, config, rawserver):
        self.response_size = config['response_size']
        self.urlprefix = 'http://' + config['ip'] + ':' + str(config['port'])
        self.statefile = config['file']
        self.dfile = config['dfile']
        self.rawserver = rawserver
        self.cached = {}
        self.published = {}
        if exists(self.statefile):
            h = open(self.statefile, 'rb')
            r = h.read()
            h.close()
            self.published = bdecode(r)
            infofiletemplate(self.published)
        self.downloads = {}
        self.times = {}
        if exists(self.dfile):
            h = open(self.dfile, 'rb')
            ds = h.read()
            h.close()
            self.downloads = bdecode(ds)
            downloaderfiletemplate(self.downloads)
            for x in self.downloads.keys():
                self.times[x] = {}
                for y in self.downloads[x].keys():
                    self.times[x][y] = 0
        self.reannounce_interval = config['reannounce_interval']
        self.save_dfile_interval = config['save_dfile_interval']
        rawserver.add_task(self.save_dfile, self.save_dfile_interval)
        self.prevtime = time()
        self.timeout_downloaders_interval = config['timeout_downloaders_interval']
        rawserver.add_task(self.expire_downloaders, self.timeout_downloaders_interval)

    def get(self, connection, path, headers):
        (scheme, netloc, path, pars, query, fragment) = urlparse(path)
        path = unquote(path)[1:]
        params = {}
        for s in query.split('&'):
            if s != '':
                i = s.index('=')
                params[unquote(s[:i])] = unquote(s[i+1:])
        if path == '' or path == 'index.html':
            s = StringIO()
            s.write('<head><title>Published BitTorrent files</title></head>Published BitTorrent files<p>\n')
            names = self.published.keys()
            if names == []:
                s.write('(no files published yet)')
            names.sort()
            for name in names:
                s.write('<a href="' + name + '">' + name + '</a> (' + 
                    str(len(self.downloads.get(name, []))) + ')<p>\n\n')
            return (200, 'OK', {'Content-Type': 'text/html'}, s.getvalue())
        if path == 'announce/':
            try:
                if not params.has_key('file_id'):
                    raise ValueError, 'no file_id'
                fileid = params['file_id']
                if not params.has_key('ip'):
                    raise ValueError, 'no ip'
                print params.get('event')
                if params.get('event', '') not in ['', 'started', 'completed', 'stopped']:
                    raise ValueError, 'invalid event'
                port = long(params.get('port', ''))
                uploaded = long(params.get('uploaded', ''))
                downloaded = long(params.get('downloaded', ''))
                left = long(params.get('left', ''))
                peers = self.downloads.setdefault(fileid, {})
                myid = params.get('peer_id', '')
                if len(myid) != 20:
                    raise ValueError, 'id not of length 20'
            except ValueError, e:
                return (400, 'Bad Request', {'Content-Type': 'text/plain'}, 
                    'you sent me garbage - ' + `e`)
            if params.get('event', '') != 'stopped':
                self.times.setdefault(fileid, {})[myid] = time()
                if not peers.has_key(myid):
                    peers[myid] = {'ip': params['ip'], 'port': port}
            else:
                if peers.has_key(myid):
                    del peers[myid]
                    del self.times[fileid][myid]
            return thanks
        if not self.published.has_key(path):
            return (404, 'Not Found', {'Content-Type': 'text/plain'}, alas)
        data = {'info': self.published[path], 'file id': path, 
            'url': self.urlprefix + path, 
            'announce': self.urlprefix + '/announce/', 'junk': None,
            'your ip': connection.get_ip(), 'interval': self.reannounce_interval}
        if len(self.cached.get(path, [])) < self.response_size:
            self.cached[path] = [{'peer id': key, 'ip': value['ip'], 
                'port': value['port']} for key, value in 
                self.downloads.setdefault(path, {}).items()]
            shuffle(self.cached[path])
        data['peers'] = self.cached[path][-self.response_size:]
        del self.cached[path][-self.response_size:]
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
        self.rawserver.add_task(self.save_dfile, self.save_dfile_interval)
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
        self.rawserver.add_task(self.expire_downloaders, self.timeout_downloaders_interval)

def track(args):
    if len(args) == 0:
        print formatDefinitions(defaults, 80)
    try:
        config, files = parseargs(args, defaults, 0, 0)
    except ValueError, e:
        print 'error: ' + str(e)
        print 'run with no arguments for parameter explanations'
    try:
        h = urlopen('http://bitconjurer.org/BitTorrent/status-tracker-02-08-00.txt')
        status = h.read().strip()
        h.close()
        if status != 'current':
            print 'No longer the latest version - see http://bitconjurer.org/BitTorrent/download.html'
            return
    except IOError, e:
        print "Couldn't check version number - " + str(e)
    r = RawServer(Event(), config['socket_timeout'])
    t = Tracker(config, r)
    r.bind(config['port'], config['bind'])
    r.listen_forever(HTTPHandler(t.get, t.put))


