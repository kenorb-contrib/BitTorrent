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
        self.storage = storage
        self.request_size = request_size
        self.hashes = hashes
        self.piece_length = piece_length
        self.total_length = storage.get_total_length()
        self.amount_left = self.total_length
        if self.total_length <= piece_length * (len(hashes) - 1):
            raise ValueError, 'bad data from tracker - total too small'
        if self.total_length > piece_length * len(hashes):
            raise ValueError, 'bad data from tracker - total too big'
        self.callback = callback
        self.numactive = [0] * len(hashes)
        self.inactive_requests = [[] for i in xrange(len(hashes))]
        self.have = [false] * len(hashes)
        if len(hashes) == 0:
            callback(true)
            return
        if storage.was_preexisting():
            statusfunc(activity = 'checking existing file', 
                fractionDone = 0)
            for i in xrange(len(hashes)):
                self._check_single(i)
                statusfunc(fractionDone = float(i)/len(hashes))
                if flag.isSet():
                    return
        else:
            for i in xrange(len(hashes)):
                self._check_single(i, false)

    def get_amount_left(self):
        return self.amount_left

    def do_I_have_anything(self):
        return self.amount_left < self.total_length

    def _check_single(self, index, check = true):
        low = self.piece_length * index
        high = low + self.piece_length
        if index == len(self.hashes) - 1:
            high = self.total_length
        length = high - low
        if check and sha(self.storage.read(low, length)).digest() == self.hashes[index]:
            self.have[index] = true
            self.amount_left -= length
            if self.amount_left == 0:
                self.callback(true)
        else:
            l = self.inactive_requests[index]
            x = 0
            while x + self.request_size < length:
                l.append((x, self.request_size))
                x += self.request_size
            l.append((x, length - x))

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
        if not self.have[index]:
            return None
        low = self.piece_length * index + begin
        if low + length > min(self.total_length, 
                self.piece_length * (index + 1)):
            return None
        return self.storage.read(low, length)

class DummyStorage:
    def __init__(self, total, pre = false):
        self.pre = pre
        self.s = 'q' * total
        self.done = false

    def was_preexisting(self):
        return self.pre

    def get_total_length(self):
        return len(self.s)

    def read(self, begin, length):
        return self.s[begin:begin + length]

    def write(self, begin, piece):
        self.s = self.s[:begin] + piece + self.s[begin + len(piece):]

    def callback(self, result):
        assert result
        self.done = true

def test_basic():
    ds = DummyStorage(3)
    sw = StorageWrapper(ds, 2, [sha('abc').digest()], 4, ds.callback)
    assert sw.get_amount_left() == 3
    assert not sw.do_I_have_anything()
    assert sw.get_have_list() == [false]
    assert sw.do_I_have_requests(0)
    x = []
    x.append(sw.new_request(0))
    assert sw.do_I_have_requests(0)
    x.append(sw.new_request(0))
    assert not sw.do_I_have_requests(0)
    x.sort()
    assert x == [(0, 2), (2, 1)]
    sw.request_lost(0, 2, 1)
    del x[-1]
    assert sw.do_I_have_requests(0)
    x.append(sw.new_request(0))
    assert x == [(0, 2), (2, 1)]
    assert not sw.do_I_have_requests(0)
    sw.piece_came_in(0, 0, 'ab')
    assert not sw.do_I_have_requests(0)
    assert sw.get_amount_left() == 3
    assert not sw.do_I_have_anything()
    assert sw.get_have_list() == [false]
    assert not ds.done
    sw.piece_came_in(0, 2, 'c')
    assert not sw.do_I_have_requests(0)
    assert sw.get_amount_left() == 0
    assert sw.do_I_have_anything()
    assert sw.get_have_list() == [true]
    assert sw.get_piece(0, 0, 3) == 'abc'
    assert sw.get_piece(0, 1, 2) == 'bc'
    assert sw.get_piece(0, 0, 2) == 'ab'
    assert sw.get_piece(0, 1, 1) == 'b'
    assert ds.done

