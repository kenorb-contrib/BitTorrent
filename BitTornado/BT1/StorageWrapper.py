# Written by Bram Cohen
# see LICENSE.txt for license information

from BitTornado.bitfield import Bitfield
from sha import sha
from threading import Event
try:
    True
except:
    True = 1
    False = 0

def dummy_status(fractionDone = None, activity = None):
    pass

class StorageWrapper:
    def __init__(self, storage, request_size, hashes, 
            piece_size, finished, failed, 
            statusfunc = dummy_status, flag = Event(), check_hashes = True,
            data_flunked = lambda x: None, backfunc = None,
            config = {}, unpauseflag = None):
        self.storage = storage
        self.request_size = request_size
        self.hashes = hashes
        self.piece_size = piece_size
        self.piece_length = piece_size
        self.finished = finished
        self.failed = failed
        self.statusfunc = statusfunc
        self.flag = flag
        self.check_hashes = check_hashes
        self.data_flunked = data_flunked
        self.backfunc = backfunc
        self.config = config
        self.unpauseflag = unpauseflag
        
        self.alloc_type = config.get('alloc_type','normal')
        self.double_check = config.get('double_check', 0)
        self.triple_check = config.get('triple_check', 0)
        if self.triple_check:
            self.double_check = True
        self.bgalloc_enabled = False
        self.bgalloc_active = False
        self.total_length = storage.get_total_length()
        self.amount_left = self.total_length
        if self.total_length <= piece_size * (len(hashes) - 1):
            raise ValueError, 'bad data in responsefile - total too small'
        if self.total_length > piece_size * len(hashes):
            raise ValueError, 'bad data in responsefile - total too big'
        self.numactive = [0] * len(hashes)
        self.inactive_requests = [1] * len(hashes)
        self.amount_inactive = self.total_length
        self.have = Bitfield(len(hashes))
        self.waschecked = [check_hashes] * len(hashes)
        self.places = {}
        self.holes = []
        self.stat_active = {}
        self.stat_new = {}
        self.dirty = {}
        self.stat_numflunked = 0
        self.stat_numdownloaded = 0
        self.stat_numfound = 0
        self.download_history = {}
        self.failed_pieces = {}
        self.out_of_place = 0
        self.write_buf_max = config['write_buffer_size']*1048576L
        self.write_buf_size = 0L
        self.write_buf = {}   # structure:  piece: [(start, data), ...]
        self.write_buf_list = []


    def old_style_init(self):
        if self.init_hashcheck():
            self.statusfunc(activity = 'checking existing data', fractionDone = 0)
            x = 0
            updatenum = int(self.check_total/300)+1
            updatecount = 0
            while x is not None:
                self.unpauseflag.wait()
                if self.flag.isSet():
                    return
                x = self.hashcheckfunc()
                updatecount += 1
                if x is not None:
                    if updatecount >= updatenum:
                        updatecount = 0
                        self.statusfunc(fractionDone = x)
            self.statusfunc(fractionDone = 1.0)

        if self.init_movedata():
            self.statusfunc(activity = 'moving data', fractionDone = 1.0)
            x = 0
            updatenum = int(self.out_of_place/300)+1
            updatecount = 0
            while x is not None:
                self.unpauseflag.wait()
                if self.flag.isSet():
                    return
                x = self.movedatafunc()
                updatecount += 1
                if x is not None:
                    if updatecount >= updatenum:
                        updatecount = 0
                        self.statusfunc(fractionDone = x)
            self.statusfunc(fractionDone = 0)

        if self.init_alloc():
            self.statusfunc(activity = 'allocating disk space', fractionDone = 1.0)
            x = 0
            updatenum = int(self.out_of_place/300)+1
            updatecount = 0
            while x is not None:
                self.unpauseflag.wait()
                x = self.allocfunc()
                if self.flag.isSet():
                    return
                updatecount += 1
                if x is not None:
                    if updatecount >= updatenum:
                        updatecount = 0
                        self.statusfunc(fractionDone = x)
            self.statusfunc(fractionDone = 0)


    def initialize(self, donefunc, statusfunc = None):
        self.initialize_done = donefunc
        if statusfunc is None:
            statusfunc = self.statusfunc
        self.initialize_status = statusfunc
        self.initialize_tasks = [
            ['checking existing data', 0, self.init_hashcheck, self.hashcheckfunc],
            ['moving data', 1, self.init_movedata, self.movedatafunc],
            ['allocating disk space', 1, self.init_alloc, self.allocfunc] ]
        self.initialize_next = None
            
        self.backfunc(self._initialize)

    def _initialize(self):
        if self.initialize_next:
            x = self.initialize_next()
            if x is None:
                self.initialize_next = None
            else:
                self.initialize_status(fractionDone = x)
        else:
            if not self.initialize_tasks:
                self.initialize_done()
                return
            msg, done, init, next = self.initialize_tasks.pop(0)
            if init():
                self.initialize_status(activity = msg, fractionDone = done)
                self.initialize_next = next

        self.backfunc(self._initialize)


    def init_hashcheck(self):        
        if self.flag.isSet():
            return False
        self.check_list = []
        if len(self.hashes) == 0:
            self.finished()
            self.check_total = 0
            return False
        
        self.check_targets = {}
        for i in xrange(len(self.hashes)):
            if self._waspre(i):
                self.check_list.append(i)
            else:
                if not self.check_hashes:
                    self.failed('told file complete on start-up, but data is missing')
                    return False
                self.holes.append(i)
                if self.check_targets.has_key(self.hashes[i]):
                    self.check_targets[self.hashes[i]] = [] # in case of a hash collision, discard
                else:
                    self.check_targets[self.hashes[i]] = [i]
        self.check_total = len(self.check_list)
        self.check_numchecked = 0.0
        self.lastlen = self._piecelen(len(self.hashes) - 1)
        self.numchecked = 0.0
        return self.check_total > 0

    def _markgot(self, piece, pos):
        self.places[piece] = pos
        self.have[piece] = True
        self.amount_left -= self._piecelen(piece)
        self.amount_inactive -= self._piecelen(piece)
        self.inactive_requests[piece] = None
        self.waschecked[piece] = self.check_hashes
        self.stat_numfound += 1

    def hashcheckfunc(self):
        if self.flag.isSet():
            return None
        if not self.check_list:
            return None
        
        i = self.check_list.pop(0)
        if not self.check_hashes:
            self._markgot(i, i)
        else:
            try:
                sh = sha(self.storage.read(self.piece_size * i, self.lastlen))
                sp = sh.digest()
                sh.update(self.storage.read(self.piece_size * i + self.lastlen,
                                            self._piecelen(i) - self.lastlen))
            except IOError, e:
                self.failed('IO Error ' + str(e))
                return None
            s = sh.digest()
            if s == self.hashes[i]:
                self._markgot(i, i)
            elif ( self.check_targets.get(s)
                   and self._piecelen(i) == self._piecelen(self.check_targets[s][-1]) ):
                self._markgot(self.check_targets[s].pop(), i)
                self.out_of_place += 1
            elif ( not self.have[-1] and sp == self.hashes[-1]
                   and (i == len(self.hashes) - 1
                        or not self._waspre(len(self.hashes) - 1)) ):
                self._markgot(len(self.hashes) - 1, i)
                self.out_of_place += 1
            else:
                self.places[i] = i
        self.numchecked += 1
        if self.amount_left == 0:
            self.finished()
        return (self.numchecked / self.check_total)


    def init_movedata(self):
        if self.flag.isSet():
            return False
        if self.alloc_type != 'sparse':
            return False
        self.storage.top_off()  # sets file lengths to their final size
        self.movelist = []
        if self.out_of_place == 0:
            for i in self.holes:
                self.places[i] = i
            self.holes = []
            return False
        self.tomove = float(self.out_of_place)
        for i in xrange(len(self.hashes)):
            if not self.places.has_key(i):
                self.places[i] = i
            elif self.places[i] != i:
                self.movelist.append(i)
        self.holes = []
        return True

    def movedatafunc(self):    
        if self.flag.isSet():
            return None
        if not self.movelist:
            return None
        i = self.movelist.pop(0)
        try:
            old = self.storage.read(self.piece_size * self.places[i],
                                    self._piecelen(i))
            self.storage.write(self.piece_size * i, old)
            if self.double_check and self.have[i]:
                if self.triple_check:
                    old = self.storage.read(self.piece_size * i, self._piecelen(i),
                                            flush_first = True)
                if sha(old).digest() != self.hashes[i]:
                    self.failed('download corrupted; please restart and resume')
                    return None
        except IOError, e:
            self.failed('IO Error ' + str(e))
            return None

        self.places[i] = i
        self.tomove -= 1
        return (self.tomove / self.out_of_place)

        
    def init_alloc(self):
        if self.flag.isSet():
            return False
        if not self.holes:
            return False
        self.numholes = float(len(self.holes))
        self.alloc_buf = chr(0xFF) * self.piece_size
        if self.alloc_type == 'pre-allocate':
            return True
        if self.alloc_type == 'background':
            self.bgalloc()
        return False

    def allocfunc(self):
        if self.flag.isSet():
            return None
        if not self.holes:
            self.alloc_buf = None
            return None
        n = self.holes.pop(0)
        try:
            if self.places.has_key(n):
                oldpos = self.places[n]
                self.places[oldpos] = oldpos
                old = self.storage.read(self.piece_size * oldpos,
                                    self._piecelen(n))
                self.storage.write(self.piece_size * n, old)
                if self.double_check and self.have[n]:
                    if self.triple_check:
                        old = self.storage.read(self.piece_size * n,
                                    self._piecelen(n), flush_first = True)
                    if sha(old).digest() != self.hashes[n]:
                        self.failed('download corrupted; please restart and resume')
                        return None
            else:
                self.storage.write(self.piece_size * n,
                                   self.alloc_buf[:self._piecelen(n)])
            self.places[n] = n
        except IOError, e:
            self.failed('IO Error ' + str(e))
            return None

        return len(self.holes) / self.numholes

            
    def bgalloc(self):
        if self.holes and not self.bgalloc_enabled:
            self.bgalloc_enabled = True
            self.bgalloc_active = True
            if self.backfunc:
                self.backfunc(self._bgalloc,0.1)
                return True
        else:
            if self.backfunc:
                self.backfunc(self.storage.flush)
                # force a flush whenever the "finish allocation" button is hit
        return False

    def _bgalloc(self):
        if self.allocfunc() == None:
            if not self.flag.isSet():
                self.storage.flush()
            self.bgalloc_active = False
        else:
            self.backfunc(self._bgalloc,
                  float(self.piece_size)/(self.config.get('alloc_rate',1.0)*1048576))


    def _waspre(self, piece):
        return self.storage.was_preallocated(piece * self.piece_size, self._piecelen(piece))

    def _piecelen(self, piece):
        if piece < len(self.hashes) - 1:
            return self.piece_size
        else:
            return self.total_length - (piece * self.piece_size)

    def get_amount_left(self):
        return self.amount_left

    def do_I_have_anything(self):
        return self.amount_left < self.total_length

    def _make_inactive(self, index):
        length = min(self.piece_size, self.total_length - self.piece_size * index)
        l = []
        x = 0
        while x + self.request_size < length:
            l.append((x, self.request_size))
            x += self.request_size
        l.append((x, length - x))
        self.inactive_requests[index] = l

    def is_endgame(self):
        return not self.amount_inactive

    def reset_endgame(self, requestlist):
        for index, begin, length in requestlist:
            self.request_lost(index, begin, length)

    def get_have_list(self):
        return self.have.tostring()

    def do_I_have(self, index):
        return self.have[index]

    def do_I_have_requests(self, index):
        return not not self.inactive_requests[index]

    def is_unstarted(self, index):
        return ( not self.have[index] and not self.numactive[index]
                 and not self.dirty.has_key(index) )

    def get_hash(self, index):
        return self.hashes[index]

    def new_request(self, index):
        # returns (begin, length)
        if self.inactive_requests[index] == 1:
            self._make_inactive(index)
        self.numactive[index] += 1
        self.stat_active[index] = 1
        if not self.dirty.has_key(index):
            self.stat_new[index] = 1
        rs = self.inactive_requests[index]
        r = min(rs)
        rs.remove(r)
        self.amount_inactive -= r[1]
        return r


    def _write_to_buffer(self, piece, start, data):
        if not self.write_buf_max:
            self.storage.write((self.piece_length*self.places[piece])+start, data)
            return
        self.write_buf_size += len(data)
        while self.write_buf_size > self.write_buf_max:
            old = self.write_buf_list.pop(0)
            self._flush_buffer(old, True)
        if self.write_buf.has_key(piece):
            self.write_buf_list.remove(piece)
        else:
            self.write_buf[piece] = []
        self.write_buf_list.append(piece)
        self.write_buf[piece].append((start,data))

    def _flush_buffer(self, piece, popped = False):
        if not self.write_buf.has_key(piece):
            return
        if not popped:
            self.write_buf_list.remove(piece)
        l = self.write_buf[piece]
        del self.write_buf[piece]
        l.sort()
        for start, data in l:
            self.write_buf_size -= len(data)
            self.storage.write((self.piece_length*self.places[piece])+start, data)
        
    def piece_came_in(self, index, begin, piece, source = None):
        try:
            return self._piece_came_in(index, begin, piece, source)
        except IOError, e:
            self.failed('IO Error: ' + str(e))
            return True

    def _piece_came_in(self, index, begin, piece, source):
        if not self.places.has_key(index):
            n = self.holes.pop(0)
            if self.places.has_key(n):
                oldpos = self.places[n]
                old = self.storage.read(self.piece_size * oldpos, self._piecelen(n))
                self.storage.write(self.piece_size * n, old)
                if self.double_check and self.have[n]:
                    if self.triple_check:
                        old = self.storage.read(self.piece_size * n, self._piecelen(n), flush_first = True)
                    if sha(old).digest() != self.hashes[n]:
                        self.failed('download corrupted; please restart and resume')
                        return True
                self.places[n] = n
                if index == oldpos or index in self.holes:
                    self.places[index] = oldpos
                else:
                    for p, v in self.places.items():
                        if v == index:
                            break
                    self.places[index] = index
                    self.places[p] = oldpos
                    old = self.storage.read(self.piece_size * index, self.piece_size)
                    self.storage.write(self.piece_size * oldpos, old)
            elif index in self.holes or index == n:
                self.storage.write(self.piece_size * n, self.alloc_buf[:self._piecelen(n)])
                self.places[index] = n
            else:
                for p, v in self.places.items():
                    if v == index:
                        break
                else:
                    self.failed('download corrupted; please restart and resume')
                    return True
                self.places[index] = index
                self.places[p] = n
                old = self.storage.read(self.piece_size * index, self._piecelen(n))
                self.storage.write(self.piece_size * n, old)
                if self.triple_check and self.have[p]:
                    old = self.storage.read(self.piece_size * n, self._piecelen(n), flush_first = True)
                    if sha(old).digest() != self.hashes[p]:
                        self.failed('download corrupted; please restart and resume')
                        return True
            if not self.holes:
                self.alloc_buf = None

        if self.failed_pieces.has_key(index):
            old = self.storage.read(self.piece_size * self.places[index] +
                                    begin, len(piece))
            if old != piece:
                self.failed_pieces[index][self.download_history[index][begin]] = 1
        self.download_history.setdefault(index, {})
        self.download_history[index][begin] = source
        
        self._write_to_buffer(index, begin, piece)
        self.dirty[index] = 1
        self.numactive[index] -= 1
        assert self.numactive[index] >= 0
        if not self.numactive[index]:
            del self.stat_active[index]
        if self.stat_new.has_key(index):
            del self.stat_new[index]
        if not self.inactive_requests[index] and not self.numactive[index]:
            del self.dirty[index]
            self._flush_buffer(index)
            data = self.storage.read(self.piece_size * self.places[index], self._piecelen(index),
                                     flush_first = self.triple_check)
            if sha(data).digest() == self.hashes[index]:
                self.have[index] = True
                self.inactive_requests[index] = None
                self.waschecked[index] = True
                self.amount_left -= self._piecelen(index)
                self.stat_numdownloaded += 1

                for d in self.download_history[index].values():
                    if d is not None:
                        d.good(index)
                del self.download_history[index]
                if self.failed_pieces.has_key(index):
                    for d in self.failed_pieces[index].keys():
                        if d is not None:
                            d.failed(index)
                    del self.failed_pieces[index]

                if self.amount_left == 0:
                    self.finished()
            else:
                self.data_flunked(self._piecelen(index), index)
                self.inactive_requests[index] = 1
                self.amount_inactive += self._piecelen(index)
                self.stat_numflunked += 1

                self.failed_pieces[index] = {}
                allsenders = {}
                for d in self.download_history[index].values():
                    allsenders[d] = 1
                if len(allsenders) == 1:
                    culprit = allsenders.keys()[0]
                    if culprit is not None:
                        culprit.failed(index, bump = True)
                    del self.failed_pieces[index] # found the culprit already
                
                return False
        return True

    def request_lost(self, index, begin, length):
        self.inactive_requests[index].append((begin, length))
        self.amount_inactive += length
        self.numactive[index] -= 1
        if not self.numactive[index]:
            del self.stat_active[index]
            if self.stat_new.has_key(index):
                del self.stat_new[index]

    def get_piece(self, index, begin, length):
        try:
            return self._get_piece(index, begin, length)
        except IOError, e:
            self.failed('IO Error: ' + str(e))
            return None

    def _get_piece(self, index, begin, length):
        if not self.have[index]:
            return None
        if not self.waschecked[index]:
            if sha(self.storage.read(self.piece_size * self.places[index], self._piecelen(index))).digest() != self.hashes[index]:
                self.failed('told file complete on start-up, but piece failed hash check')
                return None
            self.waschecked[index] = True
        if length == -1:
            length = self._piecelen(index)-begin
        if begin + length > self._piecelen(index):
            return None
        return self.storage.read(self.piece_size * self.places[index] + begin, length)

