# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time
from BTL.sparse_set import SparseSet

def main():
    _t = time.clock()
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
    except ValueError:
        pass
    else:
        assert False
    test([])


    blank()
    try:
        s.add(1, 0)
    except ValueError:
        pass
    else:
        assert False
    test([])


    blank()
    try:
        s.add(1, 2)
    except ValueError:
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
    
    print "passed all tests in", time.clock() - _t

if __name__ == '__main__':
    main()    