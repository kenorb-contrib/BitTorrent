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
from Scheduler import Scheduler
from DownloaderFeedback import DownloaderFeedback
from threading import Condition
from entropy import entropy
from bencode import bencode, bdecode
from btemplate import compile_template, string_template, ListMarker, OptionMarker
from binascii import b2a_hex
from Tkinter import Tk
from tkFileDialog import asksaveasfilename

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
    if file is None:
        root = Tk()
	root.withdraw()
	file = asksaveasfilename(initialfile=response['name'])
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
    piece_length = long(config.get('piece_size', str(2 ** 20)))
    uploader = Uploader(throttler, blobs)
    downloader = Downloader(throttler, blobs, uploader, 
        long(config.get('download_chunk_size', '32768')), 
        long(config.get('request_backlog', '5')))
    lock = Condition()
    scheduler = Scheduler(lock)
    connecter = Connecter(uploader, downloader, scheduler.add_task, 
        long(config.get('min_fast_reconnect', '60')), 
        long(config.get('max_fast_reconnect', '180')))
    encrypter = Encrypter(connecter, noncefunc, private_key, 
        long(config.get('max_message_length', str(2 ** 20))))
    connecter.set_encrypter(encrypter)
    listen_port = long(config.get('port', '6880'))
    rawserver = RawServer(listen_port, encrypter, 
        lock, long(config.get('socket_poll_period', '100')))
    encrypter.set_raw_server(rawserver)
    rawserver.start_listening()
    doneflag = []
    
    def finished(result, rawserver = rawserver, scheduler = scheduler, doneflag = doneflag):
        if result:
            print 'download succeeded'
        else:
            print 'download failed'
        rawserver.shutdown()
        scheduler.shutdown()
        doneflag.append(1)
    blobs.callback = finished

    try:
        lock.acquire()
        connecter.start_connecting([(x['ip'], x['port']) for x in response['peers']])
    finally:
        lock.release()

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
        else:
            DownloaderFeedback(uploader, downloader, throttler, lock, 
                listen_port, response['your ip'], doneflag, file_length)
    except IOError, e:
        print "Couldn't announce - " + str(e)
        return
    except ValueError, e:
        print "got bad announcement response - " + str(e)
        return

def download(response, filename, config):
    private_key = entropy(20)
    noncefunc = lambda e = entropy: e(20)
    run(private_key, noncefunc, response, filename, config)

def downloadurl(url, filename, config):
    try:
        h = urlopen(url)
        response = h.read()
        h.close()
        download(response, filename, config)
    except IOError, e:
        print "Couldn't download - " + str(e)