class DummyStorage:
    def __init__(self, total, pre = False, ranges = []):
        self.pre = pre
        self.ranges = ranges
        self.s = chr(0xFF) * total
        self.done = False

    def was_preexisting(self):
        return self.pre

    def was_preallocated(self, begin, length):
        for b, l in self.ranges:
            if begin >= b and begin + length <= b + l:
                return True
        return False

    def get_total_length(self):
        return len(self.s)

    def read(self, begin, length):
        return self.s[begin:begin + length]

    def write(self, begin, piece):
        self.s = self.s[:begin] + piece + self.s[begin + len(piece):]

    def finished(self):
        self.done = True

def test_basic():
    ds = DummyStorage(3)
    sw = StorageWrapper(ds, 2, [sha('abc').digest()], 4, ds.finished, None)
    assert sw.get_amount_left() == 3
    assert not sw.do_I_have_anything()
    assert sw.get_have_list() == [False]
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
    assert sw.get_have_list() == [False]
    assert not ds.done
    sw.piece_came_in(0, 2, 'c')
    assert not sw.do_I_have_requests(0)
    assert sw.get_amount_left() == 0
    assert sw.do_I_have_anything()
    assert sw.get_have_list() == [True]
    assert sw.get_piece(0, 0, 3) == 'abc'
    assert sw.get_piece(0, 1, 2) == 'bc'
    assert sw.get_piece(0, 0, 2) == 'ab'
    assert sw.get_piece(0, 1, 1) == 'b'
    assert ds.done

