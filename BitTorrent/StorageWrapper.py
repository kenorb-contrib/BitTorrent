# Written by Bram Cohen
# see LICENSE.txt for license information

from sha import sha
from threading import Event
true = 1
false = 0

def dummy_status(fractionDone = None, activity = None):
    pass

class StorageWrapper:
    def __init__(self, storage, request_size, hashes, 
            piece_length, callback, 
            statusfunc = dummy_status, flag = Event()):
        # sanity checking for everything but get_piece is assumed to have been done externally
        total_length = storage.get_total_length()
        self.storage = storage
        self.request_size = request_size
        self.hashes = hashes
        self.piece_length = piece_length
        self.total_length = total_length
        self.amount_left = total_length
        self.callback = callback
        self.numactive = [0] * len(hashes)
        self.inactive_requests = [[] for i in xrange(len(hashes))]
        self.have = [false] * len(hashes)
        if len(hashes) == 0:
            callback(true)
        elif storage.was_preexisting:
            statusfunc(activity = 'checking existing file', 
                fractionDone = 0)
            for i in xrange(len(hashes)):
                self._check_single(i)
                statusfunc(fractionDone = float(i)/len(hashes))
                if flag.isSet():
                    return

    def get_amount_left(self):
        return self.amount_left

    def do_I_have_anything(self):
        return self.amount_left < self.total_length

    def _check_single(self, index):
        low = self.piece_length * index
        high = low + self.piece_length
        if index == len(self.hashes) - 1:
            high = self.total_length
        length = high - low
        if sha(self.storage.read(low, length)).digest() == self.hashes[index]:
            self.have[i] = true
            self.amount_left -= length
            if self.amount_left == 0:
                self.callback(true)
        else:
            l = self.inactive_requests[index]
            x = 0
            while x + self.request_size < length:
                l.append((x, x + self.request_size))
                x += self.request_size
            l.append((x, length))

    def get_have_list(self):
        return self.have

    def do_I_have(self, index):
        return self.have[index]

    def do_I_have_requests(self, index):
        return self.inactive_requests[index] != []

    def new_request(self, index):
        # returns (begin, length)
        self.numactive[index] += 1
        return self.inactive_requests[index].pop()

    def piece_came_in(self, index, begin, piece):
        try:
            self._piece_came_in(index, begin, piece)
        except IOError, e:
            self.callback(false, 'IO Error ' + str(e), true)

    def _piece_came_in(self, index, begin, piece):
        self.storage.write(index * self.piece_length + begin, piece)
        self.numactive[index] -= 1
        if (self.inactive_requests[index] == [] and 
                self.numactive[index] == 0):
            self._check_single(index)

    def request_lost(self, index, begin, length):
        self.inactive_requests[index].append((begin, length))
        self.numactive[index] -= 1

    def get_piece(self, index, begin, length):
        try:
            return self._get_piece(index, begin, length)
        except IOError, e:
            self.callback(false, 'IO Error ' + str(e), true)
            return None

    def _get_piece(self, index, begin, length):
        if index >= len(self.have) or not self.have[index]:
            return None
        low = self.piece_length * index
        high = low + self.piece_length
        if index == len(self.hashes) - 1:
            high = self.total_length
        if length > high - low:
            return None
        return self.storage.read(low, length)



