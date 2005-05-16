from UserDict import DictMixin
from time import time

class Cache(DictMixin):
    def __init__(self, touch_on_access = False):
        self.d = {}
        self.q = []
        self.touch = touch_on_access
        
    def __getitem__(self, key):
        if self.touch:
            t = time()
            v = self.d[key][1]
            self.d[key] = (t, v)
            self.q.insert(0, (t, key, v))
        return self.d[key][1]

    def __setitem__(self, key, value):
        t = time()
        self.d[key] = (t, value)
        self.q.insert(0, (t, key, value))

    def __delitem__(self, key):
        del(self.d[key])

    def keys(self):
        return self.d.keys()

    def expire(self, t):
        try:
            while self.q[-1][0] < t:
                x = self.q.pop()
                try:
                    t, v = self.d[x[1]]
                    if v == x[2] and t == x[0]:
                        del(self.d[x[1]])
                except KeyError:
                    pass
        except IndexError:
            pass
        
