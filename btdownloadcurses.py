#!/usr/bin/env python

# Written by Henry 'Pi' James
# see LICENSE.txt for license information

SPEW_SCROLL_RATE = 3

from BitTorrent import PSYCO
if PSYCO.psyco:
    try:
        import psyco
        assert psyco.__version__ >= 0x010100f0
        psyco.full()
    except:
        pass

from BitTorrent.download import Download
from threading import Event
from os.path import abspath
from signal import signal, SIGWINCH
from sys import argv, version, stdout
import sys
from time import time, strftime
assert version >= '2', "Install Python 2.0 or greater"

def fmttime(n):
    if n == -1:
        return 'download not progressing (file not being uploaded by others?)'
    if n == 0:
        return 'download complete!'
    n = int(n)
    m, s = divmod(n, 60)
    h, m = divmod(m, 60)
    if h > 1000000:
        return 'n/a'
    return 'finishing in %d:%02d:%02d' % (h, m, s)

def fmtsize(n):
    s = str(n)
    size = s[-3:]
    while len(s) > 3:
        s = s[:-3]
        size = '%s,%s' % (s[-3:], size)
    if n > 999:
        unit = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
        i = 1
        while i + 1 < len(unit) and (n >> 10) >= 999:
            i += 1
            n >>= 10
        n = float(n) / (1 << 10)
        size = '%s (%.0f %s)' % (size, n, unit[i])
    return size

def winch_handler(signum, stackframe):
    global scrwin, scrpan, labelwin, labelpan
    global fieldh, fieldw, fieldy, fieldx, fieldwin, fieldpan
    global spewwin, spewpan, spewh, speww, spewy, spewx
    # SIGWINCH. Remake the frames!
    ## Curses Trickery
    try:
        curses.endwin()
    except:
        pass
    # delete scrwin somehow?
    scrwin.refresh()
    scrwin = curses.newwin(0, 0, 0, 0) 
    scrh, scrw = scrwin.getmaxyx()
    scrpan = curses.panel.new_panel(scrwin)
    labelh, labelw, labely, labelx = 11, 9, 1, 2
    labelwin = curses.newwin(labelh, labelw, labely, labelx)
    labelpan = curses.panel.new_panel(labelwin)
    fieldh, fieldw, fieldy, fieldx = labelh, scrw - 2 - labelw - 3, 1, labelw + 3
    fieldwin = curses.newwin(fieldh, fieldw, fieldy, fieldx)
    fieldpan = curses.panel.new_panel(fieldwin)
    spewh, speww, spewy, spewx = scrh - labelh - 2, scrw - 3, 1 + labelh, 2
    spewwin = curses.newwin(spewh, speww, spewy, spewx)
    spewpan = curses.panel.new_panel(spewwin)
    prepare_display()


