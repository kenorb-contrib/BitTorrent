# Written by Bram Cohen
# see LICENSE.txt for license information

from random import randrange, shuffle
from bisect import insort
from BitTornado.clock import clock
try:
    True
except:
    True = 1
    False = 0

class PiecePicker:
    def __init__(self, numpieces,
                 rarest_first_cutoff = 1, rarest_first_priority_cutoff = 3):
        self.numpieces = numpieces
        self.rarest_first_cutoff = rarest_first_cutoff
        self.rarest_first_priority_cutoff = rarest_first_priority_cutoff
        self.totalcount = 0
        self.numhaves = [0] * numpieces
        self.priority = [1] * numpieces
        self.removed_partials = {}
        self.crosscount = [numpieces]
        self.crosscount2 = [numpieces]
        self.has = [0] * numpieces
        self.numgot = 0
        self.done = False
        self.priority = [1] * numpieces
        self.lookup = [[-1,0,randrange(10000),i] for i in xrange(numpieces)]
        # [a,b,c,d]: a = priority or -1 if numhaves < rarest_first_priority_cutoff
        #            b = numhaves
        #            c = random number, used to keep random order in sort
        #            d = piece #
        self.started = []
        self.started_lookup = {}
        # piece: [numhaves, random#, piece]
        self._init_interests()

    def _init_interests(self):
        self.interests = [l for l in self.lookup]
        self.re_sort()

    def re_sort(self):
        self.interests.sort()
        self.started.sort()


    def complete(self, piece):
        assert not self.has[piece]
        assert self.lookup[piece]
        self.interests.remove(self.lookup[piece])
        self.lookup[piece] = None
        self.has[piece] = 1
        self.numgot += 1
        if self.numgot == self.numpieces:
            self.done = True
        self._remove_from_interests(piece)


    def got_have(self, piece):
        i = self.lookup[piece]
        if not i:
            return
        i[1] += 1
        if i[1] == self.rarest_first_cutoff:
            i[0] = self.priority[piece]

    def lost_have(self, piece):
        i = self.lookup[piece]
        if not i:
            return
        i[1] -= 1
        if i[1] == self.rarest_first_cutoff-1:
            i[0] = -1


    def got_seed(self):
        for p in xrange(self.numpieces):
            self.got_have(p)

    def became_seed(self):
        pass

    def lost_seed(self):
        for p in xrange(self.numpieces):
            self.lost_have(p)


    def requested(self, piece):
        if not self.started_lookup.has_key(piece):
            self.started_lookup[piece] = [self.lookup[piece][1],randrange(10000),piece]
            insort(self.started, self.started_lookup[piece])

    def _remove_from_interests(self, piece, keep_partial = False):
        if self.started_lookup.has_key(piece):
            self.started.remove(self.started_lookup[piece])
            if keep_partial:
                self.removed_partials[piece] = 1
            del self.started_lookup[piece]


    def next(self, haves, wantfunc, complete_first = False):
        cutoff = self.numgot < self.rarest_first_cutoff
        complete_first = (complete_first or cutoff) and not haves.complete()
        best = None
        bestnum = 2 ** 30
        for l in self.started:
            i = l[2]
            if haves[i] and wantfunc(i):
                    best = i
                    bestnum = l[0]
                    break
        if best is not None:
            if complete_first or (cutoff and len(self.interests) > self.cutoff):
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
                for j in self.interests[i]:
                    if haves[j] and wantfunc(j):
                        return j
        if best is not None:
            return best
        return None


    def am_I_complete(self):
        return self.done
    
    def bump(self, piece):
        l = self.interests[self.level_in_interests[piece]]
        pos = self.pos_in_interests[piece]
        del l[pos]
        l.append(piece)
        for i in range(pos,len(l)):
            self.pos_in_interests[l[i]] = i
        try:
            self.started.remove(piece)
        except:
            pass

    def set_priority(self, piece, p):
        if self.superseed:
            return False    # don't muck with this if you're a superseed
        oldp = self.priority[piece]
        if oldp == p:
            return False
        self.priority[piece] = p
        if p == -1:
            # when setting priority -1,
            # make sure to cancel any downloads for this piece
            if not self.has[piece]:
                self._remove_from_interests(piece, True)
            return True
        if oldp == -1:
            level = self.numhaves[piece] + (self.priority_step * p)
            self.level_in_interests[piece] = level
            if self.has[piece]:
                return True
            while len(self.interests) < level+1:
                self.interests.append([])
            l2 = self.interests[level]
            parray = self.pos_in_interests
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
            if self.removed_partials.has_key(piece):
                del self.removed_partials[piece]
                self.started.append(piece)
            # now go to downloader and try requesting more
            return True
        numint = self.level_in_interests[piece]
        newint = numint + ((p - oldp) * self.priority_step)
        self.level_in_interests[piece] = newint
        if self.has[piece]:
            return False
        while len(self.interests) < newint+1:
            self.interests.append([])
        self._shift_over(piece, self.interests[numint], self.interests[newint])
        return False

    def is_blocked(self, piece):
        return self.priority[piece] < 0


    def set_superseed(self):
        assert self.done
        self.superseed = True
        self.seed_got_haves = [0] * self.numpieces
        self._init_interests()  # assume everyone is disconnected

    def next_have(self, connection, looser_upload):
        if self.seed_time is None:
            self.seed_time = clock()
            return None
        if clock() < self.seed_time+10:  # wait 10 seconds after seeing the first peers
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
                    seedint = self.level_in_interests[piece]
                    self.level_in_interests[piece] += 1  # tweak it up one, so you don't duplicate effort
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
