# Written by Bram Cohen
# see LICENSE.txt for license information

from time import time
from cStringIO import StringIO
from zurllib import quote

true = 1
false = 0

class DownloaderFeedback:
    def __init__(self, choker, httpdl, add_task, statusfunc, upfunc, downfunc,
            remainingfunc, leftfunc, file_length, finflag, interval, sp,
            statistics):
        self.choker = choker
        self.httpdl = httpdl
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
        self.statistics = statistics
        self.lastids = []
        self.display()
        self.spewdata = None

    def _rotate(self):
        cs = self.choker.connections
        for id in self.lastids:
            for i in xrange(len(cs)):
                if cs[i].get_id() == id:
                    return cs[i:] + cs[:i]
        return cs

    def spews(self):
        l = []
        cs = self._rotate()
        self.lastids = [c.get_id() for c in cs]
        for c in cs:
            a = {}
            a['id'] = quote(c.get_id())
            a['ip'] = c.get_ip()
            a['optimistic'] = (c is self.choker.connections[0])
            if c.is_locally_initiated():
                a['direction'] = 'L'
            else:
                a['direction'] = 'R'
            u = c.get_upload()
            a['uprate'] = int(u.measure.get_rate())
            a['uinterested'] = u.is_interested()
            a['uchoked'] = u.is_choked()
            d = c.get_download()
            a['downrate'] = int(d.measure.get_rate())
            a['dinterested'] = d.is_interested()
            a['dchoked'] = d.is_choked()
            a['snubbed'] = d.is_snubbed()
            a['utotal'] = d.connection.upload.measure.get_total()
            a['dtotal'] = d.connection.download.measure.get_total()
            if len(d.connection.download.have) > 0:
                a['completed'] = float(len(d.connection.download.have)-d.connection.download.unhave)/float(len(d.connection.download.have))
            else:
                a['completed'] = 1.0
            a['speed'] = d.connection.download.peermeasure.get_rate()
                                               
            l = l + [a]

        for dl in self.httpdl.get_downloads():
            if dl.goodseed:
                a = {}
                a['id'] = 'http seed'
                a['ip'] = dl.baseurl
                a['optimistic'] = false
                a['direction'] = 'L'
                a['uprate'] = 0
                a['uinterested'] = false
                a['uchoked'] = false
                a['downrate'] = int(dl.measure.get_rate())
                a['dinterested'] = true
                a['dchoked'] = not dl.active
                a['snubbed'] = not dl.active
                a['utotal'] = None
                a['dtotal'] = dl.measure.get_total()
                a['completed'] = 1.0
                a['speed'] = None

                l = l + [a]

        return l


    def display(self):
        self.add_task(self.display, self.interval)
        self.statistics.update()
        if self.sp.isSet():
            spewdata = self.spews()
        else:
            spewdata = None
        if self.finflag.isSet():
            self.statusfunc(upRate = self.upfunc(),
            statistics = self.statistics, spew = spewdata, sizeDone = self.file_length)
            return
        timeEst = self.remainingfunc()

        if self.file_length > 0:
            fractionDone = (self.file_length - self.leftfunc()) / float(self.file_length)
        else:
            fractionDone = 1.0
        sizeDone = self.file_length - self.leftfunc()
        
        if timeEst is not None:
            self.statusfunc(timeEst = timeEst, fractionDone = fractionDone, 
                downRate = self.downfunc(), upRate = self.upfunc(),
                statistics = self.statistics, spew = spewdata, sizeDone = sizeDone)
        else:
            self.statusfunc(fractionDone = fractionDone, 
                downRate = self.downfunc(), upRate = self.upfunc(),
                statistics = self.statistics, spew = spewdata, sizeDone = sizeDone)
