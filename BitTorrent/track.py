# Written by Bram Cohen
# see LICENSE.txt for license information

from parseargs import parseargs, formatDefinitions
from RawServer import RawServer, autodetect_ipv6, autodetect_socket_style
from HTTPHandler import HTTPHandler
from NatCheck import NatCheck
from T2T import T2TList
from subnetparse import IP_List, to_ipv4
from threading import Event, Thread
from bencode import bencode, bdecode, Bencached
from zurllib import urlopen, quote, unquote
from urlparse import urlparse
from os import rename, getpid
from os.path import exists, isfile
from cStringIO import StringIO
from traceback import print_exc
from time import time, gmtime, strftime, localtime
from random import shuffle, seed, randrange
from sha import sha
from types import StringType, LongType, ListType, DictType
from binascii import b2a_hex, a2b_hex, a2b_base64
from string import lower
import sys, os
import signal
import __init__
from __init__ import version, createPeerID
true = 1
false = 0

NOISY = false

defaults = [
    ('port', 80, "Port to listen on."),
    ('dfile', None, 'file to store recent downloader info in'),
    ('bind', '', 'comma-separated list of ips/hostnames to bind to locally'),
#    ('ipv6_enabled', autodetect_ipv6(),
    ('ipv6_enabled', 0,
         'allow the client to connect to peers via IPv6'),
    ('ipv6_binds_v4', autodetect_socket_style(),
        'set if an IPv6 server socket will also field IPv4 connections'),
    ('socket_timeout', 15, 'timeout for closing connections'),
    ('save_dfile_interval', 5 * 60, 'seconds between saving dfile'),
    ('timeout_downloaders_interval', 45 * 60, 'seconds between expiring downloaders'),
    ('reannounce_interval', 30 * 60, 'seconds downloaders should wait between reannouncements'),
    ('response_size', 50, 'number of peers to send in an info message'),
    ('timeout_check_interval', 5,
        'time to wait between checking if any connections have timed out'),
    ('nat_check', 3,
        "how many times to check if a downloader is behind a NAT (0 = don't check)"),
    ('log_nat_checks', 0,
        "whether to add entries to the log for nat-check results"),
    ('min_time_between_log_flushes', 3.0,
        'minimum time it must have been since the last flush to do another one'),
    ('min_time_between_cache_refreshes', 60.0,
        'minimum time in seconds before a cache is considered stale and is flushed'),
    ('allowed_dir', '', 'only allow downloads for .torrents in this dir'),
    ('allowed_controls', 0, 'allow special keys in torrents in the allowed_dir to affect tracker access'),
    ('multitracker_enabled', 0, 'whether to enable multitracker operation'),
    ('multitracker_allowed', 'autodetect', 'whether to allow incoming tracker announces (can be none, autodetect or all)'),
    ('multitracker_reannounce_interval', 2 * 60, 'seconds between outgoing tracker announces'),
    ('multitracker_maxpeers', 20, 'number of peers to get in a tracker announce'),
    ('aggregate_forward', '', 'format: <url>[,<password>] - if set, forwards all non-multitracker to this url with this optional password'),
    ('aggregator', '0', 'whether to act as a data aggregator rather than a tracker.  If enabled, may be 1, or <password>; ' +
             'if password is set, then an incoming password is required for access'),
    ('hupmonitor', 0, 'whether to reopen the log file upon receipt of HUP signal'),
    ('http_timeout', 60, 
        'number of seconds to wait before assuming that an http connection has timed out'),
    ('parse_allowed_interval', 1, 'minutes between reloading of allowed_dir'),
    ('show_infopage', 1, "whether to display an info page when the tracker's root dir is loaded"),
    ('infopage_redirect', '', 'a URL to redirect the info page to'),
    ('show_names', 1, 'whether to display names from allowed dir'),
    ('favicon', '', 'file containing x-icon data to return when browser requests favicon.ico'),
    ('allowed_ips', '', 'only allow connections from IPs specified in the given file; '+
             'file contains subnet data in the format: aa.bb.cc.dd/len'),
    ('only_local_override_ip', 1, "ignore the ip GET parameter from machines which aren't on local network IPs"),
    ('logfile', '', 'file to write the tracker logs, use - for stdout (default)'),
    ('allow_get', 0, 'use with allowed_dir; adds a /file?hash={hash} url that allows users to download the torrent file'),
    ('keep_dead', 0, 'keep dead torrents after they expire (so they still show up on your /scrape and web page)'),
    ('scrape_allowed', 'full', 'scrape access allowed (can be none, specific or full)')
  ]

