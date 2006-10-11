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

# Original version written by Henry 'Pi' James, modified by (at least)
# John Hoffman and Uoti Urpala and David Harrison

from __future__ import division

app_name = "BitTorrent"
from BitTorrent.translation import _

SPEW_SCROLL_RATE = 1

import sys
import os
import logging
from logging import ERROR, WARNING
from time import time, strftime, sleep
import traceback

from BitTorrent import platform
from BTL.platform import encode_for_filesystem, decode_from_filesystem
import BTL.stackthreading as threading
from BTL.defer import DeferredEvent
from BitTorrent.MultiTorrent import MultiTorrent, TorrentAlreadyRunning
from BitTorrent.Torrent import Feedback
from BitTorrent.defaultargs import get_defaults
from BitTorrent.parseargs import printHelp
from BTL.zurllib import urlopen
from BitTorrent.prefs import Preferences
from BTL.obsoletepythonsupport import import_curses
from BitTorrent import configfile
from BitTorrent import BTFailure, UserFailure
from BitTorrent import version
from BTL import GetTorrent
from BitTorrent.RawServer_twisted import RawServer, task
from BTL.ConvertedMetainfo import ConvertedMetainfo
from BTL.yielddefer import launch_coroutine, _wrap_task
from BitTorrent import inject_main_logfile
debug = False
#debug = True
inject_main_logfile()
from BitTorrent import console
from BitTorrent import stderr_console  # must import after inject_main_logfile
                                       # because import is really a copy.
                                       # If imported earlier, stderr_console
                                       # doesn't reflect the changes made in 
                                       # inject_main_logfile!! 
                                       # BAAAHHHH!!


def wrap_log(context_string, logger):
    """Useful when passing a logger to a deferred's errback.  The context
       specifies what was being done when the exception was raised."""
    return lambda e, *args, **kwargs : logger.error(context_string, exc_info=e)


try:
    curses = import_curses()
    import curses.panel
    from curses.wrapper import wrapper as curses_wrapper
    from signal import signal, SIGWINCH
except:
    print _("Textmode UI initialization failed, cannot proceed.")
    print
    print _("This download interface requires the standard Python module "
            "\"curses\", which is unfortunately not available for the native "
            "Windows port of Python. It is however available for the Cygwin "
            "port of Python, running on all Win32 systems (www.cygwin.com).")
    print
    print _('You may still use "bittorrent-console" to download.')
    sys.exit(1)

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


