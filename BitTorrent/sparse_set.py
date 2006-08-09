# SparseSet is meant to act just like a set object, but without actually
# storing discrete values for every item in the set
#
# by Greg Hazel

from __future__ import generators

from bisect import bisect_left
from itertools import izip

class SparseSet(object):

    def __init__(self, s = None):
        self._begins = []
        # ends are non-inclusive
        self._ends = []
        if s is not None:
            if isinstance(s, SparseSet):
                self._begins = list(s._begins)
                self._ends = list(s._ends)
            else:                
                self.add_range(s)

    def _collapse_range(self, l):
        last = None
        begins = []
        ends = []
        if len(l) == 0:
            return begins, ends
        
        begins.append(l[0])
        for i in l:
            if last and i > (last + 1):
                ends.append(last + 1)
                begins.append(i)
            last = i

        if last is not None:
            ends.append(last + 1)

        return begins, ends        

    def subtract_range(self, l):
        begins, ends = self._collapse_range(l)
        for b, e in izip(begins, ends):
            self.subtract(b, e)
        
    def add_range(self, l):
        begins, ends = self._collapse_range(l)
        for b, e in izip(begins, ends):
            self.add(b, e)

    def add(self, begin, end=None):
        if end is None:
            end = begin + 1
        else:
            assert end > begin

        if len(self._begins) == 0:
            b_i = 0
        else:
            b_i = bisect_left(self._begins, begin)

            if b_i == 0:
                if begin >= self._begins[b_i]:
                    begin = self._begins[b_i]
            elif begin <= self._ends[b_i - 1]:
                b_i -= 1
                begin = self._begins[b_i]

            e_i = bisect_left(self._ends, end, b_i)

            if e_i < len(self._ends):
                if end >= self._begins[e_i]:
                    end = self._ends[e_i]
                else:
                    e_i -= 1

            # small optimization
            if b_i == e_i:
                if b_i == len(self._begins):
                    self._begins.append(begin)
                    self._ends.append(end)
                else:
                    self._begins[b_i] = begin
                    self._ends[b_i] = end
                return
            
            del self._begins[b_i:e_i + 1]
            del self._ends[b_i:e_i + 1]
                
        self._begins.insert(b_i, begin)
        self._ends.insert(b_i, end)

    def subtract(self, begin, end=None):
        if end is None:
            end = begin + 1
        else:
            assert end > begin

        b_i = bisect_left(self._begins, begin)
        s_b_i = max(b_i - 1, 0)
        e_i = bisect_left(self._ends, end, s_b_i)

        beginning_is_an_end = False
        end_is_an_end = False

        if b_i > 0 and begin < self._ends[b_i - 1]:
            beginning_is_an_end = True

        if e_i < len(self._ends):
            if end == self._ends[e_i]:
                e_i += 1
            elif end > self._begins[e_i]:
                end_is_an_end = True

        del self._begins[b_i:e_i]
        del self._ends[b_i:e_i]

        if beginning_is_an_end:
            old_end = self._ends[b_i - 1]
            self._ends[b_i - 1] = begin
    
        if beginning_is_an_end and end_is_an_end:
            if b_i > e_i:
                self._begins.insert(b_i, end)
                self._ends.insert(b_i, old_end)

        if end_is_an_end:
            self._begins[b_i] = end
    remove = subtract

    def is_range_in(self, x, y):
        assert y > x
        i = bisect_left(self._begins, x)
        if i > 0 and x < self._ends[i - 1]:
            if y <= self._ends[i - 1]:
                return True
        if i < len(self._begins) and x >= self._begins[i] and x < self._ends[i]:
            if y <= self._ends[i]:
                return True
        return False

    def offset(self, x):
        for i in xrange(len(self._begins)):
            self._begins[i] += x
            self._ends[i] += x

    def __getitem__(self, i):
        r = i
        if r < 0:
            r = len(self) + i
        for b, e in izip(self._begins, self._ends):
            l = e - b
            if r < 0:
                break
            if l > r:
                return b + r
            r -= l
        raise IndexError("SparseSet index '%s' out of range" % i)

    def __iter__(self):
        for b, e in izip(self._begins, self._ends):
            for i in xrange(b, e):
                yield i

    def iterneg(self, begin, end):
        ranges = []
        b_i = bisect_left(self._begins, begin)
        for b, e in izip(self._begins[b_i:], self._ends[b_i:]):
            for i in xrange(begin, b):
                yield i
            begin = e
        if begin < end:
            for i in xrange(begin, end):
                yield i        

    def iterrange(self):
        for b, e in izip(self._begins, self._ends):
            yield (b, e)

    def largest_range(self):
        m = None
        r = None
        for b, e in izip(self._begins, self._ends):
            if b - e > m:
                m = b - e
                r = (b, e)
        return r

    def __eq__(self, s):
        if not isinstance(s, SparseSet):
            return False
        return (self._begins == s._begins) and (self._ends == s._ends)

    def __ne__(self, s):
        if not isinstance(s, SparseSet):
            return True
        return (self._begins != s._begins) or (self._ends != s._ends)

    def __contains__(self, x):
        i = bisect_left(self._begins, x)
        if i > 0 and x < self._ends[i - 1]:
            return True
        if i < len(self._begins) and x == self._begins[i]:
            return True
        return False

    def __len__(self):
        l = 0
        for b, e in izip(self._begins, self._ends):
            l += e - b
        return l

    def __sub__(self, s):
        n = SparseSet(self)
        if isinstance(s, SparseSet):
            for b, e in izip(s._begins, s._ends):
                n.subtract(b, e)
        else:
            n.subtract_range(list(s))
        return n

    def __add__(self, s):
        n = SparseSet(self)
        if isinstance(s, SparseSet):
            for b, e in izip(s._begins, s._ends):
                n.add(b, e)
        else:
            n.add_range(list(s))
        return n

    def __repr__(self):
        return 'SparseSet(%s)' % str(zip(self._begins, self._ends))

    def __str__(self):
        return str(zip(self._begins, self._ends))