def statefiletemplate(x):
    if type(x) != DictType:
        raise ValueError
    for cname, cinfo in x.items():
        if cname == 'peers':
            for y in cinfo.values():      # The 'peers' key is a dictionary of SHA hashes (torrent ids)
                 if type(y) != DictType:   # ... for the active torrents, and each is a dictionary
                     raise ValueError
                 for id, info in y.items(): # ... of client ids interested in that torrent
                     if (len(id) != 20):
                         raise ValueError
                     if type(info) != DictType:  # ... each of which is also a dictionary
                         raise ValueError # ... which has an IP, a Port, and a Bytes Left count for that client for that torrent
                     if type(info.get('ip', '')) != StringType:
                         raise ValueError
                     port = info.get('port')
                     if type(port) != LongType or port < 0:
                         raise ValueError
                     left = info.get('left')
                     if type(left) != LongType or left < 0:
                         raise ValueError
        elif cname == 'completed':
            if (type(cinfo) != DictType): # The 'completed' key is a dictionary of SHA hashes (torrent ids)
                raise ValueError          # ... for keeping track of the total completions per torrent
            for y in cinfo.values():      # ... each torrent has an integer value
                if type(y) != LongType:   # ... for the number of reported completions for that torrent
                    raise ValueError
        elif cname == 'allowed':
            if (type(cinfo) != DictType): # a list of info_hashes and included data
                raise ValueError
            if x.has_key('allowed_dir_files'):
                adlist = [z[1] for z in x['allowed_dir_files'].values()]
                for y in cinfo.keys():        # and each should have a corresponding key here
                    if not y in adlist:
                        raise ValueError
        elif cname == 'allowed_dir_files':
            if (type(cinfo) != DictType): # a list of files, their attributes and info hashes
                raise ValueError
            dirkeys = {}
            for y in cinfo.values():      # each entry should have a corresponding info_hash
                if not y[1]:
                    continue
                if not x['allowed'].has_key(y[1]):
                    raise ValueError
                if dirkeys.has_key(y[1]): # and each should have a unique info_hash
                    raise ValueError
                dirkeys[y[1]] = 1
            

alas = 'your file may exist elsewhere in the universe\nbut alas, not here\n'

def isotime(secs = None):
    if secs == None:
        secs = time()
    return strftime('%Y-%m-%d %H:%M UTC', gmtime(secs))

