# Written by Bram Cohen, Uoti Urpala, and John Hoffman
# see LICENSE.txt for license information

from array import array
counts = [sum([(i >> j) & 1 for j in xrange(8)]) for i in xrange(256)]

class Bitfield:
    def __init__(self, length, bitstring = None):
        self.length = length
        rlen, extra = divmod(length, 8)
        if bitstring is None:
            self.numfalse = length
            if extra:
                self.bits = array('B', chr(0) * (rlen + 1))
            else:
                self.bits = array('B', chr(0) * rlen)
        else:
            if extra:
                if len(bitstring) != rlen + 1:
                    raise ValueError
                if (ord(bitstring[-1]) << extra) & 0xFF != 0:
                    raise ValueError
            else:
                if len(bitstring) != rlen:
                    raise ValueError
            c = counts
            self.numfalse = length - sum([c[ord(i)] for i in bitstring])
            if self.numfalse != 0:
                self.bits = array('B', bitstring)
            else:
                self.bits = None

    def __setitem__(self, index, val):
        assert val == 1
        if self[index]:
            return
        a, b = divmod(index, 8)
        self.bits[a] |= (1 << (7 - b))
        self.numfalse -= 1
        if self.numfalse == 0:
            self.bits = None

    def __getitem__(self, index):
        if self.bits is None:
            return 1
        a, b = divmod(index, 8)
        return (self.bits[a] >> (7 - b)) & 1

    def tostring(self):
        if self.bits is None:
            rlen, extra = divmod(self.length, 8)
            r = chr(0xFF) * rlen
            if extra:
                r += chr((0xFF << (8 - extra)) & 0xFF)
            return r
        else:
            return self.bits.tostring()

def test_bitfield():
    try:
        x = Bitfield(7, 'ab')
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(7, 'ab')
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(9, 'abc')
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(0, 'a')
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(1, '')
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(7, '')
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(8, '')
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(9, 'a')
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(7, chr(1))
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(9, chr(0) + chr(0x40))
        assert False
    except ValueError:
        pass
    assert Bitfield(0, '').tostring() == ''
    assert Bitfield(1, chr(0x80)).tostring() == chr(0x80)
    assert Bitfield(7, chr(0x02)).tostring() == chr(0x02)
    assert Bitfield(8, chr(0xFF)).tostring() == chr(0xFF)
    assert Bitfield(9, chr(0) + chr(0x80)).tostring() == chr(0) + chr(0x80)
    x = Bitfield(1)
    assert x.numfalse == 1
    x[0] = 1
    assert x.numfalse == 0
    x[0] = 1
    assert x.numfalse == 0
    assert x.tostring() == chr(0x80)
    x = Bitfield(7)
    x[6] = 1
    assert x.numfalse == 6
    assert x.tostring() == chr(0x02)
    x = Bitfield(8)
    x[7] = 1
    assert x.tostring() == chr(1)
    x = Bitfield(9)
    x[8] = 1
    assert x.numfalse == 8
    assert x.tostring() == chr(0) + chr(0x80)
    x = Bitfield(8, chr(0xC4))
    assert x.numfalse == 5
    assert x.tostring() == chr(0xC4)

def _int_to_booleans(x):
    r = []
    for i in range(8):
        if x & 0x80:
            r.append(True)
        else:
            r.append(False)
        x <<= 1
    return tuple(r)

lookup_table = [_int_to_booleans(i) for i in range(256)]

reverse_lookup_table = {}
for i in xrange(256):
    reverse_lookup_table[lookup_table[i]] = chr(i)

def booleans_to_bitfield(booleans):
    t = reverse_lookup_table
    s = len(booleans) % 8
    r = ''.join([t[tuple(booleans[x:x+8])] for x in xrange(0, len(booleans) - s, 8)])
    if s:
        r += t[tuple(booleans[-s:] + ([0] * (8-s)))]
    return r

def bitfield_to_booleans(bitfield, l):
    extra = len(bitfield) * 8 - l
    if extra < 0 or extra >= 8:
        return None
    t = lookup_table
    r = []
    for c in bitfield:
        r.extend(t[ord(c)])
    if extra > 0:
        if r[-extra:] != [0] * extra:
            return None
        del r[-extra:]
    return r

def test_basic():
    x = [1, 1, 1, 0, 0, 0, 1, 1, 1]
    y = [1, 1, 1, 0, 0, 0, 1, 1]
    for a in [x, y, []]:
        assert bitfield_to_booleans(booleans_to_bitfield(a), len(a)) == a

def test_too_long():
    assert bitfield_to_booleans('ab', 8) == None
    
def test_too_short():
    assert bitfield_to_booleans('a', 9) == None
    
def test_nonzero_in_excess():
    assert bitfield_to_booleans(chr(0xFF), 7) == None 

