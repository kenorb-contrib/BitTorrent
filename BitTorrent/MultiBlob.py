# Written by Bram Cohen
# this file is public domain

from sha import sha
true = 1
false = 0

class MultiBlob:
    def __init__(self, files, piece_length, open, getsize):
        self.open = open
        # blob: (file, begin, end)
        self.blobs = {}
        # name, hash, [pieces]
        self.info = []
        for file in files:
            pieces = []
            fhash = sha()
            len = getsize(file)
            h = open(file, 'rb')
            i = 0
            while i + piece_length < len:
                block = h.read(piece_length)
                piece = sha(block).digest()
                pieces.append(piece)
                fhash.update(block)
                self.blobs[piece] = (file, i, i + piece_length)
                i += piece_length
            block = h.read(len - i)
            piece = sha(block).digest()
            pieces.append(piece)
            fhash.update(block)
            self.blobs[piece] = (file, i, len)
            h.close()
            self.info.append((file, fhash.digest(), pieces, len))

    def get_info(self):
        return self.info

    def get_slice(self, blob, begin, length):
        if not self.blobs.has_key(blob):
            return None
        file, beginindex, endindex = self.blobs[blob]
        if begin > endindex - beginindex:
            return None
        mybegin = beginindex + begin
        if mybegin + length > endindex:
            return None
        h = self.open(file, 'rb')
        h.seek(mybegin)
        r = h.read(length)
        h.close()
        return r
        
    def get_list_of_files_I_have(self):
        return self.blobs.keys()

from fakeopen import FakeOpen

def test_long_file():
    s = 'abc' * 5
    a = sha(s[:10]).digest()
    b = sha(s[10:]).digest()
    fo = FakeOpen({'test': s})
    mb = MultiBlob(['test'], 10, fo.open, fo.getsize)
    x = mb.get_list_of_files_I_have()
    assert x == [a, b] or x == [b, a]
    assert mb.get_slice(a, 0, 5) == s[:5]
    assert mb.get_slice(a, 5, 5) == s[5:10]
    assert mb.get_slice(a, 5, 20) == None
    assert mb.get_slice(b, 0, 2) == s[10:12]
    assert mb.get_slice(b, 4, 1) == s[14:]
    assert mb.get_slice(b, 4, 3) == None
    assert mb.get_slice(chr(0) * 20, 0, 2) == None
    assert mb.get_info() == [('test', sha(s).digest(), [a, b], 15)]

def test_even():
    s = 'abcd' * 5
    a = sha(s[:10]).digest()
    b = sha(s[10:]).digest()
    fo = FakeOpen({'test': s})
    mb = MultiBlob(['test'], 10, fo.open, fo.getsize)
    x = mb.get_list_of_files_I_have()
    assert x == [a, b] or x == [b, a]
    assert mb.get_slice(a, 0, 5) == s[:5]
    assert mb.get_slice(a, 5, 5) == s[5:10]
    assert mb.get_slice(a, 5, 20) == None
    assert mb.get_slice(b, 0, 2) == s[10:12]
    assert mb.get_slice(b, 4, 6) == s[14:]
    assert mb.get_info() == [('test', sha(s).digest(), [a, b], 20)]

def dirtest_short():
    s = 'abc' * 2
    a = sha(s).digest()
    fo = FakeOpen({'test': s})
    mb = MultiBlob(['test'], 10, fo.open, fo.getsize)
    assert mb.get_list_of_files_I_have() == [a]
    assert mb.get_slice(a, 0, 5) == s[:5]
    assert mb.get_slice(a, 5, 1) == s[5:]
    assert mb.get_slice(a, 5, 20) == None
    assert mb.get_slice(a, 2, 1) == s[2:3]
    assert mb.get_info() == [(file, a, [a], 6)]

def dirtest_null():
    s = ''
    a = sha(s).digest()
    fo = FakeOpen({'test': s})
    mb = MultiBlob(['test'], 10, fo.open, fo.getsize)
    assert mb.get_list_of_files_I_have() == [a]
    assert mb.get_slice(a, 0, 5) == None
    assert mb.get_slice(a, 0, 0) == ''
    assert mb.get_slice(a, 1, 2) == None
    assert mb.get_info() == [('test', a, [a], 0)]


