# Written by Bram Cohen
# see LICENSE.txt for license information

from sha import sha
from random import shuffle
from threading import Event
from suck import suck
from cStringIO import StringIO
true = 1
false = 0

def make_indices(pieces, piece_length, file_length):
    if file_length > len(pieces) * piece_length:
        raise ValueError, "bigger than the sum of it's parts"
    if file_length <= (len(pieces) - 1) * piece_length:
        raise ValueError, "smaller than the sum of it's parts"
    # hash:  [(begin, end)]
    indices = {}
    for i in xrange(len(pieces)):
        begin = i * piece_length
        end = min((i+1) * piece_length, file_length)
        if indices.has_key(pieces[i]):
            array = indices[pieces[i]]
            if end - begin != array[0][1] - array[0][0]:
                raise ValueError, 'pieces with different lengths supposedly have the same hash'
            array.append((begin, end))
        else:
            indices[pieces[i]] = [(begin, end)]
    return indices

def dummy_status(fractionDone = None, activity = None):
    pass

class SingleBlob:
    def __init__(self, file, file_length, pieces, piece_length,
                callback, open, exists, getsize, flag = Event(),
                statusfunc = dummy_status):
        try:
            self.fileobj = MultiFile([(file, file_length)], open, exists, getsize, statusfunc)
            self.init(file_length, pieces, piece_length, callback, 
                flag, statusfunc)
        except IOError, e:
            callback(false, 'got disk access error -' + str(e), fatal = true)
        except ValueError, e:
            callback(false, 'error - ' + str(e), fatal = true)
            return

    def init(self, file_length, pieces, piece_length,
                callback, flag, statusfunc):
        self.callback = callback
        self.indices = make_indices(pieces, piece_length, file_length)
        # hash: 1
        self.complete = {}
        # hash: 1
        self.want = {}
        for i in pieces:
            self.want[i] = 1
        self.want_list = self.want.keys()
        shuffle(self.want_list)
        if len(self.want_list) == 0:
            self.callback(true)
            return
        if self.fileobj.preexisting:
            i = 0
            numofblobs = len(self.want_list)
            statusfunc(activity = 'checking existing file', 
                fractionDone = 0)
            for blob in self.want.keys():
                self._check_blob(blob)
                fracdone = float(i)/numofblobs
                statusfunc(fractionDone = float(i)/numofblobs)
                i += 1
                if flag.isSet():
                    return
            statusfunc(fractionDone = 1.0)

    def get_size(self, blob):
        begin, end = self.indices[blob][0]
        return end - begin

    def get_amount_left(self):
        sum = 0
        for i in self.want_list:
            begin, end = self.indices[i][0]
            sum += end - begin
        return sum

    def get_slice(self, blob, begin, length):
        try:
            return self._get_slice(blob, begin, length)
        except IOError, e:
            self.callback(false, 'IOError: ' + str(e), fatal = true)

    def _get_slice(self, blob, begin, length):
        if not self.complete.has_key(blob):
            return None
        beginindex, endindex = self.indices[blob][0]
        mybegin = beginindex + begin
        if mybegin > endindex:
            return None
        myend = mybegin + length
        if myend > endindex:
            return None
        return self.fileobj.read(mybegin, myend - mybegin)

    def do_I_want(self, blob):
        return self.want.has_key(blob)

    def get_list_of_blobs_I_want(self):
        return self.want_list

    def get_list_of_blobs_I_have(self):
        return self.complete.keys()

    def save_slice(self, blob, begin, slice):
        try:
            self._save_slice(blob, begin, slice)
        except IOError, e:
            self.callback(false, 'IOError: ' + str(e), fatal = true)

    def _save_slice(self, blob, begin, slice):
        beginindex, endindex = self.indices[blob][0]
        self.fileobj.write(beginindex + begin, slice)

    def check_blob(self, blob):
        try:
            return self._check_blob(blob)
        except IOError, e:
            self.callback(false, 'IOError: ' + str(e), fatal = true)
            return false

    def _check_blob(self, blob):
        beginindex, endindex = self.indices[blob][0]
        x = self.fileobj.read(beginindex, endindex - beginindex)
        if sha(x).digest() != blob:
            return false
        else:
            for begin, end in self.indices[blob][1:]:
                self.fileobj.write(begin, x)
        self.complete[blob] = 1
        del self.want[blob]
        self.want_list.remove(blob)
        if len(self.want) == 0:
            self.callback(true)
        return true

