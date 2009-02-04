#!/usr/bin/env python

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

import sys
from common import pub_key_path, pri_key_path

try:
    from Crypto.PublicKey import _fastmath
except ImportError:
    _fastmath = None

if _fastmath is not None:
    raise SystemError("Bug in DSA implementation.  Please generate a "
                      "key using a python installation that does not "
                      "provide the Crypto.PublicKey._fastmath module.")

import pickle
from Crypto.PublicKey import DSA as pklib
from Crypto.Util import randpool

r = randpool.KeyboardRandomPool()
r.randomize()

pub_key_file = open(pub_key_path, 'wb')
pri_key_file = open(pri_key_path, 'wb')

r.add_event()
key = pklib.generate(2**10, r.get_bytes)

pickle.dump(key            , pri_key_file, protocol=2)
pickle.dump(key.publickey(), pub_key_file, protocol=2)








