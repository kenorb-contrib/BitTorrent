# Written by Bram Cohen
# see LICENSE.txt for license information

from random import randrange
true = 1
false = 0

class SinglePicker:
    def __init__(self, picker):
        self.picker = picker
        self.num_interest = 1
        self.num_done = 0
        self.fixedpos = 0

    def next(self):
        if self.fixedpos < len(self.picker.fixed):
            self.fixedpos += 1
            return self.picker.fixed[self.fixedpos - 1]
        while true:
            if self.num_interest >= len(self.picker.interests):
                raise StopIteration
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

    # this is a total hack to support python2.1 but supports for ... in
    def __getitem__(self, key):
        if key == 0:
            self.picker = SinglePicker(self)
        try:
            return self.picker.next()
        except NameError:
            raise IndexError

    def got_have(self, i):
        if self.numinterests[i] is None:
            return
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

    def lost_have(self, i):
        if self.numinterests[i] is None:
            return
        interests = self.interests[self.numinterests[i]]
        pos = self.interestpos[i]
        interests[pos] = interests[-1]
        self.interestpos[interests[-1]] = pos
        del interests[-1]

        self.numinterests[i] -= 1
        interests = self.interests[self.numinterests[i]]
        self.interestpos[i] = len(interests)
        interests.append(i)

    def came_in(self, piece):
        if self.numinterests[piece] is not None:
            interests = self.interests[self.numinterests[piece]]
            interests[self.interestpos[piece]] = interests[-1]
            self.interestpos[interests[-1]] = self.interestpos[piece]
            del interests[-1]
            self.numinterests[piece] = None
            self.fixed.append(piece)

    def complete(self, piece):
        self.came_in(piece)
        self.fixed.remove(piece)

    def __iter__(self):
        return SinglePicker(self)

def test_came_in():
    p = PiecePicker(8)
    p.got_have(0)
    p.got_have(2)
    p.got_have(4)
    p.got_have(6)
    p.came_in(1)
    p.came_in(1)
    p.came_in(3)
    p.came_in(0)
    p.came_in(6)
    v = [i for i in p]
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
    v = [i for i in p]
    assert v == [0, 4] or v == [4, 0]

def test_complete():
    p = PiecePicker(1)
    p.got_have(0)
    p.complete(0)
    assert [i for i in p] == []
    p.got_have(0)
    p.lost_have(0)

def test_zero():
    assert [i for i in PiecePicker(0)] == []
