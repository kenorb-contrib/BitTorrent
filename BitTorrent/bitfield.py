# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Written by Bram Cohen, Uoti Urpala, and John Hoffman

from array import array

from BitTorrent.obsoletepythonsupport import *

counts = [chr(sum([(i >> j) & 1 for j in xrange(8)])) for i in xrange(256)]
counts = ''.join(counts)


class Bitfield:

    def __init__(self, length, bitstring=None):
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
            self.numfalse = length - sum(array('B',
                                               bitstring.translate(counts)))
            if self.numfalse != 0:
                self.bits = array('B', bitstring)
            else:
                self.bits = None

    def __setitem__(self, index, val):
        assert val
        pos = index >> 3
        mask = 128 >> (index & 7)
        if self.bits[pos] & mask:
            return
        self.bits[pos] |= mask
        self.numfalse -= 1
        if self.numfalse == 0:
            self.bits = None

    def __getitem__(self, index):
        bits = self.bits
        if bits is None:
            return 1
        return bits[index >> 3] & 128 >> (index & 7)

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