class CursesDisplayer:
    def __init__(self, mainerrlist):
        self.done = 0
        self.file = ''
        self.fileSize = ''
        self.activity = ''
        self.status = ''
        self.progress = ''
        self.downloadTo = ''
        self.downRate = '---'
        self.upRate = '---'
        self.shareRating = ''
        self.seedStatus = ''
        self.peerStatus = ''
        self.errors = []
        self.globalerrlist = mainerrlist
        self.last_update_time = 0
        self.spew_scroll_time = 0
        self.spew_scroll_pos = 0

    def finished(self):
        self.done = 1
        self.activity = 'download succeeded!'
        self.downRate = '---'
        self.display(fractionDone = 1)

    def failed(self):
        self.done = 1
        self.activity = 'download failed!'
        self.downRate = '---'
        self.display()

    def error(self, errormsg):
        newerrmsg = strftime('[%H:%M:%S] ') + errormsg
        self.errors.append(newerrmsg)
        self.globalerrlist.append(newerrmsg)
        self.display()

    def display(self, fractionDone = None, timeEst = None,
            downRate = None, upRate = None, activity = None,
            statistics = None, spew = None, **kws):
        if self.last_update_time + 0.1 > time() and fractionDone not in (0.0, 1.0) and activity is not None:
            return
        self.last_update_time = time()
        if activity is not None and not self.done:
            self.activity = activity
        elif timeEst is not None:
            self.activity = fmttime(timeEst)
        if fractionDone is not None:
            blocknum = int(fieldw * fractionDone)
            self.progress = blocknum * '#' + (fieldw - blocknum) * '_'
            self.status = '%s (%.1f%%)' % (self.activity, fractionDone * 100)
        else:
            self.status = self.activity
        if downRate is not None:
            self.downRate = '%.1f KB/s' % (float(downRate) / (1 << 10))
        if upRate is not None:
            self.upRate = '%.1f KB/s' % (float(upRate) / (1 << 10))
        if statistics is not None:
           if (statistics.shareRating < 0) or (statistics.shareRating > 100):
               self.shareRating = 'oo  (%.1f MB up / %.1f MB down)' % (float(statistics.upTotal) / (1<<20), float(statistics.downTotal) / (1<<20))
           else:
               self.shareRating = '%.3f  (%.1f MB up / %.1f MB down)' % (statistics.shareRating, float(statistics.upTotal) / (1<<20), float(statistics.downTotal) / (1<<20))
           if not self.done:
              self.seedStatus = '%d seen now, plus %.3f distributed copies' % (statistics.numSeeds,0.001*int(1000*statistics.numCopies))
           else:
              self.seedStatus = '%d seen recently, plus %.3f distributed copies' % (statistics.numOldSeeds,0.001*int(1000*statistics.numCopies))
           self.peerStatus = '%d seen now, %.1f%% done at %.1f kB/s' % (statistics.numPeers,statistics.percentDone,float(statistics.torrentRate) / (1 << 10))

        fieldwin.erase()
        fieldwin.addnstr(0, 0, self.file, fieldw, curses.A_BOLD)
        fieldwin.addnstr(1, 0, self.fileSize, fieldw)
        fieldwin.addnstr(2, 0, self.downloadTo, fieldw)
        if self.progress:
          fieldwin.addnstr(3, 0, self.progress, fieldw, curses.A_BOLD)
        fieldwin.addnstr(4, 0, self.status, fieldw)
        fieldwin.addnstr(5, 0, self.downRate, fieldw)
        fieldwin.addnstr(6, 0, self.upRate, fieldw)
        fieldwin.addnstr(7, 0, self.shareRating, fieldw)
        fieldwin.addnstr(8, 0, self.seedStatus, fieldw)
        fieldwin.addnstr(9, 0, self.peerStatus, fieldw)

        spewwin.erase()

        if not spew:
            errsize = spewh
            if self.errors:
                spewwin.addnstr(0, 0, "error(s):", speww, curses.A_BOLD)
                errsize = len(self.errors)
                displaysize = min(errsize, spewh)
                displaytop = errsize - displaysize
                for i in range(displaysize):
                    spewwin.addnstr(i, labelw, self.errors[displaytop + i],
                                 speww-labelw-1, curses.A_BOLD)
        else:
            if self.errors:
                spewwin.addnstr(0, 0, "error:", speww, curses.A_BOLD)
                spewwin.addnstr(0, labelw, self.errors[-1],
                                 speww-labelw-1, curses.A_BOLD)
            spewwin.addnstr(2, 0, " #      IP                 Upload           Download     Completed  Speed", speww, curses.A_BOLD)


            if self.spew_scroll_time + SPEW_SCROLL_RATE < time():
                self.spew_scroll_time = time()
                if len(spew) > spewh-5 or self.spew_scroll_pos > 0:
                    self.spew_scroll_pos += 1
            if self.spew_scroll_pos > len(spew):
                self.spew_scroll_pos = 0

            for i in range(len(spew)):
                spew[i]['lineno'] = i+1
            spew.append({'lineno': None})
            spew = spew[self.spew_scroll_pos:] + spew[:self.spew_scroll_pos]                
            
            for i in range(min(spewh - 5, len(spew))):
                if not spew[i]['lineno']:
                    continue
                spewwin.addnstr(i+3, 0, '%3d' % spew[i]['lineno'], 3)
                spewwin.addnstr(i+3, 4, spew[i]['ip'], 15)
                if spew[i]['uprate'] > 100:
                    spewwin.addnstr(i+3, 20, '%6.0f KB/s' % (float(spew[i]['uprate']) / 1000), 11)
                spewwin.addnstr(i+3, 32, '-----', 5)
                if spew[i]['uinterested'] == 1:
                    spewwin.addnstr(i+3, 33, 'I', 1)
                if spew[i]['uchoked'] == 1:
                    spewwin.addnstr(i+3, 35, 'C', 1)
                if spew[i]['downrate'] > 100:
                    spewwin.addnstr(i+3, 38, '%6.0f KB/s' % (float(spew[i]['downrate']) / 1000), 11)
                spewwin.addnstr(i+3, 50, '-------', 7)
                if spew[i]['dinterested'] == 1:
                    spewwin.addnstr(i+3, 51, 'I', 1)
                if spew[i]['dchoked'] == 1:
                    spewwin.addnstr(i+3, 53, 'C', 1)
                if spew[i]['snubbed'] == 1:
                    spewwin.addnstr(i+3, 55, 'S', 1)
                spewwin.addnstr(i+3, 58, '%5.1f%%' % (float(int(spew[i]['completed']*1000))/10), 6)
                if spew[i]['speed'] is not None:
                    spewwin.addnstr(i+3, 64, '%5.0f KB/s' % (float(spew[i]['speed'])/1000), 10)

            if statistics is not None:
                spewwin.addnstr(spewh-1, 0,
                        'downloading %d pieces, have %d fragments, %d of %d pieces completed'
                        % ( statistics.storage_active, statistics.storage_dirty,
                            statistics.storage_numcomplete,
                            statistics.storage_totalpieces ), speww-1 )

        curses.panel.update_panels()
        curses.doupdate()

    def chooseFile(self, default, size, saveas, dir):
        self.file = default
        self.fileSize = fmtsize(size)
        if saveas == '':
            saveas = default
        self.downloadTo = abspath(saveas)
        return saveas

