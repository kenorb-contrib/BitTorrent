# written by Bram Cohen
# this file is public domain

from time import time
from cStringIO import StringIO
from sys import stdout
true = 1
false = 0

def kify(n):
    return str(long((n / (2 ** 10)) * 10) / 10.0)

class PublisherFeedback:
    def __init__(self, choker, add_task, port, ip):
        self.choker = choker
        self.add_task = add_task
        self.port = port
        self.ip = ip
        self.start = time()
        self.add_task(self.display, 1)

    def display(self):
        self.add_task(self.display, 1)
        t = time()
        s = StringIO()
        s.write('\n\n\n\n')
        for c in self.choker.connections:
            u = c.get_upload()
            if u.lastout < t - 15:
                u.update_rate(0)
            s.write(c.get_ip())
            s.write(' ')
            if u.is_choked():
                s.write('c')
            else:
                s.write(' ')
            if u.is_interested():
                s.write('i')
            else:
                s.write(' ')
            s.write(' %6s\n' % kify(u.rate))
        s.write('\nat ' + self.ip + ':' + str(self.port))
        print s.getvalue()
        stdout.flush()