class Tracker:
    def __init__(self, config, rawserver):
        self.config = config
        self.response_size = config['response_size']
        self.dfile = config['dfile']
        self.natcheck = config['nat_check']
        favicon = config['favicon']
        if favicon and (favicon != '') and isfile(favicon):
            self.favicon = open(favicon,'r').read()
        else:
            if favicon and (favicon != ''):
                print "**warning** specified favicon file -- %s -- does not exist." % favicon
            self.favicon = None
        self.rawserver = rawserver
        self.cached = {}    # format: infohash: [time, [l1, s1], [l2, s2]]
        self.cached_t = {}  # format: infohash: [time, cache]
        self.times = {}
        self.state = {}
        if exists(self.dfile):
            try:
                h = open(self.dfile, 'rb')
                ds = h.read()
                h.close()
                tempstate = bdecode(ds)
                if not tempstate.has_key('peers'):
                    tempstate = {'peers': tempstate}
                statefiletemplate(tempstate)
                self.state = tempstate
            except:
                print '**warning** statefile '+self.dfile+' corrupt; resetting'
        self.downloads    = self.state.setdefault('peers', {})
        self.completed    = self.state.setdefault('completed', {})

        self.becache = {}   # format: infohash: [0, [l1, s1], [l2, s2]]
        for infohash, ds in self.downloads.items():
            bc = self.becache.setdefault(infohash,[0, [{}, {}], [{}, {}]])
            bc1_l = bc[1][0]
            bc1_s = bc[1][1]
            bc2_l = bc[2][0]
            bc2_s = bc[2][1]
            for x,y in ds.items():
                if not y.get('nat',-1):
                    if y['left']:
                        bc1_l[x] = Bencached(bencode({'ip': y['ip'], 'port': y['port'], 'peer id': x}))
                        bc2_l[x] = Bencached(bencode({'ip': y['ip'], 'port': y['port']}))
                    else:
                        bc1_s[x] = Bencached(bencode({'ip': y['ip'], 'port': y['port'], 'peer id': x}))
                        bc2_s[x] = Bencached(bencode({'ip': y['ip'], 'port': y['port']}))
            
        for x in self.downloads.keys():
            self.times[x] = {}
            for y in self.downloads[x].keys():
                self.times[x][y] = 0

        self.trackerid = createPeerID('-T-')
        seed(self.trackerid)
                
        self.reannounce_interval = config['reannounce_interval']
        self.save_dfile_interval = config['save_dfile_interval']
        self.show_names = config['show_names']
        rawserver.add_task(self.save_dfile, self.save_dfile_interval)
        self.prevtime = time()
        self.timeout_downloaders_interval = config['timeout_downloaders_interval']
        rawserver.add_task(self.expire_downloaders, self.timeout_downloaders_interval)
        self.logfile = None
        self.log = None
        if (config['logfile'] != '') and (config['logfile'] != '-'):
            try:
                self.logfile = config['logfile']
                self.log = open(self.logfile,'a')
                sys.stdout = self.log
                print "# Log Started: ", isotime()
            except:
                print "**warning** could not redirect stdout to log file: ", sys.exc_info()[0]

        if config['hupmonitor']:
            def huphandler(signum, frame, self = self):
                try:
                    self.log.close ()
                    self.log = open(self.logfile,'a')
                    sys.stdout = self.log
                    print "# Log reopened: ", isotime()
                except:
                    print "**warning** could not reopen logfile"
             
            signal.signal(signal.SIGHUP, huphandler)            
                
        self.allow_get = config['allow_get']
        
        self.t2tlist = T2TList(config['multitracker_enabled'], self.trackerid,
                               config['multitracker_reannounce_interval'],
                               config['multitracker_maxpeers'], config['http_timeout'],
                               self.rawserver)
        if config['allowed_dir'] != '':
            self.allowed_dir = config['allowed_dir']
            self.parse_allowed_interval = config['parse_allowed_interval']
            self.allowed = self.state.setdefault('allowed',{})
            self.allowed_dir_files = self.state.setdefault('allowed_dir_files',{})
            self.parse_allowed()
        else:
            try:
                del self.state['allowed']
            except:
                pass
            try:
                del self.state['allowed_dir_files']
            except:
                pass
            self.allowed = None
            if config['multitracker_allowed'] == 'autodetect':
                config['multitracker_allowed'] = 'none'
                
        self.uq_broken = unquote('+') != ' '
        self.keep_dead = config['keep_dead']
        
        aggregator = config['aggregator']
        if aggregator == '0':
            self.is_aggregator = false
            self.aggregator_key = None
        else:
            self.is_aggregator = true
            if aggregator == '1':
                self.aggregator_key = None
            else:
                self.aggregator_key = aggregator
            self.natcheck = false
                
        send = config['aggregate_forward']
        if send == '':
            self.aggregate_forward = None
        else:
            try:
                self.aggregate_forward, self.aggregate_password = send.split(',')
            except:
                self.aggregate_forward = send
                self.aggregate_password = None

        self.allowed_IPs = IP_List()
        if config['allowed_ips'] != '':
            self.allowed_IPs.read_fieldlist(config['allowed_ips'])
        self.overridable_IPs = IP_List()
        if config['only_local_override_ip']:
            self.overridable_IPs.set_intranet_addresses()
            

    def aggregate_senddata(self, query):
        url = self.aggregate_forward+'?'+query
        if self.aggregate_password is not None:
            url += '&password='+self.aggregate_password
        rq = Thread(target = self._aggregate_senddata, args = [url])
        rq.setDaemon(false)
        rq.start()

    def _aggregate_senddata(self, url):     # just send, don't attempt to error check,
        try:                                # discard any returned data
            h = urlopen(url)
            h.read()
            h.close()
        except:
            return


    def get_infopage(self):
        if not self.config['show_infopage']:
            return (404, 'Not Found', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'}, alas)
        red = self.config['infopage_redirect']
        if red != '':
            return (302, 'Found', {'Content-Type': 'text/html', 'Location': red},
                    '<A HREF="'+red+'">Click Here</A>')
        
        s = StringIO()
        s.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n' \
            '<html><head><title>BitTorrent download info</title>\n')
        if self.favicon != None:
            s.write('<link rel="shortcut icon" href="/favicon.ico">\n')
        s.write('</head>\n<body>\n' \
            '<h3>BitTorrent download info</h3>\n'\
            '<ul>\n'
            '<li><strong>tracker version:</strong> %s</li>\n' \
            '<li><strong>server time:</strong> %s</li>\n' \
            '</ul>\n' % (version, isotime()))
        names = self.downloads.keys()
        if not names:
            s.write('<p>not tracking any files yet...</p>\n')
        else:
            names.sort()
            tn = 0
            tc = 0
            td = 0
            tt = 0  # Total transferred
            ts = 0  # Total size
            nf = 0  # Number of files displayed
            uc = {}
            ud = {}
            if self.allowed != None and self.show_names:
                s.write('<table summary="files" border="1">\n' \
                    '<tr><th>info hash</th><th>torrent name</th><th align="right">size</th><th align="right">complete</th><th align="right">downloading</th><th align="right">downloaded</th><th align="right">transferred</th></tr>\n')
            else:
                s.write('<table summary="files">\n' \
                    '<tr><th>info hash</th><th align="right">complete</th><th align="right">downloading</th><th align="right">downloaded</th></tr>\n')
            for name in names:
                l = self.downloads[name]
                n = self.completed.get(name, 0)
                tn = tn + n
                lc = []
                for i in l.values():
                    if i['left'] == 0:
                        lc.append(1)
                        uc[i['ip']] = 1
                    else:
                        ud[i['ip']] = 1
                c = len(lc)
                tc = tc + c
                d = len(l) - c
                td = td + d
                if self.allowed != None and self.show_names:
                    if self.allowed.has_key(name):
                        nf = nf + 1
                        sz = self.allowed[name]['length']  # size
                        ts = ts + sz
                        szt = sz * n   # Transferred for this torrent
                        tt = tt + szt
                        if self.allow_get == 1:
                            linkname = '<a href="/file?info_hash=' + quote(name) + '">' + self.allowed[name]['name'] + '</a>'
                        else:
                            linkname = self.allowed[name]['name']
                        s.write('<tr><td><code>%s</code></td><td>%s</td><td align="right">%s</td><td align="right">%i</td><td align="right">%i</td><td align="right">%i</td><td align="right">%s</td></tr>\n' \
                            % (b2a_hex(name), linkname, size_format(sz), c, d, n, size_format(szt)))
                else:
                    s.write('<tr><td><code>%s</code></td><td align="right"><code>%i</code></td><td align="right"><code>%i</code></td><td align="right"><code>%i</code></td></tr>\n' \
                        % (b2a_hex(name), c, d, n))
            ttn = 0
            for i in self.completed.values():
                ttn = ttn + i
            if self.allowed != None and self.show_names:
                s.write('<tr><td align="right" colspan="2">%i files</td><td align="right">%s</td><td align="right">%i/%i</td><td align="right">%i/%i</td><td align="right">%i/%i</td><td align="right">%s</td></tr>\n'
                        % (nf, size_format(ts), len(uc), tc, len(ud), td, tn, ttn, size_format(tt)))
            else:
                s.write('<tr><td align="right">%i files</td><td align="right">%i/%i</td><td align="right">%i/%i</td><td align="right">%i/%i</td></tr>\n'
                        % (nf, len(uc), tc, len(ud), td, tn, ttn))
            s.write('</table>\n' \
                '<ul>\n' \
                '<li><em>info hash:</em> SHA1 hash of the "info" section of the metainfo (*.torrent)</li>\n' \
                '<li><em>complete:</em> number of connected clients with the complete file (total: unique IPs/total connections)</li>\n' \
                '<li><em>downloading:</em> number of connected clients still downloading (total: unique IPs/total connections)</li>\n' \
                '<li><em>downloaded:</em> reported complete downloads (total: current/all)</li>\n' \
                '<li><em>transferred:</em> torrent size * total downloaded (does not include partial transfers)</li>\n' \
                '</ul>\n')

        s.write('</body>\n' \
            '</html>\n')
        return (200, 'OK', {'Content-Type': 'text/html; charset=iso-8859-1'}, s.getvalue())


    def scrapedata(self, name, return_name = true):        
        l = self.downloads[name]
        n = self.completed.get(name, 0)
        c = len([1 for i in l.values() if i['left'] == 0])
        d = len(l) - c
        f = {'complete': c, 'incomplete': d, 'downloaded': n}
        if return_name and self.allowed is not None and self.allowed.has_key(name):
            f['name'] = self.allowed[name]['name']
        return (f)

    def get_scrape(self, paramslist):
        fs = {}
        if paramslist.has_key('info_hash'):
            if self.config['scrape_allowed'] not in ['specific', 'full']:
                return (400, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                    bencode({'failure reason':
                    'specific scrape function is not available with this tracker.'}))
            for infohash in paramslist['info_hash']:
                if infohash in self.downloads.keys():
                    fs[infohash] = self.scrapedata(infohash)
        else:
            if self.config['scrape_allowed'] != 'full':
                return (400, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                    bencode({'failure reason':
                    'full scrape function is not available with this tracker.'}))
            names = self.downloads.keys()
            names.sort()
            for name in names:
                fs[name] = self.scrapedata(name)

        return (200, 'OK', {'Content-Type': 'text/plain'}, bencode({'files': fs}))


    def get_file(self, hash):
         if not self.allow_get:
             return (400, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                 'get function is not available with this tracker.')
         if not self.allowed.has_key(hash):
             return (404, 'Not Found', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'}, alas)
         fname = self.allowed[hash]['file']
         fpath = self.allowed[hash]['path']
         return (200, 'OK', {'Content-Type': 'application/x-bittorrent',
             'Content-Disposition': 'attachment; filename=' + fname},
             open(fpath, 'rb').read())


    def check_allowed(self, infohash, paramslist):
        if ( self.aggregator_key is not None
                and not ( paramslist.has_key('password')
                        and paramslist['password'][0] == self.aggregator_key ) ):
            return (200, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                bencode({'failure reason':
                'Requested download is not authorized for use with this tracker.'}))

        if self.allowed is not None:
            if not self.allowed.has_key(infohash):
                return (200, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                    bencode({'failure reason':
                    'Requested download is not authorized for use with this tracker.'}))
            if self.config['allowed_controls']:
                if self.allowed[infohash].has_key('failure reason'):
                    return (200, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                        bencode({'failure reason': self.allowed[infohash]['failure reason']}))

        if paramslist.has_key('tracker'):
            if ( self.config['multitracker_allowed'] == 'none' or       # turned off
                          paramslist['peer_id'][0] == self.trackerid ): # oops! contacted myself
                return (200, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                    bencode({'failure reason': 'disallowed'}))
            
            if ( self.config['multitracker_allowed'] == 'autodetect'
                        and not self.allowed[infohash].has_key('multitracker') ):
                return (200, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                    bencode({'failure reason':
                    'Requested download is not authorized for multitracker use.'}))

        return None


    def add_data(self, infohash, event, ip, paramslist):
        peers = self.downloads.setdefault(infohash, {})
        ts = self.times.setdefault(infohash, {})
        self.completed.setdefault(infohash, 0)

        def params(key, retval = None, list = paramslist):
            if list.has_key(key):
                return list[key][0]
            return retval
        
        myid = params('peer_id','')
        if len(myid) != 20:
            raise ValueError, 'id not of length 20'
        if event not in ['started', 'completed', 'stopped', 'snooped', None]:
            raise ValueError, 'invalid event'
        port = long(params('port',''))
        if port < 0:
            raise ValueError, 'invalid port'
        left = long(params('left',''))
        if left < 0:
            raise ValueError, 'invalid amount left'
        uploaded = long(params('uploaded',''))
        downloaded = long(params('downloaded',''))

        peer = peers.get(myid)

        if ( params('ip') is not None and (not peers.has_key(myid) or event == 'stopped')
                 and (not self.overridable_IPs or self.overridable_IPs.includes(ip)) ):
            ip = params('ip')

        if params('numwant') is not None:
            rsize = min(int(params('numwant')),self.response_size)
        else:
            rsize = self.response_size

        if event == 'stopped':
            if peer and peer['ip'] == ip:
                del peers[myid]
                del ts[myid]
                if not peer.get('nat', 1):
                    bc = self.becache[infohash]
                    if peer['left']:
                        del bc[1][0][myid]
                        del bc[2][0][myid]
                    else:
                        del bc[1][1][myid]
                        del bc[2][1][myid]
        else:
            ts[myid] = time()
            if not peer:
                peer = {'ip': ip, 'port': port, 'left': left}
                peers[myid] = peer
                if port:
                    if not self.natcheck:
                        peer['nat'] = 0
                        self.natcheckOK(infohash,myid,ip,port,left)
                else:
                    peer['nat'] = 2**30
            elif peer['ip'] != ip:
                return rsize
            else:
                if not left and peer['left'] and not peer.get('nat', -1):
                    for bc in self.becache[infohash][1:]:
                        bc[1][myid] = bc[0][myid]
                        del bc[0][myid]
                if peer['left']:
                    peer['left'] = left
                
            if event == 'completed':
                self.completed[infohash] += 1
                
            if port and self.natcheck:
                to_nat = peer.get('nat', -1)
                if to_nat and to_nat < self.natcheck:
                    NatCheck(self.connectback_result, infohash, myid, ip, port, self.rawserver)

        return rsize


    def peerlist(self, infohash, stopped, tracker, is_seed, no_peer_id, rsize):
        data = {}    # return data
        
        if ( self.allowed is not None and self.config['allowed_controls'] and
                                self.allowed[infohash].has_key('warning message') ):
            data['warning message'] = self.allowed[infohash]['warning message']

        if tracker:
            data['interval'] = self.config['multitracker_reannounce_interval']
            if not rsize:
                return data
            cache = self.cached_t.setdefault(infohash, None)
            if ( not cache or len(cache[1]) < rsize
                 or cache[0] + self.config['min_time_between_cache_refreshes'] < time() ):
                bc = self.becache.setdefault(infohash,[0, [{}, {}], [{}, {}]])
                cache = [ time(), bc[1][0].values() + bc[1][1].values() ]
                self.cached_t[infohash] = cache
                shuffle(cache[1])
                cache = cache[1]

            data['peers'] = cache[-rsize:]
            del cache[-rsize:]
            return data

        data['interval'] = self.reannounce_interval
        if stopped or not rsize:     # save some bandwidth
            data['peers'] = []
            return data

        bc = self.becache.setdefault(infohash,[0, [{}, {}], [{}, {}]])
        len_l = len(bc[1][0])
        len_s = len(bc[1][1])
        if not (len_l+len_s):   # caches are empty!
            data['peers'] = []
            return data
        l_get_size = int(float(rsize)*(len_l)/(len_l+len_s))
        cache = self.cached.setdefault(infohash, None)
        if cache:
            if cache[0] + self.config['min_time_between_cache_refreshes'] < time():
                cache = None
            else:
                if no_peer_id:
                    cache_l = cache[2][0]
                    cache_s = cache[2][1]
                else:
                    cache_l = cache[1][0]
                    cache_s = cache[1][1]

                if ( (is_seed and len(cache_l) < rsize)
                     or len(cache_l) < l_get_size or not l_get_size ):
                        cache = None
        if not cache:
            cache = [ time(),
                      [ bc[1][0].values(), bc[1][1].values() ],
                      [ bc[2][0].values(), bc[2][1].values() ] ]
            self.cached[infohash] = cache
            cache_l1 = cache[1][0]
            cache_l2 = cache[2][0]
            peers = self.downloads[infohash]
            v1 = []
            v2 = []
            for key, ip, port in self.t2tlist.harvest(infohash):   # empty if disabled
                if not peers.has_key(key):
                    v1.append({'ip': ip, 'port': port, 'peer id': key})
                    v2.append({'ip': ip, 'port': port})
            if len(cache_l1) >= 2*l_get_size:
                cache_l1.extend(v1)
                shuffle(cache_l1)
                cache_l2.extend(v2)
                shuffle(cache_l2)
            else:
                shuffle(cache_l1)
                cache_l1.extend(v1)
                shuffle(cache_l2)
                cache_l2.extend(v2)
            shuffle(cache[1][1])
            shuffle(cache[2][1])
            if no_peer_id:
                cache_l = cache[2][0]
                cache_s = cache[2][1]
            else:
                cache_l = cache[1][0]
                cache_s = cache[1][1]

        if len(cache_l) < l_get_size:
            peerdata = cache_l+cache_s
            del cache_l[:]
            del cache_s[:]
        else:
            if not is_seed:
                peerdata = cache_s[l_get_size-rsize:]
                del cache_s[l_get_size-rsize:]
                rsize -= len(peerdata)
            else:
                peerdata = []
            if rsize:
                peerdata.extend(cache_l[-rsize:])
                del cache_l[-rsize:]
        data['peers'] = peerdata
        return data


    def get(self, connection, path, headers):
        ip = connection.get_ip()
        try:
            ip = to_ipv4(ip)
        except ValueError:
            pass

        if self.allowed_IPs and not self.allowed_IPs.includes(ip):
            return (400, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                bencode({'failure reason':
                'your IP is not allowed on this tracker'}))

        paramslist = {}
        def params(key, retval = None, list = paramslist):
            if list.has_key(key):
                return list[key][0]
            return retval

        try:
            (scheme, netloc, path, pars, query, fragment) = urlparse(path)
            if self.uq_broken == 1:
                path = path.replace('+',' ')
                query = query.replace('+',' ')
            path = unquote(path)[1:]
            for s in query.split('&'):
                if s != '':
                    i = s.index('=')
                    kw = unquote(s[:i])
                    paramslist.setdefault(kw, [])
                    paramslist[kw] += [unquote(s[i+1:])]
                    
            if path == '' or path == 'index.html':
                return self.get_infopage()
            if path == 'scrape':
                return self.get_scrape(paramslist)
            if (path == 'file'):
                return self.get_file(params('info_hash'))
            if path == 'favicon.ico' and self.favicon != None:
                return (200, 'OK', {'Content-Type' : 'image/x-icon'}, self.favicon)
            if path != 'announce':
                return (404, 'Not Found', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'}, alas)

            # main tracker function
            infohash = params('info_hash')
            if not infohash:
                raise ValueError, 'no info hash'

            notallowed = self.check_allowed(infohash, paramslist)
            if notallowed:
                return notallowed

            event = params('event')

            rsize = self.add_data(infohash, event, ip, paramslist)

        except ValueError, e:
            return (400, 'Bad Request', {'Content-Type': 'text/plain'}, 
                'you sent me garbage - ' + str(e))

        if self.aggregate_forward and not paramslist.has_key('tracker'):
            self.aggregate_senddata(query)

        if self.is_aggregator:      # don't return peer data here
            return (200, 'OK', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                    bencode({'response': 'OK'}))

        data = self.peerlist(infohash, event=='stopped',
                             params('tracker'), not params('left'),
                             params('no_peer_id'), rsize)

        if paramslist.has_key('scrape'):
            data['scrape'] = self.scrapedata(infohash, false)
            
        return (200, 'OK', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'}, bencode(data))


    def natcheckOK(self, infohash, peerid, ip, port, not_seed):
        bc = self.becache.setdefault(infohash,[0, [{}, {}], [{}, {}]])
        if not_seed:
            bc[1][0][peerid] = Bencached(bencode({'ip': ip, 'port': port,
                                                  'peer id': peerid}))
            bc[2][0][peerid] = Bencached(bencode({'ip': ip, 'port': port}))
        else:
            bc[1][1][peerid] = Bencached(bencode({'ip': ip, 'port': port,
                                                  'peer id': peerid}))
            bc[2][1][peerid] = Bencached(bencode({'ip': ip, 'port': port}))


    def natchecklog(self, peerid, ip, port, result):
        year, month, day, hour, minute, second, a, b, c = localtime(time())
        print '%s - %s [%02d/%3s/%04d:%02d:%02d:%02d] "!natcheck-%s:%i" %i 0 - -' % (
            ip, peerid, day, months[month], year, hour, minute, second,
            ip, port, result)

    def connectback_result(self, result, downloadid, peerid, ip, port):
        record = self.downloads.get(downloadid, {}).get(peerid)
        if record is None or record['ip'] != ip or record['port'] != port:
            if self.config['log_nat_checks']:
                self.natchecklog(peerid, ip, port, 404)
            return
        if self.config['log_nat_checks']:
            if result:
                x = 200
            else:
                x = 503
            self.natchecklog(peerid, ip, port, x)
        if not record.has_key('nat'):
            record['nat'] = int(not result)
            if result:
                self.natcheckOK(downloadid,peerid,ip,port,record['left'])
        elif result and record['nat']:
            record['nat'] = 0
            self.natcheckOK(downloadid,peerid,ip,port,record['left'])
        elif not result:
            record['nat'] += 1


    def save_dfile(self):
        self.rawserver.add_task(self.save_dfile, self.save_dfile_interval)
        h = open(self.dfile, 'wb')
        h.write(bencode(self.state))
        h.close()

    def parse_allowed(self):
        self.rawserver.add_task(self.parse_allowed, self.parse_allowed_interval * 60)

        if NOISY:
            print ':: checking allowed_dir'
        dirs_to_check = [self.allowed_dir]
        new_allowed_dir_files = {}
        while dirs_to_check:
            dir = dirs_to_check.pop()
            newtorrents = false
            for f in os.listdir(dir):
                if f[-8:] == '.torrent':
                    newtorrents = true
                    p = os.path.join(dir,f)
                    new_allowed_dir_files[p] = [os.path.getmtime(p), os.path.getsize(p)]
            if not newtorrents:
                for f in os.listdir(dir):
                    p = os.path.join(dir,f)
                    if os.path.isdir(p):
                        dirs_to_check.append(p)
            # first, find new torrents
        new_allowed = {}
        for p,v in new_allowed_dir_files.items():
            result = self.allowed_dir_files.get(p)
            if result and result[0] == v and result[1]:
                new_allowed_dir_files[p] = result
                new_allowed[result[1]] = self.allowed[result[1]]
                continue
            if NOISY:
                print ':: adding '+p
            result = [v, 0]
            new_allowed_dir_files[p] = result
            try:
                ff = open(p, 'rb')
                d = bdecode(ff.read())
                ff.close()
                i = d['info']
                h = sha(bencode(i)).digest()
                if new_allowed.has_key(h):
                    print '**warning** '+p+' is a duplicate torrent for '+new_allowed[h]['path']
                    continue
                a = {}
                l = 0
                nf = 0
                if i.has_key('length'):
                    l = i.get('length',0)
                    nf = 1
                elif i.has_key('files'):
                    for li in i['files']:
                        nf += 1
                        if li.has_key('length'):
                            l += li['length']
                a['numfiles'] = nf
                a['length'] = l
                f = os.path.basename(p)
                a['name'] = d['info'].get('name', f)
                a['file'] = f
                a['path'] = p
                def setkey(k, d = d, a = a):
                    if d.has_key(k):
                        a[k] = d[k]
                    elif a.has_key(k):
                        del a[k]
                setkey('failure reason')
                setkey('warning message')
                setkey('announce-list')
                new_allowed_dir_files[p][1] = h
                new_allowed[h] = a
                if NOISY:
                    print '::    -- successful'
            except:
                print '**warning** '+p+' has errors'

        self.allowed = new_allowed
        self.state['allowed'] = new_allowed
        self.allowed_dir_files = new_allowed_dir_files
        self.state['allowed_dir_files'] = new_allowed_dir_files

        self.t2tlist.parse(self.allowed)

        
    def expire_downloaders(self):
        for x in self.times.keys():
            for myid, t in self.times[x].items():
                if t < self.prevtime:
                    del self.times[x][myid]
                    if not self.downloads[x][myid].get('nat', 1):
                        bc = self.becache[x]
                        if self.downloads[x][myid]['left']:
                            del bc[1][0][myid]
                            del bc[2][0][myid]
                        else:
                            del bc[1][1][myid]
                            del bc[2][1][myid]
                    del self.downloads[x][myid]
        self.prevtime = time()
        if (self.keep_dead != 1):
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
    r = RawServer(Event(), config['timeout_check_interval'],
                  config['socket_timeout'], ipv6_enable = config['ipv6_enabled'])
    t = Tracker(config, r)
    r.bind(config['port'], config['bind'],
           reuse = true, ipv6_socket_style = config['ipv6_binds_v4'])
    r.listen_forever(HTTPHandler(t.get, config['min_time_between_log_flushes']))
    t.save_dfile()
    print '# Shutting down: ' + isotime()

def size_format(s):
    if (s < 1024):
        r = str(s) + 'B'
    elif (s < 1048576):
        r = str(int(s/1024)) + 'KiB'
    elif (s < 1073741824L):
        r = str(int(s/1048576)) + 'MiB'
    elif (s < 1099511627776L):
        r = str(int((s/1073741824.0)*100.0)/100.0) + 'GiB'
    else:
        r = str(int((s/1099511627776.0)*100.0)/100.0) + 'TiB'
    return(r)

