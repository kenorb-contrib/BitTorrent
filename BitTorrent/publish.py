# Written by Bram Cohen
# this file is public domain

from parseargs import parseargs, formatDefinitions
from urllib import urlopen
from StreamEncrypter import make_encrypter
from PublisherChoker import Choker
from MultiBlob import MultiBlob
from Uploader import Upload
from Connecter import Connecter
from Encrypter import Encrypter
from RawServer import RawServer
from PublisherFeedback import PublisherFeedback
from threading import Condition, Event
from entropy import entropy
from bencode import bencode, bdecode
from binascii import b2a_hex
from btemplate import compile_template, string_template
from os.path import split, getsize, exists, isfile, getmtime
from random import randrange
from time import time
true = 1
false = 0

defaults = [
    ('max_uploads', None, 10,
        "the maximum number of uploads to allow at once."),
    ('piece_size', None, 2 ** 20,
        "Size of individually hashed pieces of file to be published."),
    ('max_message_length', None, 2 ** 23,
        "maximum length prefix encoding you'll accept over the wire - larger values get the connection dropped."),
    ('port', 'p', 0, """Port to listen on, zero indicates choose randomly."""),
    ('max_poll_period', None, 2.0,
        "Maximum number of seconds to block in calls to select()"),
    ('ip', 'i', '',
        "ip to report you have to the publicist."),
    ('location', None, None,
        "The prefix url for announcing to the publicist."),
    ('postlocation', None, '',
        "post url for announcing to the publicist."),
    ('keepalive_interval', None, 120.0,
        'number of seconds to pause between sending keepalives'),
    ('timeout', None, 300.0,
        'time to wait between closing sockets which nothing has been received on'),
    ('choke_interval', None, 30.0,
        "number of seconds to pause between changing who's choked"),
    ]

def publish(params, cols):
    try:
        config, files = parseargs(params, defaults, 1, 10000)
        if config['port'] == 0:
            raise ValueError, 'port required'
    except ValueError, e:
        print 'error: ' + str(e) + '\n'
        print formatDefinitions(defaults, cols)
        return
    try:
        h = urlopen('http://bitconjurer.org/BitTorrent/status-publisher-02-05-01.txt')
        status = h.read().strip()
        h.close()
        if status != 'current':
            print 'No longer the latest version - see http://bitconjurer.org/BitTorrent/download.html'
            return
    except IOError, e:
        print "Couldn't check version number - " + str(e)

    private_key = entropy(20)
    noncefunc = lambda e = entropy: e(20)
    listen_port = config['port']
    rawserver = RawServer(config['max_poll_period'], Event(),
        config['timeout'])
    choker = Choker(config['max_uploads'], rawserver.add_task, config['choke_interval'])
    piece_length = config['piece_size']
    blobs = MultiBlob(files, piece_length, open, getsize, exists, 
        split, getmtime, time, isfile)
    def make_upload(connection, choker = choker, blobs = blobs):
        return Upload(connection, choker, blobs)
    connecter = Connecter(make_upload, DummyDownload, choker)
    encrypter = Encrypter(connecter, rawserver, noncefunc, private_key, 
        config['max_message_length'], rawserver.add_task, 
        config['keepalive_interval'])

    try:
        files = []
        for name, hash, pieces, length in blobs.get_info():
            files.append({'hash': hash, 'pieces': pieces, 'name': name, 
                'piece length': piece_length, 'length': length})
        message = {'type': 'publish', 'port': listen_port, 'files': files}
        if config['ip'] != '':
            message['ip'] = config['ip']
        h = urlopen(config['location'] + b2a_hex(bencode(message)) + 
            config['postlocation'])
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
    PublisherFeedback(connecter, rawserver.add_task, listen_port, response['your ip'])
    rawserver.start_listening(encrypter, listen_port, false)

class DummyDownload:
    def __init__(self, connection):
        pass

    def got_choke(self, message):
        pass
    
    def got_unchoke(self, message):
        pass
    
    def got_slice(self, message):
        pass
    
    def got_I_have(self, message):
        pass

    def disconnected(self):
        pass
