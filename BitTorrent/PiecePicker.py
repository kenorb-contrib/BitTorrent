# Written by Bram Cohen
# see LICENSE.txt for license information

from random import randrange
true = 1
false = 0

class SinglePicker:
    def __init__(self, picker):
        self.picker = picker
        self.num_interest = 0
        self.num_done = 0
        self.fixedpos = 0

    def next(self):
        if self.fixedpos < len(self.picker.fixed):
            self.fixedpos += 1
            return self.picker.fixed[self.fixedpos - 1]
        while true:
            if self.num_interest >= len(self.picker.interests):
                return None
            interests = self.picker.interests[self.num_interest]
            if len(interests) <= self.num_done:
                self.num_interest += 1
                self.num_done = 0
            else:
                break
        self.num_done += 1
        y = len(interests) - self.num_done
        x = randrange(y + 1)
        last = interests[x]
        interests[x] = interests[y]
        interests[y] = last
        self.picker.interestpos[interests[x]] = x
        self.picker.interestpos[interests[y]] = y
        return last

class PiecePicker:
    def __init__(self, numpieces):
        self.numpieces = numpieces
        self.interests = [range(numpieces)]
        self.numinterests = [0] * numpieces
        self.interestpos = range(numpieces)
        self.fixed = []

    def got_interest(self, i):
        interests = self.interests[self.numinterests[i]]
        pos = self.interestpos[i]
        interests[pos] = interests[-1]
        self.interestpos[interests[-1]] = pos
        del interests[-1]

        self.numinterests[i] += 1
        if len(self.interests) == self.numinterests[i]:
            self.interests.append([])
        interests = self.interests[self.numinterests[i]]
        self.interestpos[i] = len(interests)
        interests.append(i)

    def lost_interest(self, i):
        interests = self.interests[self.numinterests[i]]
        pos = self.interestpos[i]
        interests[pos] = interests[-1]
        self.interestpos[interests[-1]] = pos
        del interests[-1]

        self.numinterests[i] -= 1
        interests = self.interests[self.numinterests[i]]
        self.interestpos[i] = len(interests)
        interests.append(i)

    def used(self, piece):
        if self.numinterests[piece] is not None:
            interests = self.interests[self.numinterests[piece]]
            interests[self.interestpos[piece]] = interests[-1]
            self.interestpos[interests[-1]] = self.interestpos[piece]
            del interests[-1]
            self.numinterests[piece] = None
            self.fixed.append(piece)

    def complete(self, piece):
        self.used(piece)
        self.fixed.remove(piece)

    def get_picker(self):
        return SinglePicker(self)

def test_used():
    p = PiecePicker(8)
    p.got_interest(0)
    p.got_interest(2)
    p.got_interest(4)
    p.got_interest(6)
    p.used(1)
    p.used(1)
    p.used(3)
    p.used(0)
    p.used(6)
    s = p.get_picker()
    v = [s.next() for i in xrange(8)]
    assert s.next() is None
    assert v[0:4] == [1, 3, 0, 6]
    assert v[4:6] == [5, 7] or v[4:6] == [7, 5]
    assert v[6:8] == [2, 4] or v[6:8] == [4, 2]

def test_change_interest():
    p = PiecePicker(8)
    p.got_interest(0)
    p.got_interest(2)
    p.got_interest(4)
    p.got_interest(6)
    p.lost_interest(2)
    p.lost_interest(6)
    s = p.get_picker()
    v = [s.next() for i in xrange(8)]
    assert s.next() is None 
    assert v[6:] == [0, 4] or v[6:] == [4, 0]
    a = v[:6]
    a.sort()
    assert a == [1, 2, 3, 5, 6, 7]

def test_zero():
    p = PiecePicker(0)
    assert p.get_picker().next() is None
