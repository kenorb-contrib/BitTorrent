# Written by Bram Cohen
# see LICENSE.txt for license information

from zurllib import urlopen
from urlparse import urljoin
from btformats import check_message
from Choker import Choker
from Storage import Storage
from StorageWrapper import StorageWrapper
from Uploader import Upload
from Downloader import Downloader
from HTTPDownloader import HTTPDownloader
from Connecter import Connecter
from Encrypter import Encoder
from RawServer import RawServer, autodetect_ipv6, autodetect_socket_style
from Rerequester import Rerequester
from DownloaderFeedback import DownloaderFeedback
from RateMeasure import RateMeasure
from CurrentRateMeasure import Measure
from PiecePicker import PiecePicker
from Statistics import Statistics
from bencode import bencode, bdecode
from sha import sha
from os import path, makedirs, listdir
from parseargs import parseargs, formatDefinitions, defaultargs
from socket import error as socketerror
from random import seed
from threading import Thread, Event
from time import time
from __init__ import createPeerID

true = 1
false = 0

defaults = [
    ('max_uploads', 7,
        "the maximum number of uploads to allow at once."),
    ('keepalive_interval', 120.0,
        'number of seconds to pause between sending keepalives'),
    ('download_slice_size', 2 ** 14,
        "How many bytes to query for per request."),
    ('request_backlog', 10,
        "maximum number of requests to keep in a single pipe at once."),
    ('max_message_length', 2 ** 23,
        "maximum length prefix encoding you'll accept over the wire - larger values get the connection dropped."),
    ('ip', '',
        "ip to report you have to the tracker."),
    ('minport', 6881, 'minimum port to listen on, counts up if unavailable'),
    ('maxport', 6999, 'maximum port to listen on'),
    ('responsefile', '',
        'file the server response was stored in, alternative to url'),
    ('url', '',
        'url to get file from, alternative to responsefile'),
    ('saveas', '',
        'local file name to save the file as, null indicates query user'),
    ('timeout', 300.0,
        'time to wait between closing sockets which nothing has been received on'),
    ('timeout_check_interval', 60.0,
        'time to wait between checking if any connections have timed out'),
    ('max_slice_length', 2 ** 17,
        "maximum length slice to send to peers, larger requests are ignored"),
    ('max_rate_period', 20.0,
        "maximum amount of time to guess the current rate estimate represents"),
    ('bind', '', 
        'comma-separated list of ips/hostnames to bind to locally'),
#    ('ipv6_enabled', autodetect_ipv6(),
    ('ipv6_enabled', 0,
         'allow the client to connect to peers via IPv6'),
    ('ipv6_binds_v4', autodetect_socket_style(),
        'set if an IPv6 server socket will also field IPv4 connections'),
    ('upload_rate_fudge', 5.0, 
        'time equivalent of writing to kernel-level TCP buffer, for rate adjustment'),
    ('display_interval', .5,
        'time between updates of displayed information'),
    ('rerequest_interval', 5 * 60,
        'time to wait between requesting more peers'),
    ('min_peers', 20, 
        'minimum number of peers to not do rerequesting'),
    ('http_timeout', 60, 
        'number of seconds to wait before assuming that an http connection has timed out'),
    ('max_initiate', 40,
        'number of peers at which to stop initiating new connections'),
    ('check_hashes', 1,
        'whether to check hashes on disk'),
    ('max_upload_rate', 0,
        'maximum kB/s to upload at, 0 means no limit'),
    ('alloc_type', 'normal',
        'allocation type (may be normal, background, pre-allocate or sparse)'),
    ('alloc_rate', 2.0,
        'rate (in MiB/s) to allocate space at using background allocation'),
    ('snub_time', 30.0,
        "seconds to wait for data to come in over a connection before assuming it's semi-permanently choked"),
    ('spew', 0,
        "whether to display diagnostic info to stdout"),
    ('rarest_first_cutoff', 2,
        "number of downloads at which to switch from random to rarest first"),
    ('rarest_first_priority_cutoff', 3,
        'the number of peers which need to have a piece before other partials take priority over rarest first'),
    ('min_uploads', 4,
        "the number of uploads to fill out to with extra optimistic unchokes"),
    ('max_files_open', 50,
        'the maximum number of files to keep open at a time, 0 means no limit'),
    ('round_robin_period', 30,
        "the number of seconds between the client's switching upload targets"),
    ('super_seeder', 0,
        "whether to use special upload-efficiency-maximizing routines (only for dedicated seeds)"),
    ('security', 1,
        "whether to enable extra security features intended to prevent abuse"),
    ('max_connections', 0,
        "the absolute maximum number of peers to connect with (0 = no limit)"),
    ('auto_kick', 1,
        "whether to allow the client to automatically kick/ban peers that send bad data"),
    ('double_check', 1,
        "whether to double-check data being written to the disk for errors (may increase CPU load)"),
    ('triple_check', 0,
        "whether to thoroughly check data being written to the disk (may slow disk access)"),
    ('lock_files', 1,
        "whether to lock files the client is working with"),
    ('lock_while_reading', 0,
        "whether to lock access to files being read"),
    ]



