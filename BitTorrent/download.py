# Written by Bram Cohen
# see LICENSE.txt for license information

from urllib import urlopen
from urlparse import urljoin
from StreamEncrypter import make_encrypter
from Choker import Choker
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
from readput import putqueue
from bencode import bencode, bdecode
from btemplate import compile_template, string_template, ListMarker, OptionMarker, exact_length
from sha import sha
from os import path, makedirs
from parseargs import parseargs, formatDefinitions
from socket import error as socketerror
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
    ('ip', 'i', '',
        "ip to report you have to the tracker."),
    ('port', None, 0, 'port to listen on, 0 means scan up from 6881'),
    ('responsefile', None, '',
        'file the server response was stored in, alternative to response and url'),
    ('url', None, '',
        'url to get file from, alternative to response and responsefile'),
    ('saveas', None, '',
        'local file name to save the file as, null indicates query user'),
    ('timeout', None, 300.0,
        'time to wait between closing sockets which nothing has been received on'),
    ('max_slice_length', None, 2 ** 17,
        "maximum length slice to send to peers, larger requests are ignored"),
    ('max_rate_recalculate_interval', None, 15.0,
        "maximum amount of time to let a connection pause before reducing it's rate"),
    ('max_rate_period', None, 20.0,
        "maximum amount of time to guess the current rate estimate represents"),
    ('permanent', None, 0,
        "whether this peer will stop uploading once it's done downloading"),
    ('bind', None, '', 
        'ip to bind to locally'),
    ]

t = compile_template({'info': [{'type': 'single', 
    'pieces': ListMarker(exact_length(20)),
    'piece length': 1, 'length': 0, 'name': string_template}, 
    {'type': 'multiple', 'pieces': ListMarker(exact_length(20)), 
    'piece length': 1, 'files': ListMarker({'path': ListMarker(string_template), 
    'length': 0}), 'name': string_template}], 
    'peers': ListMarker({'ip': string_template, 'port': 1}), 
    'id': string_template, 'announce': string_template, 
    'url': string_template, 'your ip': string_template})

def download(params, filefunc, statusfunc, resultfunc, doneflag, cols):
    if len(params) == 0:
        resultfunc(false, formatDefinitions(defaults, cols))
        return
    try:
        config, garbage = parseargs(params, defaults, 0, 0)
        if config['responsefile'] == '' and config['url'] == '':
            raise ValueError('need responsefile or url')
    except ValueError, e:
        resultfunc(false, 'error: ' + str(e) + '\nrun with no args for parameter explanations')
        return
    
    if config['responsefile'] != '':
        try:
            h = open(config['responsefile'], 'rb')
            response = h.read()
            h.close()
        except IOError, e:
            resultfunc(false, 'IO problem reading response file - ' + str(e))
            return
    else:
        try:
            h = urlopen(config['url'])
            response = h.read()
            h.close()
        except IOError, e:
            resultfunc(false, 'IO problem in initial http request - ' + str(e))
            return false

    try:
        h = urlopen('http://bitconjurer.org/BitTorrent/status-downloader-02-07-00.txt')
        status = h.read().strip()
        h.close()
        if status != 'current':
            resultfunc(false, 'No longer the latest version - see http://bitconjurer.org/BitTorrent/download.html')
            return
    except IOError, e:
        print "Couldn't check version number - " + str(e)

    try:
        response = bdecode(response)
        t(response)
    except ValueError, e:
        resultfunc(false, "got bad publication response - " + str(e))
        return
    info = response['info']
    if info['type'] == 'single':
        file_length = info['length']
        file = filefunc(info['name'], file_length, config['saveas'], false)
        if file is None:
            return
        files = [(file, info['length'])]
    else:
        file_length = 0
        for x in info['files']:
            file_length += x['length']
        file = filefunc(info['name'], file_length, config['saveas'], true)
        if file is None:
            return
        files = []
        for x in info['files']:
            n = file
            for i in x['path']:
                n = path.join(n, i)
            files.append((n, x['length']))
    r = [false]
    finflag = Event()
    def finished(result, errormsg = None, fatal = false, 
            resultfunc = resultfunc, finflag = finflag, 
            doneflag = doneflag, r = r):
        r[0] = result
        if doneflag.isSet():
            return
        finflag.set()
        if fatal:
            doneflag.set()
        resultfunc(result, errormsg)
    def make(f):
        try:
            makedirs(path.split(f)[0])
        except OSError:
            pass
    blobs = SingleBlob(files, info['pieces'], 
        info['piece length'], finished, open, path.exists, 
        path.getsize, doneflag, statusfunc, make)
    if doneflag.isSet():
        return
    left = blobs.get_amount_left()
    rawserver = RawServer(config['max_poll_period'], doneflag,
        config['timeout'])
    def preference(c, finflag = finflag):
        if finflag.isSet():
            return c.get_upload().rate
        return c.get_download().rate
    choker = Choker(config['max_uploads'], rawserver.add_task, 
        preference)
    total_up = [0l]
    total_down = [0l]
    def make_upload(connection, choker = choker, blobs = blobs, 
            max_slice_length = config['max_slice_length'],
            max_rate_period = config['max_rate_period'],
            total_up = total_up):
        return Upload(connection, choker, blobs, max_slice_length,
            max_rate_period, total_up = total_up)
    ratemeasure = RateMeasure(left)
    dd = DownloaderData(blobs, config['download_slice_size'], ratemeasure.data_came_in)
    def make_download(connection, data = dd, 
            backlog = config['request_backlog'],
            max_rate_period = config['max_rate_period'],
            total_down = total_down):
        return Download(connection, data, backlog, max_rate_period,
            total_down = total_down)
    connecter = Connecter(make_upload, make_download, choker)
    seed(entropy(20))
    encrypter = Encrypter(connecter, rawserver, lambda e = entropy: e(20),
        entropy(20), config['max_message_length'], rawserver.add_task, 
        config['keepalive_interval'], sha(bencode(info)).digest())
    DownloaderFeedback(choker, rawserver.add_task, 
        response['your ip'], statusfunc, 
        config['max_rate_recalculate_interval'], ratemeasure.get_time_left, 
        ratemeasure.get_size_left, file_length, finflag)

    if config['port'] == 0:
        r = xrange(6881, 6890)
    else:
        r = [config['port']]
    for listen_port in r:
        try:
            rawserver.bind(listen_port, config['bind'])
            break
        except socketerror, e:
            pass
    else:
        resultfunc(false, "Couldn't listen - " + str(e))
        return
    for x in response['peers']:
        encrypter.start_connection((x['ip'], x['port']))

    if not finflag.isSet():
        statusfunc(activity = 'connecting to peers')
    q = putqueue(response['announce'])
    myid = encrypter.get_id()
    a = {'type': 'announce', 'id': response['id'], 'myid': myid,
            'contact': {'ip': response['your ip'], 'port': listen_port}}
    if config['permanent']:
        a['permanent'] = None
    if config['ip'] != '':
        a['contact']['ip'] = config['ip']
    if blobs.was_preexisting():
        a['left'] = left
    q.addrequest(bencode(a))

    rawserver.listen_forever(encrypter)

    a = {'type': 'finished', 'myid': myid, 
        'uploaded': total_up[0], 'downloaded': total_down[0]}
    if r[0]:
        a['result'] = 'success'
    else:
        a['result'] = 'failure'
    q.addrequest(bencode(a))
