_ = _ # put _ into the module namespace so the console doesn't override it
from twisted.web.xmlrpc import Proxy, XMLRPC, Fault, Binary
from BitTorrent.prefs import Preferences
from BitTorrent.NewTorrentQueue import TorrentQueue, TorrentAlreadyInQueue, TorrentAlreadyRunning, TorrentNotRunning, UnknownInfohash, TorrentShutdownFailed
from BitTorrent.ConvertedMetainfo import ConvertedMetainfo
from BitTorrent.bencode import bdecode

TORRENT_ALREADY_STORED = (201, _("Torrent already on disk."))
TORRENT_ALREADY_CREATED = (203, _("Torrent already created and under control of the seed."))
UNKNOWN_TORRENT = (202,  _("Unknown Torrent"))
TORRENT_NOT_RUNNING = (204, _("Torrent is not running."))
TORRENT_SHUTDOWN_FAILED = (205, _("Torrent shut down failed."))

class XMLRPCTQ(XMLRPC):
    def __init__(self, config, torrent_queue, logger):
        XMLRPC.__init__(self)
        self.config = Preferences(config)
        self.log = logger
        self.port = self.config['xmlrpc_port']
        self.tq = torrent_queue
        
    def xmlrpc_create_torrent(self, torrent, save_incomplete_as, 
                              save_as, shouldstart=False):
        try:
            infohash = self._create_torrent(torrent.data, save_incomplete_as,
                                            save_as)
        except (TorrentAlreadyRunning, TorrentAlreadyInQueue):
            return Fault(*TORRENT_ALREADY_CREATED)
        
        if shouldstart:
            self._start_torrent(infohash)
            
        return Binary(infohash)
    
    def _create_torrent(self, torrent, dlpath):
        d = bdecode(torrent)
        metainfo = ConvertedMetainfo(d)
        self.tq.create_torrent(metainfo, dlpath)
        return metainfo.infohash

    def xmlrpc_start_torrent(self, infohash):
        try:
            df = self._start_torrent(infohash.data)
        except UnknownInfohash:
            return Fault(*UNKNOWN_TORRENT)
        df.addCallback(lambda a: 0)
        return df

    def _start_torrent(self, infohash):
        return self.tq.start_torrent(infohash)
    
    def xmlrpc_stop_torrent(self, infohash):
        infohash = infohash.data
        try:
            self.tq.stop_torrent(infohash)
        except UnknownInfohash:
            return Fault(*UNKNOWN_TORRENT)
        except TorrentNotRunning:
            return Fault(*TORRENT_NOT_RUNNING)
        except TorrentShutdownFailed:
            return Fault(*TORRENT_SHUTDOWN_FAILED)
        return 0
        
    def xmlrpc_get_torrents(self):
         ### returns a list of all torrents in queue order, followed by a list running hashes
        return ([Binary(x) for x in self.tq.get_torrents()], [Binary(x) for x in self.tq.get_running()])
    
    def xmlrpc_get_status(self, infohash, spew=False, fileinfo=False):
        infohash = infohash.data
        try:
            d = self.tq.torrent_status(infohash, spew, fileinfo)
        except UnknownInfohash:
            return Fault(*UNKNOWN_TORRENT)
        except TorrentNotRunning:
            return Fault(*TORRENT_NOT_RUNNING)                
        n = {}
        for key, value in d.iteritems():
            if value != None:
                n[key] = value
        return n

    def xmlrpc_get_log(self, infohash, clear=True):
        try:
            l = self.tq.torrent_log(infohash, clear)
        except UnknownInfohash:
            return Fault(*UNKNOWN_TORRENT)
        except TorrentNotRunning:
            return Fault(*TORRENT_NOT_RUNNING)                
        return l

    def xmlrpc_get_global_log(self, clear=True):
        return self.tq.get_log(clear)
    
    def xmlrpc_set_torrent_option(self, infohash, option, value):
        infohash = infohash.data
        try:
            self.tq.set_config(self, option, value, infohash)
        except UnknownInfohash:
            return Fault(*UNKNOWN_TORRENT)
        return 0
    
