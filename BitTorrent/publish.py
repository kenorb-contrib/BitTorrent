# Written by Bram Cohen
# this file is public domain

from urllib import urlopen
from StreamEncrypter import make_encrypter
from Throttler import Throttler
from MultiBlob import MultiBlob
from Uploader import Uploader
from DummyDownloader import DummyDownloader
from Connecter import Connecter
from Encrypter import Encrypter
from RawServer import RawServer
from PublisherFeedback import PublisherFeedback
from threading import Condition
from entropy import entropy
from bencode import bencode, bdecode
from binascii import b2a_hex
from btemplate import compile_template, string_template
from os.path import split

def publish(config, files):
    private_key = entropy(20)
    noncefunc = lambda e = entropy: e(20)
    throttler = Throttler(long(config.get('rethrottle_diff', str(2 ** 20))), 
        long(config.get('unthrottle_diff', str(2 ** 23))), 
        int(config.get('max_uploads', '2')), 
        int(config.get('max_downloads', '4')))
    piece_length = long(config.get('piece_size', str(2 ** 20)))
    blobs = MultiBlob(files, piece_length)
    uploader = Uploader(throttler, blobs)
    downloader = DummyDownloader()
    lock = Condition()
    connecter = Connecter(uploader, downloader, None, None, None)
    encrypter = Encrypter(connecter, noncefunc, private_key, 
        long(config.get('max_message_length', str(2 ** 20))))
    connecter.set_encrypter(encrypter)
    listen_port = long(config.get('port', '6881'))
    rawserver = RawServer(listen_port, encrypter, 
        lock, long(config.get('socket_poll_period', '100')))
    encrypter.set_raw_server(rawserver)
    rawserver.start_listening()

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
        else:
            PublisherFeedback(uploader, lock, listen_port, response['your ip'], blobs.blobs)
    except IOError, e:
        print "Couldn't publish - " + str(e)
    except ValueError, e:
        print "got bad publication response - " + str(e)
