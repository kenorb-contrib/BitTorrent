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

# Written by Bram Cohen, Uoti Urpala, John Hoffman, and David Harrison

from __future__ import division

from BitTorrent.platform import install_translation
install_translation()

import pdb
import sys
import os
import threading
from time import strftime, sleep
from cStringIO import StringIO
import logging
from logging import ERROR

import traceback
import BitTorrent
from BitTorrent import inject_main_logfile
from BitTorrent.MultiTorrent import Feedback, MultiTorrent
from BitTorrent.defaultargs import get_defaults
from BitTorrent.parseargs import printHelp
from BitTorrent.zurllib import urlopen
from BitTorrent.prefs import Preferences
from BitTorrent import configfile
from BitTorrent import BTFailure
from BitTorrent import version
from BitTorrent import console, stderr_console
from BitTorrent import GetTorrent
from BitTorrent.RawServer_twisted import RawServer, task
from BitTorrent.ConvertedMetainfo import ConvertedMetainfo
from BitTorrent import filesystem_encoding
from BitTorrent.platform import get_temp_dir
#debug = False
debug = True

inject_main_logfile()

def wrap_log(context_string, logger):
    """Useful when passing a logger to a deferred's errback.  The context
       specifies what was being done when the exception was raised."""
    return lambda e, *args, **kwargs : logger.error(context_string, exc_info=e)


def fmttime(n):
    if n == 0:
        return _("download complete!")
    try:
        n = int(n)
        assert n >= 0 and n < 5184000  # 60 days
    except:
        return _("<unknown>")
    m, s = divmod(n, 60)
    h, m = divmod(m, 60)
    return _("finishing in %d:%02d:%02d") % (h, m, s)

def fmtsize(n):
    s = str(n)
    size = s[-3:]
    while len(s) > 3:
        s = s[:-3]
        size = '%s,%s' % (s[-3:], size)
    if n > 999:
        unit = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
        i = 1
        while i + 1 < len(unit) and (n >> 10) >= 999:
            i += 1
            n >>= 10
        n /= (1 << 10)
        size = '%s (%.0f %s)' % (size, n, unit[i])
    return size


class HeadlessDisplayer(object):

    def __init__(self, doneflag):
        self.doneflag = doneflag

        self.done = False
        self.percentDone = ''
        self.timeEst = ''
        self.downRate = '---'
        self.upRate = '---'
        self.shareRating = ''
        self.seedStatus = ''
        self.peerStatus = ''
        self.errors = []
        self.file = ''
        self.downloadTo = ''
        self.fileSize = ''
        self.numpieces = 0

    def set_torrent_values(self, name, path, size, numpieces):
        self.file = name
        self.downloadTo = path
        self.fileSize = fmtsize(size)
        self.numpieces = numpieces

    def finished(self):
        self.done = True
        self.downRate = '---'
        self.display({'activity':_("download succeeded"), 'fractionDone':1})

    def error(self, errormsg):
        newerrmsg = strftime('[%H:%M:%S] ') + errormsg
        self.errors.append(newerrmsg)
        print errormsg
        #self.display({})    # display is only called periodically.

    def display(self, statistics):
        fractionDone = statistics.get('fractionDone')
        activity = statistics.get('activity')
        timeEst = statistics.get('timeEst')
        downRate = statistics.get('downRate')
        upRate = statistics.get('upRate')
        spew = statistics.get('spew')

        print '\n\n\n\n'
        if spew is not None:
            self.print_spew(spew)

        if timeEst is not None:
            self.timeEst = fmttime(timeEst)
        elif activity is not None:
            self.timeEst = activity

        if fractionDone is not None:
            self.percentDone = str(int(fractionDone * 1000) / 10)
        if downRate is not None:
            self.downRate = '%.1f KB/s' % (downRate / (1 << 10))
        if upRate is not None:
            self.upRate = '%.1f KB/s' % (upRate / (1 << 10))
        downTotal = statistics.get('downTotal')
        if downTotal is not None:
            upTotal = statistics['upTotal']
            if downTotal <= upTotal / 100:
                self.shareRating = _("oo  (%.1f MB up / %.1f MB down)") % (
                    upTotal / (1<<20), downTotal / (1<<20))
            else:
                self.shareRating = _("%.3f  (%.1f MB up / %.1f MB down)") % (
                   upTotal / downTotal, upTotal / (1<<20), downTotal / (1<<20))
            #numCopies = statistics['numCopies']
            #nextCopies = ', '.join(["%d:%.1f%%" % (a,int(b*1000)/10) for a,b in
            #        zip(xrange(numCopies+1, 1000), statistics['numCopyList'])])
            if not self.done:
                self.seedStatus = _("%d seen now") % statistics['numSeeds']
            #    self.seedStatus = _("%d seen now, plus %d distributed copies"
            #                        "(%s)") % (statistics['numSeeds' ],
            #                                   statistics['numCopies'],
            #                                   nextCopies)
            else:
                self.seedStatus = ""
            #    self.seedStatus = _("%d distributed copies (next: %s)") % (
            #        statistics['numCopies'], nextCopies)
            self.peerStatus = _("%d seen now") % statistics['numPeers']

        if not self.errors:
            print _("Log: none")
        else:
            print _("Log:")
        for err in self.errors[-4:]:
            print err 
        print    
        print _("saving:        "), self.file
        print _("file size:     "), self.fileSize
        print _("percent done:  "), self.percentDone
        print _("time left:     "), self.timeEst
        print _("download to:   "), self.downloadTo
        print _("download rate: "), self.downRate
        print _("upload rate:   "), self.upRate
        print _("share rating:  "), self.shareRating
        print _("seed status:   "), self.seedStatus
        print _("peer status:   "), self.peerStatus

    def print_spew(self, spew):
        s = StringIO()
        s.write('\n\n\n')
        for c in spew:
            s.write('%20s ' % c['ip'])
            if c['initiation'] == 'L':
                s.write('l')
            else:
                s.write('r')
            total, rate, interested, choked = c['upload']
            s.write(' %10s %10s ' % (str(int(total/10485.76)/100),
                                     str(int(rate))))
            if c['is_optimistic_unchoke']:
                s.write('*')
            else:
                s.write(' ')
            if interested:
                s.write('i')
            else:
                s.write(' ')
            if choked:
                s.write('c')
            else:
                s.write(' ')

            total, rate, interested, choked, snubbed = c['download']
            s.write(' %10s %10s ' % (str(int(total/10485.76)/100),
                                     str(int(rate))))
            if interested:
                s.write('i')
            else:
                s.write(' ')
            if choked:
                s.write('c')
            else:
                s.write(' ')
            if snubbed:
                s.write('s')
            else:
                s.write(' ')
            s.write('\n')
        print s.getvalue()