class MultiFile:
    def __init__(self, files, open, exists, getsize, statusfunc):
        self.ranges = []
        total = 0
        so_far = 0
        for file, length in files:
            if length != 0:
                self.ranges.append((total, total + length, file))
                total += length
                if exists(file):
                    l = getsize(file)
                    if l > length:
                        raise ValueError, 'existing file %s too large' % file
                    so_far += l
            else:
                if exists(file):
                    if getsize(file) > 0:
                        raise ValueError, 'existing file %s too large' % file
                else:
                    open(file, 'wb').close()
        self.handles = {}
        self.preexisting = false
        for file, length in files:
            if exists(file):
                self.handles[file] = open(file, 'rb+')
                self.preexisting = true
            else:
                self.handles[file] = open(file, 'wb+')
        if total > so_far:
            interval = max(2048, total / 100)
            statusfunc(activity = 'allocating', 
                fractionDone = float(so_far)/total)
            for file, length in files:
                l = 0
                if exists(file):
                    l = getsize(file)
                    if l == length:
                        continue
                h = self.handles[file]
                for i in range(l, length, interval)[1:] + [length-1]:
                    h.seek(i)
                    h.write(chr(1))
                    h.flush()
                    statusfunc(fractionDone = float(so_far + i - l)/total)
                so_far += length - l
            statusfunc(fractionDone = 1.0)

    def intervals(self, pos, amount):
        r = []
        stop = pos + amount
        for begin, end, file in self.ranges:
            if end <= pos:
                continue
            if begin >= stop:
                break
            r.append((file, max(pos, begin) - begin, min(end, stop) - begin))
        return r

    def read(self, pos, amount):
        r = StringIO()
        for file, pos, end in self.intervals(pos, amount):
            h = self.handles[file]
            h.seek(pos)
            r.write(suck(h, end - pos))
        return r.getvalue()
        
    def write(self, pos, s):
        total = 0
        for file, begin, end in self.intervals(pos, len(s)):
            h = self.handles[file]
            h.seek(begin)
            h.write(s[total: total + end - begin])
            total += end - begin

# everything below is for testing

from fakeopen import FakeOpen

def test_multifile_simple():
    f = FakeOpen()
    m = MultiFile([('a', 5)], f.open, f.exists, f.getsize, dummy_status)
    assert f.files.keys() == ['a']
    assert len(f.files['a']) == 5
    m.write(0, 'abc')
    assert m.read(0, 3) == 'abc'
    m.write(2, 'abc')
    assert m.read(2, 3) == 'abc'
    m.write(1, 'abc')
    assert m.read(0, 5) == 'aabcc'
    
def test_multifile_multiple():
    f = FakeOpen()
    m = MultiFile([('a', 5), ('2', 4), ('c', 3)], 
        f.open, f.exists, f.getsize, dummy_status)
    x = f.files.keys()
    x.sort()
    assert x == ['2', 'a', 'c']
    assert len(f.files['a']) == 5
    assert len(f.files['2']) == 4
    assert len(f.files['c']) == 3
    m.write(3, 'abc')
    assert m.read(3, 3) == 'abc'
    m.write(5, 'ab')
    assert m.read(4, 3) == 'bab'
    m.write(3, 'pqrstuvw')
    assert m.read(3, 8) == 'pqrstuvw'
    m.write(3, 'abcdef')
    assert m.read(3, 7) == 'abcdefv'

def test_multifile_zero():
    f = FakeOpen()
    m = MultiFile([('a', 0)], 
        f.open, f.exists, f.getsize, dummy_status)
    assert f.files == {'a': []}

def test_resume_zero():
    f = FakeOpen({'a': ''})
    m = MultiFile([('a', 0)], 
        f.open, f.exists, f.getsize, dummy_status)
    assert f.files == {'a': []}

def test_multifile_with_zero():
    f = FakeOpen()
    m = MultiFile([('a', 3), ('b', 0), ('c', 3)], 
        f.open, f.exists, f.getsize, dummy_status)
    m.write(2, 'abc')
    assert m.read(2, 3) == 'abc'
    x = f.files.keys()
    x.sort()
    assert x == ['a', 'b', 'c']
    assert len(f.files['a']) == 3
    assert len(f.files['b']) == 0
    assert len(f.files['c']) == 3

