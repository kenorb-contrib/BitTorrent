# Written by Bram Cohen
# see LICENSE.txt for license information

from zurllib import urlopen
from urlparse import urlparse
from BT1.btformats import check_message
from BT1.Choker import Choker
from BT1.Storage import Storage
from BT1.StorageWrapper import StorageWrapper
from BT1.Uploader import Upload
from BT1.Downloader import Downloader
from BT1.HTTPDownloader import HTTPDownloader
from BT1.Connecter import Connecter
from RateLimiter import RateLimiter
from BT1.Encrypter import Encoder
from RawServer import RawServer, autodetect_ipv6, autodetect_socket_style
from BT1.Rerequester import Rerequester
from BT1.DownloaderFeedback import DownloaderFeedback
from RateMeasure import RateMeasure
from CurrentRateMeasure import Measure
from BT1.PiecePicker import PiecePicker
from BT1.Statistics import Statistics
from bencode import bencode, bdecode
from sha import sha
from os import path, makedirs, listdir
from parseargs import parseargs, formatDefinitions, defaultargs
from socket import error as socketerror
from random import seed
from threading import Thread, Event
from time import time
from __init__ import createPeerID

try:
    True
except:
    True = 1
    False = 0

defaults = [
    ('max_uploads', 7,
        "the maximum number of uploads to allow at once."),
    ('keepalive_interval', 120.0,
        'number of seconds to pause between sending keepalives'),
    ('download_slice_size', 2 ** 14,
        "How many bytes to query for per request."),
    ('upload_unit_size', 1460,
        "when limiting upload rate, how many bytes to send at a time"),
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
    ('upnp_nat_access', 0,
        'attempt to autoconfigure a UPnP router to forward a server port'),
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
    ('buffer_reads', 1,
        'whether to buffer disk reads'),
    ('write_buffer_size', 4,
        'the maximum amount of space to use for buffering disk writes ' +
        '(in megabytes, 0 = disabled)'),
    ('snub_time', 30.0,
        "seconds to wait for data to come in over a connection before assuming it's semi-permanently choked"),
    ('spew', 0,
        "whether to display diagnostic info to stdout"),
    ('rarest_first_cutoff', 2,
        "number of downloads at which to switch from random to rarest first"),
    ('rarest_first_priority_cutoff', 5,
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

argslistheader = 'Arguments are:\n\n'


# old-style downloader
def download(self, params, filefunc, statusfunc, finfunc, errorfunc, doneflag, cols,
             pathFunc = None, presets = {}, exchandler = None):

    try:
        config = parse_params(params, presets)
    except ValueError, e:
        failed('error: ' + str(e) + '\nrun with no args for parameter explanations')
        return
    if not config:
        errorfunc(get_usage())
        return
    
    myid = createPeerID()
    seed(myid)

    rawserver = RawServer(doneflag, config['timeout_check_interval'],
                          config['timeout'], ipv6_enable = config['ipv6_enabled'],
                          failfunc = failed, errorfunc = exchandler)

    try:
        listen_port = rawserver.find_and_bind(config['minport'], config['maxport'],
                        config['bind'], ipv6_socket_style = config['ipv6_binds_v4'],
                        upnp = config['upnp_nat_access'])
    except socketerror, e:
        failed("Couldn't listen - " + str(e))
        return

    response = get_response(config['responsefile'], config['url'], failed)
    if not response:
        return

    infohash = sha(bencode(response['info'])).digest()

    d = BT1Download(statusfunc, finfunc, errorfunc, exchandler, doneflag,
                    config, response, infohash, myid, rawserver, listen_port)

    if not d.saveAs(filefunc):
        return

    if pathFunc:
        pathFunc(d.getFilename())

    if not d.initFiles(old_style = True):
        return
    if not d.startEngine():
        return
    d.startRerequester()
    d.autoStats()

    statusfunc(activity = 'connecting to peers')

    if paramfunc:
        paramfunc({ 'max_upload_rate' : d.setUploadRate,  # change_max_upload_rate(<int KiB/sec>)
                    'max_uploads': d.setConns, # change_max_uploads(<int max uploads>)
                    'listen_port' : listen_port, # int
                    'peer_id' : myid, # string
                    'info_hash' : infohash, # string
                    'start_connection' : d._startConnection, # start_connection((<string ip>, <int port>), <peer id>)
                    })
        
    rawserver.listen_forever(d.getPortHandler())
    
    d.shutdown()


def parse_params(params, presets = {}):
    if len(params) == 0:
        return None
    config, args = parseargs(params, defaults, 0, 1, presets = presets)
    if args:
        if config['responsefile'] or config['url']:
            raise ValueError,'must have responsefile or url as arg or parameter, not both'
        if path.isfile(args[0]):
            config['responsefile'] = args[0]
        else:
            try:
                urlparse(args[0])
            except:
                raise ValueError, 'bad filename or url'
            config['url'] = args[0]
    elif (config['responsefile'] == '') == (config['url'] == ''):
        raise ValueError, 'need responsefile or url, must have one, cannot have both'
    return config


def get_usage(defaults = defaults, cols = 100):
    return (argslistheader + formatDefinitions(defaults, cols))


def get_response(file, url, failfunc):
    try:
        if file:
            h = open(file, 'rb')
            try:
                line = h.read(10)   # quick test to see if responsefile contains a dict
                front,garbage = line.split(':',1)
                assert front[0] == 'd'
                int(front[1:])
            except:
                failfunc(file+' is not a valid responsefile')
                return None
            try:
                h.seek(0)
            except:
                h.close()
                h = open(file, 'rb')
        else:
            try:
                h = urlopen(url)
            except:
                failfunc(url+' bad url')
                return None
        response = h.read()
        h.close()
    
    except IOError, e:
        failfunc('problem getting response info - ' + str(e))
        return None
    
    try:
        response = bdecode(response)
        check_message(response)
    except ValueError, e:
        failfunc("got bad file info - " + str(e))
        return None

    return response


class BT1Download:    
    def __init__(self, statusfunc, finfunc, errorfunc, excfunc, doneflag,
                 config, response, infohash, id, rawserver, port):
        self.statusfunc = statusfunc
        self.finfunc = finfunc
        self.errorfunc = errorfunc
        self.excfunc = excfunc
        self.doneflag = doneflag
        self.config = config
        self.response = response
        self.infohash = infohash
        self.myid = id
        self.rawserver = rawserver
        self.port = port
        
        self.info = self.response['info']
        self.pieces = [self.info['pieces'][x:x+20]
                       for x in xrange(0, len(self.info['pieces']), 20)]
        self.len_pieces = len(self.pieces)
        self.argslistheader = argslistheader
        self.unpauseflag = Event()
        self.unpauseflag.set()
        self.storagewrapper = None
        self.super_seeding_active = False
        self.filedatflag = Event()
        self.spewflag = Event()
        self.superseedflag = Event()
        self.whenpaused = None
        self.finflag = Event()
        self.rerequest = None
        self.rerequest_complete = lambda: None
        self.rerequest_stopped = lambda: None


    def saveAs(self, filefunc, pathfunc = None):
        try:
            def make(f, forcedir = False):
                if not forcedir:
                    f = path.split(f)[0]
                if f != '' and not path.exists(f):
                    makedirs(f)

            if self.info.has_key('length'):
                file_length = self.info['length']
                file = filefunc(self.info['name'], file_length,
                                self.config['saveas'], False)
                if file is None:
                    return False
                make(file)
                files = [(file, file_length)]
            else:
                file_length = 0
                for x in self.info['files']:
                    file_length += x['length']
                file = filefunc(self.info['name'], file_length,
                                self.config['saveas'], True)
                if file is None:
                    return False

                # if this path exists, and no files from the info dict exist, we assume it's a new download and 
                # the user wants to create a new directory with the default name
                existing = 0
                if path.exists(file):
                    if not path.isdir(file):
                        self.errorfunc(file + 'is not a dir')
                        return False
                    if len(listdir(file)) > 0:  # if it's not empty
                        for x in self.info['files']:
                            if path.exists(path.join(file, x['path'][0])):
                                existing = 1
                        if not existing:
                            file = path.join(file, self.info['name'])
                            if path.exists(file) and not path.isdir(file):
                                if file[-8:] == '.torrent':
                                    file = file[:-8]
                                if path.exists(file) and not path.isdir(file):
                                    self.errorfunc("Can't create dir - " + self.info['name'])
                                    return False
                make(file, True)

                # alert the UI to any possible change in path
                if pathfunc != None:
                    pathfunc(file)

                files = []
                for x in self.info['files']:
                    n = file
                    for i in x['path']:
                        n = path.join(n, i)
                    files.append((n, x['length']))
                    make(n)
        except OSError, e:
            self.errorfunc("Couldn't allocate dir - " + str(e))
            return False

        self.filename = file
        self.files = files
        self.datalength = file_length

        return True
    

    def getFilename(self):
        return self.filename


    def initFiles(self, old_style = False, statusfunc = None):
        if self.doneflag.isSet():
            return None
        if not statusfunc:
            statusfunc = self.statusfunc

        def failed(reason, self = self):
            self.doneflag.set()
            if reason is not None:
                self.errorfunc(reason)
        try:
            try:
                self.storage = Storage(self.files, open, path.exists,
                                       statusfunc, self.doneflag, self.config)
            except IOError, e:
                self.errorfunc('trouble accessing files - ' + str(e))
                return None
            if self.doneflag.isSet():
                return None

            def finished(self = self):
                self.finflag.set()
                try:
                    self.storage.set_readonly()
                except (IOError, OSError), e:
                    self.errorfunc('trouble setting readonly at end - ' + str(e))
                if self.superseedflag.isSet():
                    self._set_super_seed()
                self.config['round_robin_period'] = max( self.config['round_robin_period'],
                    int(self.config['round_robin_period']
                        * self.info['piece length']/(200000)) )
                self.rerequest_complete()
                self.finfunc()

            self.ratemeasure_datarejected = [lambda x: None]
            def data_flunked(amount, index, self = self):
                self.ratemeasure_datarejected(amount)
                if not self.doneflag.isSet():
                    self.errorfunc('piece %d failed hash check, re-downloading it' % index)
            self.storagewrapper = StorageWrapper(self.storage, self.config['download_slice_size'],
                self.pieces, self.info['piece length'], finished, failed, statusfunc, self.doneflag,
                self.config['check_hashes'], data_flunked, self.rawserver.external_add_task,
                self.config, self.unpauseflag)
            if old_style:
                self.storagewrapper.old_style_init()
            
        except ValueError, e:
            failed('bad data - ' + str(e))
        except IOError, e:
            failed('IOError - ' + str(e))
        if self.doneflag.isSet():
            return None

        return self.storagewrapper.initialize


    def startEngine(self, ratelimiter = None, statusfunc = None):
        if self.doneflag.isSet():
            return False
        if not statusfunc:
            statusfunc = self.statusfunc

        self.picker = PiecePicker(self.len_pieces, self.config['rarest_first_cutoff'],
                             self.config['rarest_first_priority_cutoff'])
        for i in xrange(self.len_pieces):
            if self.storagewrapper.do_I_have(i):
                self.picker.complete(i)
        self.choker = Choker(self.config, self.rawserver.add_task,
                             self.picker, self.finflag.isSet)
        self.upmeasure = Measure(self.config['max_rate_period'],
                            self.config['upload_rate_fudge'])
        self.downmeasure = Measure(self.config['max_rate_period'])

        if ratelimiter:
            self.ratelimiter = ratelimiter
        else:
            self.ratelimiter = RateLimiter(self.rawserver.add_task,
                                           self.config['upload_unit_size'])
            self.ratelimiter.set_upload_rate(self.config['max_upload_rate'])
        
        def make_upload(connection, ratelimiter, totalup, self = self):
            return Upload(connection, ratelimiter, totalup,
                          self.choker, self.storagewrapper, self.picker,
                          self.config['max_slice_length'], self.config['max_rate_period'],
                          self.config['upload_rate_fudge'], self.config['buffer_reads'])
        self.ratemeasure = RateMeasure(self.storagewrapper.get_amount_left())
        self.ratemeasure_datarejected = self.ratemeasure.data_rejected

        def kickpeer(connection, self = self):
            def k(connection = connection):
                connection.close()
            self.rawserver.add_task(k,0)

        self.encoder_ban = [lambda x: None]
        def banpeer(ip, self = self):
            self.encoder_ban(ip)
        self.downloader = Downloader(self.storagewrapper, self.picker,
            self.config['request_backlog'], self.config['max_rate_period'],
            self.len_pieces, self.config['download_slice_size'], self.downmeasure,
            self.config['snub_time'], self.config['auto_kick'],
            kickpeer, banpeer, self.ratemeasure.data_came_in)

        self.connecter = Connecter(make_upload, self.downloader, self.choker,
                            self.len_pieces, self.upmeasure, self.config,
                            self.ratelimiter, self.rawserver.add_task)
        self.encoder = Encoder(self.connecter, self.rawserver,
            self.myid, self.config['max_message_length'], self.rawserver.add_task,
            self.config['keepalive_interval'], self.infohash, self.config)
        self.encoder_ban = self.encoder.ban

        self.httpdownloader = HTTPDownloader(self.storagewrapper, self.picker,
            self.rawserver, self.finflag, self.errorfunc, self.downloader,
            self.config['max_rate_period'], self.infohash, self.downmeasure,
            self.connecter.got_piece, self.ratemeasure.data_came_in)
        if self.response.has_key('httpseeds') and not self.finflag.isSet():
            for u in self.response['httpseeds']:
                self.httpdownloader.make_download(u)

        return True


    def startRerequester(self):
        if self.response.has_key('announce-list'):
            trackerlist = self.response['announce-list']
        else:
            trackerlist = [[self.response['announce']]]

        self.rerequest = Rerequester(trackerlist, self.config['rerequest_interval'], 
            self.rawserver.add_task, self.connecter.how_many_connections, 
            self.config['min_peers'], self.encoder.start_connections,
            self.rawserver.external_add_task, self.storagewrapper.get_amount_left, 
            self.upmeasure.get_total, self.downmeasure.get_total, self.port, self.config['ip'],
            self.myid, self.infohash, self.config['http_timeout'],
            self.errorfunc, self.excfunc, self.config['max_initiate'],
            self.doneflag, self.upmeasure.get_rate, self.downmeasure.get_rate)

        def rerequest_complete(self = self):
            self.rerequest.announce(1)
        self.rerequest_complete = rerequest_complete

        def rerequest_stopped(self = self):
            self.rerequest.announce(2)
        self.rerequest_stopped = rerequest_stopped

        self.rerequest.d(0)


    def _init_stats(self):
        def lastfailedfunc(self=self):
            if self.rerequest:
                return self.rerequest.last_failed
            return False
        self.statistics = Statistics(self.upmeasure, self.downmeasure,
                    self.connecter, self.httpdownloader,
                    lastfailedfunc, self.filedatflag)
        if self.info.has_key('files'):
            self.statistics.set_dirstats(self.files, self.len_pieces, self.info['piece length'])
        if self.config['spew']:
            self.spewflag.set()

    def autoStats(self, displayfunc = None):
        if not displayfunc:
            displayfunc = self.statusfunc

        self._init_stats()
        DownloaderFeedback(self.choker, self.httpdownloader, self.rawserver.add_task,
            self.upmeasure.get_rate, self.downmeasure.get_rate,
            self.ratemeasure.get_time_left, self.ratemeasure.get_size_left,
            self.datalength, self.finflag, self.spewflag, self.statistics,
            displayfunc, self.config['display_interval'])

    def startStats(self):
        self._init_stats()
        d = DownloaderFeedback(self.choker, self.httpdownloader, self.rawserver.add_task,
            self.upmeasure.get_rate, self.downmeasure.get_rate,
            self.ratemeasure.get_time_left, self.ratemeasure.get_size_left,
            self.datalength, self.finflag, self.spewflag, self.statistics)
        return d.gather


    def getPortHandler(self):
        return self.encoder

    def shutdown(self):
        self.storage.close()
        self.rerequest_stopped()


    def setUploadRate(self, rate):
        try:
            def s(self = self, rate = rate):
                self.config['max_upload_rate'] = rate
                self.ratelimiter.set_upload_rate(rate)
            self.rawserver.external_add_task(s)
        except AttributeError:
            pass

    def setConns(self, conns, conns2 = None):
        if not conns2:
            conns2 = conns
        try:
            def s(self = self, conns = conns, conns2 = conns2):
                self.config['min_uploads'] = conns
                self.config['max_uploads'] = conns2
                if (conns > 30):
                    self.config['max_initiate'] = conns + 10
            self.rawserver.external_add_task(s)
        except AttributeError:
            pass
        
    def startConnection(self, ip, port, id):
        self.encrypter._start_connection((ip, port), id)
      
    def _startConnection(self, ipandport, id):
        self.encrypter._start_connection(ipandport, id)
        
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
        return defaultargs(defaults)

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
            return False
        self.unpauseflag.clear()
        return True

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
            self.super_seeding_active = True
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