def test_two_pieces():
    ds = DummyStorage(4)
    sw = StorageWrapper(ds, 3, [sha('abc').digest(),
        sha('d').digest()], 3, ds.callback)
    assert sw.get_amount_left() == 4
    assert not sw.do_I_have_anything()
    assert sw.get_have_list() == [false, false]
    assert sw.do_I_have_requests(0)
    assert sw.do_I_have_requests(1)

    assert sw.new_request(0) == (0, 3)
    assert sw.get_amount_left() == 4
    assert not sw.do_I_have_anything()
    assert sw.get_have_list() == [false, false]
    assert not sw.do_I_have_requests(0)
    assert sw.do_I_have_requests(1)

    assert sw.new_request(1) == (0, 1)
    assert sw.get_amount_left() == 4
    assert not sw.do_I_have_anything()
    assert sw.get_have_list() == [false, false]
    assert not sw.do_I_have_requests(0)
    assert not sw.do_I_have_requests(1)

    sw.piece_came_in(0, 0, 'abc')
    assert sw.get_amount_left() == 1
    assert sw.do_I_have_anything()
    assert sw.get_have_list() == [true, false]
    assert not sw.do_I_have_requests(0)
    assert not sw.do_I_have_requests(1)
    assert sw.get_piece(0, 0, 3) == 'abc'
    assert not ds.done

    sw.piece_came_in(1, 0, 'd')
    assert ds.done
    assert sw.get_amount_left() == 0
    assert sw.do_I_have_anything()
    assert sw.get_have_list() == [true, true]
    assert not sw.do_I_have_requests(0)
    assert not sw.do_I_have_requests(1)
    assert sw.get_piece(1, 0, 1) == 'd'

def test_hash_fail():
    ds = DummyStorage(4)
    sw = StorageWrapper(ds, 4, [sha('abcd').digest()], 4, ds.callback)
    assert sw.get_amount_left() == 4
    assert not sw.do_I_have_anything()
    assert sw.get_have_list() == [false]
    assert sw.do_I_have_requests(0)

    assert sw.new_request(0) == (0, 4)
    sw.piece_came_in(0, 0, 'abcx')
    assert sw.get_amount_left() == 4
    assert not sw.do_I_have_anything()
    assert sw.get_have_list() == [false]
    assert sw.do_I_have_requests(0)

    assert sw.new_request(0) == (0, 4)
    assert not ds.done
    sw.piece_came_in(0, 0, 'abcd')
    assert ds.done
    assert sw.get_amount_left() == 0
    assert sw.do_I_have_anything()
    assert sw.get_have_list() == [true]
    assert not sw.do_I_have_requests(0)

def test_preexisting():
    ds = DummyStorage(4, true)
    sw = StorageWrapper(ds, 2, [sha('qq').digest(), 
        sha('ab').digest()], 2, ds.callback)
    assert sw.get_amount_left() == 2
    assert sw.do_I_have_anything()
    assert sw.get_have_list() == [true, false]
    assert not sw.do_I_have_requests(0)
    assert sw.do_I_have_requests(1)
    assert sw.new_request(1) == (0, 2)
    assert not ds.done
    sw.piece_came_in(1, 0, 'ab')
    assert ds.done
    assert sw.get_amount_left() == 0
    assert sw.do_I_have_anything()
    assert sw.get_have_list() == [true, true]
    assert not sw.do_I_have_requests(0)
    assert not sw.do_I_have_requests(1)

def test_total_too_short():
    ds = DummyStorage(4)
    try:
        sw = StorageWrapper(ds, 4, [sha('qqqq').digest(),
            sha('qqqq').digest()], 4, ds.callback)
        raise 'fail'
    except ValueError:
        pass

def test_total_too_big():
    ds = DummyStorage(9)
    try:
        sw = StorageWrapper(ds, 4, [sha('qqqq').digest(),
            sha('qqqq').digest()], 4, ds.callback)
        raise 'fail'
    except ValueError:
        pass

def test_end_above_total_length():
    ds = DummyStorage(3, true)
    sw = StorageWrapper(ds, 4, [sha('qqq').digest()], 4, ds.callback)
    assert sw.get_piece(0, 0, 4) == None

def test_end_past_piece_end():
    ds = DummyStorage(4, true)
    sw = StorageWrapper(ds, 4, [sha('qq').digest(), 
        sha('qq').digest()], 2, ds.callback)
    assert ds.done
    assert sw.get_piece(0, 0, 3) == None
