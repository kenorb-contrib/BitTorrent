# Written by Bram Cohen
# see LICENSE.txt for license information

false = 0
true = 1

def _int_to_booleans(x):
    r = []
    for i in range(8):
        if x & 0x80:
            r.append(true)
        else:
            r.append(false)
        x <<= 1
    return tuple(r)

# lookup table
TBL = [_int_to_booleans(i) for i in range(256)]


def booleans_to_bitfield(booleans):
    r = [None] * ((len(booleans) + 7) // 8)
    p = 0x80
    v = 0
    pos = 0
    for b in booleans:
        if b:
            v |= p
        p >>= 1
        if not p:
            r[pos] = chr(v)
            pos += 1
            v = 0
            p = 0x80
    if p != 0x80:
        r[pos] = chr(v)
    return ''.join(r)


def bitfield_to_booleans(bitfield, l):
    extra = len(bitfield) * 8 - l
    if extra < 0 or extra >= 8:
        return None
    r = []
    t = TBL
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

