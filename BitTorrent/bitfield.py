# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bram Cohen, Uoti Urpala, and John Hoffman

try:
    sum([1])
    negsum = lambda a: len(a)-sum(a)
except:
    negsum = lambda a: reduce(lambda x,y: x+(not y), a, 0)
    
def _int_to_booleans(x):
    r = []
    for i in range(8):
        r.append(bool(x & 0x80))
        x <<= 1
    return tuple(r)

lookup_table = [_int_to_booleans(i) for i in range(256)]

reverse_lookup_table = {}
for i in xrange(256):
    reverse_lookup_table[lookup_table[i]] = chr(i)


class Bitfield(object):

    def __init__(self, length, bitstring = None):
        self.length = length
        if bitstring is not None:
            extra = len(bitstring) * 8 - length
            if extra < 0 or extra >= 8:
                raise ValueError
            t = lookup_table
            r = []
            for c in bitstring:
                r.extend(t[ord(c)])
            if extra > 0:
                if r[-extra:] != [0] * extra:
                    raise ValueError
                del r[-extra:]
            self.array = r
            self.numfalse = negsum(r)
        else:
            self.array = [False] * length
            self.numfalse = length

    def __setitem__(self, index, val):
        val = bool(val)
        self.numfalse += self.array[index]-val
        self.array[index] = val

    def __getitem__(self, index):
        return self.array[index]

    def __len__(self):
        return self.length

    def tostring(self):
        booleans = self.array
        t = reverse_lookup_table
        s = len(booleans) % 8
        r = [ t[tuple(booleans[x:x+8])] for x in xrange(0, len(booleans)-s, 8) ]
        if s:
            r += t[tuple(booleans[-s:] + ([0] * (8-s)))]
        return ''.join(r)

    def complete(self):
        return not self.numfalse
