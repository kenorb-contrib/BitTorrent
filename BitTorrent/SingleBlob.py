# Written by Bram Cohen
# this file is public domain

from sha import sha
from random import shuffle
true = 1
false = 0

csize = 2 ** 20

class SingleBlob:
    def __init__(self, file, file_hash, file_length, pieces, piece_length, callback, open, exists, getsize):
        self.open = open
        self.exists = exists
        self.getsize = getsize
        self.piece_length = piece_length
        self.file_hash = file_hash
        self.file_length = file_length
        self.callback = callback
        if file_length > len(pieces) * piece_length:
            raise ValueError, "bigger than the sum of it's parts"
        if file_length < (len(pieces) - 1) * piece_length:
            raise ValueError, "smaller than the sum of it's parts"
        # hash:  [(begin, end)]
        self.indices = {}
        for i in xrange(len(pieces)):
            begin = i * piece_length
            end = min((i+1) * piece_length, file_length)
            if end - begin == 0:
                break
            if self.indices.has_key(pieces[i]):
                array = self.indices[pieces[i]]
                if end - begin != array[0][1] - array[0][0]:
                    raise ValueError, 'pieces with different lengths supposedly have the same hash'
                array.append((begin, end))
            else:
                self.indices[pieces[i]] = [(begin, end)]
        # hash: 1
        self.complete = {}
        # hash: amount have
        self.amount_have = {}
        # hash: 1
        self.want = {}
        for i in pieces:
            self.amount_have[i] = 0
            self.want[i] = 1
        self.want_list = self.want.keys()
        shuffle(self.want_list)
        if self.exists(file):
            if self.getsize(file) != file_length:
                raise ValueError, 'existing file is of incorrect length'
            i = 0
            self.h = self.open(file, 'rb+')
            for ph, array in self.indices.items():
                for i in xrange(len(array)):
                    begin, end = array[i]
                    amount = end - begin
                    self.h.seek(begin)
                    b = self.h.read(amount)
                    if sha(b).digest() == ph:
                        del self.want[ph]
                        self.complete[ph] = 1
                        self.amount_have[ph] = amount
                        self.want_list.remove(ph)
                        for j in xrange(len(array)):
                            if j != i:
                                begin, end = array[j]
                                self.h.seek(begin)
                                self.h.write(b)
                        break
        else:
            self.h = self.open(file, 'wb+')
            c = chr(0) * csize
            i = 0
            while i + csize < file_length:
                self.h.write(c)
                i += csize
            self.h.write(chr(0) * (file_length - i))
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
        
    def get_list_of_files_I_want(self):
        return self.want_list

    def get_list_of_files_I_have(self):
        return self.complete.keys()

    def get_amount_have(self, blob):
        return self.amount_have.get(blob, 0)
        
    def save_slice(self, blob, begin, slice):
        if self.complete.has_key(blob):
            return true
        if not self.want.has_key(blob):
            return true
        if begin != self.amount_have[blob]:
            return false
        beginindex, endindex = self.indices[blob][0]
        mybegin = beginindex + begin
        if len(slice) > endindex - mybegin:
            slice = slice[:endindex - mybegin]
        self.h.seek(mybegin)
        self.h.write(slice)
        self.amount_have[blob] += len(slice)
        if self.amount_have[blob] == endindex - beginindex:
            self.h.seek(beginindex)
            x = self.h.read(endindex - beginindex)
            if sha(x).digest() != blob:
                self.amount_have[blob] = 0
                return false
            else:
                for begin, end in self.indices[blob][1:]:
                    self.h.seek(begin)
                    self.h.write(x)
            self.complete[blob] = 1
            del self.want[blob]
            self.want_list.remove(blob)
            if len(self.want) == 0:
                f = sha()
                self.h.seek(0)
                i = 0
                while i + csize < self.file_length:
                    f.update(self.h.read(csize))
                    i += csize
                f.update(self.h.read(self.file_length - i))
                self.callback(f.digest() == self.file_hash)
            return true
        else:
            return false

# everything below is for testing

from fakeopen import FakeOpen

def test_normal():
    s = 'abc' * 5
    a = sha(s[:10]).digest()
    b = sha(s[10:]).digest()
    r = []
    f = FakeOpen()
    sb = SingleBlob('test', sha(s).digest(), 
        15, [a, b], 10, r.append, f.open, f.exists, f.getsize)
    assert r == []
    x = sb.get_list_of_files_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_files_I_have() == []
    assert sb.get_slice(a, 0, 2) == None
    
    assert not sb.save_slice(a, 0, s[0:5])
    assert r == []
    x = sb.get_list_of_files_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_files_I_have() == []
    assert sb.get_slice(a, 0, 2) == None
    
    assert not sb.save_slice(b, 0, s[10:12])
    assert r == []
    x = sb.get_list_of_files_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_files_I_have() == []
    assert sb.get_slice(a, 0, 2) == None

    assert sb.save_slice(a, 5, s[5:10])
    assert r == []
    assert sb.get_list_of_files_I_want() == [b]
    assert sb.get_list_of_files_I_have() == [a]
    assert sb.get_slice(a, 0, 2) == s[:2]
    assert sb.get_slice(a, 7, 3) == s[7:10]
    assert sb.get_slice(a, 7, 20) == None

    assert sb.save_slice(b, 2, s[12:])
    assert r == [true]
    assert sb.get_list_of_files_I_want() == []
    x = sb.get_list_of_files_I_have()
    assert x == [a, b] or x == [b, a]
    assert sb.get_slice(b, 0, 2) == s[10:12]
    assert sb.get_slice(b, 4, 1) == s[14:]

