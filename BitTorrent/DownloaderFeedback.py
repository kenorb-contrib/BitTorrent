# Written by Bram Cohen
# This file is public domain
# The authors disclaim all liability for any damages resulting from
# any use of this software.

from time import time
from cStringIO import StringIO
true = 1
false = 0

def kify(n):
    return str(long((n / (2 ** 10)) * 10) / 10.0)

def ex(n):
    if n >= 10:
        return str(n)
    else:
        return '0' + str(n)

def hours(n):
    n = int(n)
    h, r = divmod(n, 60 * 60)
    m, sec = divmod(r, 60)
    if h > 0:
        return str(h) + ':' + ex(m) + ':' + ex(sec)
    else:
        return str(m) + ':' + ex(sec)

class DownloaderFeedback:
    def __init__(self, choker, add_task, port, ip, displayfunc, max_pause, remainingfunc):
        self.choker = choker
        self.add_task = add_task
        self.port = port
        self.ip = ip
        self.displayfunc = displayfunc
        self.max_pause = max_pause
        self.remainingfunc = remainingfunc
        self.add_task(self.display, 1)

    def display(self):
        self.add_task(self.display, 1)
        t = time()
        s = StringIO()
        s.write('listening on ' + self.ip + ':' + str(self.port) + '\n')
        r = self.remainingfunc()
        if r is None:
            s.write('time left: ---\n')
        else:
            s.write('time left: ' + hours(r) + '\n')

        for c in self.choker.connections:
            s.write(c.get_ip() + ' ')
            u = c.get_upload()
            if u.lastout < t - self.max_pause:
                u.update_rate(0)
            if c.is_locally_initiated():
                s.write('l ')
            else:
                s.write('r ')
            if u.is_choked():
                s.write('c')
            else:
                s.write(' ')
            if u.is_interested():
                s.write('i')
            else:
                s.write(' ')
            s.write(' %6s up ' % kify(u.rate) + '    ')

            d = c.get_download()
            if d.lastin < t - self.max_pause:
                d.update_rate(0)
            if d.is_choked():
                s.write('c')
            else:
                s.write(' ')
            if d.is_interested():
                s.write('i')
            else:
                s.write(' ')
            s.write(' %6s down\n' % kify(d.rate))
        self.displayfunc(s.getvalue(), 'Cancel')
