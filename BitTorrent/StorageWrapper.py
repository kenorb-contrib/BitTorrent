# Written by Bram Cohen
# see LICENSE.txt for license information

from sha import sha
from threading import Event
true = 1
false = 0

def dummy_status(fractionDone = None, activity = None):
    pass

def dummy_data_flunked(size):
    pass

class StorageWrapper:
    def __init__(self, storage, request_size, hashes, 
            piece_size, finished, failed, 
            statusfunc = dummy_status, flag = Event(), check_hashes = true,
            data_flunked = dummy_data_flunked, schedulefunc = None):
        self.check_hashes = check_hashes
        self.storage = storage
        self.request_size = request_size
        self.hashes = hashes
        self.piece_size = piece_size
        self.data_flunked = data_flunked
        self.total_length = storage.get_total_length()
        self.amount_left = self.total_length
        if self.total_length <= piece_size * (len(hashes) - 1):
            raise ValueError, 'bad data from tracker - total too small'
        if self.total_length > piece_size * len(hashes):
            raise ValueError, 'bad data from tracker - total too big'
        self.finished = finished
        self.failed = failed
        self.numactive = [0] * len(hashes)
        self.inactive_requests = [[] for i in xrange(len(hashes))]
        self.total_inactive = 0
        self.have = [false] * len(hashes)
        self.waschecked = [check_hashes] * len(hashes)
        self.schedulefunc = schedulefunc
        self.doneflag = flag
        if len(hashes) == 0:
            finished()
            return
        self.done_checking = false
        if storage.was_preexisting():
            statusfunc({"activity" : 'checking existing file', 
                "fractionDone" : 0})
            self.places = {}
            for i in xrange(len(hashes)):
                self.places[i] = i
            self.alloclimit = len(hashes)
            for i in xrange(len(hashes)):
                self._check_single(i)
                if flag.isSet():
                    return
                statusfunc({"fractionDone" : float(i+1)/len(hashes)})
        else:
            for i in xrange(len(hashes)):
                self._make_inactive(i)
            self.alloclimit = 0
            self.places = {}
            self.schedulefunc(self._background_allocate, 0)

    def _background_allocate(self):
        if self.alloclimit < len(self.hashes):
            self._bg()
            self.places[self.alloclimit - 1] = self.alloclimit - 1
            self.schedulefunc(self._background_allocate, 0)

    def _bg(self):
        l = min(self.piece_size, self.total_length - self.piece_size * self.alloclimit)
        if self.places.has_key(self.alloclimit):
            old = self.storage.read(self.piece_size * self.places[self.alloclimit], l)
            self.storage.write(self.piece_size * self.alloclimit, old)
            self.places[self.alloclimit] = self.alloclimit
        else:
            self.storage.write(self.piece_size * self.alloclimit, chr(0xFF) * l)
        self.alloclimit += 1

    def get_amount_left(self):
        return self.amount_left

    def do_I_have_anything(self):
        return self.amount_left < self.total_length

    def _check_single(self, index):
        low = self.piece_size * self.places[index]
        length = min(self.piece_size, self.total_length - low)
        self.waschecked[index] = true
        if not self.check_hashes or sha(self.storage.read(low, length)).digest() == self.hashes[index]:
            self.have[index] = true
            self.amount_left -= length
            if self.amount_left == 0:
                self.finished()
            return
        else:
            if self.done_checking:
                self.data_flunked(length)
        self._make_inactive(index)

    def _make_inactive(self, index):
        length = min(self.piece_size, self.total_length - self.piece_size * index)
        l = self.inactive_requests[index]
        x = 0
        while x + self.request_size < length:
            l.append((x, self.request_size))
            self.total_inactive += 1
            x += self.request_size
        l.append((x, length - x))
        self.total_inactive += 1

    def is_everything_pending(self):
        return self.total_inactive == 0

    def get_have_list(self):
        return self.have

    def do_I_have(self, index):
        return self.have[index]

    def do_I_have_requests(self, index):
        return self.inactive_requests[index] != []

    def new_request(self, index):
        # returns (begin, length)
        self.numactive[index] += 1
        self.total_inactive -= 1
        rs = self.inactive_requests[index]
        r = min(rs)
        rs.remove(r)
        return r

    def piece_came_in(self, index, begin, piece):
        try:
            self._piece_came_in(index, begin, piece)
        except IOError, e:
            self.failed('IO Error ' + str(e))

    def _piece_came_in(self, index, begin, piece):
        if not self.places.has_key(index):
            if index < self.alloclimit:
                for (key, value) in self.places.items():
                    if value == index:
                        l = min(self.piece_size, self.total_length - self.piece_size * self.alloclimit)
                        old = self.storage.read(self.piece_size * index, l)
                        self.storage.write(self.piece_size * self.alloclimit, old)
                        self.places[key] = self.alloclimit
                        self.alloclimit += 1
                        break
                self.places[index] = index
            else:
                while self.places.has_key(self.alloclimit):
                    self._bg()
                if not self.places.has_key(index):
                    self._bg()
                    self.places[index] = self.alloclimit - 1
        self.storage.write(self.places[index] * self.piece_size + begin, piece)
        self.numactive[index] -= 1
        if (self.inactive_requests[index] == [] and 
                self.numactive[index] == 0):
            self._check_single(index)

    def request_lost(self, index, begin, length):
        self.inactive_requests[index].append((begin, length))
        self.numactive[index] -= 1
        self.total_inactive += 1

    def get_piece(self, index, begin, length):
        try:
            return self._get_piece(index, begin, length)
        except IOError, e:
            self.failed('IO Error ' + str(e))
            return None

    def _get_piece(self, index, begin, length):
        if not self.waschecked[index]:
            low = self.piece_size * index
            high = min(low + self.piece_size, self.total_length)
            if sha(self.storage.read(low, high - low)).digest() != self.hashes[index]:
                self.failed('told file complete on start-up, but piece failed hash check')
                return None
            self.waschecked[index] = true
        if not self.have[index]:
            return None
        index = self.places[index]
        low = self.piece_size * index + begin
        if low + length > min(self.total_length, 
                self.piece_size * (index + 1)):
            return None
        return self.storage.read(low, length)

