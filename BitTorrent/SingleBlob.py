# Written by Bram Cohen
# see LICENSE.txt for license information

from sha import sha
from random import shuffle
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

class SingleBlob:
    def __init__(self, file, file_length, pieces, piece_length, 
            callback, open, exists, getsize):
        self.open = open
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
        if exists(file):
            if getsize(file) != file_length:
                raise ValueError, 'existing file is of incorrect length'
            self.h = self.open(file, 'rb+')
            for blob in self.want.keys():
                self.check_blob(blob)
        else:
            self.h = self.open(file, 'wb+')
            self.h.seek(file_length - 1)
            self.h.write(chr(0))
            self.h.flush()

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
        if not self.complete.has_key(blob):
            return None
        beginindex, endindex = self.indices[blob][0]
        mybegin = beginindex + begin
        if mybegin > endindex:
            return None
        myend = mybegin + length
        if myend > endindex:
            return None
        self.h.seek(mybegin)
        return self.h.read(myend - mybegin)

    def do_I_want(self, blob):
        return self.want.has_key(blob)

    def get_list_of_blobs_I_want(self):
        return self.want_list

    def get_list_of_blobs_I_have(self):
        return self.complete.keys()

    def save_slice(self, blob, begin, slice):
        beginindex, endindex = self.indices[blob][0]
        self.h.seek(beginindex + begin)
        self.h.write(slice)
    
    def check_blob(self, blob):
        beginindex, endindex = self.indices[blob][0]
        self.h.seek(beginindex)
        x = self.h.read(endindex - beginindex)
        if sha(x).digest() != blob:
            return false
        else:
            for begin, end in self.indices[blob][1:]:
                self.h.seek(begin)
                self.h.write(x)
        self.complete[blob] = 1
        del self.want[blob]
        self.want_list.remove(blob)
        if len(self.want) == 0:
            self.callback(true)
        return true

# everything below is for testing

from fakeopen import FakeOpen

def test_normal():
    s = 'abc' * 5
    a = sha(s[:10]).digest()
    b = sha(s[10:]).digest()
    r = []
    f = FakeOpen()
    sb = SingleBlob('test', 15, [a, b], 10, 
        r.append, f.open, f.exists, f.getsize)
    assert r == []
    x = sb.get_list_of_blobs_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_blobs_I_have() == []
    assert sb.get_slice(a, 0, 2) == None
    
    sb.save_slice(a, 0, s[0:5])
    assert not sb.check_blob(a)
    assert r == []
    x = sb.get_list_of_blobs_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_blobs_I_have() == []
    assert sb.get_slice(a, 0, 2) == None
    
    sb.save_slice(b, 0, s[10:12])
    assert not sb.check_blob(b)
    assert r == []
    x = sb.get_list_of_blobs_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_blobs_I_have() == []
    assert sb.get_slice(a, 0, 2) == None

    sb.save_slice(a, 5, s[5:10])
    assert sb.check_blob(a)
    assert r == []
    assert sb.get_list_of_blobs_I_want() == [b]
    assert sb.get_list_of_blobs_I_have() == [a]
    assert sb.get_slice(a, 0, 2) == s[:2]
    assert sb.get_slice(a, 7, 3) == s[7:10]
    assert sb.get_slice(a, 7, 20) == None

    sb.save_slice(b, 2, s[12:])
    assert sb.check_blob(b)
    assert r == [true]
    assert sb.get_list_of_blobs_I_want() == []
    x = sb.get_list_of_blobs_I_have()
    assert x == [a, b] or x == [b, a]
    assert sb.get_slice(b, 0, 2) == s[10:12]
    assert sb.get_slice(b, 4, 1) == s[14:]

