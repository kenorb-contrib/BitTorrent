#!/usr/bin/env python

# Written by Bram Cohen
# this file is public domain

from sys import version
assert version >= '2', "Install Python 2.0 or greater"

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from types import StringType
from threading import Thread, Condition
from binascii import a2b_hex
from BitTorrent.btemplate import compile_template, ListMarker, string_template, OptionMarker
from BitTorrent.bencode import bencode, bdecode
from BitTorrent.parseargs import parseargs, formatDefinitions
from sys import argv
from urllib import urlopen, quote, unquote
from traceback import print_exc
from time import sleep
from os.path import exists
true = 1
false = 0

def len20(s, verbose):
    if ((type(s) != StringType) or (len(s) != 20)):
        raise ValueError, 'bad hash value'

checkfunc = compile_template({'type': 'publish', 'files': ListMarker({
    'pieces': ListMarker(len20), 'piece length': 1, 'name': string_template, 
    'length': 0}), 'ip': OptionMarker(string_template), 'port': 1})

checkfunc2 = compile_template({'type': 'announce', 'id': string_template,
    'ip': OptionMarker(string_template), 'port': 1})

prefix = '/publish/'
prefix2 = '/announce/'
prefix3 = '/finish/'

class TrackerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.server.lock.acquire()
            self.get(false)
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
            self.wfile.write('<html><head><title>Published BitTorrent files</title></head><body>\n')
            names = published.keys()
            names.sort()
            for name in names:
                self.wfile.write('<a href="' + name + '">' + name + '</a><p>\n\n')
            self.wfile.write('</body></html>\n')
        elif path[:len(prefix)] == prefix:
            try:
                try:
                    message = bdecode(a2b_hex(path[len(prefix):]))
                except TypeError, e:
                    raise ValueError, str(e)
                checkfunc(message)
                ip = message.get('ip', self.client_address[0])
                for file in message['files']:
                    if published.has_key('name') and (file['length'],
                            file['pieces'], file['piece length']) != published[name][1:]:
                        self.send_response(200)
                        self.end_headers()
                        if head:
                            return
                        self.wfile.write(bencode({'type': 'failure', 
                            'reason': 'mismatching data for ' + file}))
                        return
                changed = false
                for file in message['files']:
                    name = file['name']
                    if not published.has_key(name):
                        published[name] = ([], file['length'], 
                            file['pieces'], file['piece length'])
                    n = {'ip': ip, 'port': message['port']}
                    if n not in published[name][0]:
                        published[name][0].append(n)
                        changed = true
                if changed:
                    h = open(self.server.file, 'wb')
                    h.write(bencode(published))
                    h.flush()
                    h.close()
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                if head:
                    return
                self.wfile.write(bencode({'type': 'success', 'your ip': ip}))
            except ValueError, e:
                print_exc()
                self.send_response(400)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                if head:
                    return
                self.wfile.write('you sent me garbage - ' + str(e))
        elif path[:len(prefix3)] == prefix3:
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            if head:
                return
            self.wfile.write('Thank you for your feedback! Love, Nina')
        elif path[:len(prefix2)] == prefix2:
            try:
                try:
                    message = bdecode(a2b_hex(path[len(prefix2):]))
                except TypeError, e:
                    raise ValueError, str(e)
                checkfunc2(message)
                f = message['id']
                if not published.has_key(f):
                    self.send_response(200)
                    self.send_header('content-type', 'text/plain')
                    self.end_headers()
                    if head:
                        return
                    self.wfile.write(bencode({'type': 'failure', 'reason': 'no such file'}))
                else:
                    publishers, length, pieces, piece_length = published[f]
                    requesters = self.server.downloads.setdefault(f, [])
                    ip = message.get('ip', self.client_address[0])
                    requesters.append({'ip': ip, 'port': message['port']})
                    if len(requesters) > 25:
                        del requesters[0]
                    response = {'type': 'success', 'your ip': ip}
                    self.send_response(200)
                    self.send_header('content-type', 'text/plain')
                    self.end_headers()
                    if head:
                        return
                    self.wfile.write(bencode(response))
            except ValueError, e:
                print_exc()
                self.send_response(400)
                self.send_header('content-type', 'text/plain')
                self.end_headers()
                if head:
                    return
                self.wfile.write('you sent me garbage - ' + str(e))
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
                    'peers': requesters, 'type': 'success', 'finish': prefix3,
                    'length': length, 'id': f, 'name': f, 'announce': prefix2,
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
        h = urlopen('http://bitconjurer.org/BitTorrent/status-tracker-02-05-01.txt')
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

if __name__ == '__main__':
    try:
        config, files = parseargs(argv[1:], defaults, 0, 0)
        track(config)
    except ValueError, e:
        print "usage: %s [options]" % argv[0]
        print formatDefinitions(defaults, 80)
