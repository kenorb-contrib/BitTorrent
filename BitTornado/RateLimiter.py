# Written by Bram Cohen
# see LICENSE.txt for license information

from traceback import print_exc
from binascii import b2a_hex
from clock import clock
from cStringIO import StringIO

try:
    True
except:
    True = 1
    False = 0


class RateLimiter:
    def __init__(self, sched, unitsize):
        self.sched = sched
        self.last = None
        self.unitsize = unitsize

    def set_upload_rate(self, rate):
        if rate == 0:
            rate = 10e10
        self.upload_rate = rate * 1000
        self.lasttime = clock()
        self.bytes_sent = 0

    def queue(self, conn):
        assert conn.next_upload is None
        if self.last is None:
            self.last = conn
            conn.next_upload = conn
            self.try_send(True)
        else:
            conn.next_upload = self.last.next_upload
            self.last.next_upload = conn
            self.last = conn

    def try_send(self, check_time = False):
        t = clock()
        self.bytes_sent -= (t - self.lasttime) * self.upload_rate
        self.lasttime = t
        if check_time:
            self.bytes_sent = max(self.bytes_sent, 0)
        cur = self.last.next_upload
        while self.bytes_sent <= 0:
            bytes = cur.send_partial(self.unitsize)
            self.bytes_sent += bytes
            if bytes == 0 or cur.backlogged():
                if self.last is cur:
                    self.last = None
                    cur.next_upload = None
                    break
                else:
                    self.last.next_upload = cur.next_upload
                    cur.next_upload = None
                    cur = self.last.next_upload
            else:
                self.last = cur
                cur = cur.next_upload
        else:
            self.sched(self.try_send, self.bytes_sent / self.upload_rate)