class CursesDisplayer(object):

    def __init__(self, scrwin, errlist, doneflag, reread_config, ulrate):
        self.scrwin = scrwin
        self.errlist = errlist
        self.doneflag = doneflag

        signal(SIGWINCH, self.winch_handler)
        self.changeflag = DeferredEvent()

        self.done = False
        self.reread_config = reread_config
        self.ulrate = ulrate
        self.activity = ''
        self.status = ''
        self.progress = ''
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
        self.spew_scroll_time = 0
        self.spew_scroll_pos = 0

        self._remake_window()
        curses.use_default_colors()

    def set_torrent_values(self, name, path, size, numpieces):
        self.file = name
        self.downloadTo = path
        self.fileSize = fmtsize(size)
        self.numpieces = numpieces
        self._remake_window()

    def winch_handler(self, signum, stackframe):
        self.changeflag.set()
        curses.endwin()
        self.scrwin.refresh()
        self.scrwin = curses.newwin(0, 0, 0, 0)
        self._remake_window()

    def _remake_window(self):
        self.scrh, self.scrw = self.scrwin.getmaxyx()
        self.scrpan = curses.panel.new_panel(self.scrwin)
        self.labelh, self.labelw, self.labely, self.labelx = 11, 9, 1, 2
        self.labelwin = curses.newwin(self.labelh, self.labelw,
                                      self.labely, self.labelx)
        self.labelpan = curses.panel.new_panel(self.labelwin)
        self.fieldh, self.fieldw, self.fieldy, self.fieldx = (
                            self.labelh, self.scrw-2 - self.labelw-3,
                            1, self.labelw+3)
        self.fieldwin = curses.newwin(self.fieldh, self.fieldw,
                                      self.fieldy, self.fieldx)
        self.fieldwin.nodelay(1)
        self.fieldpan = curses.panel.new_panel(self.fieldwin)
        self.spewh, self.speww, self.spewy, self.spewx = (
            self.scrh - self.labelh - 2, self.scrw - 3, 1 + self.labelh, 2)
        self.spewwin = curses.newwin(self.spewh, self.speww,
                                     self.spewy, self.spewx)
        self.spewpan = curses.panel.new_panel(self.spewwin)
        try:
            self.scrwin.border(ord('|'),ord('|'),ord('-'),ord('-'),ord(' '),ord(' '),ord(' '),ord(' '))
        except:
            pass
        self.labelwin.addstr(0, 0, _("file:"))
        self.labelwin.addstr(1, 0, _("size:"))
        self.labelwin.addstr(2, 0, _("dest:"))
        self.labelwin.addstr(3, 0, _("progress:"))
        self.labelwin.addstr(4, 0, _("status:"))
        self.labelwin.addstr(5, 0, _("dl speed:"))
        self.labelwin.addstr(6, 0, _("ul speed:"))
        self.labelwin.addstr(7, 0, _("sharing:"))
        self.labelwin.addstr(8, 0, _("seeds:"))
        self.labelwin.addstr(9, 0, _("peers:"))
        curses.panel.update_panels()
        curses.doupdate()
        self.changeflag.clear()


    def finished(self):
        self.done = True
        self.downRate = '---'
        self.display({'activity':_("download succeeded"), 'fractionDone':1})

    def error(self, errormsg):
        newerrmsg = strftime('[%H:%M:%S] ') + errormsg
        self.errors.append(newerrmsg.split('\n')[0])
        self.errlist.append(newerrmsg)
        self.display({})

    def display(self, statistics):
        fractionDone = statistics.get('fractionDone')
        activity = statistics.get('activity')
        timeEst = statistics.get('timeEst')
        downRate = statistics.get('downRate')
        upRate = statistics.get('upRate')
        spew = statistics.get('spew')

        inchar = self.fieldwin.getch()
        if inchar == 12: # ^L
            self._remake_window()
        elif inchar in (ord('q'),ord('Q')):
            self.doneflag.set()
        elif inchar in (ord('r'),ord('R')):
            self.reread_config()
        elif inchar in (ord('u'),ord('U')):
            curses.echo()
            self.fieldwin.nodelay(0)
            s = self.fieldwin.getstr(6,10)
            curses.noecho()
            self.fieldwin.nodelay(1)
            r = None
            try:
                r = int(s)
            except ValueError:
                pass
            if r is not None:
                self.ulrate(r)

        if timeEst is not None:
            self.activity = fmttime(timeEst)
        elif activity is not None:
            self.activity = activity
        if self.changeflag.isSet():
            return

        if fractionDone is not None:
            blocknum = int(self.fieldw * fractionDone)
            self.progress = blocknum * '#' + (self.fieldw - blocknum) * '_'
            self.status = '%s (%.1f%%)' % (self.activity, fractionDone * 100)

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

        self.fieldwin.erase()
        self.fieldwin.addnstr(0, 0, self.file, self.fieldw, curses.A_BOLD)
        self.fieldwin.addnstr(1, 0, self.fileSize, self.fieldw)
        self.fieldwin.addnstr(2, 0, self.downloadTo, self.fieldw)
        if self.progress:
            self.fieldwin.addnstr(3, 0, self.progress, self.fieldw, curses.A_BOLD)
        self.fieldwin.addnstr(4, 0, self.status, self.fieldw)
        self.fieldwin.addnstr(5, 0, self.downRate, self.fieldw)
        self.fieldwin.addnstr(6, 0, self.upRate, self.fieldw)
        self.fieldwin.addnstr(7, 0, self.shareRating, self.fieldw)
        self.fieldwin.addnstr(8, 0, self.seedStatus, self.fieldw)
        self.fieldwin.addnstr(9, 0, self.peerStatus, self.fieldw)

        self.spewwin.erase()

        if not spew:
            errsize = self.spewh
            if self.errors:
                self.spewwin.addnstr(0, 0, _("log:"), self.speww,
                                     curses.A_BOLD)
                errsize = len(self.errors)
                displaysize = min(errsize, self.spewh-1)
                displaytop = errsize - displaysize
                errlst = [e[0:self.speww-self.labelw-2] for e in self.errors]
                for i in range(displaysize):
                    self.spewwin.addnstr(i, self.labelw,
                                         errlst[displaytop + i],
                                         #self.speww-self.labelw-1,
                                         self.speww-self.labelw-2,
                                         curses.A_BOLD)
        else:
            if self.errors:
                self.spewwin.addnstr(0, 0, _("log:"), self.speww,
                                     curses.A_BOLD)
                err = self.errors[-1][0:self.speww-self.labelw-2]
                self.spewwin.addnstr(0, self.labelw, err,
                                 self.speww-self.labelw-1, curses.A_BOLD)
            self.spewwin.addnstr(2, 0, _("  #     IP                 Upload           Download     Completed  Speed"), self.speww, curses.A_BOLD)


            if self.spew_scroll_time + SPEW_SCROLL_RATE < time():
                self.spew_scroll_time = time()
                if len(spew) > self.spewh-5 or self.spew_scroll_pos > 0:
                    self.spew_scroll_pos += 1
            if self.spew_scroll_pos > len(spew):
                self.spew_scroll_pos = 0

            for i in range(len(spew)):
                spew[i]['lineno'] = i+1
            spew.append({'lineno': None})
            spew = spew[self.spew_scroll_pos:] + spew[:self.spew_scroll_pos]

            for i in range(min(self.spewh - 5, len(spew))):
                if not spew[i]['lineno']:
                    continue
                self.spewwin.addnstr(i+3, 0, '%3d' % spew[i]['lineno'], 3)
                self.spewwin.addnstr(i+3, 4, spew[i]['ip'], 15)
                ul = spew[i]['upload']
                if ul[1] > 100:
                    self.spewwin.addnstr(i+3, 20, '%6.0f KB/s' % (
                        ul[1] / 1000), 11)
                self.spewwin.addnstr(i+3, 32, '-----', 5)
                if ul[2]:
                    self.spewwin.addnstr(i+3, 33, 'I', 1)
                if ul[3]:
                    self.spewwin.addnstr(i+3, 35, 'C', 1)
                dl = spew[i]['download']
                if dl[1] > 100:
                    self.spewwin.addnstr(i+3, 38, '%6.0f KB/s' % (
                        dl[1] / 1000), 11)
                self.spewwin.addnstr(i+3, 50, '-------', 7)
                if dl[2]:
                    self.spewwin.addnstr(i+3, 51, 'I', 1)
                if dl[3]:
                    self.spewwin.addnstr(i+3, 53, 'C', 1)
                if dl[4]:
                    self.spewwin.addnstr(i+3, 55, 'S', 1)
                self.spewwin.addnstr(i+3, 58,
                    '%5.1f%%' % (int(spew[i]['completed']*1000)/10), 6)
                if spew[i]['speed'] is not None:
                    self.spewwin.addnstr(i+3, 64,
                        '%5.0f KB/s' % (spew[i]['speed']/1000), 10)
            """
            self.spewwin.addnstr(self.spewh-1, 0,
                    _("downloading %d pieces, have %d fragments, "
                      "%d of %d pieces completed") %
                    (statistics['storage_active'], statistics['storage_dirty'],
                     statistics['storage_numcomplete'], self.numpieces),
                    self.speww-1)
            """
        curses.panel.update_panels()
        curses.doupdate()


