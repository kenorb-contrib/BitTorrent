#!/usr/bin/env python

# Written by Bram Cohen
# this file is public domain

from sys import version
assert version >= '2', "Install Python 2.0 or greater"

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from types import StringType
from threading import Thread
from binascii import a2b_hex
from BitTorrent.btemplate import compile_template, ListMarker, string_template, OptionMarker
from BitTorrent.bencode import bencode, bdecode
from BitTorrent.parseargs import parseargs
from sys import argv
from urllib import urlopen, quote, unquote
from traceback import print_exc
from threading import Condition
from time import sleep
true = 1
false = 0

def len20(s, verbose):
    if ((type(s) != StringType) or (len(s) != 20)):
        raise ValueError

checkfunc = compile_template({'type': 'publish', 'files': ListMarker({'hash': len20, 
    'pieces': ListMarker(len20), 'piece length': 1, 'name': string_template, 
    'length': 0}), 'ip': OptionMarker(string_template), 'port': 1})

checkfunc2 = compile_template({'type': 'announce', 'id': string_template,
    'ip': OptionMarker(string_template), 'port': 1})

prefix = '/publish/'
prefix2 = '/announce/'

class PublicistHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.server.lock.acquire()
            self.get()
        finally:
            self.server.lock.release()
    
    def get(self):
        # {filename: ([{'ip': ip, 'port': port}], [{'ip': ip, 'port': port}], hash, length, pieces, piece_length)}
        published = self.server.published
        path = unquote(self.path)
        if path[:len(prefix)] == prefix:
            try:
                try:
                    message = bdecode(a2b_hex(path[len(prefix):]))
                except TypeError, e:
                    raise ValueError, str(e)
                checkfunc(message)
                ip = message.get('ip', self.client_address[0])
                for file in message['files']:
                    name = file['name']
                    if not published.has_key(name) or (file['hash'], file['length'],
                            file['pieces'], file['piece length']) != published[name][2:]:
                        published[name] = ([{'ip': ip, 'port': message['port']}], [], 
                            file['hash'], file['length'], file['pieces'], 
                            file['piece length'])
                    else:
                        n = {'ip': ip, 'port': message['port']}
                        if n not in published[name][0]:
                            published[name][0].append(n)
                self.send_response(200)
                self.send_header('content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(bencode({'type': 'success', 'your ip': ip}))
            except ValueError, e:
                print_exc()
                self.send_response(400)
                self.send_header('content-type', 'text/plain')
                self.end_headers()
                self.wfile.write('you sent me garbage - ' + str(e))
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
                    self.wfile.write(bencode({'type': 'failure', 'reason': 'no such file'}))
                else:
                    publishers, requesters, hash, length, pieces, piece_length = published[f]
                    ip = message.get('ip', self.client_address[0])
                    requesters.append({'ip': ip, 'port': message['port']})
                    if len(requesters) > 25:
                        del requesters[0]
                    response = {'type': 'success', 'your ip': ip}
                    self.send_response(200)
                    self.send_header('content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(bencode(response))
            except ValueError, e:
                print_exc()
                self.send_response(400)
                self.send_header('content-type', 'text/plain')
                self.end_headers()
                self.wfile.write('you sent me garbage - ' + str(e))
        else:
            f = path[1:]
            if not published.has_key(f):
                self.send_response(404)
                self.send_header('content-type', 'text/plain')
                self.end_headers()
                self.wfile.write('your file may exist elsewhere in the universe\n\n')
                self.wfile.write('but alas, not here')
            else:
                self.send_response(200)
                self.send_header('content-type', 'bittorrent/redirect')
                self.end_headers()
                publishers, requesters, blob, length, pieces, piece_length = published[f]
                if self.client_address[0] in self.server.ips:
                    requesters = publishers + requesters
                elif self.server.level < 600:
                    self.server.level += 60
                    self.server.ips.append(self.client_address[0])
                    requesters = publishers + requesters
                response = {'hash': blob, 'pieces': pieces, 'piece length': piece_length, 
                    'peers': requesters, 'type': 'success', 
                    'length': length, 'id': f, 'name': f, 'announce': prefix2,
                    'url': 'http://' + self.server.ip + ':' + str(self.server.port) + '/' + quote(f)}
                self.wfile.write(bencode(response))

def publicize(config):
    try:
        h = urlopen('http://bitconjurer.org/BitTorrent/status-publicist-02-04-00.txt')
        status = h.read().strip()
        h.close()
        if status != 'current':
            print 'No longer the latest version - see http://bitconjurer.org/BitTorrent/download.html'
            return
    except IOError, e:
        print "Couldn't check version number - " + str(e)

    port = long(config.get('port', '8080'))
    s = HTTPServer(('', port), PublicistHandler)
    s.port = port
    s.published = {}
    s.lock = Condition()
    s.ip = config['ip']
    s.ips = []
    s.level = 0
    def reduce_level(s = s):
        while true:
            sleep(1)
            try:
                s.lock.acquire()
                s.level = max(0, s.level - 1)
            finally:
                s.lock.release()
    def clear_ips(s = s):
        while true:
            sleep(600)
            try:
                s.lock.acquire()
                del s.ips[:]
            finally:
                s.lock.release()
    Thread(target = reduce_level).start()
    Thread(target = clear_ips).start()
    Thread(target = s.serve_forever).start()

configDefinitions = [
    ('port', 'port=', 'p:', 6800, """Port to listen on.  Defaults to 6800.  Will be random in the future."""),
    ('ip', 'ip=', 'i:', None,
     """ip to report you have to the publicist."""),
    (None, 'help', 'h', None, """Display the command line help.""")
]

if __name__ == '__main__':
    usageHeading = "usage: %s [options]" % argv[0]
    configDictionary, files = parseargs(argv[1:], usageHeading, configDefinitions, 0, 0, requiredConfig = ['ip'])
    publicize(configDictionary)