def test_two_pieces():
    ds = DummyStorage(4)
    sw = StorageWrapper(ds, 3, [sha('abc').digest(),
        sha('d').digest()], 3, ds.finished, None)
    assert sw.get_amount_left() == 4
    assert not sw.do_I_have_anything()
    assert sw.get_have_list() == [False, False]
    assert sw.do_I_have_requests(0)
    assert sw.do_I_have_requests(1)

    assert sw.new_request(0) == (0, 3)
    assert sw.get_amount_left() == 4
    assert not sw.do_I_have_anything()
    assert sw.get_have_list() == [False, False]
    assert not sw.do_I_have_requests(0)
    assert sw.do_I_have_requests(1)

    assert sw.new_request(1) == (0, 1)
    assert sw.get_amount_left() == 4
    assert not sw.do_I_have_anything()
    assert sw.get_have_list() == [False, False]
    assert not sw.do_I_have_requests(0)
    assert not sw.do_I_have_requests(1)

    sw.piece_came_in(0, 0, 'abc')
    assert sw.get_amount_left() == 1
    assert sw.do_I_have_anything()
    assert sw.get_have_list() == [True, False]
    assert not sw.do_I_have_requests(0)
    assert not sw.do_I_have_requests(1)
    assert sw.get_piece(0, 0, 3) == 'abc'
    assert not ds.done

    sw.piece_came_in(1, 0, 'd')
    assert ds.done
    assert sw.get_amount_left() == 0
    assert sw.do_I_have_anything()
    assert sw.get_have_list() == [True, True]
    assert not sw.do_I_have_requests(0)
    assert not sw.do_I_have_requests(1)
    assert sw.get_piece(1, 0, 1) == 'd'

