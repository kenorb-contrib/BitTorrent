# Written by Bram Cohen
# see LICENSE.txt for license information

from urllib import urlopen
from urlparse import urljoin
from btformats import check_message
from Choker import Choker
from Storage import Storage
from StorageWrapper import StorageWrapper
from Uploader import Upload
from Downloader import Downloader
from Connecter import Connecter
from Encrypter import Encrypter
from RawServer import RawServer
from Rerequester import Rerequester
from DownloaderFeedback import DownloaderFeedback
from RateMeasure import RateMeasure
from CurrentRateMeasure import Measure
from EndgameDownloader import EndgameDownloader
from bencode import bencode, bdecode
from sha import sha
from os import getpid, path, makedirs
from parseargs import parseargs, formatDefinitions
from socket import error as socketerror
from random import seed
from traceback import print_exc
from threading import Thread, Event
from time import time
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
    ('ip', 'i', '',
        "ip to report you have to the tracker."),
    ('minport', None, 6881, 'minimum port to listen on, counts up if unavailable'),
    ('maxport', None, 6889, 'maximum port to listen on'),
    ('responsefile', None, '',
        'file the server response was stored in, alternative to url'),
    ('url', None, '',
        'url to get file from, alternative to responsefile'),
    ('saveas', None, '',
        'local file name to save the file as, null indicates query user'),
    ('timeout', None, 300.0,
        'time to wait between closing sockets which nothing has been received on'),
    ('timeout_check_interval', None, 60.0,
        'time to wait between checking if any connections have timed out'),
    ('max_slice_length', None, 2 ** 17,
        "maximum length slice to send to peers, larger requests are ignored"),
    ('max_rate_period', None, 20.0,
        "maximum amount of time to guess the current rate estimate represents"),
    ('bind', None, '', 
        'ip to bind to locally'),
    ('upload_rate_fudge', None, 5.0, 
        'time equivalent of writing to kernel-level TCP buffer, for rate adjustment'),
    ('display_interval', None, .1,
        'time between updates of displayed information'),
    ('rerequest_interval', None, 5 * 60,
        'time to wait between requesting more peers'),
    ('min_peers', None, 20, 
        'minimum number of peers to not do rerequesting'),
    ('http_timeout', None, 60, 
        'number of seconds to wait before assuming that an http connection has timed out'),
    ('max_initiate', None, 40,
        'number of peers at which to stop initiating new connections'),
    ('check_hashes', None, 1,
        'whether to check hashes on disk'),
    ('max_upload_rate', None, 0,
        'maximum kB/s to upload at, 0 means no limit'),
    ]

