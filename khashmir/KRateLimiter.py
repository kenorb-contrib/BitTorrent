# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

from BitTorrent.platform import bttime as time
from const import *

class KRateLimiter:
    # special rate limiter that drops entries that have been sitting in the queue for longer than self.age seconds
    # by default we toss anything that has less than 5 seconds to live
    def __init__(self, transport, rate, call_later, age=(KRPC_TIMEOUT - 5)):
        self.q = []
        self.transport = transport
        self.rate = rate
        self.curr = 0
        self.running = False
        self.age = age
        self.last = 0
        self.call_later = call_later

        if self.rate == 0:
            self.rate = 1e10
            
    def sendto(self, s, i, addr):
        self.q.insert(0, (time(), (s, i, addr)))
        if not self.running:
            self.run(check=True)

    def run(self, check=False):
        self.expire()

        self.curr -= (time() - self.last) * self.rate
        if check:
            self.curr = max(self.curr, 0 - self.rate)
            
        while self.q and self.curr <= 0:
            x, tup = self.q.pop()
            self.curr += len(tup[0])
            self.transport.sendto(*tup)
            
        if self.q or self.curr > 0:
            self.running = True
            # sleep for at least a half second
            self.call_later(self.run, max(self.curr / self.rate, 0.5))
        else:
            self.running = False
                          
    def expire(self):
        if self.q:
            expire_time = time() - self.age
            while self.q[-1][0] < expire_time:
                self.q.pop()
