#!/usr/bin/env python

# Written by Bram Cohen
# see LICENSE.txt for license information

import sys
assert sys.version >= '2', "Install Python 2.0 or greater"

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Lock
from BitTorrent.btemplate import compile_template, ListMarker, string_template, OptionMarker, exact_length, ValuesMarker
from BitTorrent.bencode import bencode, bdecode
from BitTorrent.parseargs import parseargs, formatDefinitions
from sys import argv
from urllib import urlopen, quote, unquote
from traceback import print_exc
from os.path import exists
from cStringIO import StringIO
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

class TrackerHandler(BaseHTTPRequestHandler):
    def answer(self, response, head = false, code = 200, type = 'text/plain', 
            headers = {}):
        self.send_response(code)
        self.send_header('Content-Type', type)
        self.send_header('Content-Length', len(response))
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        if not head:
            self.wfile.write(response)

    def do_PUT(self):
        try:
            self.server.lock.acquire()
            try:
                self.put()
            except IOError:
                pass
            except ValueError, e:
                print_exc()
                self.answerno('you sent me garbage - ' + str(e))
        finally:
            self.server.lock.release()

    def put(self):
        path = unquote(self.path)[1:]
        l = self.headers.getheader('content-length')
        if l is None:
            self.answer('need content-length header for put', code = 400)
            return
        message = bdecode(self.rfile.read(int(l)))
        self.server.loghandle.write(str(message) + '\n')
        if path == 'announce/':
            announcetemplate(message)
            downloaders = self.server.downloaders
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
                        del self.server.myid_to_id[perm[i]['myid']]
                        del perm[i]
                        break
                else:
                    for i in xrange(len(temp)):
                        if temp[i]['contact'] == contact:
                            del self.server.myid_to_id[temp[i]['myid']]
                            del temp[i]
                            break
                if not message.has_key('permanent'):
                    temp.append({'myid': myid, 'contact': contact})
                    if len(temp) > 25:
                        del temp[0]
                else:
                    perm.append({'myid': myid, 'contact': contact})
                self.server.myid_to_id[myid] = id
            else:
                if self.server.myid_to_id.has_key(myid):
                    id = self.server.myid_to_id[myid]
                    del self.server.myid_to_id[myid]
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
            h = open(self.server.dfile, 'wb')
            h.write(bencode(downloaders))
            h.close()
        else:
            if self.headers.getheader('content-type') != 'application/x-bittorrent':
                self.answer('only accepting puts of content-type application/x-bittorrent', code = 400)
                return
            infotemplate(message)
            published = self.server.published
            if published.has_key(path):
                if published[path] != message:
                    self.answer('incompatible existing information', code = 400)
                    return
            else:
                published[path] = message
                h = open(self.server.file, 'wb')
                h.write(bencode(published))
                h.close()
        self.answer('Thanks! Love, Kerensa.')

    def do_GET(self, head = false):
        try:
            self.server.lock.acquire()
            try:
                self.get(head)
            except IOError:
                pass
            except ValueError, e:
                print_exc()
                self.answer('you sent me garbage - ' + str(e), head, 400)
        finally:
            self.server.lock.release()
    
    def do_HEAD(self):
        self.do_GET(true)
    
    def get(self, head):
        published = self.server.published
        path = unquote(self.path)[1:]
        if path == '' or path == 'index.html':
            s = StringIO()
            s.write('<head><title>Published BitTorrent files</title></head>Published BitTorrent files<p>\n')
            names = published.keys()
            if names == []:
                s.write('(no files published yet)')
            names.sort()
            for name in names:
                s.write('<a href="' + name + '">' + name + '</a><p>\n\n')
            self.answer(s.getvalue(), head, 200, 'text/html')
            return
        if not published.has_key(path):
            self.answer(alas, head, 404)
            return
        p = self.server.downloaders.get(path)
        if p is None:
            peers = []
        else:
            peers = [x['contact'] for x in (p['permanent'] + p['temporary'])]
        self.answer(bencode({'info': published[path], 'id': path, 
            'url': self.server.urlprefix + self.path,
            'announce': self.server.urlprefix + '/announce/',
            'your ip': self.client_address[0], 'peers': peers}),
            head, 200, 'application/x-bittorrent', 
            {'Pragma': 'no-cache'})

def track(config):
    try:
        h = urlopen('http://bitconjurer.org/BitTorrent/status-tracker-02-07-00.txt')
        status = h.read().strip()
        h.close()
        if status != 'current':
            print 'No longer the latest version - see http://bitconjurer.org/BitTorrent/download.html'
            return
    except IOError, e:
        print "Couldn't check version number - " + str(e)

    port = config['port']
    s = HTTPServer(('', port), TrackerHandler)
    s.published = {}
    s.file = config['file']
    if exists(s.file):
        h = open(s.file, 'rb')
        r = h.read()
        h.close()
        s.published = bdecode(r)
        infofiletemplate(s.published)
    s.lock = Lock()
    s.urlprefix = 'http://' + config['ip'] + ':' + str(port)
    s.logfile = config['logfile']
    s.loghandle = open(s.logfile, 'ab')
    s.downloaders = {}
    s.myid_to_id = {}
    d = config['dfile']
    s.dfile = d
    if exists(d):
        h = open(d, 'rb')
        ds = h.read()
        h.close()
        s.downloads = bdecode(ds)
        downloaderfiletemplate(s.downloads)
        for key, value in s.downloads.items():
            for j in value['permanent'] + value['temporary']:
                s.myid_to_id[j['myid']] = id
    s.serve_forever()

defaults = [
    ('port', 'p', 80, "Port to listen on."),
    ('ip', 'i', None, "ip to report you have to downloaders."),
    ('file', 's', None, 'file to store state in'),
    ('dfile', 'd', None, 'file to store recent downloader info in'),
    ('logfile', None, None, 'file to write BitTorrent announcements to'),
    ]

def run(args):
    if len(args) == 0:
        print formatDefinitions(defaults, 80)
    try:
        config, files = parseargs(args, defaults, 0, 0)
        track(config)
    except ValueError, e:
        print 'error: ' + str(e)
        print 'run with no arguments for parameter explanations'

if __name__ == '__main__':
    run(argv[1:])
