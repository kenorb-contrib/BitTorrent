# Written by Bram Cohen
# see LICENSE.txt for license information

from urllib import urlopen, quote
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
from bencode import bencode, bdecode
from sha import sha
from os import path, makedirs
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
    ('bind', None, '', 
        'ip to bind to locally'),
    ('upload_rate_fudge', None, 5.0, 
        'time equivalent of writing to kernel-level TCP buffer, for rate adjustment'),
    ('display_interval', None, .1,
        'time between updates of displayed information'),
    ('rerequest_interval', None, 5 * 60,
        'time to wait between requesting more peers'),
    ('min_peers', None, 10, 
        'minimum number of peers to not do rerequesting'),
    ]

def download(params, filefunc, statusfunc, resultfunc, doneflag, cols):
    if len(params) == 0:
        resultfunc(false, 'arguments are -\n' + formatDefinitions(defaults, cols))
        return
    try:
        config, garbage = parseargs(params, defaults, 0, 0)
        if (config['responsefile'] == '') == (config['url'] == ''):
            raise ValueError, 'need responsefile or url'
    except ValueError, e:
        print_exc()
        resultfunc(false, 'error: ' + str(e) + '\nrun with no args for parameter explanations')
        return
    
    try:
        h = urlopen('http://bitconjurer.org/BitTorrent/status-downloader-02-08-01.txt')
        status = h.read().strip()
        h.close()
        if status != 'current':
            resultfunc(false, 'No longer the latest version - see http://bitconjurer.org/BitTorrent/download.html')
            return
    except IOError, e:
        print "Couldn't check version number - " + str(e)

    try:
        if config['responsefile'] != '':
            h = open(config['responsefile'], 'rb')
        else:
            h = urlopen(config['url'])
        response = h.read()
        h.close()
    except IOError, e:
        resultfunc(false, 'problem getting response info - ' + str(e))
        return

    try:
        response = bdecode(response)
        check_message(response)
    except ValueError, e:
        print_exc()
        resultfunc(false, "got bad file info - " + str(e))
        return
    
    def make(f, forcedir = false, resultfunc = resultfunc):
        try:
            if not forcedir:
                f = path.split(f)[0]
            if f != '' and not path.exists(f):
                makedirs(f)
            return true
        except OSError, e:
            resultfunc(false, "Couldn't allocate dir - " + str(e))
            return false
    info = response['info']
    if info.has_key('length'):
        file_length = info['length']
        file = filefunc(info['name'], file_length, config['saveas'], false)
        if file is None:
            return
        if not make(file):
            return
        files = [(file, file_length)]
    else:
        file_length = 0
        for x in info['files']:
            file_length += x['length']
        file = filefunc(info['name'], file_length, config['saveas'], true)
        if file is None:
            return
        if not make(file, true):
            return
        files = []
        for x in info['files']:
            n = file
            for i in x['path']:
                n = path.join(n, i)
            files.append((n, x['length']))
            if not make(n):
                return
    r = [false]
    finflag = Event()
    ann = [None]
    ip = response['your ip']
    if config['ip'] != '':
        ip = config['ip']
    myid = sha(str(time()) + ' ' + ip).digest()
    seed(myid)
    pieces = [info['pieces'][x:x+20] for x in xrange(0, 
        len(info['pieces']), 20)]
    try:
        storage = Storage(files, open, path.exists, 
            path.getsize, statusfunc)
        def finished(result, errormsg = None, fatal = false, 
                resultfunc = resultfunc, finflag = finflag, 
                doneflag = doneflag, r = r, ann = ann, storage = storage):
            r[0] = result
            if doneflag.isSet():
                return
            finflag.set()
            if fatal:
                doneflag.set()
            if result:
                storage.set_readonly()
                if ann[0] is not None:
                    ann[0](1)
            resultfunc(result, errormsg)
        storagewrapper = StorageWrapper(storage, 
            config['download_slice_size'], pieces, 
            info['piece length'], finished, statusfunc, doneflag)
    except ValueError, e:
        finished(false, str(e), true)
        return
    except IOError, e:
        finished(false, str(e), true)
        return
    if doneflag.isSet():
        return
    rawserver = RawServer(doneflag, config['timeout'])
    def preference(c, finflag = finflag):
        if finflag.isSet():
            return c.get_upload().rate
        return c.get_download().rate
    choker = Choker(config['max_uploads'], rawserver.add_task, 
        preference)
    total_up = [0l]
    total_down = [0l]
    def make_upload(connection, choker = choker, 
            storagewrapper = storagewrapper, 
            max_slice_length = config['max_slice_length'],
            max_rate_period = config['max_rate_period'],
            total_up = total_up, fudge = config['upload_rate_fudge']):
        return Upload(connection, choker, storagewrapper, 
            max_slice_length, max_rate_period, total_up, fudge)
    ratemeasure = RateMeasure(storagewrapper.get_amount_left())
    downloader = Downloader(storagewrapper, 
        config['request_backlog'], config['max_rate_period'],
        len(pieces), total_down, ratemeasure.data_came_in)
    connecter = Connecter(make_upload, downloader.make_download, choker,
        len(pieces))
    encrypter = Encrypter(connecter, rawserver, 
        myid, config['max_message_length'], rawserver.add_task, 
        config['keepalive_interval'], sha(bencode(info)).digest())
    url = response['url']
    if response.has_key('peer url'):
        url = response['peer url']
    Rerequester(url, config['rerequest_interval'], rawserver.add_task,
        connecter.how_many_connections, config['min_peers'],
        encrypter.start_connection, rawserver.external_add_task,
        storagewrapper.get_amount_left, downloader.close_finished)
    DownloaderFeedback(choker, rawserver.add_task, ip, statusfunc, 
        config['max_rate_recalculate_interval'], ratemeasure.get_time_left, 
        ratemeasure.get_size_left, file_length, finflag,
        config['display_interval'])

    for listen_port in xrange(config['minport'], config['maxport'] + 1):
        try:
            rawserver.bind(listen_port, config['bind'])
            break
        except socketerror, e:
            pass
    else:
        resultfunc(false, "Couldn't listen - " + str(e))
        return
    for x in response['peers']:
        encrypter.start_connection((x['ip'], x['port']), x['peer id'])

    if not finflag.isSet():
        statusfunc(activity = 'connecting to peers')
    def announce(event = 3, url = response['announce'], 
            fileid = response['file id'], myid = myid, 
            ip = ip, port = listen_port, 
            up = total_up, down = total_down, 
            storage = storagewrapper):
        s = (('%s?ip=%s&file_id=%s&peer_id=%s&port=%s&event=%s' +
            '&uploaded=%s&downloaded=%s&left=%s') %
            (url, quote(ip), quote(fileid), quote(myid), str(port), 
            ['started', 'completed', 'stopped', ''][event], 
            str(up[0]), str(down[0]), str(storage.get_amount_left())))
        Thread(target = urlopen, args = [s]).start()
    ann[0] = announce

    announce(0)
    regannounce(announce, rawserver.add_task, response['interval'])
    rawserver.listen_forever(encrypter)
    announce(2)
    return r[0]

class regannounce:
    def __init__(self, announce, sched, interval):
        self.announce = announce
        self.sched = sched
        self.interval = interval
        sched(self.c, interval)

    def c(self):
        self.sched(self.c, self.interval)
        self.announce()