def test_hash_fail():
    ds = DummyStorage(4)
    sw = StorageWrapper(ds, 4, [sha('abcd').digest()], 4, ds.finished, None)
    assert sw.get_amount_left() == 4
    assert not sw.do_I_have_anything()
    assert sw.get_have_list() == [False]
    assert sw.do_I_have_requests(0)

    assert sw.new_request(0) == (0, 4)
    sw.piece_came_in(0, 0, 'abcx')
    assert sw.get_amount_left() == 4
    assert not sw.do_I_have_anything()
    assert sw.get_have_list() == [False]
    assert sw.do_I_have_requests(0)

    assert sw.new_request(0) == (0, 4)
    assert not ds.done
    sw.piece_came_in(0, 0, 'abcd')
    assert ds.done
    assert sw.get_amount_left() == 0
    assert sw.do_I_have_anything()
    assert sw.get_have_list() == [True]
    assert not sw.do_I_have_requests(0)

def test_lazy_hashing():
    ds = DummyStorage(4, ranges = [(0, 4)])
    flag = Event()
    sw = StorageWrapper(ds, 4, [sha('abcd').digest()], 4, ds.finished, lambda x, flag = flag: flag.set(), check_hashes = False)
    assert sw.get_piece(0, 0, 2) is None
    assert flag.isSet()

