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
from time import time, gmtime, strftime
from random import shuffle
from sha import sha
from types import StringType, LongType, ListType, DictType
from binascii import b2a_hex
import __init__
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
    ('response_size', None, 50, 'number of peers to send in an info message'),
    ('timeout_check_interval', None, 5,
        'time to wait between checking if any connections have timed out'),
    ('nat_check', None, 1,
        'whether to check back and ban downloaders behind NAT'),
    ('min_time_between_log_flushes', None, 3.0,
        'minimum time it must have been since the last flush to do another one'),
    ('allowed_dir', None, '', 'only allow downloads for .torrents in this dir'),
    ('parse_allowed_interval', None, 15, 'minutes between reloading of allowed_dir'),
    ('show_names', None, 1, 'whether to display names from allowed dir'),
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

def parseTorrents(dir):
    import os
    a = {}
    for f in os.listdir(dir):
        if f[-8:] == '.torrent':
            try:
                d = bdecode(open(os.path.join(dir,f), 'rb').read())
                h = sha(bencode(d['info'])).digest()
                a[h] = d['info'].get('name', f)
            except:
                # what now, boss?
                print "Error parsing " + f
    return a

alas = 'your file may exist elsewhere in the universe\nbut alas, not here\n'

def isotime(secs = None):
    if secs == None:
        secs = time()
    return strftime('%Y-%m-%d %H:%M UTC', gmtime(secs))

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
        self.show_names = config['show_names']
        rawserver.add_task(self.save_dfile, self.save_dfile_interval)
        self.prevtime = time()
        self.timeout_downloaders_interval = config['timeout_downloaders_interval']
        rawserver.add_task(self.expire_downloaders, self.timeout_downloaders_interval)
        if config['allowed_dir'] != '':
            self.allowed_dir = config['allowed_dir']
            self.parse_allowed_interval = config['parse_allowed_interval']
            self.parse_allowed()
        else:
            self.allowed = None

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
            s.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n' \
                '<html><head><title>BitTorrent download info</title></head>\n' \
                '<body>\n' \
                '<h3>BitTorrent download info</h3>\n'\
                '<ul>\n'
                '<li><strong>tracker version:</strong> %s</li>\n' \
                '<li><strong>server time:</strong> %s</li>\n' \
                '</ul>\n' % (__init__.version, isotime()))
            names = self.downloads.keys()
            if names:
                names.sort()
                if self.allowed != None and self.show_names:
                    s.write('<table summary="files" border=1>\n' \
                        '<tr><th>info hash</th><th>torrent name</th><th align="right">complete</th><th align="right">downloading</th></tr>\n')
                else:
                    s.write('<table summary="files">\n' \
                        '<tr><th>info hash</th><th align="right">complete</th><th align="right">downloading</th></tr>\n')
                for name in names:
                    l = self.downloads[name]
                    c = len([1 for i in l.values() if i['left'] == 0])
                    d = len(l) - c
                    if self.allowed != None and self.show_names:
                        if self.allowed.has_key(name):
                            s.write('<tr><td><code>%s</code></td><td><code>%s</code></td><td align="right"><code>%i</code></td><td align="right"><code>%i</code></td></tr>\n' \
                                % (b2a_hex(name), self.allowed[name], c, d))

                    else:
                        s.write('<tr><td><code>%s</code></td><td align="right"><code>%i</code></td><td align="right"><code>%i</code></td></tr>\n' \
                            % (b2a_hex(name), c, d))
                s.write('</table>\n' \
                    '<ul>\n' \
                    '<li><em>info hash:</em> SHA1 hash of the "info" section of the metainfo (*.torrent)</li>\n' \
                    '<li><em>complete:</em> number of connected clients with the complete file</li>\n' \
                    '<li><em>downloading:</em> number of connected clients still downloading</li>\n' \
                    '</ul>\n')
            else:
                s.write('<p>not tracking any files yet...</p>\n')
            s.write('</body>\n' \
                '</html>\n')
            return (200, 'OK', {'Content-Type': 'text/html; charset=iso-8859-1'}, s.getvalue())
        if path == 'scrape':
            names = self.downloads.keys()
            names.sort()
            fs = {}
            for name in names:
                l = self.downloads[name]
                c = len([1 for i in l.values() if i['left'] == 0])
                d = len(l) - c
                fs[name] = {'complete': c, 'incomplete': d}
                if self.allowed is not None and self.allowed.has_key(name):
                    fs[name]['name'] = self.allowed[name]
            r = {'files': fs}
            return (200, 'OK', {'Content-Type': 'text/plain'}, bencode(r))
        if path != 'announce':
            return (404, 'Not Found', {'Content-Type': 'text/plain'}, alas)
        try:
            if not params.has_key('info_hash'):
                raise ValueError, 'no info hash'
            infohash = params['info_hash']
            if self.allowed != None:
                if not self.allowed.has_key(infohash):
                    return (400, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'}, bencode({'failure reason':
                    'Requested download is not authorized for use with this tracker.'}))
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
            rsize = self.response_size
            if params.has_key('num want'):
                rsize = int(params['num want'])
        except ValueError, e:
            return (400, 'Bad Request', {'Content-Type': 'text/plain'}, 
                'you sent me garbage - ' + str(e))
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
        if len(cache) < rsize:
            for key, value in self.downloads.setdefault(
                    infohash, {}).items():
                if not value.get('nat'):
                    cache.append({'peer id': key, 'ip': value['ip'], 
                        'port': value['port']})
            shuffle(cache)
        data['peers'] = cache[-rsize:]
        del cache[-rsize:]
        connection.answer((200, 'OK', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'}, bencode(data)))
        if self.natcheck:
            NatCheck(self.connectback_result, infohash, myid, ip, port, self.rawserver)

    def connectback_result(self, result, downloadid, peerid, ip, port):
        if not result:
            record = self.downloads.get(downloadid, {}).get(peerid)
            if record and record['ip'] == ip and record['port'] == port:
                record['nat'] = 1

    def save_dfile(self):
        self.rawserver.add_task(self.save_dfile, self.save_dfile_interval)
        h = open(self.dfile, 'wb')
        h.write(bencode(self.downloads))
        h.close()

    def parse_allowed(self):
        self.rawserver.add_task(self.parse_allowed, self.parse_allowed_interval * 60)
        self.allowed = parseTorrents(self.allowed_dir)
        
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


