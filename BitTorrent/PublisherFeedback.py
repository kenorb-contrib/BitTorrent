# written by Bram Cohen
# this file is public domain

from urllib import urlopen
from threading import Thread
from time import sleep
from cStringIO import StringIO
from binascii import b2a_hex
from sys import stdout
true = 1
false = 0

def kify(n):
    return long((n / (2 ** 10)) * 10) / 10.0

class PublisherFeedback:
    def __init__(self, uploader, add_task, port, ip, blobs):
        self.add_task = add_task
        self.uploader = uploader
        self.port = port
        self.blobs = blobs
        self.ip = ip
        self.total = 0
        self.rate = 0
        self.add_task(self.display, 1)

    def display(self):
        self.add_task(self.display, 1)
        s = StringIO()
        s.write('\n\n\n\n')
        sum = 0
        for u in self.uploader.uploads.values():
            sum += u.sent_since_checkpoint
            u.rate = (u.rate * 19.0 + u.sent_since_checkpoint) / 20
            u.sent_since_checkpoint = 0
        self.total += sum
        self.rate = (self.rate * 19.0 + sum) / 20.0
        k = self.uploader.uploads.keys()
        k.sort()
        for x in k:
            u = self.uploader.uploads[x]
            s.write(u.get_ip())
            if u.is_throttled():
                s.write(' T ')
            elif u.is_uploading():
                s.write(' U ')
            else:
                s.write(' O ')
            if u.last_sent is not None:
                s.write(b2a_hex(u.last_sent[:2]) + ' ' + self.blobs[u.last_sent][0] + ' ')
                s.write(str(u.total) + ' ' + str(kify(u.rate)))
            s.write('\n')
        s.write('\nlistening on port ' + str(self.port) + ' of ' + self.ip + '\n')
        s.write('total sent ' + str(self.total) + '\n')
        s.write('sending rate (kilobytes/sec) '+ str(kify(self.rate)))
        print s.getvalue()
        stdout.flush()
