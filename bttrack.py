#!/usr/bin/env python

# Written by Bram Cohen
# see LICENSE.txt for license information

import sys
assert sys.version >= '2', "Install Python 2.0 or greater"

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from types import StringType
from threading import Thread, Condition
from BitTorrent.btemplate import compile_template, ListMarker, string_template, OptionMarker, exact_length
from BitTorrent.bencode import bencode, bdecode
from BitTorrent.parseargs import parseargs, formatDefinitions
from sys import argv
from urllib import urlopen, quote, unquote
from traceback import print_exc
from time import sleep
from os.path import exists
true = 1
false = 0

checkfunc = compile_template({'type': 'publish', 'files': ListMarker({
    'pieces': ListMarker(exact_length(20)), 'piece length': 1, 'name': string_template, 
    'length': 0}), 'ip': OptionMarker(string_template), 'port': 1})

checkfunc2 = compile_template({'type': 'announce', 'id': string_template,
    'ip': OptionMarker(string_template), 'port': 1})

class TrackerHandler(BaseHTTPRequestHandler):
    def answer(self, response):
        self.send_response(200)
        self.send_header('Content-Type', 'binary')
        response = bencode(response)
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response)

    def answerno(self, response):
        self.send_response(400)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response)

    def do_PUT(self):
        try:
            self.server.lock.acquire()
            try:
                self.put()
            except IOError:
                pass
        finally:
            self.server.lock.release()

    def put(self):
        # {filename: ([{'ip': ip, 'port': port}], length, pieces, piece_length)}
        published = self.server.published
        path = unquote(self.path)
        try:
            l = self.headers.getheader('content-length')
            if l is None:
                self.answerno('need content-length header for put')
                return
            message = bdecode(self.rfile.read(int(l)))
            if path == '/publish/':
                checkfunc(message)
                ip = message.get('ip', self.client_address[0])
                for file in message['files']:
                    name = file['name']
                    if published.has_key(name) and [file['length'],
                            file['pieces'], file['piece length']] != published[name][1:]:
                        self.answer({'type': 'failure', 
                            'reason': 'mismatching data for ' + name})
                        print published[name][1:]
                        print (file['length'], file['pieces'], file['piece length'])
                        return
                changed = false
                for file in message['files']:
                    name = file['name']
                    if not published.has_key(name):
                        published[name] = [[], file['length'], 
                            file['pieces'], file['piece length']]
                    n = {'ip': ip, 'port': message['port']}
                    if n not in published[name][0]:
                        published[name][0].append(n)
                        changed = true
                if changed:
                    h = open(self.server.file, 'wb')
                    h.write(bencode(published))
                    h.flush()
                    h.close()
                self.answer({'type': 'success', 'your ip': ip})
            elif path == '/announce/':
                checkfunc2(message)
                f = message['id']
                if not published.has_key(f):
                    self.answer({'type': 'failure', 'reason': 'no such file'})
                else:
                    publishers, length, pieces, piece_length = published[f]
                    requesters = self.server.downloads.setdefault(f, [])
                    ip = message.get('ip', self.client_address[0])
                    requesters.append({'ip': ip, 'port': message['port']})
                    del requesters[:-25]
                    self.answer({'type': 'success', 'your ip': ip})
            elif path == '/finish/':
                self.answer('Thank you for your feedback! Love, Kerensa')
                print 'finished - ' + `message`
                sys.stdout.flush()
            else:
                self.answerno('no put!')
        except ValueError, e:
            print_exc()
            self.answerno('you sent me garbage - ' + str(e))

    def do_GET(self):
        try:
            self.server.lock.acquire()
            try:
                self.get(false)
            except IOError:
                pass
        finally:
            self.server.lock.release()
    
    def do_HEAD(self):
        try:
            self.server.lock.acquire()
            self.get(true)
        finally:
            self.server.lock.release()
    
    def get(self, head):
        # {filename: ([{'ip': ip, 'port': port}], length, pieces, piece_length)}
        published = self.server.published
        path = unquote(self.path)
        if path == '/' or path == '/index.html':
            self.send_response(200)
            self.end_headers()
            if head:
                return
            self.wfile.write('<head><title>Published BitTorrent files</title></head>\n')
            names = published.keys()
            names.sort()
            for name in names:
                self.wfile.write('<a href="' + name + '">' + name + '</a><p>\n\n')
        else:
            f = path[1:]
            if not published.has_key(f):
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                if head:
                    return
                self.wfile.write('your file may exist elsewhere in the universe\n\n')
                self.wfile.write('but alas, not here')
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'application/x-bittorrent')
                publishers, length, pieces, piece_length = published[f]
                requesters = self.server.downloads.get(f, [])
                requesters = publishers + requesters
                response = {'pieces': pieces, 'piece length': piece_length, 
                    'peers': requesters, 'type': 'success', 'finish': '/finish/',
                    'length': length, 'id': f, 'name': f, 'announce': '/announce/',
                    'url': 'http://' + self.server.ip + ':' + str(self.server.port) + '/' + quote(f)}
                r = bencode(response)
                self.send_header('Content-Length', str(len(r)))
                self.send_header('Pragma', 'no-cache')
                self.end_headers()
                if head:
                    return
                self.wfile.write(r)

def track(config):
    try:
        h = urlopen('http://bitconjurer.org/BitTorrent/status-tracker-02-06-01.txt')
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
    s.downloads = {}
    s.port = port
    s.lock = Condition()
    s.ip = config['ip']
    d = config['dfile']
    if d != '':
        if exists(d):
            h = open(d, 'rb')
            ds = h.read()
            h.close()
            s.downloads = bdecode(ds)
        
        def store_downloads(s = s, d = d):
            while true:
                sleep(600)
                try:
                    s.lock.acquire()
                    h = open(d, 'wb')
                    h.write(bencode(s.downloads))
                    h.flush()
                    h.close()
                finally:
                    s.lock.release()
        Thread(target = store_downloads).start()
    Thread(target = s.serve_forever).start()

defaults = [
    ('port', 'p', 80, "Port to listen on."),
    ('ip', 'i', None, "ip to report you have to downloaders."),
    ('file', 's', None, 'file to store state in'),
    ('dfile', 'd', '', 'file to store recent downloader info in'),
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
