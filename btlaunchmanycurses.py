#!/usr/bin/env python

# Written by Michael Janssen (jamuraa at base0 dot net)
# heavily borrowed code from btlaunchmany.py written by Bram Cohen
# and btdownloadcurses.py written by Henry 'Pi' James
# fmttime and fmtsize mercilessly stolen from btdownloadcurses. 0% of them are mine.
# see LICENSE.txt for license information

from BitTorrent.download import download
from threading import Thread, Event
from os import listdir
from os.path import abspath, join, exists
from sys import argv, version, stdout, exit
from time import sleep
import traceback

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
    unit = [' B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    i = 0
    if (n > 999):
        i = 1
        while i + 1 < len(unit) and (n >> 10) >= 999:
            i += 1
            n >>= 10
        n = float(n) / (1 << 10)
    if i > 0:
        size = '%.1f' % n + '%s' % unit[i]
    else:
        size = '%.0f' % n + '%s' % unit[i]
    return size

def dummy(*args, **kwargs):
    pass

ext = '.torrent'
wininfo = {} 

def runmany(d, params):
    threads = []
    deadfiles = []
    try:
        while 1:
            files = listdir(d)
            # new files
            for file in files:
                if file[-len(ext):] == ext:
                    if file not in [x.getName() for x in threads] + deadfiles:
                        wininfo[file] = {'basex': 2 * len(threads), 'killflag': Event()}
                        statuswin.erase()
                        statuswin.addnstr(0, 0,'new torrent detected: %s' % file, mainwinw)
                        threads.append(Thread(target = SingleCursesDisplayer(join(d, file), params, file).download, name = file))
                        threads[-1].start()
            # gone files
            for i in range(len(threads)):
                try:
                    threadname = threads[i].getName()
                except IndexError:
                    # raised when we delete a thread from earlier, so the last ones fall out of range
                    continue
                if not threads[i].isAlive():
                    # died without "permission"
                    deadfiles.append(threadname)
                    statuswin.erase()
                    statuswin.addnstr(0, 0,'torrent died: %s' % threadname, mainwinw)

                    # rearrange remaining windows
                    mainwin.addnstr(wininfo[threadname]['basex'], 0, ' ' * mainwinw, mainwinw)
                    mainwin.addnstr(wininfo[threadname]['basex']+1, 0, ' ' * mainwinw, mainwinw)
                    for _, win in wininfo.items():
                        if win['basex'] > wininfo[threadname]['basex']:
                            win['basex'] = win['basex'] - 2
                    del wininfo[threadname]
                    del threads[i]
                elif threadname not in files:
                    wininfo[threadname]['killflag'].set()
                    # rearrange remaining windows
                    mainwin.addnstr(wininfo[threadname]['basex'], 0, ' ' * mainwinw, mainwinw)
                    mainwin.addnstr(wininfo[threadname]['basex']+1, 0, ' ' * mainwinw, mainwinw)
                    for _, win in wininfo.items():
                        if win['basex'] > wininfo[threadname]['basex']:
                            win['basex'] = win['basex'] - 2
                    threads[i].join()
                    del wininfo[threadname]
                    del threads[i]
            # update the totals
            totalup = 0
            totaldown = 0
            for info in wininfo.values():
                totalup += info.get('uprate', 0)
                totaldown += info.get('downrate', 0)
            stringup = '%s/s' % fmtsize(totalup)
            stringdown = '%s/s' % fmtsize(totaldown)

            totalwin.addnstr(0, mainwinw-20, ' ' * 20, 20)
            totalwin.addnstr(0, mainwinw-20 + (10 - len(stringdown)), stringdown, 10)
            totalwin.addnstr(0, mainwinw-10 + (10 - len(stringup)), stringup, 10)

            sleep(1)
    except KeyboardInterrupt:
        statuswin.erase()
        statuswin.addnstr(0, 0,'^C caught.. cleaning up.. ', mainwinw)
        curses.panel.update_panels()
        curses.doupdate()
        for thread in threads: 
            threadname = thread.getName()
            statuswin.erase()
            statuswin.addnstr(0, 0,'killing torrent %s' % threadname, mainwinw)
            curses.panel.update_panels()
            curses.doupdate()
            wininfo[threadname]['killflag'].set()
            thread.join()
        statuswin.erase()
        statuswin.addnstr(0, 0,'Bye Bye!', mainwinw)
        curses.panel.update_panels()
        curses.doupdate()


class SingleCursesDisplayer: 
    def __init__(self, file, params, name):
        self.file = file
        self.params = params
        self.status = 'starting...'
        self.doingdown = ''
        self.doingup = ''
        self.done = 0
        self.downfile = ''
        self.localfile = ''
        self.fileSize = ''
        self.activity = ''
        self.myname = name
        self.basex = wininfo[self.myname]['basex']
        self.display()

    def download(self):
        download(self.params + ['--responsefile', self.file], self.choose, self.display, self.finished, self.err, wininfo[self.myname]['killflag'], mainwinw)
        statuswin.erase();
        statuswin.addnstr(0, 0, '%s: torrent stopped' % self.localfile, mainwinw)
        curses.panel.update_panels()
        curses.doupdate()

    def finished(self):
        self.done = 1
        self.doingdown = '--- KB/s'
        self.activity = 'download succeeded!'
        self.display(fractionDone = 1)
   
    def err(self, msg): 
        self.status = msg
        self.display()

    def failed(self):
        self.activity = 'download failed!'
        self.display()
 
    def choose(self, default, size, saveas, dir): 
        self.downfile = default
        self.fileSize = fmtsize(size)
        if saveas == '':
            saveas = default
        self.localfile = abspath(saveas)
        return saveas

    def display(self, fractionDone = None, timeEst = None, downRate = None, upRate = None, activity = None):
        if self.basex != wininfo[self.myname]['basex']: 
            # leave nothing but blank space
            mainwin.addnstr(self.basex, 0, ' ' * 1000, mainwinw)
            mainwin.addnstr(self.basex+1, 0, ' ' * 1000, mainwinw)
            self.basex = wininfo[self.myname]['basex']
        if activity is not None and not self.done:
            self.activity = activity
        elif timeEst is not None:
            self.activity = fmttime(timeEst)
        if fractionDone is not None:
            self.status = '%s (%.1f%%)' % (self.activity, fractionDone * 100)
        else:
            self.status = self.activity
        if downRate is None: 
            downRate = 0
        if upRate is None:
            upRate = 0
        wininfo[self.myname]['downrate'] = int(downRate)
        wininfo[self.myname]['uprate'] = int(upRate)
        self.doingdown = '%s/s' % fmtsize(int(downRate))
        self.doingup = '%s/s' % fmtsize(int(upRate))
   
        # clear the stats section 
        mainwin.addnstr(self.basex, 0, ' ' * mainwinw, mainwinw)
        mainwin.addnstr(self.basex, 0, self.downfile, mainwinw - 28, curses.A_BOLD)
        mainwin.addnstr(self.basex, mainwinw - 28 + (8 - len(self.fileSize)), self.fileSize, 8)
        mainwin.addnstr(self.basex, mainwinw - 20 + (10 - len(self.doingdown)), self.doingdown, 10)
        mainwin.addnstr(self.basex, mainwinw - 10 + (10 - len(self.doingup)), self.doingup, 10)
        # clear the status bar first 
        mainwin.addnstr(self.basex+1, 0, ' ' * mainwinw, mainwinw)
        mainwin.addnstr(self.basex+1, 0, '^--- ', 5)
        mainwin.addnstr(self.basex+1, 6, self.status, (mainwinw-1) - 5)
        curses.panel.update_panels()
        curses.doupdate()

def prepare_display():
    scrwin.hline(0, 1, '-', scrw - 2)
    scrwin.hline(scrh - 1, 1, '-', scrw - 2)
    scrwin.vline(1, 0, '|', scrh - 2)
    scrwin.vline(1, scrw - 1, '|', scrh - 2)
   
    headerwin.addnstr(0, 0, 'Filename', mainwinw - 25, curses.A_BOLD)
    headerwin.addnstr(0, mainwinw - 24, 'Size', 4);
    headerwin.addnstr(0, mainwinw - 18, 'Download', 8);
    headerwin.addnstr(0, mainwinw -  6, 'Upload', 6);

    totalwin.addnstr(0, mainwinw - 27, 'Totals:', 7);

    curses.panel.update_panels()
    curses.doupdate()

if __name__ == '__main__':
    if (len(argv) < 2): 
        print """Usage: btlaunchmanycurses.py <directory> <global options>
  <directory> - directory to look for .torrent files (non-recursive)
  <global options> - options to be applied to all torrents (see btdownloadheadless.py)
"""
        exit(-1)
    try: 
        import curses
        import curses.panel
     
        scrwin = curses.initscr()
        curses.noecho()
        curses.cbreak()
    except:
        print 'Textmode GUI initialization failed, cannot proceed.'
        exit(-1)
    scrh, scrw = scrwin.getmaxyx()
    scrpan = curses.panel.new_panel(scrwin)
    mainwinh = scrh - 5  # - 2 (bars) - 1 (debugwin) - 1 (borderwin) - 1 (totalwin)
    mainwinw = scrw - 4  # - 2 (bars) - 2 (spaces)
    mainwiny = 2         # + 1 (bar) + 1 (titles)
    mainwinx = 2         # + 1 (bar) + 1 (space)
    # + 1 to all windows so we can write at mainwinw
    mainwin = curses.newwin(mainwinh, mainwinw+1, mainwiny, mainwinx)
    mainpan = curses.panel.new_panel(mainwin)

    headerwin = curses.newwin(1, mainwinw+1, 1, mainwinx)
    headerpan = curses.panel.new_panel(headerwin)

    totalwin = curses.newwin(1, mainwinw+1, scrh-3, mainwinx)
    totalpan = curses.panel.new_panel(totalwin)

    statuswin = curses.newwin(1, mainwinw+1, scrh-2, mainwinx)
    statuspan = curses.panel.new_panel(statuswin)
    try:
        try:
            mainwin.scrollok(0)
            headerwin.scrollok(0)
            totalwin.scrollok(0)
            statuswin.addstr(0, 0, 'btlaunchmany started')
            statuswin.scrollok(0)
            prepare_display()
            curses.panel.update_panels()
            curses.doupdate()
            runmany(argv[1], argv[2:])
        finally:
            curses.nocbreak()
            curses.echo()
            curses.endwin()
    except:
        traceback.print_exc()