class DummyStorage:
    def __init__(self, total, pre = false):
        self.pre = pre
        self.s = chr(0xFF) * total
        self.done = false

    def was_preexisting(self):
        return self.pre

    def get_total_length(self):
        return len(self.s)

    def read(self, begin, length):
        return self.s[begin:begin + length]

    def write(self, begin, piece):
        self.s = self.s[:begin] + piece + self.s[begin + len(piece):]

    def finished(self):
        self.done = true

def dummy_sched(func, pause):
    func()

def test_basic():
    ds = DummyStorage(3)
    sw = StorageWrapper(ds, 2, [sha('abc').digest()], 4, ds.finished, None, schedulefunc = dummy_sched)
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
        sha('d').digest()], 3, ds.finished, None, schedulefunc = dummy_sched)
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
    sw = StorageWrapper(ds, 4, [sha('abcd').digest()], 4, ds.finished, None, schedulefunc = dummy_sched)
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

def test_lazy_hashing():
    ds = DummyStorage(4)
    flag = Event()
    sw = StorageWrapper(ds, 4, [sha('abcd').digest()], 4, ds.finished, lambda x, flag = flag: flag.set(), check_hashes = false, schedulefunc = dummy_sched)
    assert sw.get_piece(0, 0, 2) is None
    assert flag.isSet()

def test_lazy_hashing_pass():
    ds = DummyStorage(4)
    flag = Event()
    sw = StorageWrapper(ds, 4, [sha(chr(0xFF) * 4).digest()], 4, ds.finished, lambda x, flag = flag: flag.set(), check_hashes = false, schedulefunc = dummy_sched)
    assert sw.get_piece(0, 0, 2) is None
    assert not flag.isSet()

def test_preexisting():
    ds = DummyStorage(4, true)
    sw = StorageWrapper(ds, 2, [sha(chr(0xFF) * 2).digest(), 
        sha('ab').digest()], 2, ds.finished, None, schedulefunc = dummy_sched)
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
        StorageWrapper(ds, 4, [sha(chr(0xff) * 4).digest(),
            sha(chr(0xFF) * 4).digest()], 4, ds.finished, None, schedulefunc = dummy_sched)
        raise 'fail'
    except ValueError:
        pass

def test_total_too_big():
    ds = DummyStorage(9)
    try:
        sw = StorageWrapper(ds, 4, [sha('qqqq').digest(),
            sha(chr(0xFF) * 4).digest()], 4, ds.finished, None, schedulefunc = dummy_sched)
        raise 'fail'
    except ValueError:
        pass

def test_end_above_total_length():
    ds = DummyStorage(3, true)
    sw = StorageWrapper(ds, 4, [sha('qqq').digest()], 4, ds.finished, None, schedulefunc = dummy_sched)
    assert sw.get_piece(0, 0, 4) == None

def test_end_past_piece_end():
    ds = DummyStorage(4, true)
    sw = StorageWrapper(ds, 4, [sha(chr(0xFF) * 2).digest(), 
        sha(chr(0xFF) * 2).digest()], 2, ds.finished, None, schedulefunc = dummy_sched)
    assert ds.done
    assert sw.get_piece(0, 0, 3) == None

