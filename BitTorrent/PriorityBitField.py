# Written by Bram Cohen
# see LICENSE.txt for license information

bignum = 2 ** 30

class PriorityBitField:
    def __init__(self, size):
        self.size = size
        p = 1
        while p < self.size:
            p *= 2
        self.p = p
        self.vals = [bignum] * (p * 2)

    def is_empty(self):
        return self.vals[1] == bignum

    def get_first(self):
        return self.vals[1]

    def insert_strict(self, index):
        assert self.vals[index + self.p] > index
        self.insert(index)

    def insert(self, index):
        i = index + self.p
        while i > 0 and self.vals[i] > index:
            self.vals[i] = index
            i = int(i / 2)

    def remove_strict(self, index):
        assert self.vals[index + self.p] == index
        self.remove(index)

    def remove(self, index):
        i = index + self.p
        self.vals[i] = bignum
        while i > 1:
            n = int(i / 2)
            m = min(self.vals[n * 2], self.vals[n * 2 + 1])
            if self.vals[n] == m:
                return
            self.vals[n] = m
            i = n

    def contains(self, index):
        return self.vals[index + self.p] != bignum

def test_length_one():
    p = PriorityBitField(1)
    assert p.is_empty()
    assert not p.contains(0)
    p.insert(0)
    assert not p.is_empty()
    assert p.get_first() == 0
    assert p.contains(0)
    p.remove(0)
    assert p.is_empty()
    assert not p.contains(0)
    
def test_20_02():
    p = PriorityBitField(3)
    assert p.is_empty()
    p.insert(2)
    assert not p.is_empty()
    assert p.contains(2)
    assert p.get_first() == 2
    p.insert(0)
    assert not p.is_empty()
    assert p.contains(2)
    assert p.contains(0)
    assert p.get_first() == 0
    p.remove(0)
    assert not p.is_empty()
    assert p.contains(2)
    assert not p.contains(0)
    assert p.get_first() == 2
    p.remove(2)
    assert p.is_empty()
    assert not p.contains(2)
    assert not p.contains(0)

def test_20_20():
    p = PriorityBitField(3)
    assert p.is_empty()
    p.insert(2)
    assert not p.is_empty()
    assert p.contains(2)
    assert p.get_first() == 2
    p.insert(0)
    assert not p.is_empty()
    assert p.contains(2)
    assert p.contains(0)
    assert p.get_first() == 0
    p.remove(2)
    assert not p.is_empty()
    assert not p.contains(2)
    assert p.contains(0)
    assert p.get_first() == 0
    p.remove(0)
    assert p.is_empty()
    assert not p.contains(2)
    assert not p.contains(0)

def test_02_02():
    p = PriorityBitField(3)
    assert p.is_empty()
    p.insert(0)
    assert not p.is_empty()
    assert p.contains(0)
    assert p.get_first() == 0
    p.insert(2)
    assert not p.is_empty()
    assert p.contains(2)
    assert p.contains(0)
    assert p.get_first() == 0
    p.remove(0)
    assert not p.is_empty()
    assert p.contains(2)
    assert not p.contains(0)
    assert p.get_first() == 2
    p.remove(2)
    assert p.is_empty()
    assert not p.contains(2)
    assert not p.contains(0)

def test_02_20():
    p = PriorityBitField(3)
    assert p.is_empty()
    p.insert(0)
    assert not p.is_empty()
    assert p.contains(0)
    assert p.get_first() == 0
    p.insert(2)
    assert not p.is_empty()
    assert p.contains(2)
    assert p.contains(0)
    assert p.get_first() == 0
    p.remove(2)
    assert not p.is_empty()
    assert not p.contains(2)
    assert p.contains(0)
    assert p.get_first() == 0
    p.remove(0)
    assert p.is_empty()
    assert not p.contains(2)
    assert not p.contains(0)

def test_triple():
    p = PriorityBitField(3)
    p.insert(0)
    p.insert(1)
    p.insert(2)
    p.remove(0)
    assert p.get_first() == 1
    p.remove(1)
    assert p.get_first() == 2
    p.remove(2)
    assert p.is_empty()