def test_lazy_hashing_pass():
    ds = DummyStorage(4)
    flag = Event()
    sw = StorageWrapper(ds, 4, [sha(chr(0xFF) * 4).digest()], 4, ds.finished, lambda x, flag = flag: flag.set(), check_hashes = False)
    assert sw.get_piece(0, 0, 2) is None
    assert not flag.isSet()

def test_preexisting():
    ds = DummyStorage(4, True, [(0, 4)])
    sw = StorageWrapper(ds, 2, [sha(chr(0xFF) * 2).digest(), 
        sha('ab').digest()], 2, ds.finished, None)
    assert sw.get_amount_left() == 2
    assert sw.do_I_have_anything()
    assert sw.get_have_list() == [True, False]
    assert not sw.do_I_have_requests(0)
    assert sw.do_I_have_requests(1)
    assert sw.new_request(1) == (0, 2)
    assert not ds.done
    sw.piece_came_in(1, 0, 'ab')
    assert ds.done
    assert sw.get_amount_left() == 0
    assert sw.do_I_have_anything()
    assert sw.get_have_list() == [True, True]
    assert not sw.do_I_have_requests(0)
    assert not sw.do_I_have_requests(1)

def test_total_too_short():
    ds = DummyStorage(4)
    try:
        StorageWrapper(ds, 4, [sha(chr(0xff) * 4).digest(),
            sha(chr(0xFF) * 4).digest()], 4, ds.finished, None)
        raise 'fail'
    except ValueError:
        pass