def download(*argv, **kws):
    d=Download()
    d.download(*argv, **kws)

class Download:
    def __init__(self):
        self.defaultargs = defaultargs(defaults)
        self.argslistheader = 'arguments are:\n'
        self.unpauseflag = Event()
        self.unpauseflag.set()
        self.storagewrapper = None
        self.super_seeding_active = false
        self.config = None
        self.filedatflag = Event()
        self.spewflag = Event()
        self.superseedflag = Event()
        self.whenpaused = None

    def download(self, params, filefunc, statusfunc, finfunc, errorfunc, doneflag, cols,
                 pathFunc = None, presets = {}, exchandler = None):

        self.errorfunc = errorfunc
        self.finfunc = finfunc

        def failed(reason, errorfunc = errorfunc, doneflag = doneflag):
            doneflag.set()
            if reason is not None:
                errorfunc(reason)

        if len(params) == 0:
            failed(self.argslistheader + formatDefinitions(defaults, cols))
            return
        try:
            config, args = parseargs(params, defaults, 0, 1, presets = presets)
            if args:
                if config['responsefile'] or config['url']:
                    raise ValueError,'must have responsefile or url as arg or parameter, not both'
                if path.isfile(args[0]):
                    config['responsefile'] = args[0]
                else: 
                    config['url'] = args[0]
            if (config['responsefile'] == '') == (config['url'] == ''):
                raise ValueError, 'need responsefile or url, must have one, cannot have both'
            config['max_upload_rate'] *= 1000
            self.config = config
        except ValueError, e:
            failed('error: ' + str(e) + '\nrun with no args for parameter explanations')
            return

        if config['spew']:
            self.spewflag.set()
        if config['super_seeder']:
            self.superseedflag.set()

        try:
            if config['responsefile'] != '':
                h = open(config['responsefile'], 'rb')
                try:
                    line = h.read(10)   # quick test to see if responsefile contains a dict
                    front,garbage = line.split(':',1)
                    assert front[0] == 'd'
                    n = int(front[1:])
                except:
                    failed(config['responsefile']+' is not a valid responsefile')
                    return
                try:
                    h.seek(0)
                except:
                    h.close()
                    h = open(config['responsefile'], 'rb')
            else:
                try:
                    h = urlopen(config['url'])
                except:
                    failed(config['url']+' bad url')
                    return
            response = h.read()
            h.close()
        except IOError, e:
            failed('problem getting response info - ' + str(e))
            return

        try:
            response = bdecode(response)
            check_message(response)
        except ValueError, e:
            failed("got bad file info - " + str(e))
            return

        self.response = response

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

                # if this path exists, and no files from the info dict exist, we assume it's a new download and 
                # the user wants to create a new directory with the default name
                existing = 0
                if path.exists(file):
                    if not path.isdir(file):
                        failed(file + 'is not a dir')
                        return
                    if len(listdir(file)) > 0:  # if it's not empty
                        for x in info['files']:
                            if path.exists(path.join(file, x['path'][0])):
                                existing = 1
                        if not existing:
                            file = path.join(file, info['name'])
                            if path.exists(file) and not path.isdir(file):
                                if file[-8:] == '.torrent':
                                    file = file[:-8]
                                if path.exists(file) and not path.isdir(file):
                                    failed("Can't create dir - " + info['name'])
                                    return

                make(file, true)

                # alert the UI to any possible change in path
                if pathFunc != None:
                    pathFunc(file)

                files = []
                for x in info['files']:
                    n = file
                    for i in x['path']:
                        n = path.join(n, i)
                    files.append((n, x['length']))
                    make(n)
        except OSError, e:
            failed("Couldn't allocate dir - " + str(e))
            return

        try:
            v,garbage = version.split(' ',1)
            garbage,v = v.split('-',1)
            v += '.'
        except:
            v = ''

        myid = createPeerID()
        seed(myid)
        pieces = [info['pieces'][x:x+20] for x in xrange(0, len(info['pieces']), 20)]
        rawserver = RawServer(doneflag, config['timeout_check_interval'],
                              config['timeout'], ipv6_enable = config['ipv6_enabled'],
                              failfunc = failed, errorfunc = exchandler)
        self.rawserver = rawserver

        finflag = Event()
        self.finflag = finflag

        try:
            try:
                storage = Storage(files, open, path.exists, statusfunc, doneflag, config)
                self.storage = storage
            except IOError, e:
                failed('trouble accessing files - ' + str(e))
                return
            if doneflag.isSet():
                return

            ann = [lambda x: None]
            def finished(self = self, ann = ann):
                if self.superseedflag.isSet():
                    self._set_super_seed()
                self.finflag.set()
                self.config['round_robin_period'] = max( self.config['round_robin_period'],
                    int(self.config['round_robin_period']
                        * self.response['info']['piece length']/(200000)) )
                try:
                    self.storage.set_readonly()
                except (IOError, OSError), e:
                    self.errorfunc('trouble setting readonly at end - ' + str(e))
                ann[0](1)
                self.finfunc()

            rm = [lambda x: None]
            def data_flunked(amount, index, rm = rm, errorfunc = errorfunc, doneflag = doneflag):
                rm[0](amount)
                if not doneflag.isSet():
                    errorfunc('piece %d failed hash check, re-downloading it' % index)
            storagewrapper = StorageWrapper(storage, config['download_slice_size'],
                pieces, info['piece length'], finished, failed, statusfunc, doneflag,
                config['check_hashes'], data_flunked, rawserver.external_add_task,
                config, self.unpauseflag)
            self.storagewrapper = storagewrapper
        except ValueError, e:
            failed('bad data - ' + str(e))
        except IOError, e:
            failed('IOError - ' + str(e))
        if doneflag.isSet():
            return

        e = 'maxport less than minport - no ports to check'
        for listen_port in xrange(config['minport'], config['maxport'] + 1):
            try:
                rawserver.bind(listen_port, config['bind'],
                               ipv6_socket_style = config['ipv6_binds_v4'])
                break
            except socketerror, e:
                pass
        else:
            failed("Couldn't listen - " + str(e))
            return

        picker = PiecePicker(len(pieces), config['rarest_first_cutoff'],
                             config['rarest_first_priority_cutoff'])
        for i in xrange(len(pieces)):
            if storagewrapper.do_I_have(i):
                picker.complete(i)
        choker = Choker(config, rawserver.add_task, picker, finflag.isSet)
        self.choker = choker
        upmeasure = Measure(config['max_rate_period'],
            config['upload_rate_fudge'])
        downmeasure = Measure(config['max_rate_period'])
        def make_upload(connection, choker = choker,
                storagewrapper = storagewrapper, picker = picker,
                max_slice_length = config['max_slice_length'],
                max_rate_period = config['max_rate_period'],
                fudge = config['upload_rate_fudge']):
            return Upload(connection, choker, storagewrapper, picker,
                max_slice_length, max_rate_period, fudge)
        ratemeasure = RateMeasure(storagewrapper.get_amount_left())
        rm[0] = ratemeasure.data_rejected

        def kickpeer(connection, self = self):
            def k(connection = connection):
                connection.close()
            self.rawserver.add_task(k,0)
        bp = [lambda x: None]
        def banpeer(ip, self = self, bp = bp):
            bp[0](ip)
        downloader = Downloader(storagewrapper, picker,
            config['request_backlog'], config['max_rate_period'],
            len(pieces), config['download_slice_size'], downmeasure, config['snub_time'],
            config['auto_kick'], kickpeer, banpeer, ratemeasure.data_came_in)
        self.downloader = downloader

        infohash = sha(bencode(info)).digest()

        connecter = Connecter(make_upload, downloader, choker,
            len(pieces), upmeasure, config, rawserver.add_task)
        self.connecter = connecter
        encoder = Encoder(connecter, rawserver,
            myid, config['max_message_length'], rawserver.add_task,
            config['keepalive_interval'], infohash, config)
        bp[0] = encoder.ban

        if response.has_key('announce-list'):
            trackerlist = response['announce-list']
        else:
            trackerlist = [[response['announce']]]

        rerequest = Rerequester(trackerlist, config['rerequest_interval'], 
            rawserver.add_task, connecter.how_many_connections, 
            config['min_peers'], encoder.start_connection, 
            rawserver.external_add_task, storagewrapper.get_amount_left, 
            upmeasure.get_total, downmeasure.get_total, listen_port, 
            config['ip'], myid, infohash, config['http_timeout'], errorfunc, 
            config['max_initiate'], doneflag, upmeasure.get_rate, downmeasure.get_rate)
        self.rerequest = rerequest
        ann[0] = rerequest.announce

        httpdownloader = HTTPDownloader(storagewrapper, picker,
            rawserver, finflag, errorfunc, downloader, config['max_rate_period'],
            infohash, downmeasure, connecter.got_piece, ratemeasure.data_came_in)
        if response.has_key('httpseeds') and not finflag.isSet():
            for u in response['httpseeds']:
                httpdownloader.make_download(u)

        statistics = Statistics(upmeasure,downmeasure,connecter,
                                httpdownloader,rerequest,self.filedatflag)
        if info.has_key('files'):
            statistics.set_dirstats(files, len(pieces), info['piece length'])

        DownloaderFeedback(choker, httpdownloader, rawserver.add_task, statusfunc,
            upmeasure.get_rate, downmeasure.get_rate, ratemeasure.get_time_left, 
            ratemeasure.get_size_left, file_length, finflag,
            config['display_interval'], self.spewflag, statistics)

        if not finflag.isSet():
            statusfunc(activity = 'connecting to peers')
        rerequest.d(0)

        rawserver.listen_forever(encoder)
        storage.close()
        rerequest.announce(2)

    def setUploadRate(self, rate):
        try:
            def s(self = self, rate = rate):
                self.config['max_upload_rate'] = rate
            self.rawserver.external_add_task(s)
        except AttributeError:
            pass

    def setConns(self, conns):
        try:
            def s(self = self, conns = conns):
                self.config['min_uploads'] = conns
                self.config['max_uploads'] = conns
                if (conns > 30):
                    self.config['max_initiate'] = conns + 10
            self.rawserver.external_add_task(s)
        except AttributeError:
            pass

    def setInitiate(self, initiate):
        try:
            def s(self = self, initiate = initiate):
                self.config['max_initiate'] = initiate
            self.rawserver.external_add_task(s)
        except AttributeError:
            pass

    def getConfig(self):
        return self.config

    def getDefaults(self):
        return self.defaultargs

    def getUsageText(self):
        return self.argslistheader

    def reannounce(self, special = None):
        try:
            def r(self = self, special = special):
                if special is None:
                    self.rerequest.announce()
                else:
                    self.rerequest.announce(specialurl = special)
            self.rawserver.external_add_task (r)
        except AttributeError:
            pass

    def getResponse(self):
        try:
            return self.response
        except:
            return None

    def Pause(self):
        try:
            if self.storagewrapper:
                self.rawserver.external_add_task(self._pausemaker, 0)
        except:
            return false
        self.unpauseflag.clear()
        return true

    def _pausemaker(self):
        self.whenpaused = time()
        self.unpauseflag.wait()   # sticks a monkey wrench in the main thread

    def Unpause(self):
        self.unpauseflag.set()
        if self.whenpaused and time()-self.whenpaused > 60:
            def r(self = self):
                self.rerequest.announce(3)      # rerequest automatically if paused for >60 seconds
            self.rawserver.external_add_task(r)

    def set_super_seed(self):
        try:
            self.superseedflag.set()
            def s(self = self):
                if self.finflag.isSet():
                    self._set_super_seed()
            self.rawserver.external_add_task(s)
        except AttributeError:
            pass

    def _set_super_seed(self):
        if not self.super_seeding_active:
            self.super_seeding_active = true
            self.errorfunc('        ** SUPER-SEED OPERATION ACTIVE **\n' +
                           '  please set Max uploads so each peer gets 6-8 kB/s')
            def s(self = self):
                self.downloader.set_super_seed()
                self.choker.set_super_seed()
            self.rawserver.external_add_task(s)
            if self.finflag.isSet():        # mode started when already finished
                def r(self = self):
                    self.rerequest.announce(3)  # so after kicking everyone off, reannounce
                self.rawserver.external_add_task(r)
