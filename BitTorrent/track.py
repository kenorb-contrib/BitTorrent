# Written by Bram Cohen
# see LICENSE.txt for license information

from parseargs import parseargs, formatDefinitions
from RawServer import RawServer
from HTTPHandler import HTTPHandler
from NatCheck import NatCheck
from threading import Event
from bencode import bencode, bdecode
from urllib import urlopen, quote, unquote
from urlparse import urlparse
from os.path import exists
from cStringIO import StringIO
from traceback import print_exc
from time import time
from random import shuffle
from types import StringType, LongType, ListType, DictType
from binascii import b2a_hex
true = 1
false = 0

defaults = [
    ('port', 'p', 80, "Port to listen on."),
    ('dfile', 'd', None, 'file to store recent downloader info in'),
    ('bind', None, '', 'ip to bind to locally'),
    ('socket_timeout', None, 15, 'timeout for closing connections'),
    ('save_dfile_interval', None, 5 * 60, 'seconds between saving dfile'),
    ('timeout_downloaders_interval', None, 45 * 60, 'seconds between expiring downloaders'),
    ('reannounce_interval', None, 30 * 60, 'seconds downloaders should wait between reannouncements'),
    ('response_size', None, 25, 'number of peers to send in an info message'),
    ('timeout_check_interval', None, 5,
        'time to wait between checking if any connections have timed out'),
    ('nat_check', None, 0,
        'whether to check back and ban downloaders behind NAT'),
    ('min_time_between_log_flushes', None, 3.0,
        'minimum time it must have been since the last flush to do another one'),
    ]

def downloaderfiletemplate(x):
    if type(x) != DictType:
        raise ValueError
    for y in x.values():
        if type(y) != DictType:
            raise ValueError
        for id, info in y.items():
            if len(id) != 20:
                raise ValueError
            if type(info) != DictType:
                raise ValueError
            if type(info.get('ip', '')) != StringType:
                raise ValueError
            port = info.get('port')
            if type(port) != LongType or port <= 0:
                raise ValueError
            left = info.get('left')
            if type(left) != LongType or left < 0:
                raise ValueError

alas = 'your file may exist elsewhere in the universe\n\nbut alas, not here'

class Tracker:
    def __init__(self, config, rawserver):
        self.response_size = config['response_size']
        self.dfile = config['dfile']
        self.natcheck = config['nat_check']
        self.rawserver = rawserver
        self.cached = {}
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
        try:
            (scheme, netloc, path, pars, query, fragment) = urlparse(path)
            path = unquote(path)[1:]
            params = {}
            for s in query.split('&'):
                if s != '':
                    i = s.index('=')
                    params[unquote(s[:i])] = unquote(s[i+1:])
        except ValueError, e:
            return (400, 'Bad Request', {'Content-Type': 'text/plain'}, 
                    'you sent me garbage - ' + str(e))
        if path == '' or path == 'index.html':
            s = StringIO()
            s.write('<head><title>BitTorrent download info</title></head>BitTorrent download info<p>\n')
            names = self.downloads.keys()
            if names == []:
                s.write('(not tracking any files yet)')
            names.sort()
            for name in names:
                l = self.downloads[name]
                s.write(b2a_hex(name) + ' (' + str(len([1 for i in 
                    l.values() if i['left'] == 0])) + '/' + 
                    str(len(l)) + ')<p>\n\n')
            return (200, 'OK', {'Content-Type': 'text/html'}, s.getvalue())
        if path != 'announce':
            return (404, 'Not Found', {'Content-Type': 'text/plain'}, alas)
        try:
            if not params.has_key('info_hash'):
                raise ValueError, 'no info hash'
            infohash = params['info_hash']
            ip = connection.get_ip()
            if params.has_key('ip'):
                ip = params['ip']
            if params.has_key('event') and params['event'] not in ['started', 'completed', 'stopped']:
                raise ValueError, 'invalid event'
            port = long(params.get('port', ''))
            uploaded = long(params.get('uploaded', ''))
            downloaded = long(params.get('downloaded', ''))
            left = long(params.get('left', ''))
            myid = params.get('peer_id', '')
            if len(myid) != 20:
                raise ValueError, 'id not of length 20'
        except ValueError, e:
            return (400, 'Bad Request', {'Content-Type': 'text/plain'}, 
                'you sent me garbage - ' + str(e))
        def respond(result, self = self, infohash = infohash, myid = myid,
                ip = ip, port = port, left = left, params = params,
                connection = connection):
            if not result:
                connection.answer((200, 'OK', {}, bencode({'failure reason':
                    'You are behind NAT. Please open port 6881 or download from elsewhere'})))
                return
            peers = self.downloads.setdefault(infohash, {})
            ts = self.times.setdefault(infohash, {})
            if params.get('event', '') != 'stopped':
                ts[myid] = time()
                if not peers.has_key(myid):
                    peers[myid] = {'ip': ip, 'port': port, 'left': left}
                else:
                    peers[myid]['left'] = left
            else:
                if peers.has_key(myid) and peers[myid]['ip'] == ip:
                    del peers[myid]
                    del ts[myid]
            data = {'interval': self.reannounce_interval}
            cache = self.cached.setdefault(infohash, [])
            if len(cache) < self.response_size:
                for key, value in self.downloads.setdefault(
                        infohash, {}).items():
                    cache.append({'peer id': key, 'ip': value['ip'], 
                        'port': value['port']})
                shuffle(cache)
            data['peers'] = cache[-self.response_size:]
            del cache[-self.response_size:]
            connection.answer((200, 'OK', {'Pragma': 'no-cache'}, bencode(data)))
        if (not self.natcheck or params.get('event') == 'stopped' or
                self.downloads.get(infohash, {}).has_key(myid)):
            respond(true)
        else:
            NatCheck(respond, infohash, myid, ip, port, self.rawserver)

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
        for key, value in self.downloads.items():
            if len(value) == 0:
                del self.times[key]
                del self.downloads[key]
        self.rawserver.add_task(self.expire_downloaders, self.timeout_downloaders_interval)

def track(args):
    if len(args) == 0:
        print formatDefinitions(defaults, 80)
        return
    try:
        config, files = parseargs(args, defaults, 0, 0)
    except ValueError, e:
        print 'error: ' + str(e)
        print 'run with no arguments for parameter explanations'
        return
    r = RawServer(Event(), config['timeout_check_interval'], config['socket_timeout'])
    t = Tracker(config, r)
    r.bind(config['port'], config['bind'], true)
    r.listen_forever(HTTPHandler(t.get, config['min_time_between_log_flushes']))
    t.save_dfile()


