# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

from UserDict import DictMixin
from heapq import *
from random import sample
from BitTorrent.platform import bttime as time

class KItem:
    def __init__(self, key, value):
        self.t = time()
        self.k = key
        self.v = value
    def __cmp__(self, a):
        # same value = same item, only used to keep dupes out of db
        if self.v == a.v:
            return 0

        # compare by time
        if self.t < a.t:
            return -1
        elif self.t > a.t:
            return 1
        else:
            return 0

    def __repr__(self):
        return `(self.k, self.v, self.t - time())`

## in memory data store for distributed tracker
## keeps a list of values per key in dictionary
## keeps oldest value for each key in one heap
## can efficiently expire all values older than a given time
## can insert one val at a time, or a list:  ks['key'] = 'value' or ks['key'] = ['v1', 'v2', 'v3']
class KStore(DictMixin):
    def __init__(self):
        self.d = {}
        self.q = []
        
    def __getitem__(self, key):
        return [x.v for x in self.d[key]]

    def __setitem__(self, key, value):
        if type(value) == type([]):
            [self.__setitem__(key, v) for v in value]
            return
        x = KItem(key, value)
        try:
            l = self.d[key]
        except KeyError:
            self.d[key] = [x]
            heappush(self.q, x)
        else:
            # this is slow
            try:
                i = l.index(x)
                del(l[i])
            except ValueError:
                pass
            l.insert(0, x)

    def __delitem__(self, key):
        del(self.d[key])

    def keys(self):
        return self.d.keys()

    def expire(self, t):
        #.expire values inserted prior to t
        try:
            while self.q[0].t < t:
                x = heappop(self.q)
                l = self.d[x.k]
                try:
                    while l[-1].t < t:
                        l.pop()
                    else:
                        heappush(self.q, l[-1])
                except IndexError:
                    del(self.d[x.k])
        except IndexError:
            pass
    
    def sample(self, key, n):
        # returns n random values of key, or all values if less than n
        try:
            l = [x.v for x in sample(self.d[key], n)]
        except ValueError:
            l = [x.v for x in self.d[key]]
        return l
