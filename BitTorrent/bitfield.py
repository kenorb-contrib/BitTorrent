# Written by Bram Cohen, Uoti Urpala, and John Hoffman
# see LICENSE.txt for license information

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

