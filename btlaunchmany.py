#!/usr/bin/env python2

# Written by Bram Cohen
# Dropdir support added by Michael Janssen
# see LICENSE.txt for license information

from BitTorrent.download import download
from threading import Thread, Event
from os import listdir
from os.path import join, exists
from sys import argv, stdout
true = 1
false = 0

ext = '.torrent'

def dummy(*args, **kwargs):
    pass

def runmany(d, params):
    threads = []
    killflags = {}
    deadfiles = []
    while 1:
        files = listdir(d)
        # new files
        for file in files:
            if file[-len(ext):] == ext:
                if file not in [x.getName() for x in threads] + deadfiles:
                    print 'Starting torrent for ' + file
                    stdout.flush()
                    killflags[file] = Event()
                    threads.append(Thread(target = runsingle(join(d, file), params, killflags[file]).download, name = file))
                    threads[-1].start()
        # old files
        for i in range(len(threads)):
            try:
                threadname = threads[i].getName()
            except IndexError:
                # raised when we delete a thread from earlier,
                # the last ones fall out of range
                break
            if not threads[i].isAlive():
                # died without our permission
                deadfiles.append(threadname)
                del killflags[threadname]
                del threads[i]
            elif threadname not in files:
                # file gone!
                print threadname + ': torrent file gone, stopping downloader'
                stdout.flush()
                killflags[threadname].set()
                threads[i].join()
                del killflags[threadname]
                del threads[i]
        sleep(1)

class runsingle:
    def __init__(self, file, params, killflag):
        self.file = file
        self.params = params
        self.percentDone = 0
        self.doingdown = 0
        self.doingup = 0
        self.killflag = killflag
    
    def download(self):
        download(self.params + ['--responsefile', self.file], self.choose, self.status, self.finished, self.err, self.killflag, 80)

    def err(self, msg):
        print self.file + ': error - ' + msg
        stdout.flush()

    def failed(self):
        print self.file + ': failed'
        stdout.flush()

    def choose(self, default, size, saveas, dir):
        return self.file[:-len(ext)]

    def status(self, fractionDone = None,
            timeEst = None, downRate = None, upRate = None,
            activity = None):
        if fractionDone is not None:
            newpercent = int(fractionDone*100)
            if newpercent != self.percentDone:
                self.percentDone = newpercent
                print self.file + (': %d%%' % newpercent)
        if activity is not None:
            print self.file + ': ' + activity
        if downRate is not None:
            if self.doingdown*.8 <= downRate <= self.doingdown*1.2:
                pass
            else:
                self.doingdown = downRate
                print self.file + (': downloading %.0f kB/s' % (float(downRate) / (1 << 10)))
        if upRate is not None:
            if self.doingup*.8 <= upRate <= self.doingup*1.2:
                pass
            else:
                self.doingup = upRate
                print self.file + (': uploading %.0f kB/s' % (float(upRate) / (1 << 10)))
        stdout.flush()

    def finished(self):
        print self.file + ': fully accurate and here'
        stdout.flush()

if __name__ == '__main__':
    runmany(argv[1], argv[2:])