def run(mainerrlist, params):
    d = CursesDisplayer(mainerrlist)
    dow = Download()
    d.dow = dow
    try:
        dow.download(params, d.chooseFile, d.display, d.finished, d.error, Event(), fieldw)
    except KeyboardInterrupt:
        # ^C to exit.. 
        pass 
    if not d.done:
        d.failed()

def prepare_display():
    scrwin.border(ord('|'),ord('|'),ord('-'),ord('-'),ord(' '),ord(' '),ord(' '),ord(' '))
    labelwin.addstr(0, 0, 'file:')
    labelwin.addstr(1, 0, 'size:')
    labelwin.addstr(2, 0, 'dest:')
    labelwin.addstr(3, 0, 'progress:')
    labelwin.addstr(4, 0, 'status:')
    labelwin.addstr(5, 0, 'dl speed:')
    labelwin.addstr(6, 0, 'ul speed:')
    labelwin.addstr(7, 0, 'sharing:')
    labelwin.addstr(8, 0, 'seeds:')
    labelwin.addstr(9, 0, 'peers:')
#    labelwin.addstr(10, 0, '')
#    labelwin.addstr(11, 0, 'error(s):')
    curses.panel.update_panels()
    curses.doupdate()

try:
    import curses
    import curses.panel

    scrwin = curses.initscr()
    curses.noecho()
    curses.cbreak()

except:
    print 'Textmode GUI initialization failed, cannot proceed.'
    print
    print 'This download interface requires the standard Python module ' \
       '"curses", which is unfortunately not available for the native ' \
       'Windows port of Python. It is however available for the Cygwin ' \
       'port of Python, running on all Win32 systems (www.cygwin.com).'
    print
    print 'You may still use "btdownloadheadless.py" to download.'
    sys.exit(1)

scrh, scrw = scrwin.getmaxyx()
scrpan = curses.panel.new_panel(scrwin)
labelh, labelw, labely, labelx = 11, 9, 1, 2
labelwin = curses.newwin(labelh, labelw, labely, labelx)
labelpan = curses.panel.new_panel(labelwin)
fieldh, fieldw, fieldy, fieldx = labelh, scrw - 2 - labelw - 3, 1, labelw + 3
fieldwin = curses.newwin(fieldh, fieldw, fieldy, fieldx)
fieldpan = curses.panel.new_panel(fieldwin)
spewh, speww, spewy, spewx = scrh - labelh - 2, scrw - 3, 1 + labelh, 2
spewwin = curses.newwin(spewh, speww, spewy, spewx)
spewpan = curses.panel.new_panel(spewwin)
prepare_display()

signal(SIGWINCH, winch_handler)

if __name__ == '__main__':
    if argv[1:] == ['--version']:
        print version
        sys.exit(0)
    mainerrlist = []
    try:
        try:
            run(mainerrlist, argv[1:])
        finally:
            try:
                curses.nocbreak()
            except:
                pass
            try:
                curses.echo()
            except:
                pass
            try:
                curses.endwin()
            except:
                pass
    except KeyboardInterrupt:
        pass
    if len(mainerrlist) != 0:
       print "These errors occurred during execution:"
       for error in mainerrlist:
          print error
