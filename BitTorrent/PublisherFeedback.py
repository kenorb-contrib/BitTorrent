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
    def __init__(self, connecter, add_task, port, ip):
        self.add_task = add_task
        self.connecter = connecter
        self.port = port
        self.ip = ip
        self.start = time()
        self.add_task(self.display, 1)

    def display(self):
        self.add_task(self.display, 1)
        t = time()
        s = StringIO()
        s.write('\n\n\n\n')
        ls = []
        for c in self.connecter.connections.values():
            ls.append((c.get_ip(), c))
        ls.sort()
        sum = 0
        for ip, c in ls:
            u = c.get_upload()
            if u.lastout < t - 15:
                u.update_rate(0)
            sum += u.rate
            s.write(u.get_ip())
            s.write(' ')
            if u.is_choked():
                s.write('C')
            else:
                s.write(' ')
            if u.is_interested():
                s.write('I')
            else:
                s.write(' ')
            s.write(' ' + kify(u.rate) + '\n')
        s.write('\nat ' + self.ip + ':' + str(self.port))
        s.write('\ntotal '+ kify(sum))
        print s.getvalue()
        stdout.flush()
