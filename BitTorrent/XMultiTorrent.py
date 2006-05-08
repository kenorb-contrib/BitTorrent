# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.
#
# Written by Andrew Loewenstern

import sys
_ = _ # put _ into the module namespace so the console doesn't override it

from twisted.web.xmlrpc import Proxy, XMLRPC, Fault, Binary
from BitTorrent.prefs import Preferences
from BitTorrent.MultiTorrent import MultiTorrent, TorrentAlreadyInQueue, \
     TorrentAlreadyRunning, TorrentNotRunning, UnknownInfohash, \
     TorrentShutdownFailed
from BitTorrent.ConvertedMetainfo import ConvertedMetainfo
from BitTorrent.bencode import bdecode

TORRENT_ALREADY_STORED = (201, _("Torrent already on disk."))
TORRENT_ALREADY_CREATED = (203, _("Torrent already created and under control of the seed."))
UNKNOWN_TORRENT = (202,  _("Unknown Torrent"))
TORRENT_NOT_RUNNING = (204, _("Torrent is not running."))
TORRENT_SHUTDOWN_FAILED = (205, _("Torrent shut down failed."))

class XMultiTorrent(XMLRPC):
    def __init__(self, config, multitorrent, logger):
        XMLRPC.__init__(self)
        self.config = Preferences(config)
        self.log = logger
        self.port = self.config['xmlrpc_port']
        self.multitorrent = multitorrent
        multitorrent.rawserver.create_xmlrpc_socket(self.port, self)
        
    def xmlrpc_create_torrent(self, torrent, save_incomplete_as, 
                              save_as, shouldstart=False):
        """torrent is passed as a Binary object."""
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
        self.multitorrent.create_torrent(metainfo, dlpath)
        return metainfo.infohash

    def xmlrpc_start_torrent(self, infohash):
        try:
            df = self._start_torrent(infohash.data)
        except UnknownInfohash:
            return Fault(*UNKNOWN_TORRENT)
        df.addCallback(lambda a: 0)
        return df

    def _start_torrent(self, infohash):
        return self.multitorrent.start_torrent(infohash)
    
    def xmlrpc_stop_torrent(self, infohash):
        infohash = infohash.data
        try:
            self.multitorrent.stop_torrent(infohash)
        except UnknownInfohash:
            return Fault(*UNKNOWN_TORRENT)
        except TorrentNotRunning:
            return Fault(*TORRENT_NOT_RUNNING)
        except TorrentShutdownFailed:
            return Fault(*TORRENT_SHUTDOWN_FAILED)
        return 0
        
    def xmlrpc_get_torrents(self):
         ### returns a list of all torrents in queue order, followed by a list running hashes
        return ([Binary(x) for x in self.multitorrent.get_torrents()], [Binary(x) for x in self.multitorrent.get_running()])
    
    def xmlrpc_get_status(self, infohash, spew=False, fileinfo=False):
        """@param spew: iff true, returned dict includes the key-value
            pair 'spew : collectedspew' where 'collectedspew' contains
            per-connection statistics, such as whether a connection
            is optimistically unchoked, upload and download measurements,
            and whether a connection was locally or remotely initiated.
            (see DownloaderFeedback.collect_spew).
           @param fileinfo: iff true, returned dict includes the key-value
            pair 'files_left : bytesleftlist' where bytesleftlist is a list
            of integers where each integer corresponds to the bytes remaining
            to be downloaded for a file in the torrent.
           @return: dict
           """

        infohash = infohash.data
        try:
            d = self.multitorrent.torrent_status(infohash, spew, fileinfo)
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
            l = self.multitorrent.torrent_log(infohash, clear)
        except UnknownInfohash:
            return Fault(*UNKNOWN_TORRENT)
        except TorrentNotRunning:
            return Fault(*TORRENT_NOT_RUNNING)                
        return l

    def xmlrpc_get_global_log(self, clear=True):
        return self.multitorrent.get_log(clear)
    
    def xmlrpc_set_torrent_option(self, infohash, option, value):
        infohash = infohash.data