## below be unit tests
################################################################################
    
if __name__ == '__main__':
    import sys
    
    s = SparseSet()

    def blank():
        #print "-" * 79
        s._begins = []
        s._ends = []
    
    def reset():
        #print "-" * 79
        s._begins = [ 1,
                      10,
                      25,
                      300,
                     ]
        s._ends = [ 3,
                    15,
                    45,
                    1000,
                   ]
        
    def test(l):
        a = zip(s._begins, s._ends)
        assert a == l, str(a) + " is not " + str(l)
        
    reset()
    s.add(2, 24)
    test([(1, 24), (25, 45), (300, 1000)])

    reset()
    s.add(4, 27)
    test([(1, 3), (4, 45), (300, 1000)])

    reset()
    s.add(4, 24)
    test([(1, 3), (4, 24), (25, 45), (300, 1000)])

    reset()
    s.add(4, 23)
    test([(1, 3), (4, 23), (25, 45), (300, 1000)])

    reset()
    s.add(4, 7)
    test([(1, 3), (4, 7), (10, 15), (25, 45), (300, 1000)])
    
    reset()
    s.add(4, 46)
    test([(1, 3), (4, 46), (300, 1000)])

    blank()
    s.add_range(range(1, 3))
    s.add_range(range(10, 15))
    s.add_range(range(25, 45))
    s.add_range(range(300, 1000))
    s.add(4, 46)
    test([(1, 3), (4, 46), (300, 1000)])

    blank()
    s.add_range(range(1, 3))
    s.add_range(range(10, 15))
    s.add_range(range(25, 45))
    s.add_range(range(0))
    s.add_range(range(300, 1000))
    s.add(4, 46)
    test([(1, 3), (4, 46), (300, 1000)])

    blank()
    s.add_range(range(1, 3))
    s.add_range(range(10, 15))
    s.add_range(range(25, 45))
    s.add_range(range(1))
    s.add_range(range(300, 1000))
    s.add(4, 46)
    test([(0, 3), (4, 46), (300, 1000)])


    blank()
    s.add_range(range(1, 3))
    s.add_range(range(10, 15))
    s.add_range(range(25, 45))
    s.add_range(range(300, 1000))
    for i in xrange(1, 3):
        assert i in s, str(i) + " is in " + str(s)
    assert not (i+1) in s
    for i in xrange(10, 15):
        assert i in s, str(i) + " is in " + str(s)
    assert not (i+1) in s
    for i in xrange(300, 1000):
        assert i in s, str(i) + " is in " + str(s)
    assert not (i+1) in s
    assert s.is_range_in(1, 3)
    assert not s.is_range_in(1, 3 + 1)
    assert s.is_range_in(300, 1000)
    assert not s.is_range_in(300 - 1, 1000)
    assert not s.is_range_in(300, 2000)
    assert s.is_range_in(300, 700)

    reset()
    s.add(2, 700)
    test([(1, 1000)])

    blank()
    s.add(0, 10)
    test([(0, 10)])

    s.add(-2, 1)
    test([(-2, 10)])

    def reset2():
        blank()
        s.add(0, 10)
        s.add(20, 30)
        s.add(40, 50)
        s.add(60, 70)

    reset2()
    s.add(0, 70)
    test([(0, 70)])

    reset2()
    s.add(1, 70)
    test([(0, 70)])

    reset2()
    s.add(0, 69)
    test([(0, 70)])


    reset2()
    s.add(-1, 70)
    test([(-1, 70)])

    reset2()
    s.add(0, 71)
    test([(0, 71)])

    reset2()
    s.add(15, 55)
    test([(0, 10), (15, 55), (60, 70)])

    blank()
    try:
        s.add(1, 1)
    except AssertionError:
        pass
    else:
        assert False
    test([])


    blank()
    try:
        s.add(1, 0)
    except AssertionError:
        pass
    else:
        assert False
    test([])


    blank()
    try:
        s.add(1, 2)
    except AssertionError:
        assert False
    test([(1, 2)])


    blank()
    s.add(1.5, 3.7)
    s.add(2.5, 4.7)


    blank()
    s.add(1, 3)
    s.add(2, 4)
    test([(1, 4)])


    blank()
    s.add(2, 4)
    s.add(1, 3)
    test([(1, 4)])


    blank()
    s.add(0, 2)
    s.add(2, 4)
    test([(0, 4)])


    blank()
    s.add(2, 4)
    s.add(0, 2)
    test([(0, 4)])


    blank()
    s.add(2, 3)
    s.add(0, 1)
    test([(0, 1), (2, 3)])


    blank()
    s.add(0, 1)
    s.add(2, 4)
    test([(0, 1), (2, 4)])


    blank()
    from random import shuffle
    l = range(0, 11)
    shuffle(l)
    for i in l:
        s.add(i, i+1)

    del l

    def testy_thing(d):
        blank()
        for i in d:
            s.add(i)
        test([(0, 5)])
        
    def testy_thing2(d):
        blank()
        for i in d:
            s.add(i*2)
        test([(0, 1), (2, 3), (4, 5), (6, 7), (8, 9)])

    all = []
    def xcombinations(items, n):
        if n == 0:
            yield []
        else:
            for i in xrange(len(items)):
                for cc in xcombinations(items[:i] + items[i+1:], n - 1):
                    yield [items[i]] + cc

    for uc in xcombinations(range(5), 5):
        all.append(uc)

    for d in all:
        testy_thing(d)

    for d in all:
        testy_thing2(d)

    blank()
    s.add(0, 1000)
    s.subtract(200, 500)
    test([(0, 200), (500, 1000)])

    #blank()
    s.subtract(200, 500)
    test([(0, 200), (500, 1000)])

    s.subtract(100, 201)
    test([(0, 100), (500, 1000)])

    s.subtract(300, 500)
    test([(0, 100), (500, 1000)])

    s.subtract(30, 50)
    test([(0, 30), (50, 100), (500, 1000)])

    s.subtract(29, 1001)
    test([(0, 29)])

    blank()
    s.add(0, 30)
    s.add(51, 100)
    s.add(501, 1000)

    s.subtract(-1, 900)
    test([(900, 1000)])
    
    blank()
    s.add(0, 30)
    s.add(51, 100)
    s.add(501, 1000)

    s.subtract(29, 502)
    test([(0, 29), (502, 1000)])
    
    blank()
    s.add(0, 30)
    s.add(51, 100)
    s.add(501, 1000)

    s.subtract(35, 200)
    test([(0, 30), (501, 1000)])

    blank()
    s.add(0, 30)
    s.add(51, 100)
    s.add(501, 1000)

    s.subtract(55, 601)
    test([(0, 30), (51, 55), (601, 1000)])
    
    blank()
    s.add(0, 30)
    s.add(51, 100)
    s.add(501, 1000)

    s.subtract(25, 70)
    test([(0, 25), (70, 100), (501, 1000)])

    blank()
    s.add(0, 30)
    s.add(51, 100)
    s.add(501, 1000)
    s.add(2000, 10000)

    s.subtract(25, 502)
    test([(0, 25), (502, 1000), (2000, 10000)])

    blank()
    s.add(0, 30)
    s.add(51, 100)
    s.add(102, 189)
    s.add(501, 1000)
    s.add(2000, 10000)

    s.subtract(25, 502)
    test([(0, 25), (502, 1000), (2000, 10000)])

    blank()
    s.add(0, 30)
    s.add(51, 100)
    s.add(102, 189)
    s.add(501, 1000)

    s.subtract(25, 1000)
    test([(0, 25)])

    blank()
    s.add(0, 30)
    s.add(51, 100)
    s.add(102, 189)
    s.add(501, 1000)

    s.subtract_range(range(25, 1000))
    test([(0, 25)])

    blank()
    s.add(0, 30)
    s.add(51, 100)
    s.add(102, 189)
    s.add(501, 1000)

    s.subtract(52, 999)
    test([(0, 30), (51, 52), (999, 1000)])

    blank()
    import random
    all = []
    assert len(s._begins) == 0
    for i in range(0, 10):
        b = random.randint(0, 10000)
        l = random.randint(1, 1000)
        all.append((b, b+l))
        s.add_range(range(b, b+l))

    for b, e in all:
        s.subtract(b, e)

    assert len(s._begins) == 0

    blank()
    s.add(0, 100)
    s.add(1000, 2000)

    assert s[-1] == 1999

    assert s[0] == 0 
    assert s[99] == 99
    assert s[100] == 1000
    assert s[101] == 1001

    blank()
    s.add(-10, -5)
    s.add(0, 100)
    
    assert s[0] == -10
    assert s[10] == 5
    assert s[-1] == 99


    blank()
    s.add(0, 100)
    s.add(1000, 1100)
    f = range(0, 100) + range(1000, 1100)
    for i in s:
        assert i == f.pop(0)

    blank()
    s.add(0, 100)
    s.add(1000, 1100)
    f = range(0, 100) + range(1000, 1100)
    for i in s.iterneg(0, 1100):
        assert i not in f

    blank()
    s.add(0, 100)
    y = range(0, 100)
    n = range(100, 200)
    for i in s.iterneg(0, 200):
        assert i not in y
        assert i in n

    blank()
    s.add(100, 200)
    y = range(100, 200)
    n = range(0, 100)
    for i in s.iterneg(0, 200):
        assert i not in y
        assert i in n

    s = SparseSet()
    s.add(2, 50)
    s.add(100, 1000)
    t = SparseSet(s)
    assert t == s
    assert not (t != s)
    assert id(t) != id(s)

    s = SparseSet()
    s.add(2, 50)
    s.add(100, 1000)
    t = SparseSet()
    t.add(20, 500)
    t.add(1000, 10000)
    o = SparseSet(t)
    n = t - s
    assert t == o
    assert t._begins == o._begins
    assert t._ends == o._ends
    assert n != t    
    
    s = SparseSet()
    s.add(2, 50)
    s.add(100, 1000)
    t = SparseSet()
    t.add(20, 500)
    t.add(1000, 10000)
    o = SparseSet(t)
    n = t + s
    assert t == o
    assert t._begins == o._begins
    assert t._ends == o._ends
    assert n != t    

    s = SparseSet()
    s.add(2, 50)
    s.add(100, 1000)
    t = SparseSet()
    t.add(2, 50)
    t.add(100, 10000)
    assert t != s
    
    s = SparseSet()
    s.add(2, 50)
    s.add(100, 1000)
    t = SparseSet()
    t.add(20, 500)
    t.add(1000, 10000)
    n = t - s
    t -= s
    assert n == t, '%s %s' % (n, t)
    
    print "passed all tests."
    