def test_total_too_big():
    ds = DummyStorage(9)
    try:
        sw = StorageWrapper(ds, 4, [sha('qqqq').digest(),
            sha(chr(0xFF) * 4).digest()], 4, ds.finished, None)
        raise 'fail'
    except ValueError:
        pass

def test_end_above_total_length():
    ds = DummyStorage(3, True)
    sw = StorageWrapper(ds, 4, [sha('qqq').digest()], 4, ds.finished, None)
    assert sw.get_piece(0, 0, 4) == None

def test_end_past_piece_end():
    ds = DummyStorage(4, True, ranges = [(0, 4)])
    sw = StorageWrapper(ds, 4, [sha(chr(0xFF) * 2).digest(), 
        sha(chr(0xFF) * 2).digest()], 2, ds.finished, None)
    assert ds.done
    assert sw.get_piece(0, 0, 3) == None

from random import shuffle

def test_alloc_random():
    ds = DummyStorage(101)
    sw = StorageWrapper(ds, 1, [sha(chr(i)).digest() for i in xrange(101)], 1, ds.finished, None)
    for i in xrange(100):
        assert sw.new_request(i) == (0, 1)
    r = range(100)
    shuffle(r)
    for i in r:
        sw.piece_came_in(i, 0, chr(i))
    for i in xrange(100):
        assert sw.get_piece(i, 0, 1) == chr(i)
    assert ds.s[:100] == ''.join([chr(i) for i in xrange(100)])

