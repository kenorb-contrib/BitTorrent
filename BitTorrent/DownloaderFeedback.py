# written by Bram Cohen
# this file is public domain

from urllib import urlopen
from threading import Thread
from time import sleep
from cStringIO import StringIO
from binascii import b2a_hex
true = 1
false = 0

def kify(n):
    return long((n / (2 ** 10)) * 10) / 10.0

def ex(n):
    if n >= 10:
        return str(n)
    else:
        return '0' + str(n)

class DownloaderFeedback:
    def __init__(self, uploader, downloader, choker, add_task, port, ip, filesize, amount_left, displayfunc):
        self.add_task = add_task
        self.uploader = uploader
        self.downloader = downloader
        self.choker = choker
        self.port = port
        self.ip = ip
        self.filesize = filesize
        self.amount_left = amount_left
        self.displayfunc = displayfunc
        self.totalin = 0
        self.totalout = 0
        self.ratein = 0
        self.rateout = 0
        self.add_task(self.display, 1)

    def display(self):
        self.add_task(self.display, 1)
        s = StringIO()
        sumout = 0
        for u in self.uploader.uploads.values():
            sumout += u.sent_since_checkpoint
            u.rate = (u.rate * 19.0 + u.sent_since_checkpoint) / 20
            u.sent_since_checkpoint = 0
        self.totalout += sumout
        self.rateout = (self.rateout * 19.0 + sumout) / 20.0

        sumin = 0
        for d in self.downloader.downloads.values():
            sumin += d.received_since_checkpoint
            d.rate = (d.rate * 19.0 + d.received_since_checkpoint) / 20
            d.received_since_checkpoint = 0
        self.totalin += sumin
        self.ratein = (self.ratein * 19.0 + sumin) / 20.0

        s.write('listening on port ' + str(self.port) + ' of ' + self.ip + '\n')
        s.write('total sent ' + str(self.totalout) + '\n')
        s.write('sending rate (kilobytes/sec) '+ str(kify(self.rateout)) + '\n')
        s.write('total received ' + str(self.totalin) + '\n')
        s.write('receiving rate (kilobytes/sec) ' + str(kify(self.ratein)) + '\n')
        s.write('file size: ' + str(self.filesize) + '\n')
        s.write('bytes remaining ' + str(self.amount_left - self.totalin) + '\n')
        s.write('estimated time remaining: ')
        if self.ratein < 128:
            s.write('----')
        else:
            t = long((self.amount_left - self.totalin) / self.ratein)
            h, r = divmod(t, 60 * 60)
            m, sec = divmod(r, 60)
            if h > 0:
                s.write(str(h) + ':' + ex(m) + ':' + ex(sec))
            else:
                s.write(str(m) + ':' + ex(sec))

        d = {}
        for x in self.uploader.uploads.keys():
            d[x] = 1
        for x in self.downloader.downloads.keys():
            d[x] = 1
        k = d.keys()
        k.sort()
        for x in k:
            s.write('\n\n')
            u = self.uploader.uploads.get(x)
            d = self.downloader.downloads.get(x)
            m = u
            if m is None:
                m = d
            s.write(m.get_ip() + ' ')
            if m.connection.is_locally_initiated():
                s.write('local\n')
            else:
                s.write('remote\n')
            
            if u is not None:
                if u.is_choked():
                    s.write('T ')
                elif u.is_uploading():
                    s.write('U ')
                else:
                    s.write('O ')
                if u.last_sent is not None:
                    s.write(b2a_hex(u.last_sent[:2]) + ' ')
                    s.write(str(u.total) + ' ' + str(kify(u.rate)))
            s.write('\n')
            if d is not None:
                if d.is_choked():
                    s.write('T ')
                else:
                    s.write(str(len(d.active_requests)) + ' ')
                if d.last is not None:
                    s.write(b2a_hex(d.last[:2]) + ' ')
                    s.write(str(d.total) + ' ' + str(kify(d.rate)))
        self.displayfunc(s.getvalue(), 'Cancel')
