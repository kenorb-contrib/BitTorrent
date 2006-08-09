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

# Written by John Hoffman

from __future__ import division

from BitTorrent.translation import _

DOWNLOAD_SCROLL_RATE = 1

import sys, os
from threading import Event
from time import time, localtime, strftime

from BitTorrent.obsoletepythonsupport import *
from BitTorrent import platform
from BitTorrent.launchmanycore import LaunchMany
from BitTorrent.defaultargs import get_defaults
from BitTorrent.parseargs import parseargs, printHelp
from BitTorrent.prefs import Preferences
from BitTorrent import configfile
from BitTorrent import version
from BitTorrent.platform import encode_for_filesystem, decode_from_filesystem
from BitTorrent import BTFailure
from BitTorrent import bt_log_fmt
import logging
import traceback
from logging import ERROR, WARNING, INFO
from BitTorrent import console, STDERR #, inject_main_logfile



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
    print _("You may still use \"btdownloadheadless.py\" to download.")
    sys.exit(1)

exceptions = []

def fmttime(n):
    if n <= 0:
        return None
    n = int(n)
    m, s = divmod(n, 60)
    h, m = divmod(m, 60)
    if h > 1000000:
        return _("connecting to peers")
    return _("ETA in %d:%02d:%02d") % (h, m, s)

