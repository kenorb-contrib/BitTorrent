# Written by Bram Cohen
# this file is public domain

from sha import sha
from os import path
from random import shuffle
true = 1
false = 0

csize = 2 ** 20

class SingleBlob:
    def __init__(self, file, file_hash, file_length, pieces, piece_length, callback):
        assert len(pieces) > 0
        assert len(file_hash) == 20
        self.piece_length = piece_length
        self.file_hash = file_hash
        self.file_length = file_length
        self.callback = callback
        # hash:  (begin, end)
        self.indices = {}
        for i in xrange(len(pieces) - 1):
            self.indices[pieces[i]] = (i * piece_length, (i+1) * piece_length)
        self.indices[pieces[-1]] = ((len(pieces)-1) * piece_length, file_length)
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
        if path.exists(file):
            if path.getsize(file) != file_length:
                raise ValueError, 'existing file is of incorrect length'
            i = 0
            self.h = open(file, 'rb+')
            for ph, (begin, end) in self.indices.items():
                amount = end - begin
                self.h.seek(begin)
                if sha(self.h.read(amount)).digest() == ph:
                    del self.want[ph]
                    self.complete[ph] = 1
                    self.amount_have[ph] = amount
                    self.want_list.remove(ph)
            if len(self.want_list) == 0:
                raise ValueError, 'download already complete'
        else:
            self.h = open(file, 'wb+')
            c = chr(0) * csize
            i = 0
            while i + csize < file_length:
                self.h.write(c)
                i += csize
            self.h.write(chr(0) * (file_length - i))
            self.h.flush()

    def get_size(self, blob):
        if not self.indices.has_key(blob):
            return None
        begin, end = self.indices[blob]
        return end - begin

    def get_slice(self, blob, begin, length):
        if not self.complete.has_key(blob):
            return None
        beginindex, endindex = self.indices[blob]
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
        beginindex, endindex = self.indices[blob]
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

def dirtest_normal(dir):
    s = 'abc' * 5
    a = sha(s[:10]).digest()
    b = sha(s[10:]).digest()
    r = []
    sb = SingleBlob(path.join(dir, 'test'), sha(s).digest(), 
        15, [a, b], 10, r.append)
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

def dirtest_even(dir):
    s = 'abcd' * 5
    a = sha(s[:10]).digest()
    b = sha(s[10:]).digest()
    r = []
    sb = SingleBlob(path.join(dir, 'test'), sha(s).digest(), 
        20, [a, b], 10, r.append)
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

def dirtest_short(dir):
    s = 'abcdefgh'
    a = sha(s).digest()
    r = []
    sb = SingleBlob(path.join(dir, 'test'), a, 
        8, [a], 10, r.append)
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




