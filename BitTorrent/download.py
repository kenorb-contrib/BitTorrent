# Written by Bram Cohen
# this file is public domain

from urllib import urlopen
from urlparse import urljoin
from StreamEncrypter import make_encrypter
from Throttler import Throttler
from SingleBlob import SingleBlob
from Uploader import Uploader
from Downloader import Downloader
from Connecter import Connecter
from Encrypter import Encrypter
from RawServer import RawServer
from DownloaderFeedback import DownloaderFeedback
from threading import Condition
from entropy import entropy
from bencode import bencode, bdecode
from btemplate import compile_template, string_template, ListMarker, OptionMarker
from binascii import b2a_hex
true = 1
false = 0

def len20(s, verbose):
    if ((type(s) != type('')) or (len(s) != 20)):
        raise ValueError

t = compile_template({'hash': len20, 'piece length': 1, 'pieces': ListMarker(len20),
    'peers': ListMarker({'ip': string_template, 'port': 1}), 'type': 'success',
    'length': 0, 'id': string_template, 'name': string_template, 
    'announce': string_template, 'postannounce': OptionMarker(string_template),
    'url': string_template})

t2 = compile_template([{'type': 'success', 'your ip': string_template}, 
    {'type': 'failure', 'reason': string_template}])

def run(private_key, noncefunc, response, file, config):
    try:
        response = bdecode(response)
        t(response)
    except ValueError, e:
        print "got bad publication response - " + str(e)
        return
    if callable(file):
        file = file(response['name'])
        if file == '':
            return
    try:
        file_length = response['length']
        blobs = SingleBlob(file, response['hash'], file_length, response['pieces'], 
            response['piece length'], None)
    except ValueError, e:
        print str(e)
        return
    throttler = Throttler(long(config.get('rethrottle_diff', str(2 ** 20))), 
        long(config.get('unthrottle_diff', str(2 ** 23))), 
        int(config.get('max_uploads', '2')), 
        int(config.get('max_downloads', '4')))
    uploader = Uploader(throttler, blobs)
    downloader = Downloader(throttler, blobs, uploader, 
        long(config.get('download_chunk_size', '32768')), 
        long(config.get('request_backlog', '5')))
    rawserver = RawServer(float(config.get('max_poll_period', '2')))
    connecter = Connecter(uploader, downloader, rawserver.add_task, 
        long(config.get('min_fast_reconnect', '60')), 
        long(config.get('max_fast_reconnect', '180')))
    encrypter = Encrypter(connecter, rawserver, noncefunc, private_key, 
        long(config.get('max_message_length', str(2 ** 20))))
    connecter.set_encrypter(encrypter)
    listen_port = long(config.get('port', '6880'))
    
    def finished(result, rawserver = rawserver):
        if result:
            print 'download succeeded'
        else:
            print 'download failed'
        rawserver.shutdown()
    blobs.callback = finished

    connecter.start_connecting([(x['ip'], x['port']) for x in response['peers']])

    try:
        a = {'type': 'announce', 'id': response['id'], 'port': listen_port}
        if config.has_key('myip'):
            a['ip'] = config['myip']
        url = urljoin(response['url'], response['announce'] + 
            b2a_hex(bencode(a)) + response.get('postannounce', ''))
        h = urlopen(url)
        response = h.read()
        h.close()
        response = bdecode(response)
        t2(response)
        if response['type'] == 'failure':
            print "Couldn't announce - " + response['reason']
            return
        DownloaderFeedback(uploader, downloader, throttler, rawserver.add_task, 
            listen_port, response['your ip'], file_length)
    except IOError, e:
        print "Couldn't announce - " + str(e)
        return
    except ValueError, e:
        print "got bad announcement response - " + str(e)
        return
    rawserver.start_listening(encrypter, listen_port, false)

def checkversion():
    try:
        h = urlopen('http://bitconjurer.org/BitTorrent/status-downloader-02-04-00.txt')
        status = h.read().strip()
        h.close()
        if status != 'current':
            print 'No longer the latest version - see http://bitconjurer.org/BitTorrent/download.html'
            return false
    except IOError, e:
        print "Couldn't check version number - " + str(e)
    return true

def download(response, file, config):
    if not checkversion():
        return
    private_key = entropy(20)
    noncefunc = lambda e = entropy: e(20)
    run(private_key, noncefunc, response, file, config)

def downloadurl(url, file, config):
    if not checkversion():
        return
    try:
        h = urlopen(url)
        response = h.read()
        h.close()
        download(response, file, config)
    except IOError, e:
        print "Couldn't download - " + str(e)

