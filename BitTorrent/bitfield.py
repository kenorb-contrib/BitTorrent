# Written by Bram Cohen
# see LICENSE.txt for license information

from array import array
counts = [sum([(i >> j) & 1 for j in xrange(8)]) for i in xrange(256)]

class Bitfield:
    def __init__(self, length, bitstring = None):
        self.length = length
        rlen, extra = divmod(length, 8)
        if extra:
            rlen += 1
        if bitstring is None:
            self.numfalse = length
            self.bits = array('B', chr(0) * rlen)
        else:
            if len(bitstring) != rlen:
                raise ValueError
            if extra:
                if (ord(bitstring[-1]) << extra) & 0xFF != 0:
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

    def __len__(self):
        return self.length

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
    assert len(x) == 7
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
    assert len(x) == 8
    assert x.numfalse == 5
    assert x.tostring() == chr(0xC4)