#class TorrentApp(Feedback):
class TorrentApp(object):

    class LogHandler(logging.Handler):
        def __init__(self, app, level=logging.NOTSET):
            logging.Handler.__init__(self,level)
            self.app = app
      
        def emit(self, record):
            self.app.display_error(record.getMessage() ) 
            if record.exc_info is not None:
                self.app.display_error( " %s: %s" % ( str(record.exc_info[0]),
                                                      str(record.exc_info[1])))
                tb = record.exc_info[2]
                stack = traceback.extract_tb(tb)
                l = traceback.format_list(stack)
                for s in l:
                    self.app.display_error( " %s" % s )

    class LogFilter(logging.Filter):
        def filter( self, record):
            if record.name == "NatTraversal":
                return 0
            return 1  # allow.

    def __init__(self, metainfo, config):
        assert isinstance(metainfo, ConvertedMetainfo )
        self.metainfo = metainfo
        self.config = Preferences().initWithDict(config)
        self.torrent = None
        self.multitorrent = None
        self.logger = logging.getLogger("bittorrent-console")
        self.log_handler = TorrentApp.LogHandler(self)
        logger  = logging.getLogger()
        logger.addHandler(self.log_handler)

        # disable stdout and stderr error reporting.
        logging.getLogger().removeHandler(console)
        if stderr_console is not None:
            logging.getLogger().removeHandler(stderr_console)
        logging.getLogger().setLevel(0)

    def start_torrent(self,metainfo,save_incomplete_as,save_as):
        """Tells the MultiTorrent to begin downloading."""
        #df = launch_coroutine(
        #    _wrap_task(self.multitorrent.rawserver.add_task),
        #    self._start_torrent, metainfo, save_incomplete_as, save_as)
        #df.addErrback( wrap_log('Failed to start torrent', self.logger))
        self._create_torrent(metainfo,save_incomplete_as,save_as)
        self.multitorrent.rawserver.add_task( 1, self._start_torrent,metainfo )

    def _create_torrent( self, metainfo, save_incomplete_as, 
                         save_as ):
        try:
            # HEREDAVE:
            # We have a race condition. The torrent might still be intializing
            # from resumed state when this start_torrent is called.
            #
            # In the future there will be an INITIALIZING state.  If the
            # torrent is INITIALIZING, I could then install a policy that
            # will force it to start whenever the create_torrent completes.
            #
            # Another way is to rewrite bittorrent-curses based on Torrent
            # and avoid all of the MultiTorrent stuff.
            #
            # For now I will simply periodically check whether
            # initialized is complete before trying to start (see call
            # to raw_server.add_task in start_torrent).
            if not self.multitorrent.torrent_known(metainfo.infohash):
                self.logger.debug("creating torrent")
                df = self.multitorrent.create_torrent(metainfo, 
                                                      save_incomplete_as,
                                                      save_as)
                #yield df
                #df.getResult()  # raises exception if one occurred in yield.
                #self.logger.debug( "Torrent's state is now: %s" % 
                #    self.multitorrent.get_torrent(metainfo.infohash).state )
                
        except KeyboardInterrupt:
            raise
        except Exception, e:
            self.logger.error( "Failed to create torrent", exc_info = e )
            return

    def _start_torrent(self, metainfo):
        try:
            t = None
            if self.multitorrent.torrent_known( metainfo.infohash ):
              t = self.multitorrent.get_torrent(metainfo.infohash)
        
            # HACK!! Rewrite when INITIALIZING state is available.
            if t is None or not t.is_initialized():
                self.logger.debug( "Waiting for torrent to initialize." )
                self.multitorrent.rawserver.add_task(3,
                    self._start_torrent, metainfo)
                return

            if not self.multitorrent.torrent_running(metainfo.infohash):
                self.logger.debug("starting torrent")
                df = self.multitorrent.start_torrent(metainfo.infohash)
                #yield df
                #df.getResult()  # raises exception if one occurred in yield.
            
            if not self.torrent:
                self.torrent = self.multitorrent.get_torrent(metainfo.infohash)
                
        except KeyboardInterrupt:
            raise
        except Exception, e:
            self.logger.error("Failed to start torrent", exc_info = e)
            self.logger.debug("  Torrent's state is %s" % 
                self.multitorrent.get_torrent(metainfo.infohash).state )

        
    def run(self):
        core_doneflag = threading.Event()
        rawserver_doneflag = threading.Event()
        self.d = HeadlessDisplayer(core_doneflag)
        rawserver = RawServer(self.config)
        rawserver.install_sigint_handler(core_doneflag)
     
        try:
          try:
            # raises BTFailure if bad
            metainfo = self.metainfo
            torrent_name = metainfo.name_fs.decode(filesystem_encoding)
            if config['save_as']:
                if config['save_in']:
                    raise BTFailure(_("You cannot specify both --save_as and "
                                      "--save_in"))
                saveas = config['save_as'].decode('utf-8')
                saveas = saveas.encode(filesystem_encoding)
                savein = os.path.dirname(os.path.abspath(saveas))
            elif config['save_in']:
                savein = config['save_in'].decode('utf-8')
                savein = savein.encode(filesystem_encoding)
                saveas = os.path.join(savein,torrent_name)
            else:
                saveas = torrent_name
            if config['save_incomplete_in']:
                save_incomplete_in=config['save_incomplete_in'].decode('utf-8')
                save_incomplete_in = \
                    save_incomplete_in.encode(filesystem_encoding)
                save_incomplete_as = os.path.join(
                    config['save_incomplete_in'].decode('utf-8'),torrent_name)
            else:
                save_incomplete_as = os.path.join(savein,torrent_name)
        
            data_dir = config['data_dir']
            self.multitorrent = \
                MultiTorrent(self.config, core_doneflag, rawserver, data_dir )
                
            self.d.set_torrent_values(metainfo.name, os.path.abspath(saveas),
                                metainfo.total_bytes, len(metainfo.hashes))
            self.start_torrent(self.metainfo, save_incomplete_as, saveas)
        
            self.get_status()
          except:
            core_doneflag.set()
            raise

        finally:
            l = None
            def shutdown_check():
                if core_doneflag.isSet():  # ctrl-c will set this flag.
                   self.d.display({'activity':_("shutting down"), 
                                   'fractionDone':0})
                   if self.multitorrent:
                       df = self.multitorrent.shutdown()
                       set_flag = lambda *a : rawserver_doneflag.set()
                       df.addCallbacks(set_flag, set_flag)
                   else:
                       rawserver_doneflag.set()
                   l.stop()
                    
            l = task.LoopingCall(shutdown_check)
            rawserver.add_task(0, l.start, 1)
            rawserver.listen_forever(rawserver_doneflag)

    def get_status(self):
        self.multitorrent.rawserver.add_task(self.config['display_interval'],
                                             self.get_status)
        if self.torrent is not None:
            status = self.torrent.get_status(self.config['spew'])
            self.d.display(status)

    def display_error(self, text):
        """Called by the logger via LogHandler to display error messages in the
           curses window."""
        self.d.error(text)



