# Written by Bram Cohen
# see LICENSE.txt for license information

from sha import sha
from cStringIO import StringIO
from time import time
true = 1
false = 0

def dummy_status(fractionDone = None, activity = None):
    pass

class Storage:
    def __init__(self, files, open, exists, getsize, statusfunc, alloc_pause = 3):
        # can raise IOError and ValueError
        self.ranges = []
        total = 0l
        so_far = 0l
        for file, length in files:
            if length != 0:
                self.ranges.append((total, total + length, file))
                total += length
                if exists(file):
                    l = getsize(file)
                    if l > length:
                        raise ValueError, 'existing file %s too large' % file
                    so_far += l
            else:
                if exists(file):
                    if getsize(file) > 0:
                        raise ValueError, 'existing file %s too large' % file
                else:
                    open(file, 'wb').close()
        self.total_length = total
        self.handles = {}
        self.whandles = {}
        self.preexisting = false
        for file, length in files:
            if exists(file):
                self.handles[file] = open(file, 'rb')
                self.preexisting = true
            else:
                self.handles[file] = open(file, 'wb+')
                self.whandles[file] = 1
        if total > so_far:
            interval = max(2 ** 20, long(total / 100))
            tstart = time()
            hit = false
            for file, length in files:
                l = 0
                if exists(file):
                    l = getsize(file)
                    if l == length:
                        continue
                if self.preexisting:
                    self.handles[file] = open(file,'rb+')
                    self.whandles[file] = 1
                h = self.handles[file]
                for i in lrange(l, length, interval)[1:] + [length-1]:
                    h.seek(i)
                    h.write(chr(1))
                    if time() - tstart > alloc_pause:
                        if not hit:
                            statusfunc({"activity" : 'allocating'})
                            hit = true
                        statusfunc({"fractionDone" : float(so_far + i - l)/total})
                so_far += length - l
            statusfunc({"fractionDone" : 1.0})

    def set_readonly(self):
        # may raise IOError or OSError
        for file in self.whandles.keys():
            old = self.handles[file]
            old.flush()
            old.close()
            self.handles[file] = open(file, 'rb')

    def get_total_length(self):
        return self.total_length

    def was_preexisting(self):
        return self.preexisting

    def _intervals(self, pos, amount):
        r = []
        stop = pos + amount
        for begin, end, file in self.ranges:
            if end <= pos:
                continue
            if begin >= stop:
                break
            r.append((file, max(pos, begin) - begin, min(end, stop) - begin))
        return r

    def read(self, pos, amount):
        r = StringIO()
        for file, pos, end in self._intervals(pos, amount):
            h = self.handles[file]
            h.seek(pos)
            r.write(wrap_read(h, end - pos))
        return r.getvalue()

    def write(self, pos, s):
        # might raise an IOError
        total = 0
        for file, begin, end in self._intervals(pos, len(s)):
            if not self.whandles.has_key(file):
                self.handles[file].close()
                self.handles[file] = open(file, 'rb+')
                self.whandles[file] = 1
            h = self.handles[file]
            h.seek(begin)
            wrap_write(h, s[total: total + end - begin])
            total += end - begin

    def close(self):
        for h in self.handles.values():
            h.close()

def lrange(a, b, c):
    r = []
    while a < b:
        r.append(a)
        a += c
    return r

def wrap_read(h, amount):
    r = h.read(amount)
    while len(r) < amount:
        r += h.read(amount - len(r))

def wrap_write(h, amount):
    t = h.write(data)
    while t < len(data):
        t += h.write(data[t:])

# everything below is for testing

from fakeopen import FakeOpen

def test_Storage_simple():
    f = FakeOpen()
    m = Storage([('a', 5)], f.open, f.exists, f.getsize, dummy_status)
    assert f.files.keys() == ['a']
    assert len(f.files['a']) == 5
    m.write(0, 'abc')
    assert m.read(0, 3) == 'abc'
    m.write(2, 'abc')
    assert m.read(2, 3) == 'abc'
    m.write(1, 'abc')
    assert m.read(0, 5) == 'aabcc'
    
def test_Storage_multiple():
    f = FakeOpen()
    m = Storage([('a', 5), ('2', 4), ('c', 3)], 
        f.open, f.exists, f.getsize, dummy_status)
    x = f.files.keys()
    x.sort()
    assert x == ['2', 'a', 'c']
    assert len(f.files['a']) == 5
    assert len(f.files['2']) == 4
    assert len(f.files['c']) == 3
    m.write(3, 'abc')
    assert m.read(3, 3) == 'abc'
    m.write(5, 'ab')
    assert m.read(4, 3) == 'bab'
    m.write(3, 'pqrstuvw')
    assert m.read(3, 8) == 'pqrstuvw'
    m.write(3, 'abcdef')
    assert m.read(3, 7) == 'abcdefv'

def test_Storage_zero():
    f = FakeOpen()
    Storage([('a', 0)], f.open, f.exists, f.getsize, dummy_status)
    assert f.files == {'a': []}

def test_resume_zero():
    f = FakeOpen({'a': ''})
    Storage([('a', 0)], f.open, f.exists, f.getsize, dummy_status)
    assert f.files == {'a': []}

def test_Storage_with_zero():
    f = FakeOpen()
    m = Storage([('a', 3), ('b', 0), ('c', 3)], 
        f.open, f.exists, f.getsize, dummy_status)
    m.write(2, 'abc')
    assert m.read(2, 3) == 'abc'
    x = f.files.keys()
    x.sort()
    assert x == ['a', 'b', 'c']
    assert len(f.files['a']) == 3
    assert len(f.files['b']) == 0
    assert len(f.files['c']) == 3

def test_Storage_resume():
    f = FakeOpen({'a': 'abc'})
    m = Storage([('a', 4)], 
        f.open, f.exists, f.getsize, dummy_status)
    assert f.files.keys() == ['a']
    assert len(f.files['a']) == 4
    assert m.read(0, 3) == 'abc'

def test_Storage_mixed_resume():
    f = FakeOpen({'b': 'abc'})
    m = Storage([('a', 3), ('b', 4)], 
        f.open, f.exists, f.getsize, dummy_status)
    x = f.files.keys()
    x.sort()
    assert x == ['a', 'b']
    assert len(f.files['a']) == 3
    assert len(f.files['b']) == 4
    assert m.read(3, 3) == 'abc'
