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

    def next(self, havefunc):
        if self.got_any:
            best = None
            bestnum = 2 ** 30
            for i in self.started:
                if havefunc(i) and self.numinterests[i] < bestnum:
                    best = i
                    bestnum = self.numinterests[i]
            for i in self.interests[1:bestnum]:
                r = []
                for j in i:
                    if havefunc(j):
                        r.append(j)
                if r:
                    return r[randrange(len(r))]
            return best
        else:
            for i in self.started:
                if havefunc(i):
                    return i
            x = []
            for i in self.interests[1:]:
                x.extend(i)
            r = []
            for j in x:
                if havefunc(j):
                    r.append(j)
            if r:
                return r[randrange(len(r))]
            return None

def test_requested():
    p = PiecePicker(8)
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
    p = PiecePicker(8)
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

def _pull(pp):
    r = []
    def want(p, r = r):
        return p not in r
    while true:
        n = pp.next(want)
        if n is None:
            break
        r.append(n)
    return r
