# Written by Bram Cohen
# see LICENSE.txt for license information

from urllib import urlopen
from urlparse import urljoin
from StreamEncrypter import make_encrypter
from PublisherChoker import Choker
from SingleBlob import SingleBlob
from Uploader import Upload
from DownloaderData import DownloaderData
from Downloader import Download
from Connecter import Connecter
from Encrypter import Encrypter
from RawServer import RawServer
from DownloaderFeedback import DownloaderFeedback
from RateMeasure import RateMeasure
from entropy import entropy
from readput import readput
from bencode import bdecode
from btemplate import compile_template, string_template, ListMarker, OptionMarker, exact_length
from os import path
from parseargs import parseargs, formatDefinitions
import socket
from random import randrange, seed
from traceback import print_exc
from threading import Event
true = 1
false = 0

defaults = [
    ('max_uploads', None, 4,
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
    ('max_slice_length', None, 2 ** 17,
        "maximum length slice to send to peers, larger requests are ignored"),
    ('max_rate_recalculate_interval', None, 15.0,
        "maximum amount of time to let a connection pause before reducing it's rate"),
    ('max_rate_period', None, 20.0,
        "maximum amount of time to guess the current rate estimate represents"),
    ]

t = compile_template({'piece length': 1, 
    'pieces': ListMarker(exact_length(20)),
    'peers': ListMarker({'ip': string_template, 'port': 1}), 'type': 'success',
    'length': 0, 'id': string_template, 'name': string_template, 
    'announce': string_template, 
    'url': string_template, 'finish': OptionMarker(string_template)})

t2 = compile_template([{'type': 'success', 'your ip': string_template}, 
    {'type': 'failure', 'reason': string_template}])

def download(params, filefunc, statusfunc, resultfunc, doneflag, cols):
    try:
        config, garbage = parseargs(params, defaults, 0, 0)
        if config['response'] == '' and config['responsefile'] == '' and config['url'] == '':
            raise ValueError('need response, responsefile, or url')
    except ValueError, e:
        resultfunc(false, 'error: ' + str(e) + '\n\n' + formatDefinitions(defaults, cols))
        return
    
    if config['response'] != '':
        response = config['response']
    elif config['responsefile'] != '':
        try:
            h = open(config['responsefile'], 'rb')
            response = h.read()
            h.close()
        except IOError, e:
            print_exc()
            resultfunc(false, 'IO problem reading file - ' + str(e))
            return
    else:
        try:
            print 'url', config['url']
            h = urlopen(config['url'])
            response = h.read()
            h.close()
        except IOError, e:
            print_exc()
            resultfunc(false, 'IO problem reading file - ' + str(e))
            return false

    try:
        h = urlopen('http://bitconjurer.org/BitTorrent/status-downloader-02-06-01.txt')
        status = h.read().strip()
        h.close()
        if status != 'current':
            resultfunc(false, 'No longer the latest version - see http://bitconjurer.org/BitTorrent/download.html')
            return
    except IOError, e:
        print "Couldn't check version number - " + str(e)

    try:
        response = bdecode(response)
        response1 = response
        t(response)
    except ValueError, e:
        print_exc()
        resultfunc(false, "got bad publication response - " + str(e))
        return
    file = config['saveas']
    file_length = response['length']
    if file == '':
        file = filefunc(response['name'], file_length)
    if file is None:
        return
    try:
        if path.exists(file):
            statusfunc(activity = 'checking existing file...')
            resuming = true
        else:
            statusfunc(activity = 'allocating new file...')
            resuming = false
        r = [0]
        finflag = Event()
        def finished(result, errormsg = None, fatal = false, resultfunc = resultfunc, finflag = finflag, doneflag = doneflag):
            if doneflag.isSet():
                return
            finflag.set()
            if fatal:
                doneflag.set()
            resultfunc(result, errormsg)
        blobs = SingleBlob(file, file_length, response['pieces'], 
            response['piece length'], finished, open, path.exists, path.getsize)
        left = blobs.get_amount_left()
    except ValueError, e:
        print_exc()
        resultfunc(false, 'bad data for making blob store - ' + str(e))
        return
    except IOError, e:
        print_exc()
        resultfunc(false, 'disk access error - ' + str(e))
        return
    rawserver = RawServer(config['max_poll_period'], doneflag,
        config['timeout'])
    choker = Choker(config['max_uploads'], rawserver.add_task, config['choke_interval'],
        lambda c: c.get_download().rate)
    def make_upload(connection, choker = choker, blobs = blobs, 
            max_slice_length = config['max_slice_length'],
            max_rate_period = config['max_rate_period']):
        return Upload(connection, choker, blobs, max_slice_length,
            max_rate_period)
    ratemeasure = RateMeasure(left)
    dd = DownloaderData(blobs, config['download_slice_size'], ratemeasure.data_came_in)
    def make_download(connection, data = dd, 
            backlog = config['request_backlog'],
            max_rate_period = config['max_rate_period']):
        return Download(connection, data, backlog, max_rate_period)
    connecter = Connecter(make_upload, make_download, choker)
    seed(entropy(20))
    encrypter = Encrypter(connecter, rawserver, lambda e = entropy: e(20),
        entropy(20), config['max_message_length'], rawserver.add_task, 
        config['keepalive_interval'])
    listen_port = config['port']
    if listen_port == 0:
        listen_port = randrange(5000, 10000)
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
        url = urljoin(response['url'], response['announce'])
        response = readput(url, a)
        t2(response)
        if response['type'] == 'failure':
            resultfunc(false, "Couldn't announce - " + response['reason'])
            return
        DownloaderFeedback(choker, rawserver.add_task, 
            listen_port, response['your ip'], statusfunc, 
            config['max_rate_recalculate_interval'], ratemeasure.get_time_left, 
            ratemeasure.get_size_left, file_length, finflag)
    except IOError, e:
        print_exc()
        resultfunc(false, "Couldn't announce - " + str(e))
        return
    except ValueError, e:
        print_exc()
        resultfunc(false, "got bad announcement response - " + str(e))
        return
    try:
        statusfunc(activity = 'connecting to peers...')
        rawserver.start_listening(encrypter, listen_port, false)
    except socket.error, e:
        print_exc()
        resultfunc(false, "Couldn't listen - " + str(e))
        return
        
    if response1.has_key('finish'):
        try:
            a = {'type': 'finished', 'id': response1['id'], 'myid': myid}
            if r[0]:
                a['result'] = 'success'
            else:
                a['result'] = 'failure'
            url = urljoin(response1['url'], response1['finish'])
            readput(url, a)
        except IOError, e:
            print_exc()
            pass
    return r[0]