def test_multifile_resume():
    f = FakeOpen({'a': 'abc'})
    m = MultiFile([('a', 4)], 
        f.open, f.exists, f.getsize, dummy_status)
    assert f.files.keys() == ['a']
    assert len(f.files['a']) == 4
    assert m.read(0, 3) == 'abc'

def test_multifile_mixed_resume():
    f = FakeOpen({'b': 'abc'})
    m = MultiFile([('a', 3), ('b', 4)], 
        f.open, f.exists, f.getsize, dummy_status)
    x = f.files.keys()
    x.sort()
    assert x == ['a', 'b']
    assert len(f.files['a']) == 3
    assert len(f.files['b']) == 4
    assert m.read(3, 3) == 'abc'

class dummycalls:
    def __init__(self):
        self.r = []

    def c(self, a, b = '', fatal = false):
        self.r.append((a, b, fatal))

def test_normal():
    s = 'abc' * 5
    a = sha(s[:10]).digest()
    b = sha(s[10:]).digest()
    d = dummycalls()
    f = FakeOpen()
    sb = SingleBlob('test', 15, [a, b], 10, 
        d.c, f.open, f.exists, f.getsize)
    assert d.r == []
    x = sb.get_list_of_blobs_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_blobs_I_have() == []
    assert sb.get_slice(a, 0, 2) == None
    
    sb.save_slice(a, 0, s[0:5])
    assert not sb.check_blob(a)
    assert d.r == []
    x = sb.get_list_of_blobs_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_blobs_I_have() == []
    assert sb.get_slice(a, 0, 2) == None
    
    sb.save_slice(b, 0, s[10:12])
    assert not sb.check_blob(b)
    assert d.r == []
    x = sb.get_list_of_blobs_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_blobs_I_have() == []
    assert sb.get_slice(a, 0, 2) == None

    sb.save_slice(a, 5, s[5:10])
    assert sb.check_blob(a)
    assert d.r == []
    assert sb.get_list_of_blobs_I_want() == [b]
    assert sb.get_list_of_blobs_I_have() == [a]
    assert sb.get_slice(a, 0, 2) == s[:2]
    assert sb.get_slice(a, 7, 3) == s[7:10]
    assert sb.get_slice(a, 7, 20) == None

    sb.save_slice(b, 2, s[12:])
    assert sb.check_blob(b)
    assert d.r == [(true, '', false)]
    assert sb.get_list_of_blobs_I_want() == []
    x = sb.get_list_of_blobs_I_have()
    assert x == [a, b] or x == [b, a]
    assert sb.get_slice(b, 0, 2) == s[10:12]
    assert sb.get_slice(b, 4, 1) == s[14:]

def test_even():
    s = 'abcd' * 5
    a = sha(s[:10]).digest()
    b = sha(s[10:]).digest()
    d = dummycalls()
    f = FakeOpen()
    sb = SingleBlob('test', 20, [a, b], 10, 
        d.c, f.open, f.exists, f.getsize)
    assert d.r == []
    x = sb.get_list_of_blobs_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_blobs_I_have() == []
    assert sb.get_slice(a, 0, 2) == None
    
    assert not sb.save_slice(a, 0, s[0:5])
    assert d.r == []
    x = sb.get_list_of_blobs_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_blobs_I_have() == []
    assert sb.get_slice(a, 0, 2) == None
    
    assert not sb.save_slice(b, 0, s[10:12])
    assert d.r == []
    x = sb.get_list_of_blobs_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_blobs_I_have() == []
    assert sb.get_slice(a, 0, 2) == None

    sb.save_slice(a, 5, s[5:10])
    assert sb.check_blob(a)
    assert d.r == []
    assert sb.get_list_of_blobs_I_want() == [b]
    assert sb.get_list_of_blobs_I_have() == [a]
    assert sb.get_slice(a, 0, 2) == s[:2]
    assert sb.get_slice(a, 7, 3) == s[7:10]
    assert sb.get_slice(a, 7, 20) == None

    sb.save_slice(b, 2, s[12:])
    assert sb.check_blob(b)
    assert d.r == [(true, '', false)]
    assert sb.get_list_of_blobs_I_want() == []
    x = sb.get_list_of_blobs_I_have()
    assert x == [a, b] or x == [b, a]
    assert sb.get_slice(b, 0, 2) == s[10:12]
    assert sb.get_slice(b, 4, 6) == s[14:]