def test_even():
    s = 'abcd' * 5
    a = sha(s[:10]).digest()
    b = sha(s[10:]).digest()
    r = []
    f = FakeOpen()
    sb = SingleBlob('test', sha(s).digest(), 
        20, [a, b], 10, r.append, f.open, f.exists, f.getsize)
    assert r == []
    x = sb.get_list_of_files_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_files_I_have() == []
    assert sb.get_slice(a, 0, 2) == None
    
    assert not sb.save_slice(a, 0, s[0:5])
    assert r == []
    x = sb.get_list_of_files_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_files_I_have() == []
    assert sb.get_slice(a, 0, 2) == None
    
    assert not sb.save_slice(b, 0, s[10:12])
    assert r == []
    x = sb.get_list_of_files_I_want()
    assert x == [a, b] or x == [b, a]
    assert sb.get_list_of_files_I_have() == []
    assert sb.get_slice(a, 0, 2) == None

    assert sb.save_slice(a, 5, s[5:10])
    assert r == []
    assert sb.get_list_of_files_I_want() == [b]
    assert sb.get_list_of_files_I_have() == [a]
    assert sb.get_slice(a, 0, 2) == s[:2]
    assert sb.get_slice(a, 7, 3) == s[7:10]
    assert sb.get_slice(a, 7, 20) == None

    assert sb.save_slice(b, 2, s[12:])
    assert r == [true]
    assert sb.get_list_of_files_I_want() == []
    x = sb.get_list_of_files_I_have()
    assert x == [a, b] or x == [b, a]
    assert sb.get_slice(b, 0, 2) == s[10:12]
    assert sb.get_slice(b, 4, 6) == s[14:]

def test_short():
    s = 'abcdefgh'
    a = sha(s).digest()
    r = []
    f = FakeOpen()
    sb = SingleBlob('test', a, 
        8, [a], 10, r.append, f.open, f.exists, f.getsize)
    assert r == []
    assert sb.get_list_of_files_I_want() == [a]
    assert sb.get_slice(a, 0, 2) == None
    assert sb.get_amount_have(a) == 0
    
    assert not sb.save_slice(a, 0, s[0:5])
    assert r == []
    assert sb.get_list_of_files_I_want() == [a]
    assert sb.get_list_of_files_I_have() == []
    assert sb.get_slice(a, 0, 2) == None
    assert sb.get_amount_have(a) == 5
    
    assert sb.save_slice(a, 5, s[5:])
    assert r == [true]
    assert sb.get_list_of_files_I_want() == []
    assert sb.get_list_of_files_I_have() == [a]
    assert sb.get_slice(a, 0, 2) == s[:2]
    assert sb.get_slice(a, 7, 1) == s[7:]
    assert sb.get_slice(a, 7, 20) == None
    assert sb.get_amount_have(a) == 8
    assert sb.get_amount_have(chr(0) * 20) == 0
    assert sb.get_slice(chr(0) * 20, 0, 20) == None

def test_zero_length():
    r = []
    f = FakeOpen()
    sb = SingleBlob('test', sha('').digest(), 
        0, [], 10, r.append, f.open, f.exists, f.getsize)
    assert r == []
    assert sb.get_amount_left() == 0

def test_too_big():
    s = 'abcdefgh'
    a = sha(s).digest()
    r = []
    f = FakeOpen()
    try:
        sb = SingleBlob('test', a, 
            11, [a], 10, r.append, f.open, f.exists, f.getsize)
        assert false
    except ValueError:
        pass

def test_too_small():
    a = sha('abc').digest()
    b = sha('pqr').digest()
    r = []
    f = FakeOpen()
    try:
        sb = SingleBlob('test', sha('x').digest(), 
            8, [a, b], 10, r.append, f.open, f.exists, f.getsize)
        assert false
    except ValueError:
        pass

def test_repeat_piece():
    a = sha('abcabc').digest()
    b = sha('abc').digest()
    r = []
    f = FakeOpen()
    sb = SingleBlob('test', a, 
        6, [b, b], 3, r.append, f.open, f.exists, f.getsize)
    assert r == []
    
    assert sb.save_slice(b, 0, 'abc')
    assert r == [true]

def test_resume_with_repeat_piece_present():
    a = sha('abcabcq').digest()
    b = sha('abc').digest()
    c = sha('q').digest()
    r = []
    f = FakeOpen({'test': 'aaaabcf'})
    sb = SingleBlob('test', a, 
        7, [b, b, c], 3, r.append, f.open, f.exists, f.getsize)
    assert r == []
    assert sb.get_amount_left() == 1

    assert sb.save_slice(c, 0, 'q')
    assert r == [true]

def test_flunk_repeat_with_different_sizes():
    a = sha('abc').digest()
    r = []
    f = FakeOpen()
    try:
        sb = SingleBlob('test', sha('x').digest(), 
            15, [a, a], 10, r.append, f.open, f.exists, f.getsize)
        assert false
    except ValueError:
        pass
