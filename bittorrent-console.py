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

app_name = "BitTorrent"
from BitTorrent.translation import _
import sys
import os
from cStringIO import StringIO
import logging
from logging import ERROR, WARNING
from time import strftime, sleep
import traceback
from BitTorrent import platform
import BTL.stackthreading as threading
from BTL.platform import decode_from_filesystem, encode_for_filesystem
from BTL.defer import DeferredEvent
from BitTorrent import inject_main_logfile
from BitTorrent.MultiTorrent import Feedback, MultiTorrent
from BitTorrent.defaultargs import get_defaults
from BitTorrent.parseargs import printHelp
from BTL.zurllib import urlopen
from BitTorrent.prefs import Preferences
from BitTorrent import configfile
from BitTorrent import BTFailure, UserFailure
from BitTorrent import version
from BTL import GetTorrent
from BTL.ConvertedMetainfo import ConvertedMetainfo
from BitTorrent.MultiTorrent import TorrentNotInitialized
from BitTorrent.RawServer_twisted import RawServer, task
from BitTorrent.UI import Size, Duration
inject_main_logfile()
from BitTorrent import console
from BitTorrent import stderr_console  # must import after inject_main_logfile
                                       # because import is really a copy.
                                       # If imported earlier, stderr_console
                                       # doesn't reflect the changes made in 
                                       # inject_main_logfile!!  BAAAHHHH!!

def wrap_log(context_string, logger):
    """Useful when passing a logger to a deferred's errback.  The context
       specifies what was being done when the exception was raised."""
    return lambda e, *args, **kwargs : logger.error(context_string, exc_info=e)


def fmttime(n):
    if n == 0:
        return _("download complete!")
    return _("finishing in %s") % (str(Duration(n)))

def fmtsize(n):
    s = str(n)
    size = s[-3:]
    while len(s) > 3:
        s = s[:-3]
        size = '%s,%s' % (s[-3:], size)
    size = '%s (%s)' % (size, str(Size(n)))
    return size


