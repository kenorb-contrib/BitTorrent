# Written by Bram Cohen
# see LICENSE.txt for license information

from time import time
from cStringIO import StringIO

class DownloaderFeedback:
    def __init__(self, choker, add_task, ip, statusfunc, 
            max_pause, remainingfunc, leftfunc, file_length, finflag):
        self.choker = choker
        self.add_task = add_task
        self.ip = ip
        self.statusfunc = statusfunc
        self.max_pause = max_pause
        self.remainingfunc = remainingfunc
        self.leftfunc = leftfunc
        self.file_length = file_length
        self.finflag = finflag
        self.add_task(self.display, .1)

    def spew(self):
        s = StringIO()
        for c in self.choker.connections:
            s.write('%20s ' % c.get_ip())
            u = c.get_upload()
            s.write(' %10s ' % str(int(u.rate)))
            if u.is_interested():
                s.write('i')
            else:
                s.write(' ')
            if u.is_choked():
                s.write('c')
            else:
                s.write(' ')

            d = c.get_download()
            s.write(' %10s ' % str(int(d.rate)))
            if d.is_interested():
                s.write('i')
            else:
                s.write(' ')
            if d.is_choked():
                s.write('c')
            else:
                s.write(' ')
            s.write('\n')
        print s.getvalue()

    def display(self):
        self.add_task(self.display, 1)
        t = time()
        #print '\n\n\n'
        #self.spew()
        if self.finflag.isSet():
            upRate = 0
            for c in self.choker.connections:
                u = c.get_upload()
                if u.lastout < t - self.max_pause:
                    u.update_rate(0)
                upRate += u.rate
            self.statusfunc(upRate=upRate)
            return
        timeEst = self.remainingfunc()
        downloadedSize = self.file_length - self.leftfunc()

        fractionDone = downloadedSize / float(self.file_length)
        
        downRate = 0
        upRate = 0
        for c in self.choker.connections:
            u = c.get_upload()
            if u.lastout < t - self.max_pause:
                u.update_rate(0)
            upRate += u.rate

            d = c.get_download()
            if d.lastin < t - self.max_pause:
                d.update_rate(0)
            downRate += d.rate
        if timeEst is not None:
            self.statusfunc(timeEst=timeEst, fractionDone=fractionDone, 
                downRate=downRate, upRate=upRate)
        else:
            self.statusfunc(fractionDone=fractionDone, 
                downRate=downRate, upRate=upRate)