class CursesTorrentApp(object):

    class LogHandler(logging.Handler):
        def __init__(self, app, level=logging.NOTSET):
            logging.Handler.__init__(self,level)
            self.app = app
      
        def emit(self, record):
            if len(record.getMessage()) > 0:
                self.app.display_error(record.getMessage() ) 
            if record.exc_info is not None:
                self.app.display_error(
                    "Traceback (most recent call last):" )
                tb = record.exc_info[2]
                stack = traceback.extract_tb(tb)
                l = traceback.format_list(stack)
                for s in l:
                    self.app.display_error( " %s" % s )
                self.app.display_error( " %s: %s" %
                    ( str(record.exc_info[0]),str(record.exc_info[1])))

    class LogFilter(logging.Filter):
        def filter( self, record):
            if record.name == "NatTraversal":
                return 0
            return 1  # allow.
        
    def __init__(self, metainfo, config, errlist):
        assert isinstance(metainfo, ConvertedMetainfo )
        self.metainfo = metainfo
        self.config = Preferences().initWithDict(config)
        self.errlist = errlist
        self.torrent = None
        self.multitorrent = None
        self.d = None    # displayer (i.e., curses UI)
        self.logger = logging.getLogger("bittorrent-curses")
        log_handler = CursesTorrentApp.LogHandler(self)
        log_handler.setLevel(WARNING)
        #log_handler.setLevel(0)
        logger = logging.getLogger()
        logger.addHandler(log_handler)

        # disable stdout and stderr error reporting.
        global stderr_console
        logging.getLogger().removeHandler(console)
        if stderr_console is not None:
          logging.getLogger().removeHandler(stderr_console)
                                           
        # We log everything.  If we want to omit certain errors then
        # either raise the level or install a logging.Filter:
        log_handler.addFilter(CursesTorrentApp.LogFilter())
        logging.getLogger().setLevel(WARNING)
        #logging.getLogger().setLevel(0)

    def start_torrent(self,metainfo,save_incomplete_as,save_as):
        """Tells the MultiTorrent to begin downloading."""
        try:
            self.d.display({'activity':_("initializing"), 
                               'fractionDone':0})
            multitorrent = self.multitorrent
            df = multitorrent.create_torrent(metainfo, save_incomplete_as,
                                             save_as)
            df.addErrback( wrap_log('Failed to start torrent', self.logger))
            def create_finished(*args, **argv):
                self.torrent = multitorrent.get_torrent(metainfo.infohash)
                if self.torrent.is_initialized():
                   multitorrent.start_torrent(metainfo.infohash)
                else:
                   self.d.display({'activity':_("already being downloaded"), 
                               'fractionDone':0})
                   self.core_doneflag.set()  # e.g., if already downloading...
            df.addCallback( create_finished )
        except KeyboardInterrupt:
            raise
        except UserFailure, e:
            self.logger.error( "Failed to create torrent: " + unicode(e.args[0]) )
        except Exception, e:
            self.logger.error( "Failed to create torrent", exc_info = e )

    def run(self, scrwin):
        self.core_doneflag = DeferredEvent()
        rawserver = RawServer(self.config)

        # set up shut-down procedure before we begin doing things that
        # can throw exceptions.
        def shutdown():
            if self.d:
                self.d.display({'activity':_("shutting down"), 
                            'fractionDone':0})
            if self.multitorrent:
                df = self.multitorrent.shutdown()
                set_flag = lambda *a : rawserver.stop()
                df.addCallbacks(set_flag, set_flag)
            else:
                rawserver.stop()
                        
        # It is safe to addCallback here, because there is only one thread,
        # but even if the code were multi-threaded, core_doneflag has not
        # been passed to anyone.  There is no chance of a race condition
        # between the DeferredEvent'scallback and addCallback.
        self.core_doneflag.addCallback(
            lambda r: rawserver.external_add_task(0, shutdown))
        
        def reread():
            if self.multitorrent is not None:
                rawserver.external_add_task(0,self.reread_config)
        def ulrate(value):
            if self.multitorrent is not None:
                self.multitorrent.set_option('max_upload_rate', value)
            if self.torrent != None:
                self.torrent.set_option('max_upload_rate', value)

        self.d = CursesDisplayer(scrwin, self.errlist, self.core_doneflag, 
                                 reread, ulrate)
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
            rawserver.add_task(0,core_doneflag.set())
        except Exception, e:
            self.logger.error( "", exc_info = e )
            rawserver.add_task(0,core_doneflag.set())
        
        # always make sure events get processed even if only for
        # shutting down.
        rawserver.listen_forever()

    def reread_config(self):
        try:
            newvalues = configfile.get_config(self.config, 'bittorrent-curses')
        except Exception, e:
            self.d.error(_("Error reading config: ") + unicode(e.args[0]))
            return
        self.config.update(newvalues)
        # The set_option call can potentially trigger something that kills
        # the torrent (when writing this the only possibility is a change in
        # max_files_open causing an IOError while closing files), and so
        # the self.failed() callback can run during this loop.
        for option, value in newvalues.iteritems():
            self.multitorrent.set_option(option, value)
        if self.torrent is not None:
            for option, value in newvalues.iteritems():
                self.torrent.set_option(option, value)

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
    uiname = 'bittorrent-curses'
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
        ddir = os.path.join( platform.get_dot_dir(), "curses" )
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
                raise UserFailure(_("Error reading .torrent file: ") + '\n' + \
                                unicode(e.args[0]))
        else:
            raise UserFailure(_("you must specify a .torrent file"))
    except BTFailure, e:
        print unicode(e.args[0])
        sys.exit(1)

    errlist = []
    app = CursesTorrentApp(metainfo, config, errlist)
    curses_wrapper(app.run)
    if errlist:
        print _("These errors occurred during execution:")
        for error in errlist:
            print error
        sys.stdout.flush()
        
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