def test_short():
    s = 'abcdefgh'
    a = sha(s).digest()
    d = dummycalls()
    f = FakeOpen()
    sb = SingleBlob('test', 8, [a], 10, d.c, 
        f.open, f.exists, f.getsize)
    assert d.r == []
    assert sb.get_list_of_blobs_I_want() == [a]
    assert sb.get_slice(a, 0, 2) == None
    
    assert not sb.save_slice(a, 0, s[0:5])
    assert d.r == []
    assert sb.get_list_of_blobs_I_want() == [a]
    assert sb.get_list_of_blobs_I_have() == []
    assert sb.get_slice(a, 0, 2) == None
    
    sb.save_slice(a, 5, s[5:])
    assert sb.check_blob(a)
    assert d.r == [(true, '', false)]
    assert sb.get_list_of_blobs_I_want() == []
    assert sb.get_list_of_blobs_I_have() == [a]
    assert sb.get_slice(a, 0, 2) == s[:2]
    assert sb.get_slice(a, 7, 1) == s[7:]
    assert sb.get_slice(a, 7, 20) == None
    assert sb.get_slice(chr(0) * 20, 0, 20) == None

def test_zero_length():
    d = dummycalls()
    f = FakeOpen()
    sb = SingleBlob('test', 0, [], 10, 
        d.c, f.open, f.exists, f.getsize)
    assert d.r == [(true, '', false)]
    
def test_zero_length_resume():
    d = dummycalls()
    f = FakeOpen({'test': ''})
    sb = SingleBlob('test', 0, [], 10, 
        d.c, f.open, f.exists, f.getsize)
    assert d.r == [(true, '', false)]
    
def test_too_big():
    s = 'abcdefgh'
    a = sha(s).digest()
    d = dummycalls()
    f = FakeOpen()
    sb = SingleBlob('test', 11, [a], 10, d.c, 
        f.open, f.exists, f.getsize)
    assert len(d.r) == 1 and not d.r[0][0] and d.r[0][2]

def test_too_small():
    a = sha('abc').digest()
    b = sha('pqr').digest()
    d = dummycalls()
    f = FakeOpen()
    sb = SingleBlob('test', 8, [a, b], 
        10, d.c, f.open, f.exists, f.getsize)
    assert len(d.r) == 1 and not d.r[0][0] and d.r[0][2]

def test_repeat_piece():
    b = sha('abc').digest()
    d = dummycalls()
    f = FakeOpen()
    sb = SingleBlob('test', 6, [b, b], 3, d.c, 
        f.open, f.exists, f.getsize)
    assert d.r == []
    
    sb.save_slice(b, 0, 'abc')
    assert sb.check_blob(b)
    assert d.r == [(true, '', false)]

def test_resume_partial():
    b = sha('abc').digest()
    d = dummycalls()
    f = FakeOpen({'test': 'a'})
    sb = SingleBlob('test', 6, [b, b], 3, d.c, 
        f.open, f.exists, f.getsize)
    assert d.r == []
    
    sb.save_slice(b, 0, 'abc')
    assert sb.check_blob(b)
    assert d.r == [(true, '', false)]

def test_resume_with_repeat_piece_present():
    b = sha('abc').digest()
    c = sha('q').digest()
    d = dummycalls()
    f = FakeOpen({'test': 'abcaaaf'})
    sb = SingleBlob('test', 7, [b, b, c], 3, d.c, 
        f.open, f.exists, f.getsize)
    assert d.r == []
    
    sb.save_slice(c, 0, 'q')
    assert sb.check_blob(c)
    assert d.r == [(true, '', false)]

def test_flunk_repeat_with_different_sizes():
    a = sha('abc').digest()
    d = dummycalls()
    f = FakeOpen()
    sb = SingleBlob('test', 15, [a, a], 
        10, d.c, f.open, f.exists, f.getsize)
    assert len(d.r) == 1 and not d.r[0][0] and d.r[0][2]