def test_even():
    s = 'abcd' * 5
    a = sha(s[:10]).digest()
    b = sha(s[10:]).digest()
    r = []
    f = FakeOpen()
    sb = SingleBlob('test', 20, [a, b], 10, 
        r.append, f.open, f.exists, f.getsize)
    assert r == []
    x = sb.get_list_of_blobs_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_blobs_I_have() == []
    assert sb.get_slice(a, 0, 2) == None
    
    assert not sb.save_slice(a, 0, s[0:5])
    assert r == []
    x = sb.get_list_of_blobs_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_blobs_I_have() == []
    assert sb.get_slice(a, 0, 2) == None
    
    assert not sb.save_slice(b, 0, s[10:12])
    assert r == []
    x = sb.get_list_of_blobs_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_blobs_I_have() == []
    assert sb.get_slice(a, 0, 2) == None

    sb.save_slice(a, 5, s[5:10])
    assert sb.check_blob(a)
    assert r == []
    assert sb.get_list_of_blobs_I_want() == [b]
    assert sb.get_list_of_blobs_I_have() == [a]
    assert sb.get_slice(a, 0, 2) == s[:2]
    assert sb.get_slice(a, 7, 3) == s[7:10]
    assert sb.get_slice(a, 7, 20) == None

    sb.save_slice(b, 2, s[12:])
    assert sb.check_blob(b)
    assert r == [true]
    assert sb.get_list_of_blobs_I_want() == []
    x = sb.get_list_of_blobs_I_have()
    assert x == [a, b] or x == [b, a]
    assert sb.get_slice(b, 0, 2) == s[10:12]
    assert sb.get_slice(b, 4, 6) == s[14:]

def test_short():
    s = 'abcdefgh'
    a = sha(s).digest()
    r = []
    f = FakeOpen()
    sb = SingleBlob('test', 8, [a], 10, r.append, 
        f.open, f.exists, f.getsize)
    assert r == []
    assert sb.get_list_of_blobs_I_want() == [a]
    assert sb.get_slice(a, 0, 2) == None
    
    assert not sb.save_slice(a, 0, s[0:5])
    assert r == []
    assert sb.get_list_of_blobs_I_want() == [a]
    assert sb.get_list_of_blobs_I_have() == []
    assert sb.get_slice(a, 0, 2) == None
    
    sb.save_slice(a, 5, s[5:])
    assert sb.check_blob(a)
    assert r == [true]
    assert sb.get_list_of_blobs_I_want() == []
    assert sb.get_list_of_blobs_I_have() == [a]
    assert sb.get_slice(a, 0, 2) == s[:2]
    assert sb.get_slice(a, 7, 1) == s[7:]
    assert sb.get_slice(a, 7, 20) == None
    assert sb.get_slice(chr(0) * 20, 0, 20) == None

def test_zero_length():
    r = []
    f = FakeOpen()
    sb = SingleBlob('test', 0, [], 10, 
        r.append, f.open, f.exists, f.getsize)
    assert r == []
    
def test_too_big():
    s = 'abcdefgh'
    a = sha(s).digest()
    r = []
    f = FakeOpen()
    try:
        sb = SingleBlob('test', 11, [a], 10, r.append, 
            f.open, f.exists, f.getsize)
        assert false
    except ValueError:
        pass

def test_too_small():
    a = sha('abc').digest()
    b = sha('pqr').digest()
    r = []
    f = FakeOpen()
    try:
        sb = SingleBlob('test', 8, [a, b], 
            10, r.append, f.open, f.exists, f.getsize)
        assert false
    except ValueError:
        pass

def test_repeat_piece():
    b = sha('abc').digest()
    r = []
    f = FakeOpen()
    sb = SingleBlob('test', 6, [b, b], 3, r.append, 
        f.open, f.exists, f.getsize)
    assert r == []
    
    sb.save_slice(b, 0, 'abc')
    assert sb.check_blob(b)
    assert r == [true]

def test_resume_with_repeat_piece_present():
    a = sha('abcabcq').digest()
    b = sha('abc').digest()
    c = sha('q').digest()
    r = []
    f = FakeOpen({'test': 'abcaaaf'})
    sb = SingleBlob('test', 7, [b, b, c], 3, r.append, 
        f.open, f.exists, f.getsize)
    assert r == []
    
    sb.save_slice(c, 0, 'q')
    assert sb.check_blob(c)
    assert r == [true]

def test_flunk_repeat_with_different_sizes():
    a = sha('abc').digest()
    r = []
    f = FakeOpen()
    try:
        sb = SingleBlob('test', 15, [a, a], 
            10, r.append, f.open, f.exists, f.getsize)
        assert false
    except ValueError:
        pass