def download(params, filefunc, statusfunc, finfunc, errorfunc, doneflag, cols):
    if len(params) == 0:
        errorfunc('arguments are -\n' + formatDefinitions(defaults, cols))
        return
    try:
        config, garbage = parseargs(params, defaults, 0, 0)
        if (config['responsefile'] == '') == (config['url'] == ''):
            raise ValueError, 'need responsefile or url'
    except ValueError, e:
        errorfunc('error: ' + str(e) + '\nrun with no args for parameter explanations')
        return
    
    try:
        if config['responsefile'] != '':
            h = open(config['responsefile'], 'rb')
        else:
            h = urlopen(config['url'])
        response = h.read()
        h.close()
    except IOError, e:
        errorfunc('problem getting response info - ' + str(e))
        return

    try:
        response = bdecode(response)
        check_message(response)
    except ValueError, e:
        errorfunc("got bad file info - " + str(e))
        return
    
    try:
        def make(f, forcedir = false):
            if not forcedir:
                f = path.split(f)[0]
            if f != '' and not path.exists(f):
                makedirs(f)
        info = response['info']
        if info.has_key('length'):
            file_length = info['length']
            file = filefunc(info['name'], file_length, config['saveas'], false)
            if file is None:
                return
            make(file)
            files = [(file, file_length)]
        else:
            file_length = 0
            for x in info['files']:
                file_length += x['length']
            file = filefunc(info['name'], file_length, config['saveas'], true)
            if file is None:
                return
            make(file, true)
            files = []
            for x in info['files']:
                n = file
                for i in x['path']:
                    n = path.join(n, i)
                files.append((n, x['length']))
                make(n)
    except OSError, e:
        errorfunc("Couldn't allocate dir - " + str(e))
        return
    
    finflag = Event()
    ann = [None]
    myid = sha(repr(time()) + ' ' + str(getpid())).digest()
    seed(myid)
    pieces = [info['pieces'][x:x+20] for x in xrange(0, 
        len(info['pieces']), 20)]
    def failed(reason, errorfunc = errorfunc, doneflag = doneflag):
        doneflag.set()
        if reason is not None:
            errorfunc(reason)
    try:
        try:
            storage = Storage(files, open, path.exists, 
                path.getsize, statusfunc)
        except IOError, e:
            errorfunc('trouble accessing files - ' + str(e))
            return
        def finished(finfunc = finfunc, finflag = finflag, 
                ann = ann, storage = storage, errorfunc = errorfunc):
            finflag.set()
            try:
                storage.set_readonly()
            except (IOError, OSError), e:
                errorfunc('trouble setting readonly at end - ' + str(e))
            if ann[0] is not None:
                ann[0](1)
            finfunc()
        storagewrapper = StorageWrapper(storage, 
            config['download_slice_size'], pieces, 
            info['piece length'], finished, failed, 
            statusfunc, doneflag, config['check_hashes'])
    except ValueError, e:
        failed('bad data - ' + str(e))
    except IOError, e:
        failed('IOError - ' + str(e))
    if doneflag.isSet():
        return

    rawserver = RawServer(doneflag, config['timeout_check_interval'], config['timeout'])
    e = 'maxport less than minport - no ports to check'
    for listen_port in xrange(config['minport'], config['maxport'] + 1):
        try:
            rawserver.bind(listen_port, config['bind'])
            break
        except socketerror, e:
            pass
    else:
        errorfunc("Couldn't listen - " + str(e))
        return

    def preference(c, finflag = finflag):
        if finflag.isSet():
            return c.get_upload().measure.get_rate()
        return c.get_download().measure.get_rate()
    choker = Choker(config['max_uploads'], rawserver.add_task, preference)
    upmeasure = Measure(config['max_rate_period'], 
        config['upload_rate_fudge'])
    downmeasure = Measure(config['max_rate_period'])
    def make_upload(connection, choker = choker, 
            storagewrapper = storagewrapper, 
            max_slice_length = config['max_slice_length'],
            max_rate_period = config['max_rate_period'],
            fudge = config['upload_rate_fudge']):
        return Upload(connection, choker, storagewrapper, 
            max_slice_length, max_rate_period, fudge)
    ratemeasure = RateMeasure(storagewrapper.get_amount_left())
    downloader = Downloader(storagewrapper, 
        config['request_backlog'], config['max_rate_period'],
        len(pieces), downmeasure, ratemeasure.data_came_in)
    connecter = Connecter(make_upload, downloader, choker,
        len(pieces), storagewrapper.is_everything_pending, EndgameDownloader,
        upmeasure, config['max_upload_rate'] * 1024, rawserver.add_task)
    infohash = sha(bencode(info)).digest()
    encrypter = Encrypter(connecter, rawserver, 
        myid, config['max_message_length'], rawserver.add_task, 
        config['keepalive_interval'], infohash, config['max_initiate'])
    rerequest = Rerequester(response['announce'], config['rerequest_interval'], 
        rawserver.add_task, connecter.how_many_connections, 
        config['min_peers'], encrypter.start_connection, 
        rawserver.external_add_task, storagewrapper.get_amount_left, 
        upmeasure.get_total, downmeasure.get_total, listen_port, 
        config['ip'], myid, infohash, config['http_timeout'], errorfunc)
    DownloaderFeedback(choker, rawserver.add_task, statusfunc, 
        upmeasure.get_rate, downmeasure.get_rate, ratemeasure.get_time_left, 
        ratemeasure.get_size_left, file_length, finflag,
        config['display_interval'])

    statusfunc(activity = 'connecting to peers')
    ann[0] = rerequest.announce
    rerequest.d(0)
    rawserver.listen_forever(encrypter)
    rerequest.announce(2)
