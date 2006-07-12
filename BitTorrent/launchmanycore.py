#!/usr/bin/env python

# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Original version written by John Hoffman, heavily modified for different
# multitorrent architecture by Uoti Urpala (over 40% shorter than original),
# ported to new MultiTorrent (circa 4.20) by David Harrison.

from __future__ import division
from BitTorrent.translation import _

import os
from cStringIO import StringIO
from traceback import print_exc
import logging
from BitTorrent import configfile
from BitTorrent.parsedir import parsedir
from BitTorrent.MultiTorrent import MultiTorrent, Feedback
from BitTorrent.ConvertedMetainfo import ConvertedMetainfo
from BitTorrent import BTFailure, UserFailure
from BitTorrent.RawServer_twisted import RawServer
from BitTorrent.yielddefer import launch_coroutine, _wrap_task
from BitTorrent.ConvertedMetainfo import ConvertedMetainfo
from BitTorrent.defer import DeferredEvent
from time import time


#class LaunchMany(Feedback):
class LaunchMany(object):

    def __init__(self, config, display, configfile_key):
      """Starts torrents for all .torrent files in a directory tree.

         All errors are logged using Python logging to 'configfile_key' logger.

         @param config: Preferences object storing config.
         @param display: output function for stats.
      """
      # 4.4.x version of LaunchMany output exceptions to a displayer.
      # This version only outputs stats to the displayer.  We do not use
      # the logger to output stats so that a caller-provided object
      # can provide stats formatting as opposed to using the
      # logger Formatter, which is specific to exceptions, warnings, and
      # info messages.
      try:
        self.logger = logging.getLogger(configfile_key)
        
        self.multitorrent = None
        self.rawserver = None
        self.config = config
        self.configfile_key = configfile_key
        self.display = display

        self.torrent_dir = config['torrent_dir']

        # Ex: torrent_cache = infohash ->
        #   {path:'/a/c.torrent',file:'c.torrent',length:90911,name:'Sea'}
        self.torrent_cache = {}

        # maps path -> [(modification time, size), infohash]
        self.file_cache = {}

        # used as set containing paths of files that do not have separate
        # entries in torrent_cache either because torrent_cache already
        # contains the torrent or because the torrent file is corrupt.
        self.blocked_files = {}

        #self.torrent_list = [] 
        #self.downloads = {}

        self.hashcheck_queue = []
        self.hashcheck_store = {}
        self.hashcheck_current = None
                         
        self.core_doneflag = DeferredEvent()
        rawserver_doneflag = DeferredEvent() 
        self.rawserver = RawServer(self.config)
        try:
   
            # set up shut-down procedure before we begin doing things that
            # can throw exceptions.
            def shutdown():
                print "SHUTDOWNSHUTDOWNSHUTDOWN"
                self.logger.critical(_("shutting down"))
                for infohash in self.multitorrent.get_torrents():
                    self.logger.info(_('dropped "%s"') %
                                    self.torrent_cache[infohash]['path'])
                #    torrent = self.downloads[infohash]
                #    if torrent is not None:
                #        torrent.shutdown()
                if self.multitorrent:
                    df = self.multitorrent.shutdown()
                    set_flag = lambda *a : rawserver_doneflag.set()
                    df.addCallbacks(set_flag, set_flag)
                else:
                    rawserver_doneflag.set()
                
            # It is safe to addCallback here, because there is only one thread,
            # but even if the code were multi-threaded, core_doneflag has not
            # been passed to anyone.  There is no chance of a race condition
            # between the DeferredEvent's callback and addCallback.
            self.core_doneflag.addCallback(
                lambda r: self.rawserver.external_add_task(0, shutdown))
   
            self.rawserver.install_sigint_handler(self.core_doneflag)
    
            data_dir = config['data_dir']
            print "Creating MultiTorrent"
            self.multitorrent = MultiTorrent(config, self.rawserver, data_dir)
    
            self.rawserver.add_task(0, self.scan)
            self.rawserver.add_task(0, self.stats)
            self.rawserver.add_task(1, self.check_hashcheck_queue)
            
            try:
                import signal
                def handler(signum, frame):
                    self.rawserver.external_add_task(0, self.read_config)
                signal.signal(signal.SIGHUP, handler)
            except Exception, e:
                self.logger.error(_("Could not set signal handler: ") +
                                    unicode(e.args[0]))
                self.rawserver.add_task(0,self.core_doneflag.set())
  
        except UserFailure, e:
            output.exception(unicode(e.args[0]))
            self.rawserver.add_task(0,self.core_doneflag.set())
        except:
            data = StringIO()
            print_exc(file = data)
            output.exception(data.getvalue())
            self.rawserver.add_task(0,self.core_doneflag.set())
           
        # always make sure events get processed even if only for
        # shutting down.
        print "listening forever"
        self.rawserver.listen_forever(rawserver_doneflag)
        
      except:
        data = StringIO()
        print_exc(file = data)
        output.exception(data.getvalue())

    def scan(self):
        print "LaunchMany.scan top."
        self.rawserver.add_task(self.config['parse_dir_interval'], self.scan)

        r = parsedir(self.torrent_dir, self.torrent_cache,
                     self.file_cache, self.blocked_files,
                     self.logger.error)

        print "After parsedir"
        ( self.torrent_cache, self.file_cache, self.blocked_files,
            added, removed ) = r
        for infohash, data in removed.items():
            self.logger.info(_('dropped "%s"') % data['path'])
            self.remove(infohash)
        for infohash, data in added.items():
            print "adding item:", data['path']
            self.logger.info(_('added "%s"'  ) % data['path'])
            print "after self.logger.info"
            if self.config['launch_delay'] > 0:
                self.rawserver.add_task(self.config['launch_delay'], self.add, infohash, data)
            # torrent may have been known from resume state.
            elif not self.multitorrent.torrent_known(infohash):
                self.add(infohash, data)
        print "LaunchMany.scan bottom"

    def stats(self):
        self.rawserver.add_task(self.config['display_interval'], self.stats)
        data = []
        for d in self.get_torrents():
            infohash = d.infohash
            cache = self.torrent_cache[infohash]
            if self.config['display_path']:
                name = cache['path']
            else:
                name = cache['name']
            size = cache['length']
            #d = self.downloads[infohash]
            progress = '0.0%'
            peers = 0
            seeds = 0
            seedsmsg = "S"
            dist = 0.0
            uprate = 0.0
            dnrate = 0.0
            upamt = 0
            dnamt = 0
            t = 0
            msg = ''
            #if d.state in ["created", "initializing"]:
            #    status = _("waiting for hash check")
            #else:
            stats = d.get_status()
            status = stats['activity']
            progress = '%.1f%%' % (int(stats['fractionDone']*1000)/10.0)
            if d.is_running():
                s = stats
                dist = s['numCopies']
                if d.is_seed:
                    seeds = 0 # s['numOldSeeds']
                    seedsmsg = "s"
                else:
                    if s['numSeeds'] + s['numPeers']:
                        t = stats['timeEst']
                        if t is None:
                            t = -1
                        if t == 0:  # unlikely
                            t = 0.01
                        status = _("downloading")
                    else:
                        t = -1
                        status = _("connecting to peers")
                    seeds = s['numSeeds']
                    dnrate = stats['downRate']
                peers = s['numPeers']
                uprate = stats['upRate']
                upamt = s['upTotal']
                dnamt = s['downTotal']

            data.append(( name, status, progress, peers, seeds, seedsmsg, dist,
                          uprate, dnrate, upamt, dnamt, size, t, msg ))
        stop = self.display(data)
        if stop:
            self.core_doneflag.set()

    def remove(self, infohash):
        self.torrent_list.remove(infohash)
        if self.downloads[infohash] is not None:
            self.downloads[infohash].shutdown()
        self.was_stopped(infohash)
        del self.downloads[infohash]

    def add(self, infohash, data):

        # data is a dict like
        # { path:'/a/b/c.torrent', file:'c.torrent', length:90911, name:'Sea',
        #   metainfo: <metainfo>}  Metainfo has bdecoded but not passed
        # to ConvertedMetainfo.
        self.torrent_list.append(infohash)
        self.downloads[infohash] = None
        self.hashcheck_queue.append(infohash)
        self.hashcheck_store[infohash] = ConvertedMetainfo(data['metainfo'])
        self.check_hashcheck_queue()

    def check_hashcheck_queue(self):
        if self.hashcheck_current is not None or not self.hashcheck_queue:
            return
        infohash = self.hashcheck_current = self.hashcheck_queue.pop(0)
        metainfo = self.hashcheck_store[infohash]
        del self.hashcheck_store[infohash]
        filename = self.determine_filename(infohash)
        torrent_path = self.torrent_cache[infohash]['path']
        self.start_torrent(torrent_path, metainfo, filename, filename)

    def start_torrent(self,torrent_path,metainfo,save_incomplete_as,save_as):
        assert isinstance(metainfo, ConvertedMetainfo)
        df = launch_coroutine(_wrap_task(self.rawserver.add_task),
                              self._start_torrent, metainfo,
                              save_incomplete_as, save_as)
        df.addErrback(lambda e : self.logger.error(_("DIED: "),exc_info=e))
        return df

    def _start_torrent(self, metainfo, save_incomplete_as,save_as):
        assert isinstance(metainfo, ConvertedMetainfo)
        df = self.multitorrent.create_torrent(metainfo,
                                              save_incomplete_as, save_as)
        yield df
        torrent = self.multitorrent.get_torrent(metainfo.infohash)
        if torrent.is_initialized():
           multitorrent.start_torrent(metainfo.infohash)
        #else:  ????  # this would be an error condition already reported
                      # to logger.
        check_hashcheck_queue()

    def determine_filename(self, infohash):
        x = self.torrent_cache[infohash]
        name = x['name']
        savein = self.config['save_in']
        isdir = not x['metainfo']['info'].has_key('length')
        style = self.config['saveas_style']
        if style == 4:
            torrentname   = os.path.split(x['path'][:-8])[1]
            suggestedname = name
            if torrentname == suggestedname:
                style = 1
            else:
                style = 3

        if style == 1 or style == 3:
            if savein:
                saveas = os.path.join(savein,x['file'][:-8]) # strip '.torrent'
            else:
                saveas = x['path'][:-8] # strip '.torrent'
            if style == 3 and not isdir:
                saveas = os.path.join(saveas, name)
        else:
            if savein:
                saveas = os.path.join(savein, name)
            else:
                saveas = os.path.join(os.path.split(x['path'])[0], name)
        return saveas

    def was_stopped(self, infohash):
        try:
            self.hashcheck_queue.remove(infohash)
        except:
            pass
        else:
            del self.hashcheck_store[infohash]
        if self.hashcheck_current == infohash:
            self.hashcheck_current = None
        self.check_hashcheck_queue()

    # Exceptions are now reported via loggers.<
    #def global_error(self, level, text):
    #    self.output.message(text)

    # Exceptions are now reported via loggers.
    #def exchandler(self, s):
    #    self.output.exception(s)

    def read_config(self):
        try:
            newvalues = configfile.get_config(self.config, self.configfile_key)
        except Exception, e:
            self.logger.error(_("Error reading config: ") + unicode(e.args[0]) )
            return
        self.logger.info(_("Rereading config file"))
        self.config.update(newvalues)
        # The set_option call can potentially trigger something that kills
        # the torrent (when writing this the only possibility is a change in
        # max_files_open causing an IOError while closing files), and so
        # the self.failed() callback can run during this loop.
        for option, value in newvalues.iteritems():
            self.multitorrent.set_option(option, value)
        for torrent in self.downloads.values():
            if torrent is not None:
                for option, value in newvalues.iteritems():
                    torrent.set_option(option, value)

    # rest are callbacks from torrent instances

    # DEPRECATED. 
    # 'started' is now achieved via a callback on a deferred.
    # 'failed' is now achievecd via an errback on a deferred.
    # 'exception' is now handled via the logging package.
    # Install a root log handler to catch all exceptions.
    #
    #def started(self, torrent):
    #    self.hashcheck_current = None
    #    self.check_hashcheck_queue()
    #
    #def failed(self, torrent):
    #    infohash = torrent.infohash
    #    self.was_stopped(infohash)
    #    if self.torrent_cache.has_key(infohash):
    #        self.output.message('DIED: "'+self.torrent_cache[infohash]['path']+'"')
    #
    #def exception(self, torrent, text):
    #    self.exchandler(text)
