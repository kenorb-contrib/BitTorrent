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

    def display(self):
        self.add_task(self.display, 1)
        t = time()
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
        s = StringIO()
        s.write('\n\n\n')
        for c in self.choker.connections:
            s.write(c.get_ip() + ' ')
            u = c.get_upload()
            if u.is_interested():
                s.write('i')
            if u.is_choked():
                s.write('c')
            if u.lastout < t - self.max_pause:
                u.update_rate(0)
            s.write(' ' + str(u.rate) + ' ')
            upRate += u.rate

            d = c.get_download()
            if d.is_interested():
                s.write('i')
            if d.is_choked():
                s.write('c')
            if d.lastin < t - self.max_pause:
                d.update_rate(0)
            s.write(' ' + str(d.rate) + '\n')
            downRate += d.rate
        #print s.getvalue()
        if timeEst is not None:
            self.statusfunc(timeEst=timeEst, fractionDone=fractionDone, 
                downRate=downRate, upRate=upRate)
        else:
            self.statusfunc(fractionDone=fractionDone, 
                downRate=downRate, upRate=upRate)
