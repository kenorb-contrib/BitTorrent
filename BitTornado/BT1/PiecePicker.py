# Written by Bram Cohen
# see LICENSE.txt for license information

from random import randrange, shuffle
from time import time
try:
    True
except:
    True = 1
    False = 0

class PiecePicker:
    def __init__(self, numpieces, rarest_first_cutoff = 1, rarest_first_priority_cutoff = 3):
        self.rarest_first_cutoff = rarest_first_cutoff
        self.rarest_first_priority_cutoff = rarest_first_priority_cutoff
        self.cutoff = rarest_first_priority_cutoff
        self.numpieces = numpieces
        self.started = []
        self.totalcount = 0
        self.numhaves = [0] * numpieces
        self.crosscount = [numpieces]
        self.crosscount2 = [numpieces]
        self.has = [0] * numpieces
        self.numgot = 0
        self.done = False
        self.seed_connections = {}
        self.seed_time = None
        self.superseed = False
        self.seeds_connected = 0
        self._init_interests()

    def _init_interests(self):
        self.interests = [range(self.numpieces)]
        shuffle(self.interests[0])
        self.pos_in_interests = [0] * self.numpieces
        for i in xrange(self.numpieces):
            self.pos_in_interests[self.interests[0][i]] = i


    def got_have(self, piece):
        self.totalcount+=1
        numint = self.numhaves[piece]
        self.numhaves[piece] += 1
        self.crosscount[numint] -= 1
        if numint+1==len(self.crosscount):
            self.crosscount.append(0)
        self.crosscount[numint+1] += 1
        if not self.done:
            numintplus = numint+self.has[piece]
            self.crosscount2[numintplus] -= 1
            if numintplus+1 == len(self.crosscount2):
                self.crosscount2.append(0)
            self.crosscount2[numintplus+1] += 1
        if self.superseed:
            numint = self.seed_numhaves[piece]
            self.seed_numhaves[piece] += 1
            self.seed_got_haves[piece] += 1
        elif self.has[piece]:
            return
        if numint == len(self.interests) - 1:
            self.interests.append([])
        self._shift_over(piece, self.interests[numint], self.interests[numint + 1])

    def lost_have(self, piece):
        self.totalcount-=1
        numint = self.numhaves[piece]
        self.numhaves[piece] -= 1
        self.crosscount[numint] -= 1
        self.crosscount[numint-1] += 1
        if not self.done:
            numintplus = numint+self.has[piece]
            self.crosscount2[numintplus] -= 1
            self.crosscount2[numintplus-1] += 1
        if self.superseed:
            numint = self.seed_numhaves[piece]
            self.seed_numhaves[piece] -= 1
        elif self.has[piece]:
            return
        self._shift_over(piece, self.interests[numint], self.interests[numint - 1])

    def _shift_over(self, piece, l1, l2):
        parray = self.pos_in_interests
        p = parray[piece]
        q = l1[-1]
        l1[p] = q
        parray[q] = p
        del l1[-1]
        newp = randrange(len(l2)+1)
        if newp == len(l2):
            parray[piece] = len(l2)
            l2.append(piece)
        else:
            old = l2[newp]
            parray[old] = len(l2)
            l2.append(old)
            l2[newp] = piece
            parray[piece] = newp


    def got_seed(self):
        self.seeds_connected += 1
        self.cutoff = max(self.rarest_first_priority_cutoff-self.seeds_connected,0)

    def became_seed(self):
        self.got_seed()
        self.totalcount -= self.numpieces
        self.numhaves = [i-1 for i in self.numhaves]
        if self.superseed:
            self.seed_numhaves = [i-1 for i in self.seed_numhaves]
        if self.superseed or not self.done:
            del self.interests[0]
        del self.crosscount[0]
        if not self.done:
            del self.crosscount2[0]

    def lost_seed(self):
        self.seeds_connected -= 1
        self.cutoff = max(self.rarest_first_priority_cutoff-self.seeds_connected,0)


    def requested(self, piece):
        if piece not in self.started:
            self.started.append(piece)

    def complete(self, piece):
        assert not self.has[piece]
        self.has[piece] = 1
        self.numgot += 1
        if self.numgot == self.numpieces:
            self.done = True
            self.crosscount2 = self.crosscount
        else:
            self.crosscount2[self.numhaves[piece]] -= 1
            if self.numhaves[piece]+1 == len(self.crosscount2):
                self.crosscount2.append(0)
            self.crosscount2[self.numhaves[piece]+1] += 1
        l = self.interests[self.numhaves[piece]]
        p = self.pos_in_interests[piece]
        q = l[-1]
        l[p] = q
        self.pos_in_interests[q] = p
        del l[-1]
        try:
            self.started.remove(piece)
        except ValueError:
            pass


    def next(self, haves, wantfunc, complete_first = False):
        cutoff = self.numgot < self.rarest_first_cutoff
        complete_first = (complete_first or cutoff) and not haves.complete()
        best = None
        bestnum = 2 ** 30
        for i in self.started:
            if haves[i] and wantfunc(i):
                if self.numhaves[i] < bestnum:
                    best = i
                    bestnum = self.numhaves[i]
        if best is not None and complete_first:
            return best
        if haves.complete():
            r = [ (0, min(bestnum,len(self.interests))) ]
        elif cutoff and len(self.interests) > self.cutoff:
            r = [ (self.cutoff, min(bestnum,len(self.interests))),
                      (0, self.cutoff) ]
        else:
            r = [ (0, min(bestnum,len(self.interests))) ]
        for lo,hi in r:
            for i in xrange(lo,hi):
                if best is not None and i >= self.cutoff:
                    return best
                for j in self.interests[i]:
                    if haves[j] and wantfunc(j):
                        return j
        if best is not None:
            return best
        return None


    def am_I_complete(self):
        return self.done
    
    def bump(self, piece):
        l = self.interests[self.numhaves[piece]]
        pos = self.pos_in_interests[piece]
        del l[pos]
        l.append(piece)
        for i in range(pos,len(l)):
            self.pos_in_interests[l[i]] = i
        try:
            self.started.remove(piece)
        except:
            pass


    def set_superseed(self):
        assert self.done
        self.superseed = True
        self.seed_numhaves = [i for i in self.numhaves]
        self.seed_got_haves = [0] * self.numpieces
        self._init_interests()  # assume everyone is disconnected

    def next_have(self, connection, looser_upload):
        if self.seed_time is None:
            self.seed_time = time()
        if time() < self.seed_time+10:  # wait 10 seconds after seeing the first peers
            return None                 # to give time to grab have lists
        if not connection.upload.super_seeding:
            return None
        if connection in self.seed_connections:
            if looser_upload:
                num = 1     # send a new have even if it hasn't spread that piece elsewhere
            else:
                num = 2
            if self.seed_got_haves[self.seed_connections[connection]] < num:
                return None
            if not connection.upload.was_ever_interested:   # it never downloaded it?
                connection.upload.skipped_count += 1
                if connection.upload.skipped_count >= 3:    # probably another stealthed seed
                    return -1                               # signal to close it
        for tier in self.interests:
            for piece in tier:
                if not connection.download.have[piece]:
                    seedint = self.seed_numhaves[piece]
                    self.seed_numhaves[piece] += 1  # tweak it up one, so you don't duplicate effort
                    if seedint == len(self.interests) - 1:
                        self.interests.append([])
                    self._shift_over(piece,
                                self.interests[seedint], self.interests[seedint + 1])
                    self.seed_got_haves[piece] = 0       # reset this
                    self.seed_connections[connection] = piece
                    connection.upload.seed_have_list.append(piece)
                    return piece
        return -1       # something screwy; terminate connection

    def lost_peer(self, connection):
        try:
            del self.seed_connections[connection]
        except:
            pass




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
    assert v[:2] == [1, 3] or v[:2] == [3, 1]
    assert v[2:4] == [0, 6] or v[2:4] == [6, 0]
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

def _pull(pp):
    r = []
    def want(p, r = r):
        return p not in r
    while True:
        n = pp.next(want)
        if n is None:
            break
        r.append(n)
    return r
