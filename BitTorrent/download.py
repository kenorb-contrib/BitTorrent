# Written by Bram Cohen
# this file is public domain

from urllib import urlopen
from urlparse import urljoin
from StreamEncrypter import make_encrypter
from PublisherChoker import Choker
from SingleBlob import SingleBlob
from Uploader import Upload
from Downloader import Download
from Connecter import Connecter
from Encrypter import Encrypter
from RawServer import RawServer
from DownloaderFeedback import DownloaderFeedback
from threading import Condition
from entropy import entropy
from bencode import bencode, bdecode
from btemplate import compile_template, string_template, ListMarker, OptionMarker, exact_length
from binascii import b2a_hex
from os import path
from parseargs import parseargs, formatDefinitions
import socket
from random import randrange, seed
true = 1
false = 0

defaults = [
    ('max_uploads', None, 3,
        "the maximum number of uploads to allow at once."),
    ('keepalive_interval', None, 120.0,
        'number of seconds to pause between sending keepalives'),
    ('download_slice_size', None, 2 ** 15,
        "How many bytes to query for per request."),
    ('request_backlog', None, 5,
        "how many requests to keep in a single pipe at once."),
    ('max_message_length', None, 2 ** 23,
        "maximum length prefix encoding you'll accept over the wire - larger values get the connection dropped."),
    ('max_poll_period', None, 2.0,
        "Maximum number of seconds to block in calls to select()"),
    ('port', 'p', 0,
        "Port to listen on, zero means choose randomly"),
    ('ip', 'i', '',
        "ip to report you have to the publicist."),
    ('response', None, '',
        'response which came back from server, alternative to responsesfile and url'),
    ('responsefile', None, '',
        'file the server response was stored in, alternative to response and url'),
    ('url', None, '',
        'url to get file from, alternative to response and responsefile'),
    ('saveas', None, '',
        'local file name to save the file as, null indicates query user'),
    ('timeout', None, 300.0,
        'time to wait between closing sockets which nothing has been received on'),
    ('choke_interval', None, 30.0,
        "number of seconds to pause between changing who's choked"),
    ]

t = compile_template({'hash': exact_length(20), 'piece length': 1, 
    'pieces': ListMarker(exact_length(20)),
    'peers': ListMarker({'ip': string_template, 'port': 1}), 'type': 'success',
    'length': 0, 'id': string_template, 'name': string_template, 
    'announce': string_template, 'postannounce': OptionMarker(string_template),
    'url': string_template, 'finish': OptionMarker(string_template), 
    'postfinish': OptionMarker(string_template)})

t2 = compile_template([{'type': 'success', 'your ip': string_template}, 
    {'type': 'failure', 'reason': string_template}])

def download(params, filefunc, displayfunc, doneflag, cols):
    try:
        config, garbage = parseargs(params, defaults, 0, 0)
        if config['response'] == '' and config['responsefile'] == '' and config['url'] == '':
            raise ValueError('need response, responsefile, or url')
    except ValueError, e:
        displayfunc('error: ' + str(e) + '\n\n' + formatDefinitions(defaults, cols), 'Okay')
        return false
    
    if config['response'] != '':
        response = config['response']
    elif config['responsefile'] != '':
        try:
            h = open(config['responsefile'], 'rb')
            response = h.read()
            h.close()
        except IOError, e:
            displayfunc('IO problem reading file - ' + str(e), 'Okay')
            return false
    else:
        try:
            h = urlopen(config['url'])
            response = h.read()
            h.close()
        except IOError, e:
            displayfunc('IO problem reading file - ' + str(e), 'Okay')
            return false

    try:
        h = urlopen('http://bitconjurer.org/BitTorrent/status-downloader-02-05-01.txt')
        status = h.read().strip()
        h.close()
        if status != 'current':
            displayfunc('No longer the latest version - see http://bitconjurer.org/BitTorrent/download.html', 'Okay')
            return false
    except IOError, e:
        print "Couldn't check version number - " + str(e)

    try:
        response = bdecode(response)
        response1 = response
        t(response)
    except ValueError, e:
        displayfunc("got bad publication response - " + str(e), "Okay")
        return false
    file = config['saveas']
    if file == '':
        file = filefunc(response['name'])
    if file == '':
        return false
    try:
        file_length = response['length']
        if path.exists(file):
            displayfunc('checking existing file...', 'Cancel')
            resuming = true
        else:
            displayfunc('allocating new file...', 'Cancel')
            resuming = false
        r = [0]
        def finished(result, displayfunc = displayfunc, doneflag = doneflag, r = r):
            if result:
                r[0] = 1
                displayfunc('Download Succeeded!', 'Okay')
            else:
                displayfunc('Download Failed', 'Okay')
            doneflag.set()
        blobs = SingleBlob(file, response['hash'], file_length, response['pieces'], 
            response['piece length'], finished, open, path.exists, path.getsize)
        if len(blobs.get_list_of_files_I_want()) == 0:
            displayfunc('that file has already been completely downloaded', 'Okay')
            return true
    except ValueError, e:
        displayfunc('bad data for making blob store - ' + str(e), 'Okay')
        return false
    except IOError, e:
        displayfunc('disk access error - ' + str(e), 'Okay')
        return false
    rawserver = RawServer(config['max_poll_period'], doneflag,
        config['timeout'])
    choker = Choker(config['max_uploads'], rawserver.add_task, config['choke_interval'])
    def make_upload(connection, choker = choker, blobs = blobs):
        return Upload(connection, choker, blobs)
    dd = DownloaderData(blobs, config['download_slice_size'])
    def make_download(connection, data = dd, backlog = config['request_backlog']):
        return Download(connection, data, backlog)
    connecter = Connecter(make_upload, make_download, choker)
    seed(entropy(20))
    encrypter = Encrypter(connecter, rawserver, lambda e = entropy: e(20),
        entropy(20), config['max_message_length'], rawserver.add_task, 
        config['keepalive_interval'])
    listen_port = config['port']
    if listen_port == 0:
        listen_port = randrange(5000, 10000)
    left = blobs.get_amount_left()
    for x in response['peers']:
        encrypter.start_connection((x['ip'], x['port']))

    try:
        myid = entropy(20)
        a = {'type': 'announce', 'id': response['id'], 'port': listen_port,
            'myid': myid}
        if config['ip'] != '':
            a['ip'] = config['ip']
        if resuming:
            a['remaining'] = left
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
        DownloaderFeedback(uploader, downloader, choker, rawserver.add_task, 
            listen_port, response['your ip'], file_length, left, displayfunc)
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
        return false
        
    if response1.has_key('finish'):
        try:
            a = {'type': 'finished', 'id': response1['id'], 'myid': myid}
            if r[0]:
                a['result'] = 'success'
            else:
                a['result'] = 'failure'
            url = urljoin(response1['url'], response1['finish'] + 
                b2a_hex(bencode(a)) + response1.get('postfinish', ''))
            h = urlopen(url)
            h.read()
            h.close()
        except IOError, e:
            pass
    return r[0]
