# Written by Bram Cohen
# see LICENSE.txt for license information

from sha import sha
from bencode import bencode, bdecode
from btemplate import compile_template, st, ListMarker
from SingleBlob import make_indices
from types import StringType
true = 1
false = 0

def len20(s, verbose):
    if type(s) != StringType or len(s) != 20:
        raise ValueError

info_template = compile_template({'version': '1.0', 'file name': st,
    'file length': 0, 'pieces': ListMarker(len20),
    'piece length': 1})

class MultiBlob:
    def __init__(self, blobs, piece_length, open, getsize, exists, 
            split, time, isfile):
        self.open = open
        # blob: (file, begin, end)
        self.blobs = {}
        # name, hash, [pieces], length
        self.info = []
        for file in blobs:
            if not exists(file):
                raise ValueError, file + ' does not exist'
            if not isfile(file):
                raise ValueError, file + ' is not a file'
            filetail = split(file)[1]
            metafile = file + '.btinfo'
            if exists(metafile):
                h = open(metafile, 'rb')
                v = h.read()
                h.close()
                try:
                    v = bdecode(v)
                    info_template(v)
                    if v['file name'] != filetail:
                        raise ValueError, 'wrong file name, got ' + v['file name']
                    c = true
                    if v['file length'] != getsize(file):
                        raise ValueError, 'file has wrong length'
                    indices = make_indices(v['pieces'], piece_length, 
                        v['file length'])
                    for (blob, vs) in indices.items():
                        begin, end = vs[0]
                        self.blobs[blob] = (file, begin, end)
                    self.info.append((filetail, 
                        v['pieces'], v['file length']))
                except ValueError, e:
                    raise ValueError, 'error in ' + metafile + ' - ' + str(e)
                if c:
                    continue
            pieces = []
            len = getsize(file)
            h = open(file, 'rb')
            i = 0
            while i + piece_length < len:
                block = h.read(piece_length)
                piece = sha(block).digest()
                pieces.append(piece)
                self.blobs[piece] = (file, i, i + piece_length)
                i += piece_length
            block = h.read(len - i)
            piece = sha(block).digest()
            pieces.append(piece)
            self.blobs[piece] = (file, i, len)
            h.close()
            self.info.append((filetail, pieces, len))
            
            h = open(metafile, 'wb')
            h.write(bencode({'version': '1.0', 'file name': filetail, 
                'file length': len, 
                'piece length': piece_length, 'pieces': pieces}))
            h.close()

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
        
    def get_list_of_blobs_I_have(self):
        return self.blobs.keys()

from fakeopen import FakeOpen

def test_long_file():
    s = 'abc' * 5
    a = sha(s[:10]).digest()
    b = sha(s[10:]).digest()
    fo = FakeOpen({'test': s})
    mb = MultiBlob(['test'], 10, fo.open, fo.getsize, fo.exists, 
        lambda x: ('', x), lambda: 0, lambda x: true)
    x = mb.get_list_of_blobs_I_have()
    assert x == [a, b] or x == [b, a]
    assert mb.get_slice(a, 0, 5) == s[:5]
    assert mb.get_slice(a, 5, 5) == s[5:10]
    assert mb.get_slice(a, 5, 20) == None
    assert mb.get_slice(b, 0, 2) == s[10:12]
    assert mb.get_slice(b, 4, 1) == s[14:]
    assert mb.get_slice(b, 4, 3) == None
    assert mb.get_slice(chr(0) * 20, 0, 2) == None
    assert mb.get_info() == [('test', [a, b], 15)]

def test_resurrected():
    s = 'abc' * 5
    a = sha(s[:10]).digest()
    b = sha(s[10:]).digest()
    fo = FakeOpen({'test': s})
    mb = MultiBlob(['test'], 10, fo.open, fo.getsize, fo.exists, 
        lambda x: ('', x), lambda: 0, lambda x: true)
    mb = MultiBlob(['test'], 10, fo.open, fo.getsize, fo.exists, 
        lambda x: ('', x), lambda: 0, lambda x: true)
    x = mb.get_list_of_blobs_I_have()
    assert x == [a, b] or x == [b, a]
    assert mb.get_slice(a, 0, 5) == s[:5]
    assert mb.get_slice(a, 5, 5) == s[5:10]
    assert mb.get_slice(a, 5, 20) == None
    assert mb.get_slice(b, 0, 2) == s[10:12]
    assert mb.get_slice(b, 4, 1) == s[14:]
    assert mb.get_slice(b, 4, 3) == None
    assert mb.get_slice(chr(0) * 20, 0, 2) == None
    assert mb.get_info() == [('test', [a, b], 15)]

def test_even():
    s = 'abcd' * 5
    a = sha(s[:10]).digest()
    b = sha(s[10:]).digest()
    fo = FakeOpen({'test': s})
    mb = MultiBlob(['test'], 10, fo.open, fo.getsize, fo.exists, 
        lambda x: ('', x), lambda: 0, lambda x: true)
    x = mb.get_list_of_blobs_I_have()
    assert x == [a, b] or x == [b, a]
    assert mb.get_slice(a, 0, 5) == s[:5]
    assert mb.get_slice(a, 5, 5) == s[5:10]
    assert mb.get_slice(a, 5, 20) == None
    assert mb.get_slice(b, 0, 2) == s[10:12]
    assert mb.get_slice(b, 4, 6) == s[14:]
    assert mb.get_info() == [('test', [a, b], 20)]

def test_short():
    s = 'abc' * 2
    a = sha(s).digest()
    fo = FakeOpen({'test': s})
    mb = MultiBlob(['test'], 10, fo.open, fo.getsize, fo.exists, 
        lambda x: ('', x), lambda: 0, lambda x: true)
    assert mb.get_list_of_blobs_I_have() == [a]
    assert mb.get_slice(a, 0, 5) == s[:5]
    assert mb.get_slice(a, 5, 1) == s[5:]
    assert mb.get_slice(a, 5, 20) == None
    assert mb.get_slice(a, 2, 1) == s[2:3]
    assert mb.get_info() == [('test', [a], 6)]

def test_null():
    s = ''
    a = sha(s).digest()
    fo = FakeOpen({'test': s})
    mb = MultiBlob(['test'], 10, fo.open, fo.getsize, fo.exists, 
        lambda x: ('', x), lambda: 0, lambda x: true)
    assert mb.get_list_of_blobs_I_have() == [a]
    assert mb.get_slice(a, 0, 5) == None
    assert mb.get_slice(a, 0, 0) == ''
    assert mb.get_slice(a, 1, 2) == None
    assert mb.get_info() == [('test', [a], 0)]