def dummy_sched2(func, pause):
    pass

def test_alloc_over_taken():
    ds = DummyStorage(4)
    sw = StorageWrapper(ds, 1, [sha('qr').digest(), sha('st').digest()], 2, ds.finished, None, schedulefunc = dummy_sched2)
    assert sw.new_request(0) == (0, 1)
    assert sw.new_request(0) == (1, 1)
    assert not sw.do_I_have_requests(0)
    assert sw.new_request(1) == (0, 1)
    assert sw.new_request(1) == (1, 1)
    assert not sw.do_I_have_requests(1)
    sw.piece_came_in(1, 0, 's')
    assert ds.s[0] == 's'
    sw.piece_came_in(0, 0, 'q')
    assert ds.s[0] == 'q'
    assert ds.s[2] == 's'
    sw.piece_came_in(1, 1, 't')
    assert sw.get_piece(1, 0, 2) == 'st'
    sw.piece_came_in(0, 1, 'r')
    assert sw.get_piece(1, 0, 2) == 'st'
    assert sw.get_piece(0, 0, 2) == 'qr'
    assert ds.s == 'qrst'

def test_alloc2():
    ds = DummyStorage(6)
    sw = StorageWrapper(ds, 1, [sha('qr').digest(), sha('').digest(), sha('st').digest()], 2, ds.finished, None, schedulefunc = dummy_sched2)
    assert sw.new_request(0) == (0, 1)
    assert sw.new_request(0) == (1, 1)
    assert not sw.do_I_have_requests(0)
    assert sw.new_request(2) == (0, 1)
    assert sw.new_request(2) == (1, 1)
    assert not sw.do_I_have_requests(2)
    sw.piece_came_in(2, 0, 's')
    assert ds.s[0] == 's'
    sw.piece_came_in(0, 0, 'q')
    assert ds.s[0] == 'q'
    assert ds.s[2] == 's'
    sw.piece_came_in(2, 1, 't')
    assert sw.get_piece(2, 0, 2) == 'st'
    sw.piece_came_in(0, 1, 'r')
    assert sw.get_piece(2, 0, 2) == 'st'
    assert sw.get_piece(0, 0, 2) == 'qr'
    assert ds.s[:4] == 'qrst'

def test_force_multiple():
    ds = DummyStorage(5)
    sw = StorageWrapper(ds, 1, [sha('a').digest(), sha('b').digest(), sha('c').digest(), sha('d').digest(), sha('e').digest()], 1,
        ds.finished, None, schedulefunc = dummy_sched2)
    assert sw.new_request(2) == (0, 1)
    assert sw.new_request(3) == (0, 1)
    assert sw.new_request(4) == (0, 1)
    sw.piece_came_in(2, 0, 'c')
    assert sw.get_piece(2, 0, 1) == 'c'
    assert ds.s[:1] == 'c'
    sw.piece_came_in(3, 0, 'd')
    assert sw.get_piece(2, 0, 1) == 'c'
    assert sw.get_piece(3, 0, 1) == 'd'
    assert ds.s[:2] == 'cd'
    sw.piece_came_in(4, 0, 'e')
    assert sw.get_piece(2, 0, 1) == 'c'
    assert sw.get_piece(3, 0, 1) == 'd'
    assert sw.get_piece(4, 0, 1) == 'e'
    assert ds.s[2:] == 'cde'

def test_force_multiple2():
    ds = DummyStorage(6)
    sw = StorageWrapper(ds, 1, [sha('a').digest(), sha('b').digest(), sha('c').digest(), sha('d').digest(), sha('e').digest(), sha('f').digest()], 1,
        ds.finished, None, schedulefunc = dummy_sched2)
    assert sw.new_request(2) == (0, 1)
    assert sw.new_request(3) == (0, 1)
    assert sw.new_request(5) == (0, 1)
    sw.piece_came_in(2, 0, 'c')
    assert sw.get_piece(2, 0, 1) == 'c'
    assert ds.s[:1] == 'c'
    sw.piece_came_in(3, 0, 'd')
    assert sw.get_piece(2, 0, 1) == 'c'
    assert sw.get_piece(3, 0, 1) == 'd'
    assert ds.s[:2] == 'cd'
    sw.piece_came_in(5, 0, 'f')
    assert sw.get_piece(2, 0, 1) == 'c'
    assert sw.get_piece(3, 0, 1) == 'd'
    assert sw.get_piece(5, 0, 1) == 'f'
    assert ds.s[2:5] == 'cdf'

