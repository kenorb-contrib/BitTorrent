#!/usr/bin/env python

# Written by Michael Janssen (jamuraa at base0 dot net)
# originally heavily borrowed code from btlaunchmany.py by Bram Cohen
# and btdownloadcurses.py written by Henry 'Pi' James
# now not so much.
# fmttime and fmtsize stolen from btdownloadcurses. 
# see LICENSE.txt for license information

from BitTorrent.download import download
from threading import Thread, Event, RLock
from os import listdir
from os.path import abspath, join, exists
from sys import argv, version, stdout, exit
from time import sleep
from signal import signal, SIGWINCH 
import traceback

assert version >= '2', "Install Python 2.0 or greater"

def fmttime(n):
    if n == -1:
        return 'download not progressing (no seeds?)'
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

threads = {}
ext = '.torrent'
status = 'btlaunchmany starting..'
filecheck = RLock()

def dropdir_mainloop(d, params):
    deadfiles = []
    global threads, status
    while 1:
        files = listdir(d)
        # new files
        for file in files: 
            if file[-len(ext):] == ext:
                if file not in threads.keys() + deadfiles:
                    threads[file] = {'kill': Event(), 'try': 1}
                    status = 'New torrent: %s' % file
                    threads[file]['thread'] = Thread(target = StatusUpdater(join(d, file), params, file).download, name = file)
                    threads[file]['thread'].start()
        # files with multiple tries
        for file, threadinfo in threads.items():
            if threadinfo.get('timeout') == 0:
                # Zero seconds left, try and start the thing again.
                threadinfo['try'] = threadinfo['try'] + 1
                threadinfo['thread'] = Thread(target = StatusUpdater(join(d, file), params, file).download, name = file)
                threadinfo['thread'].start()
                threadinfo['timeout'] = -1
            elif threadinfo.get('timeout') > 0: 
                # Decrement our counter by 1
                threadinfo['timeout'] = threadinfo['timeout'] - 1
            elif not threadinfo['thread'].isAlive():
                # died without permission
                if threadinfo.get('try') == 6: 
                    # Died on the sixth try? You're dead.
                    deadfiles.append(file)
                    status = '%s died 6 times, added to dead list' % file
                    del threads[file]
                else:
                    del threadinfo['thread']
                    threadinfo['timeout'] = 10
            # dealing with files that dissapear
            if file not in files:
                status = 'Gone torrent: %s' % file
                if threadinfo['timeout'] == -1:
                    threadinfo['kill'].set()
                    threadinfo['thread'].join()
                del threads[file]
        for file in deadfiles:
            # if the file dissapears, remove it from our dead list
            if file not in files: 
                deadfiles.remove(file)
        sleep(1)

def display_thread(displaykiller):
    interval = 0.1
    global threads, status
    while 1:
        # display file info
        if (displaykiller.isSet()): 
            break
        mainwin.erase()
        winpos = 0
        totalup = 0
        totaldown = 0
        for file, threadinfo in threads.items(): 
            uprate = threadinfo.get('uprate', 0)
            downrate = threadinfo.get('downrate', 0)
            uptxt = '%s/s' % fmtsize(uprate)
            downtxt = '%s/s' % fmtsize(downrate)
            filesize = threadinfo.get('filesize', 'N/A')
            mainwin.addnstr(winpos, 0, threadinfo.get('savefile', file), mainwinw - 28, curses.A_BOLD)
            mainwin.addnstr(winpos, mainwinw - 28 + (8 - len(filesize)), filesize, 8)
            mainwin.addnstr(winpos, mainwinw - 20 + (10 - len(downtxt)), downtxt, 10)
            mainwin.addnstr(winpos, mainwinw - 10 + (10 - len(uptxt)), uptxt, 10)
            winpos = winpos + 1
            mainwin.addnstr(winpos, 0, '^--- ', 5) 
            if threadinfo.get('timeout', 0) > 0:
                mainwin.addnstr(winpos, 6, 'Try %d: died, retrying in %d' % (threadinfo.get('try', 1), threadinfo.get('timeout')), mainwinw - 5)
            else:
                mainwin.addnstr(winpos, 6, threadinfo.get('status',''), mainwinw - 5)
            winpos = winpos + 1
            totalup += uprate
            totaldown += downrate
        # display statusline
        statuswin.erase() 
        statuswin.addnstr(0, 0, status, mainwinw)
        # display totals line
        totaluptxt = '%s/s' % fmtsize(totalup)
        totaldowntxt = '%s/s' % fmtsize(totaldown)
        
        totalwin.erase()
        totalwin.addnstr(0, mainwinw - 27, 'Totals:', 7);
        totalwin.addnstr(0, mainwinw - 20 + (10 - len(totaldowntxt)), totaldowntxt, 10)
        totalwin.addnstr(0, mainwinw - 10 + (10 - len(totaluptxt)), totaluptxt, 10)
        curses.panel.update_panels()
        curses.doupdate()
        sleep(interval)

