# Written by Bram Cohen
# see LICENSE.txt for license information

from time import time
from cStringIO import StringIO

class DownloaderFeedback:
    def __init__(self, choker, add_task, statusfunc, upfunc, downfunc,
            remainingfunc, leftfunc, file_length, finflag, interval, sp):
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
        self.sp = sp
        self.lastids = []
        self.display()

    def _rotate(self):
        cs = self.choker.connections
        for id in self.lastids:
            for i in xrange(len(cs)):
                if cs[i].get_id() == id:
                    return cs[i:] + cs[:i]
        return cs

    def print_spew(self):
        s = StringIO()
        cs = self._rotate()
        self.lastids = [c.get_id() for c in cs]
        for c in cs:
            s.write('%20s ' % c.get_ip())
            if c is self.choker.connections[0]:
                s.write('*')
            else:
                s.write(' ')
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
        print s.getvalue()

    def collect_spew(self):
        l = [ ]
        cs = self._rotate()
        self.lastids = [c.get_id() for c in cs]
        for c in cs:
            rec = {}
            rec["ip"] = c.get_ip()
            if c is self.choker.connections[0]:
                rec["is_optimistic_unchoke"] = 1
            else:
                rec["is_optimistic_unchoke"] = 0
            if c.is_locally_initiated():
                rec["intiation"] = "local"
            else:
                rec["intiation"] = "remote"
            u = c.get_upload()
            rec["upload"] = (int(u.measure.get_rate()), u.is_interested(), u.is_choked())

            d = c.get_download()
            rec["download"] = (int(d.measure.get_rate()), d.is_interested(), d.is_choked(), d.is_snubbed())
            
            l.append(rec)
        return l

    def display(self):
        self.add_task(self.display, self.interval)
        spew = []
        if self.sp:
            self.print_spew()
        else:
            spew = self.collect_spew()
        if self.finflag.isSet():
            self.statusfunc({"upRate" : self.upfunc(), "spew" : spew})
            return
        timeEst = self.remainingfunc()

        fractionDone = (self.file_length - self.leftfunc()) / float(self.file_length)
        
        if timeEst is not None:
            self.statusfunc({	"timeEst" : timeEst,
                                "fractionDone" : fractionDone, 
                                "downRate" : self.downfunc(), 
                                "upRate" : self.upfunc(),
                                "spew" : spew
                            })
        else:
            self.statusfunc({	"fractionDone" : fractionDone, 
                                "downRate" : self.downfunc(), 
                                "upRate" : self.upfunc(),
                                "spew" : spew
                            })
