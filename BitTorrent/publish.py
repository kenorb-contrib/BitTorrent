# Written by Bram Cohen
# this file is public domain

from urllib import urlopen
from StreamEncrypter import make_encrypter
from PublisherThrottler import Throttler
from MultiBlob import MultiBlob
from Uploader import Uploader
from DummyDownloader import DummyDownloader
from Connecter import Connecter
from Encrypter import Encrypter
from RawServer import RawServer
from PublisherFeedback import PublisherFeedback
from threading import Condition, Event
from entropy import entropy
from bencode import bencode, bdecode
from binascii import b2a_hex
from btemplate import compile_template, string_template
from os.path import split
true = 1
false = 0

def publish(config, files):
    try:
        h = urlopen('http://bitconjurer.org/BitTorrent/status-publisher-02-04-00.txt')
        status = h.read().strip()
        h.close()
        if status != 'current':
            print 'No longer the latest version - see http://bitconjurer.org/BitTorrent/download.html'
            return
    except IOError, e:
        print "Couldn't check version number - " + str(e)

    private_key = entropy(20)
    noncefunc = lambda e = entropy: e(20)
    throttler = Throttler(int(config.get('max_uploads', '6')))
    piece_length = long(config.get('piece_size', str(2 ** 20)))
    blobs = MultiBlob(files, piece_length)
    uploader = Uploader(throttler, blobs)
    downloader = DummyDownloader()
    connecter = Connecter(uploader, downloader)
    rawserver = RawServer(float(config.get('max_poll_period', '2')), Event())
    encrypter = Encrypter(connecter, rawserver, noncefunc, private_key, 
        long(config.get('max_message_length', str(2 ** 20))))
    connecter.set_encrypter(encrypter)
    listen_port = long(config.get('port', '6881'))

    try:
        files = []
        for name, hash, pieces, length in blobs.get_info():
            head, tail = split(name)
            files.append({'hash': hash, 'pieces': pieces, 'name': tail, 
                'piece length': piece_length, 'length': length})
        message = {'type': 'publish', 'port': listen_port, 'files': files}
        if config.has_key('ip'):
            message['ip'] = config['ip']
        h = urlopen(config['location'] + b2a_hex(bencode(message)) + 
            config.get('postlocation', ''))
        response = h.read()
        h.close()
        response = bdecode(response)
        t = compile_template([{'type': 'success', 'your ip': string_template}, 
            {'type': 'failure', 'reason': string_template}])
        t(response)
        if response['type'] == 'failure':
            print "Couldn't publish - " + response['reason']
            return
    except IOError, e:
        print "Couldn't publish - " + str(e)
        return
    except ValueError, e:
        print "got bad publication response - " + str(e)
        return
    PublisherFeedback(uploader, rawserver.add_task, listen_port, response['your ip'], blobs.blobs)
    rawserver.start_listening(encrypter, listen_port, false)
