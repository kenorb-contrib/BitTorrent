# Written by Bram Cohen
# see LICENSE.txt for license information

def booleans_to_bitfield(booleans):
    r = []
    for i in xrange(0, len(booleans), 8):
        v = 0
        p = 0x80
        for j in booleans[i:i+8]:
            if j:
                v |= p
            p >>= 1
        r.append(chr(v))
    return ''.join(r)
booga booga
def bitfield_to_booleans(bitfield, l):
    extra = len(bitfield) * 8 - l
    if extra < 0 or extra >= 8:
        return None
    r = []
    for c in bitfield:
        v = ord(c)
        for i in xrange(8):
            if v & 0x80 != 0:
                r.append(True)
            else:
                r.append(False)
            v <<= 1
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

