from UserDict import DictMixin
from time import time

class Cache(DictMixin):
    def __init__(self, touch_on_access = False):
        self.data = {}
        self.q = []
        self.touch = touch_on_access
        
    def __getitem__(self, key):
        if self.touch:
            v = self.data[key][1]
            self[key] = v
        return self.data[key][1]

    def __setitem__(self, key, value):
        t = time()
        self.data[key] = (t, value)
        self.q.insert(0, (t, key, value))

    def __delitem__(self, key):
        del(self.data[key])

    def keys(self):
        return self.data.keys()

    def expire(self, expire_time):
        try:
            while self.q[-1][0] < expire_time:
                x = self.q.pop()
                assert(x[0] < expire_time)
                try:
                    t, v = self.data[x[1]]
                    if v == x[2] and t == x[0]:
                        del(self.data[x[1]])
                except KeyError:
                    pass
        except IndexError:
            pass
        