def fmtsize(n):
    n = long(n)
    unit = [' B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
    i = 0
    if (n > 999):
        i = 1
        while i + 1 < len(unit) and (n >> 10) >= 999:
            i += 1
            n >>= 10
        n /= 1024
    if i > 0:
        size = '%.1f' % n + '%s' % unit[i]
    else:
        size = '%.0f' % n + '%s' % unit[i]
    return size

def ljust(s, size):
    s = s[:size]
    return s + (' '*(size-len(s)))

def rjust(s, size):
    s = s[:size]
    return (' '*(size-len(s)))+s


class CursesDisplayer(object):

    def __init__(self, scrwin):
        self.messages = []
        self.scroll_pos = 0
        self.scroll_time = 0

        self.scrwin = scrwin
        signal(SIGWINCH, self.winch_handler)
        self.changeflag = Event()
        self._remake_window()
        curses.use_default_colors()

    def winch_handler(self, signum, stackframe):
        self.changeflag.set()
        curses.endwin()
        self.scrwin.refresh()
        self.scrwin = curses.newwin(0, 0, 0, 0)
        self._remake_window()
        self._display_messages()

    def _remake_window(self):
        self.scrh, self.scrw = self.scrwin.getmaxyx()
        self.scrpan = curses.panel.new_panel(self.scrwin)
        self.mainwinh = (2*self.scrh)//3
        self.mainwinw = self.scrw - 4  # - 2 (bars) - 2 (spaces)
        self.mainwiny = 2         # + 1 (bar) + 1 (titles)
        self.mainwinx = 2         # + 1 (bar) + 1 (space)
        # + 1 to all windows so we can write at mainwinw

        self.mainwin = curses.newwin(self.mainwinh, self.mainwinw+1,
                                     self.mainwiny, self.mainwinx)
        self.mainpan = curses.panel.new_panel(self.mainwin)
        self.mainwin.scrollok(0)
        self.mainwin.nodelay(1)

        self.headerwin = curses.newwin(1, self.mainwinw+1,
                                       1, self.mainwinx)
        self.headerpan = curses.panel.new_panel(self.headerwin)
        self.headerwin.scrollok(0)

        self.totalwin = curses.newwin(1, self.mainwinw+1,
                                      self.mainwinh+1, self.mainwinx)
        self.totalpan = curses.panel.new_panel(self.totalwin)
        self.totalwin.scrollok(0)

        self.statuswinh = self.scrh-4-self.mainwinh
        self.statuswin = curses.newwin(self.statuswinh, self.mainwinw+1,
                                       self.mainwinh+3, self.mainwinx)
        self.statuspan = curses.panel.new_panel(self.statuswin)
        self.statuswin.scrollok(0)

        try:
            self.scrwin.border(ord('|'),ord('|'),ord('-'),ord('-'),ord(' '),ord(' '),ord(' '),ord(' '))
        except:
            pass
        rcols = (_("Size"),_("Download"),_("Upload"))
        rwids = (8, 10, 10)
        rwid = sum(rwids)
        start = self.mainwinw - rwid
        self.headerwin.addnstr(0, 2, '#', start, curses.A_BOLD)
        self.headerwin.addnstr(0, 4, _("Filename"), start, curses.A_BOLD)

        for s,w in zip(rcols, rwids):
            st = start + max(w - len(s), 0)
            self.headerwin.addnstr(0, st, s[:w], len(s[:w]), curses.A_BOLD)
            start += w

        self.totalwin.addnstr(0, self.mainwinw - 27, _("Totals:"), 7, curses.A_BOLD)

        self._display_messages()

        curses.panel.update_panels()
        curses.doupdate()
        self.changeflag.clear()


    def _display_line(self, s, bold = False):
        if self.disp_end:
            return True
        line = self.disp_line
        self.disp_line += 1
        if line < 0:
            return False
        if bold:
            self.mainwin.addnstr(line, 0, s, self.mainwinw, curses.A_BOLD)
        else:
            self.mainwin.addnstr(line, 0, s, self.mainwinw)
        if self.disp_line >= self.mainwinh:
            self.disp_end = True
        return self.disp_end

    def _display_data(self, data):
        if 3*len(data) <= self.mainwinh:
            self.scroll_pos = 0
            self.scrolling = False
        elif self.scroll_time + DOWNLOAD_SCROLL_RATE < time():
            self.scroll_time = time()
            self.scroll_pos += 1
            self.scrolling = True
            if self.scroll_pos >= 3*len(data)+2:
                self.scroll_pos = 0

        i = self.scroll_pos//3
        self.disp_line = (3*i)-self.scroll_pos
        self.disp_end = False

        while not self.disp_end:
            ii = i % len(data)
            if i and not ii:
                if not self.scrolling:
                    break
                self._display_line('')
                if self._display_line(''):
                    break
            ( name, status, progress, peers, seeds, seedsmsg, #dist,
              uprate, dnrate, upamt, dnamt, size, t, msg ) = data[ii]
            t = fmttime(t)
            if t:
                status = t
            name = ljust(name,self.mainwinw-32)
            size = rjust(fmtsize(size),8)
            uprate = rjust('%s/s' % fmtsize(uprate),10)
            dnrate = rjust('%s/s' % fmtsize(dnrate),10)
            line = "%3d %s%s%s%s" % (ii+1, name, size, dnrate, uprate)
            self._display_line(line, True)
            if peers + seeds:
                datastr = _("    (%s) %s - %s peers %s seeds - %s dn %s up") % (
                    progress, status, peers, seeds, #dist,
                    fmtsize(dnamt), fmtsize(upamt) )
            else:
                datastr = '    '+status+' ('+progress+')'
            self._display_line(datastr)
            self._display_line('    '+ljust(msg,self.mainwinw-4))
            i += 1

    def display(self, data):
      try:
        if self.changeflag.isSet():
            return

        inchar = self.mainwin.getch()
        if inchar == 12: # ^L
            self._remake_window()

        self.mainwin.erase()
        if data:
            self._display_data(data)
        else:
            self.mainwin.addnstr( 1, self.mainwinw//2-5,
                                  _("no torrents"), 12, curses.A_BOLD )
        totalup = 0
        totaldn = 0
        for ( name, status, progress, peers, seeds, seedsmsg, #dist,
              uprate, dnrate, upamt, dnamt, size, t, msg ) in data:
            totalup += uprate
            totaldn += dnrate

        totalup = '%s/s' % fmtsize(totalup)
        totaldn = '%s/s' % fmtsize(totaldn)

        self.totalwin.erase()
        self.totalwin.addnstr(0, self.mainwinw-27, _("Totals:"), 7, curses.A_BOLD)
        self.totalwin.addnstr(0, self.mainwinw-20 + (10-len(totaldn)),
                              totaldn, 10, curses.A_BOLD)
        self.totalwin.addnstr(0, self.mainwinw-10 + (10-len(totalup)),
                              totalup, 10, curses.A_BOLD)

        curses.panel.update_panels()
        curses.doupdate()

      except:
          pass
      return inchar in (ord('q'),ord('Q'))

    def message(self, s):
      try:
        self.messages.append(strftime('%x %X - ',localtime(time()))+s)
        self._display_messages()
      except:
        pass

    def _display_messages(self):
        self.statuswin.erase()
        winpos = 0
        for s in self.messages[-self.statuswinh:]:
            self.statuswin.addnstr(winpos, 0, s, self.mainwinw)
            winpos += 1
        curses.panel.update_panels()
        curses.doupdate()

    def exception(self, s):
        exceptions.append(s)
        self.message(_("SYSTEM ERROR - EXCEPTION GENERATED"))

def modify_default( defaults_tuplelist, key, newvalue ):
    name,value,doc = [(n,v,d) for (n,v,d) in defaults_tuplelist if n == key][0]
    defaults_tuplelist = [(n,v,d) for (n,v,d) in defaults_tuplelist
                    if not n == key]
    defaults_tuplelist.append( (key,newvalue,doc) )
    return defaults_tuplelist


if __name__ == '__main__':
    uiname = 'launchmany-curses'
    defaults = get_defaults(uiname)
    try:
        if len(sys.argv) < 2:
            printHelp(uiname, defaults)
            sys.exit(1)

        # Modifying default values from get_defaults is annoying...
        # Implementing specific default values for each uiname in
        # defaultargs.py is even more annoying.  --Dave
        ddir = os.path.join( platform.get_dot_dir(), "launchmany-curses" )
        ddir = decode_from_filesystem(ddir)
        modify_default(defaults, 'data_dir', ddir)
        config, args = configfile.parse_configuration_and_args(defaults,
                                      uiname, sys.argv[1:], 0, 1)
        
        if args:
            torrent_dir = args[0]
            config['torrent_dir'] = \
                platform.decode_from_filesystem(torrent_dir)    
        else:
            torrent_dir = config['torrent_dir']
            torrent_dir,bad = platform.encode_for_filesystem(torrent_dir)
            if bad:
              raise BTFailure(_("Warning: ")+config['torrent_dir']+
                              _(" is not a directory"))
            
        if not os.path.isdir(torrent_dir):
            raise BTFailure(_("Warning: ")+torrent_dir+
                            _(" is not a directory"))

        # the default behavior is to save_in files to the platform
        # get_save_dir.  For launchmany, if no command-line argument 
        # changed the save directory then use the torrent directory.
        if config['save_in'] == platform.get_save_dir():
            config['save_in'] = config['torrent_dir']
        
    except BTFailure, e:
        print _("error: ") + unicode(e.args[0]) + \
              _("\nrun with no args for parameter explanations")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)

    #inject_main_logfile()

    class LaunchManyApp(object):
        class LogHandler(logging.Handler):
            def __init__(self, level, displayer):
                logging.Handler.__init__(self,level)
                self.displayer = displayer
            def emit(self, record):
                if len(record.getMessage()) > 0:
                    self.displayer.message(record.getMessage() ) 
                if record.exc_info is not None:
                    self.displayer.message(
                        "Traceback (most recent call last):" )
                    tb = record.exc_info[2]
                    stack = traceback.extract_tb(tb)
                    l = traceback.format_list(stack)
                    for s in l:
                        self.displayer.message( " %s" % s )
                    self.displayer.message( " %s: %s" %
                        ( str(record.exc_info[0]),str(record.exc_info[1])))

        def __init__(self):
            pass
        
        def run(self,scrwin, config):
            self.displayer = CursesDisplayer(scrwin)
            
            log_handler = LaunchManyApp.LogHandler(STDERR, self.displayer)
            log_handler.setFormatter(bt_log_fmt)
            logging.getLogger('').addHandler(log_handler)
            logging.getLogger().setLevel(STDERR)
            logging.getLogger('').removeHandler(console)
            
            # more liberal with logging launchmany-curses specific output.
            lmany_logger = logging.getLogger('launchmany-curses')
            lmany_handler = LaunchManyApp.LogHandler(INFO, self.displayer)
            lmany_handler.setFormatter(bt_log_fmt)
            lmany_logger.setLevel(INFO)
            lmany_logger.addHandler(lmany_handler)

            config = Preferences().initWithDict(config)
            LaunchMany(config, self.displayer.display, 'launchmany-curses')

    app = LaunchManyApp()
    curses_wrapper(app.run, config)
    if exceptions:
        print _("\nEXCEPTION:")
        print exceptions[0]
