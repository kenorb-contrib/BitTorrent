# Written by Bram Cohen
# see LICENSE.txt for license information

from time import time
from cStringIO import StringIO

class DownloaderFeedback:
    def __init__(self, choker, add_task, statusfunc, upfunc, downfunc,
            remainingfunc, leftfunc, file_length, finflag, interval):
        self.choker = choker
        self.add_task = add_task
        self.statusfunc = statusfunc
        self.upfunc = upfunc
        self.downfunc = downfunc
        self.remainingfunc = remainingfunc
        self.leftfunc = leftfunc
        self.file_length = file_length
        self.finflag = finflag
        self.interval = interval
        self.display()

    def spew(self):
        s = StringIO()
        for c in self.choker.connections:
            s.write('%20s ' % c.get_ip())
            if c.is_locally_initiated():
                s.write('l')
            else:
                s.write('r')
            u = c.get_upload()
            s.write(' %10s ' % str(int(u.measure.get_rate())))
            if u.is_interested():
                s.write('i')
            else:
                s.write(' ')
            if u.is_choked():
                s.write('c')
            else:
                s.write(' ')

            d = c.get_download()
            s.write(' %10s ' % str(int(d.measure.get_rate())))
            if d.is_interested():
                s.write('i')
            else:
                s.write(' ')
            if d.is_choked():
                s.write('c')
            else:
                s.write(' ')
            if d.is_snubbed():
                s.write('s')
            else:
                s.write(' ')
            s.write('\n')
        print '\n\n\n' + s.getvalue()

    def display(self):
        self.add_task(self.display, self.interval)
        #self.spew()
        if self.finflag.isSet():
            self.statusfunc(upRate = self.upfunc())
            return
        timeEst = self.remainingfunc()

        fractionDone = (self.file_length - self.leftfunc()) / float(self.file_length)
        
        if timeEst is not None:
            self.statusfunc(timeEst = timeEst, fractionDone = fractionDone, 
                downRate = self.downfunc(), upRate = self.upfunc())
        else:
            self.statusfunc(fractionDone = fractionDone, 
                downRate = self.downfunc(), upRate = self.upfunc())