if __name__ == '__main__':
    uiname = 'bittorrent-console'
    defaults = get_defaults(uiname)

    metainfo = None
    if len(sys.argv) <= 1:
        printHelp(uiname, defaults)
        sys.exit(1)
    try:
        config, args = configfile.parse_configuration_and_args(defaults,
                                       uiname, sys.argv[1:], 0, 1)

        if debug:
            # SUPER HACK
            #args = ["c:/Documents and Settings/David Harrison/Desktop/one-archives-vol-1-enhanced.torrent"]
            args = ["c:/Documents and Settings/David Harrison/Desktop/flyabout.m4v.torrent"]
            config['upnp'] = False

        torrentfile = None
        if len(args):
            torrentfile = args[0]
        if torrentfile is not None:
            try:
                metainfo = GetTorrent.get(torrentfile)
            except GetTorrent.GetTorrentException, e:
                raise BTFailure(_("Error reading .torrent file: ") + '\n' + str(e))
        else:
            raise BTFailure(_("you must specify a .torrent file"))
    except BTFailure, e:
        print str(e)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)

    app = TorrentApp(metainfo, config)
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception, e:
        logging.getLogger().exception(e)

    sleep(3)
    if threading.activeCount() > 1:
       print "active threads:"
       for th in threading.enumerate():
          print th
