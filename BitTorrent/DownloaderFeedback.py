# written by Bram Cohen
# this file is public domain

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
    h, r = divmod(t, 60 * 60)
    m, sec = divmod(r, 60)
    if h > 0:
        return str(h) + ':' + ex(m) + ':' + ex(sec)
    else:
        return str(m) + ':' + ex(sec)

class DownloaderFeedback:
    def __init__(self, connecter, add_task, port, ip, displayfunc):
        self.connecter = connecter
        self.add_task = add_task
        self.port = port
        self.ip = ip
        self.displayfunc = displayfunc
        self.add_task(self.display, 1)

    def display(self):
        self.add_task(self.display, 1)
        t = time()
        s = StringIO()
        s.write('listening on ' + self.ip + ':' + str(self.port) + '\n')
        ls = []
        for c in self.connecter.connections.values():
            ls.append(c.get_ip(), c)
        ls.sort()

        for ip, c in ls:
            s.write(ip + ' ')
            u = c.get_upload()
            if u.lastout < t - 15:
                u.update_rate(0)
            if c.is_locally_initiated():
                s.write('L ')
            else:
                s.write('R ')
            if u.is_choked():
                s.write('C')
            else:
                s.write(' ')
            if u.is_interested():
                s.write('I')
            else:
                s.write(' ')
            s.write(kify(u.rate) + ' up ')

            d = c.get_download()
            if d.lastin < t - 15:
                d.update_rate(0)
            if d.is_choked():
                s.write('C')
            else:
                s.write(' ')
            if d.is_interested():
                s.write('I')
            else:
                s.write(' ')
            s.write(kify(d.rate) + ' down\n')
        self.displayfunc(s.getvalue(), 'Cancel')
