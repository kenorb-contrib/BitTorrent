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
import socket
from random import randrange
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

def run(private_key, noncefunc, response, filefunc, displayfunc, doneflag, config):
    try:
        response = bdecode(response)
        t(response)
    except ValueError, e:
        displayfunc("got bad publication response - " + str(e), "Okay")
        return false
    file = filefunc(response['name'])
    if file == '':
        return false
    try:
        file_length = response['length']
        blobs = SingleBlob(file, response['hash'], file_length, response['pieces'], 
            response['piece length'], None)
        if len(blobs.get_list_of_files_I_want()) == 0:
            displayfunc('that file has already been completely downloaded', 'Okay')
            return true
    except ValueError, e:
        displayfunc('bad data for making blob store - ' + str(e), 'Okay')
        return false
    throttler = Throttler(config['rethrottle_diff'], config['unthrottle_diff'], 
        config['max_uploads'], config['max_downloads'])
    uploader = Uploader(throttler, blobs)
    downloader = Downloader(throttler, blobs, uploader, 
        config['download_chunk_size'], config['request_backlog'])
    rawserver = RawServer(config['max_poll_period'], doneflag)
    connecter = Connecter(uploader, downloader)
    encrypter = Encrypter(connecter, rawserver, noncefunc, private_key, 
        config['max_message_length'])
    connecter.set_encrypter(encrypter)
    listen_port = config['port']
    if listen_port == 0:
        listen_port = randrange(5000, 10000)
    r = []
    def finished(result, displayfunc = displayfunc, doneflag = doneflag, r = r):
        if result:
            displayfunc('download succeeded', 'Okay')
        else:
            displayfunc('download failed', 'Okay')
        r.append(1)
        doneflag.set()
    blobs.callback = finished

    connecter.start_connecting([(x['ip'], x['port']) for x in response['peers']])

    try:
        a = {'type': 'announce', 'id': response['id'], 'port': listen_port}
        if config['ip'] != '':
            a['ip'] = config['ip']
        url = urljoin(response['url'], response['announce'] + 
            b2a_hex(bencode(a)) + response.get('postannounce', ''))
        h = urlopen(url)
        response = h.read()
        h.close()
        response = bdecode(response)
        t2(response)
        if response['type'] == 'failure':
            displayfunc("Couldn't announce - " + response['reason'], 'Okay')
            return false
        DownloaderFeedback(uploader, downloader, throttler, rawserver.add_task, 
            listen_port, response['your ip'], file_length, displayfunc)
    except IOError, e:
        displayfunc("Couldn't announce - " + str(e), 'Okay')
        return false
    except ValueError, e:
        displayfunc("got bad announcement response - " + str(e), 'Okay')
        return false
    try:
        rawserver.start_listening(encrypter, listen_port, false)
    except socket.error, e:
        displayfunc("Couldn't listen - " + str(e), 'Okay')
    return len(r) > 0

def checkversion():
    try:
        h = urlopen('http://bitconjurer.org/BitTorrent/status-downloader-02-04-00.txt')
        status = h.read().strip()
        h.close()
        if status != 'current':
            return false
    except IOError, e:
        print "Couldn't check version number - " + str(e)
    return true

def download(response, filefunc, displayfunc, doneflag, config):
    if not checkversion():
        displayfunc('No longer the latest version - see http://bitconjurer.org/BitTorrent/download.html', 'Okay')
        return false
    private_key = entropy(20)
    noncefunc = lambda e = entropy: e(20)
    return run(private_key, noncefunc, response, filefunc, displayfunc, doneflag, config)

def downloadurl(url, filefunc, displayfunc, doneflag, config):
    try:
        h = urlopen(url)
        response = h.read()
        h.close()
        return download(response, filefunc, displayfunc, doneflag, config)
    except IOError, e:
        displayfunc('IO problem reading file - ' + str(e), 'Okay')
        return false

