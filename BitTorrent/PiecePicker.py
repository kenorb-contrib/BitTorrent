# Written by Bram Cohen
# see LICENSE.txt for license information

from random import randrange
true = 1
false = 0

class PiecePicker:
    def __init__(self, numpieces):
        self.numpieces = numpieces
        self.interests = [range(numpieces)]
        self.numinterests = [0] * numpieces
        self.started = []
        self.got_any = false

    def got_have(self, piece):
        if self.numinterests[piece] is not None:
            self.interests[self.numinterests[piece]].remove(piece)
            self.numinterests[piece] += 1
            if self.numinterests[piece] == len(self.interests):
                self.interests.append([])
            self.interests[self.numinterests[piece]].append(piece)

    def lost_have(self, piece):
        if self.numinterests[piece] is not None:
            self.interests[self.numinterests[piece]].remove(piece)
            self.numinterests[piece] -= 1
            self.interests[self.numinterests[piece]].append(piece)

    def requested(self, piece):
        if piece not in self.started:
            self.started.append(piece)

    def complete(self, piece):
        self.got_any = true
        self.interests[self.numinterests[piece]].remove(piece)
        self.numinterests[piece] = None
        try:
            self.started.remove(piece)
        except ValueError:
            pass

    def next(self, havefunc, havelist = None):
        if self.got_any:
            best = None
            bestnum = 2 ** 30
            for i in self.started:
                if havefunc(i) and self.numinterests[i] < bestnum:
                    best = i
                    bestnum = self.numinterests[i]
            if havelist is None:
                for i in self.interests[1:bestnum]:
                    for j in scramble(i):
                        if havefunc(j):
                            return j
            else:
                for i in scramble(havelist):
                    if havefunc(i) and self.numinterests[i] < bestnum:
                        best = i
                        bestnum = self.numinterests[i]
            return best
        else:
            for i in self.started:
                if havefunc(i):
                    return i
            if havelist is None:
                for i in scramble(xrange(self.numpieces)):
                    if havefunc(i):
                        return i
            else:
                for i in scramble(havelist):
                    if havefunc(i):
                        return i
            return None

class scramble:
    def __init__(self, mylist):
        self.mylist = mylist
        if mylist:
            self.s = randrange(len(mylist))
        else:
            self.s = 0
        self.d = len(mylist)
        if len(mylist) > 1:
            while gcd(self.d, len(mylist)) > 1:
                self.d = randrange(1, len(mylist))

    def __getitem__(self, n):
        if n >= len(self.mylist):
            raise IndexError
        return self.mylist[(self.s + self.d * n) % len(self.mylist)]

def gcd(a,b):
    while b:
        a, b = b, a%b
    return a

def test_requested():
    p = PiecePicker(9)
    p.complete(8)
    p.got_have(0)
    p.got_have(2)
    p.got_have(4)
    p.got_have(6)
    p.requested(1)
    p.requested(1)
    p.requested(3)
    p.requested(0)
    p.requested(6)
    v = _pull(p)
    assert v[:4] == [1, 3, 0, 6]
    assert v[4:] == [2, 4] or v[4:] == [4, 2]

def test_change_interest():
    p = PiecePicker(9)
    p.complete(8)
    p.got_have(0)
    p.got_have(2)
    p.got_have(4)
    p.got_have(6)
    p.lost_have(2)
    p.lost_have(6)
    v = _pull(p)
    assert v == [0, 4] or v == [4, 0]

def test_change_interest2():
    p = PiecePicker(9)
    p.complete(8)
    p.got_have(0)
    p.got_have(2)
    p.got_have(4)
    p.got_have(6)
    p.lost_have(2)
    p.lost_have(6)
    v = _pull(p)
    assert v == [0, 4] or v == [4, 0]

def test_complete():
    p = PiecePicker(1)
    p.got_have(0)
    p.complete(0)
    assert _pull(p) == []
    p.got_have(0)
    p.lost_have(0)

def test_rarest_first_takes_priority():
    p = PiecePicker(3)
    p.complete(2)
    p.requested(0)
    p.got_have(1)
    p.got_have(0)
    p.got_have(0)
    assert _pull(p) == [1, 0]

def test_rarer_in_started_takes_priority():
    p = PiecePicker(3)
    p.complete(2)
    p.requested(0)
    p.requested(1)
    p.got_have(1)
    p.got_have(0)
    p.got_have(0)
    assert _pull(p) == [1, 0]

def test_zero():
    assert _pull(PiecePicker(0)) == []

def test_have_list():
    p = PiecePicker(5)
    p.requested(3)
    x = _pull(p, [1, 2])
    assert x[0] == 3
    assert x[1:] == [1, 2] or x[1:] == [2, 1]
    p.complete(4)
    x = _pull(p, [1, 2])
    assert x[0] == 3
    assert x[1:] == [1, 2] or x[1:] == [2, 1]

def _pull(pp, have_list = None):
    r = []
    def want(p, r = r):
        return p not in r
    while true:
        n = pp.next(want, have_list)
        if n is None:
            break
        r.append(n)
    return r
