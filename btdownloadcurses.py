#!/usr/bin/env python

# Written by Henry 'Pi' James
# see LICENSE.txt for license information

from BitTorrent.download import download
from threading import Event
from os.path import abspath
from signal import signal, SIGWINCH
from sys import argv, version, stdout
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
    global scrwin, scrpan, labelwin, labelpan, fieldw, fieldwin, fieldpan
    # SIGWINCH. Remake the frames!
    ## Curses Trickery
    curses.endwin()
    # delete scrwin somehow?
    scrwin.refresh()
    scrwin = curses.newwin(0, 0, 0, 0) 
    scrh, scrw = scrwin.getmaxyx()
    scrpan = curses.panel.new_panel(scrwin)
    labelh, labelw, labely, labelx = scrh - 2, 9, 1, 2
    labelwin = curses.newwin(labelh, labelw, labely, labelx)
    labelpan = curses.panel.new_panel(labelwin)
    fieldh, fieldw, fieldy, fieldx = scrh - 2, scrw - 2 - labelw - 3, 1, labelw + 3
    fieldwin = curses.newwin(fieldh, fieldw, fieldy, fieldx)
    fieldpan = curses.panel.new_panel(fieldwin)
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
        self.errors = []
        self.globalerrlist = mainerrlist

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
        self.errors.append(errormsg)
        self.globalerrlist.append(errormsg)
        self.display()

    def display(self, fractionDone = None, timeEst = None,
            downRate = None, upRate = None, activity = None):
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

        fieldwin.erase()
        fieldwin.addnstr(0, 0, self.file, fieldw, curses.A_BOLD)
        fieldwin.addnstr(1, 0, self.fileSize, fieldw)
        fieldwin.addnstr(2, 0, self.downloadTo, fieldw)
        if self.progress:
          fieldwin.addnstr(3, 0, self.progress, fieldw, curses.A_BOLD)
        fieldwin.addnstr(4, 0, self.status, fieldw)
        fieldwin.addnstr(5, 0, self.downRate, fieldw)
        fieldwin.addnstr(6, 0, self.upRate, fieldw)

        if self.errors:
            for i in range(len(self.errors)):
                fieldwin.addnstr(7 + i, 0, self.errors[i], fieldw, curses.A_BOLD)
        else:
            fieldwin.move(7, 0)

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
    try:
        download(params, d.chooseFile, d.display, d.finished, d.error, Event(), fieldw)
    except KeyboardInterrupt:
        # ^C to exit.. 
        pass 
    if not d.done:
        d.failed()

def prepare_display():
    scrwin.border(124,124,45,45,20,20,20,20)
    labelwin.addstr(0, 0, 'file:')
    labelwin.addstr(1, 0, 'size:')
    labelwin.addstr(2, 0, 'dest:')
    labelwin.addstr(3, 0, 'progress:')
    labelwin.addstr(4, 0, 'status:')
    labelwin.addstr(5, 0, 'dl speed:')
    labelwin.addstr(6, 0, 'ul speed:')
    labelwin.addstr(7, 0, 'error(s):')
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

scrh, scrw = scrwin.getmaxyx()
scrpan = curses.panel.new_panel(scrwin)
labelh, labelw, labely, labelx = scrh - 2, 9, 1, 2
labelwin = curses.newwin(labelh, labelw, labely, labelx)
labelpan = curses.panel.new_panel(labelwin)
fieldh, fieldw, fieldy, fieldx = scrh - 2, scrw - 2 - labelw - 3, 1, labelw + 3
fieldwin = curses.newwin(fieldh, fieldw, fieldy, fieldx)
fieldpan = curses.panel.new_panel(fieldwin)
prepare_display()

signal(SIGWINCH, winch_handler)

if __name__ == '__main__':
    mainerrlist = []
    try:
        run(mainerrlist, argv[1:])
    finally:
        curses.nocbreak()
        curses.echo()
        curses.endwin()
    if len(mainerrlist) != 0:
       print "These errors occurred during execution:"
       for error in mainerrlist:
          print error