def test_alloc_resume():
    ds = DummyStorage(101)
    sw = StorageWrapper(ds, 1, [sha(chr(i)).digest() for i in xrange(101)], 1, ds.finished, None)
    for i in xrange(100):
        assert sw.new_request(i) == (0, 1)
    r = range(100)
    shuffle(r)
    for i in r[:50]:
        sw.piece_came_in(i, 0, chr(i))
    assert ds.s[50:] == chr(0xFF) * 51
    ds.ranges = [(0, 50)]
    sw = StorageWrapper(ds, 1, [sha(chr(i)).digest() for i in xrange(101)], 1, ds.finished, None)
    for i in r[50:]:
        sw.piece_came_in(i, 0, chr(i))
    assert ds.s[:100] == ''.join([chr(i) for i in xrange(100)])

def test_last_piece_pre():
    ds = DummyStorage(3, ranges = [(2, 1)])
    ds.s = chr(0xFF) + chr(0xFF) + 'c'
    sw = StorageWrapper(ds, 2, [sha('ab').digest(), sha('c').digest()], 2, ds.finished, None)
    assert not sw.do_I_have_requests(1)
    assert sw.do_I_have_requests(0)

def test_not_last_pre():
    ds = DummyStorage(3, ranges = [(1, 1)])
    ds.s = chr(0xFF) + 'a' + chr(0xFF)
    sw = StorageWrapper(ds, 1, [sha('a').digest()] * 3, 1, ds.finished, None)
    assert not sw.do_I_have_requests(1)
    assert sw.do_I_have_requests(0)
    assert sw.do_I_have_requests(2)

def test_last_piece_not_pre():
    ds = DummyStorage(51, ranges = [(50, 1)])
    sw = StorageWrapper(ds, 2, [sha('aa').digest()] * 25 + [sha('b').digest()], 2, ds.finished, None)
    for i in xrange(25):
        assert sw.new_request(i) == (0, 2)
    assert sw.new_request(25) == (0, 1)
    sw.piece_came_in(25, 0, 'b')
    r = range(25)
    shuffle(r)
    for i in r:
        sw.piece_came_in(i, 0, 'aa')
    assert ds.done
    assert ds.s == 'a' * 50 + 'b'