class HeadlessDisplayer(object):

    def __init__(self):
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
                self.app.display_error( " %s: %s" % 
                    ( str(record.exc_info[0]), str(record.exc_info[1])))
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
        log_handler = TorrentApp.LogHandler(self)
        log_handler.setLevel(WARNING)
        logger = logging.getLogger()
        logger.addHandler(log_handler)

        # disable stdout and stderr error reporting to stderr.
        global stderr_console
        logging.getLogger('').removeHandler(console)
        if stderr_console is not None:
            logging.getLogger('').removeHandler(stderr_console)
        logging.getLogger().setLevel(WARNING)

    def start_torrent(self,metainfo,save_incomplete_as,save_as):
        """Tells the MultiTorrent to begin downloading."""
        try:
            self.d.display({'activity':_("initializing"), 
                               'fractionDone':0})
            multitorrent = self.multitorrent
            df = multitorrent.create_torrent(metainfo, save_incomplete_as,
                                             save_as)
            df.addErrback( wrap_log('Failed to start torrent', self.logger))
            def create_finished(torrent):
                self.torrent = torrent
                if self.torrent.is_initialized():
                   multitorrent.start_torrent(self.torrent.infohash)
                else:
                    # HEREDAVE: why should this set the doneflag?
                   self.core_doneflag.set()  # e.g., if already downloading...
            df.addCallback( create_finished )
        except KeyboardInterrupt:
            raise
        except UserFailure, e:
            self.logger.error( "Failed to create torrent: " + unicode(e.args[0]) )
        except Exception, e:
            self.logger.error( "Failed to create torrent", exc_info = e )
            return
        
    def run(self):
        self.core_doneflag = DeferredEvent()
        rawserver = RawServer(self.config)
        self.d = HeadlessDisplayer()

        # set up shut-down procedure before we begin doing things that
        # can throw exceptions.
        def shutdown():
            print "shutdown."
            self.d.display({'activity':_("shutting down"), 
                            'fractionDone':0})
            if self.multitorrent:
                df = self.multitorrent.shutdown()
                stop_rawserver = lambda *a : rawserver.stop()
                df.addCallbacks(stop_rawserver, stop_rawserver)
            else:
                rawserver.stop()

        # It is safe to addCallback here, because there is only one thread,
        # but even if the code were multi-threaded, core_doneflag has not
        # been passed to anyone.  There is no chance of a race condition
        # between core_doneflag's callback and addCallback.
        self.core_doneflag.addCallback(
            lambda r: rawserver.external_add_task(0, shutdown))
        
        rawserver.install_sigint_handler(self.core_doneflag)


        # semantics for --save_in vs --save_as:
        #   save_in specifies the directory in which torrent is written.
        #      If the torrent is a batch torrent then the files in the batch
        #      go in save_in/metainfo.name_fs/.
        #   save_as specifies the filename for the torrent in the case of
        #      a non-batch torrent, and specifies the directory name
        #      in the case of a batch torrent.  Thus the files in a batch
        #      torrent go in save_as/.
        metainfo = self.metainfo
        torrent_name = metainfo.name_fs  # if batch then this contains
                                         # directory name.

        if config['save_as']:
            if config['save_in']:
                raise BTFailure(_("You cannot specify both --save_as and "
                                  "--save_in."))
            saveas,bad = platform.encode_for_filesystem(config['save_as'])
            if bad:
                raise BTFailure(_("Invalid path encoding."))
            savein = os.path.dirname(os.path.abspath(saveas))
        elif config['save_in']:
            savein,bad = platform.encode_for_filesystem(config['save_in'])
            if bad:
                raise BTFailure(_("Invalid path encoding."))
            saveas = os.path.join(savein,torrent_name)
        else:
            saveas = torrent_name
        if config['save_incomplete_in']:
            save_incomplete_in,bad = \
                platform.encode_for_filesystem(config['save_incomplete_in'])
            if bad:
                raise BTFailure(_("Invalid path encoding."))
            save_incomplete_as = os.path.join(save_incomplete_in,torrent_name)
        else:
            save_incomplete_as = os.path.join(savein,torrent_name)
    
        data_dir,bad = platform.encode_for_filesystem(config['data_dir'])
        if bad:
            raise BTFailure(_("Invalid path encoding."))

        try: 
            self.multitorrent = \
                MultiTorrent(self.config, rawserver, data_dir,
                             is_single_torrent = True,
                             resume_from_torrent_config = False)
                
            self.d.set_torrent_values(metainfo.name, os.path.abspath(saveas),
                                metainfo.total_bytes, len(metainfo.hashes))
            self.start_torrent(self.metainfo, save_incomplete_as, saveas)
        
            self.get_status()
        except UserFailure, e:
            self.logger.error( unicode(e.args[0]) )
            rawserver.add_task(0, self.core_doneflag.set)
        except Exception, e:
            self.logger.error( "", exc_info = e )
            rawserver.add_task(0, self.core_doneflag.set)
            
        # always make sure events get processed even if only for
        # shutting down.
        rawserver.listen_forever()

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
        # Modifying default values from get_defaults is annoying...
        # Implementing specific default values for each uiname in
        # defaultargs.py is even more annoying.  --Dave
        data_dir = [[name, value,doc] for (name, value, doc) in defaults
                        if name == "data_dir"][0]
        defaults = [(name, value,doc) for (name, value, doc) in defaults
                        if not name == "data_dir"]
        ddir = os.path.join( platform.get_dot_dir(), "console" )
        data_dir[1] = decode_from_filesystem(ddir)
        defaults.append( tuple(data_dir) )
        config, args = configfile.parse_configuration_and_args(defaults,
                                       uiname, sys.argv[1:], 0, 1)

        torrentfile = None
        if len(args):
            torrentfile = args[0]
        if torrentfile is not None:
            try:
                metainfo = GetTorrent.get(torrentfile)
            except GetTorrent.GetTorrentException, e:
                raise UserFailure(_("Error reading .torrent file: ") + '\n' + unicode(e.args[0]))
        else:
            raise UserFailure(_("you must specify a .torrent file"))
    except BTFailure, e:
        print unicode(e.args[0])
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)

    app = TorrentApp(metainfo, config)
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except BTFailure, e:
        print unicode(e.args[0])
    except Exception, e:
        logging.getLogger().exception(e)

    # if after a reasonable amount of time there are still
    # non-daemon threads hanging around then print them.
    nondaemons = [d for d in threading.enumerate() if not d.isDaemon()]
    if len(nondaemons) > 1:
       sleep(4)
       nondaemons = [d for d in threading.enumerate() if not d.isDaemon()]
       if len(nondaemons) > 1:
           print "non-daemon threads not shutting down:"
           for th in nondaemons:
               print " ", th