class StatusUpdater:
    def __init__(self, file, params, name):
        self.file = file
        self.params = params
        self.name = name
        self.myinfo = threads[name]
        self.done = 0
        self.checking = 0
        self.activity = 'starting up...'
        self.display()
        self.myinfo['errors'] = []

    def download(self): 
        download(self.params + ['--responsefile', self.file], self.choose, self.display, self.finished, self.err, self.myinfo['kill'], 80)
        status = 'Torrent %s stopped' % self.file

    def finished(self): 
        self.done = 1
        self.myinfo['done'] = 1
        self.activity = 'download succeeded!'
        self.display(fractionDone = 1)

    def err(self, msg): 
        self.myinfo['errors'].append(msg)
        self.display()

    def failed(self): 
        self.activity = 'download failed!' 
        self.display() 

    def choose(self, default, size, saveas, dir):
        global filecheck
        self.myinfo['downfile'] = default
        self.myinfo['filesize'] = fmtsize(size)
        if saveas == '': 
            saveas = default
        # it asks me where I want to save it before checking the file.. 
        if (exists(saveas)):
            # file will get checked
            while (not filecheck.acquire(blocking = 0) and not self.myinfo['kill'].isSet()):
                self.myinfo['status'] = 'Waiting for disk check...'
                sleep(0.1)
            self.checking = 1
        self.myinfo['savefile'] = saveas
        return saveas
    
    def display(self, fractionDone = None, timeEst = None, downRate = None, upRate = None, activity = None): 
        global filecheck, status
        if activity is not None and not self.done: 
            self.activity = activity
        elif timeEst is not None: 
            self.activity = fmttime(timeEst)
        if fractionDone is not None: 
            self.myinfo['status'] = '%s (%.1f%%)' % (self.activity, fractionDone * 100)
            if fractionDone == 1 and self.checking:
                # we finished checking our files. 
                filecheck.release()
                self.checking = 0
        else:
            self.myinfo['status'] = self.activity
        if downRate is None: 
            downRate = 0
        if upRate is None:
            upRate = 0
        self.myinfo['uprate'] = int(upRate)
        self.myinfo['downrate'] = int(downRate)

def prepare_display(): 
    global mainwinw, scrwin, headerwin, totalwin
    scrwin.border(ord('|'),ord('|'),ord('-'),ord('-'),ord(' '),ord(' '),ord(' '),ord(' '))
    headerwin.addnstr(0, 0, 'Filename', mainwinw - 25, curses.A_BOLD)
    headerwin.addnstr(0, mainwinw - 24, 'Size', 4);
    headerwin.addnstr(0, mainwinw - 18, 'Download', 8);
    headerwin.addnstr(0, mainwinw -  6, 'Upload', 6);
    totalwin.addnstr(0, mainwinw - 27, 'Totals:', 7);
    curses.panel.update_panels()
    curses.doupdate()

def winch_handler(signum, stackframe): 
    global scrwin, mainwin, mainwinw, headerwin, totalwin, statuswin
    global scrpan, mainpan, headerpan, totalpan, statuspan
    # SIGWINCH. Remake the frames!
    ## Curses Trickery
    curses.endwin()
    # delete scrwin somehow?
    scrwin.refresh()
    scrwin = curses.newwin(0, 0, 0, 0)
    scrh, scrw = scrwin.getmaxyx()
    scrpan = curses.panel.new_panel(scrwin)
    ### Curses Setup
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
    mainwin.scrollok(0)
    headerwin.scrollok(0)
    totalwin.scrollok(0)
    statuswin.addstr(0, 0, 'window resize: %s x %s' % (scrw, scrh))
    statuswin.scrollok(0)
    prepare_display()

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
    try:
        signal(SIGWINCH, winch_handler)
        ### Curses Setup
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
        mainwin.scrollok(0)
        headerwin.scrollok(0)
        totalwin.scrollok(0)
        statuswin.addstr(0, 0, 'btlaunchmany started')
        statuswin.scrollok(0)
        prepare_display()
        displaykiller = Event()
        displaythread = Thread(target = display_thread, name = 'display', args = [displaykiller])
        displaythread.setDaemon(1)
        displaythread.start()
        dropdir_mainloop(argv[1], argv[2:])
    except KeyboardInterrupt: 
        status = '^C caught! Killing torrents..'
        for file, threadinfo in threads.items(): 
            status = 'Killing torrent %s' % file
            threadinfo['kill'].set() 
            threadinfo['thread'].join() 
            del threads[file]
        displaykiller.set()
        displaythread.join()
        curses.nocbreak()
        curses.echo()
        curses.endwin()
    except:
        curses.nocbreak()
        curses.echo()
        curses.endwin()
        traceback.print_exc()
