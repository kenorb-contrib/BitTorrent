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

from common import sig_ext, pri_key_path

import sys
import time 
import pickle
from sha import sha
from Crypto.Util import randpool

r = randpool.KeyboardRandomPool()
r.randomize()

private_key_file = open(pri_key_path, 'rb')

key = pickle.load(private_key_file)

for f in sys.argv[1:]:
    c = open(f, 'rb').read()
    h = sha(c).digest()
    r.add_event()
    signature = key.sign(h, r.get_bytes(2**4))
    if key.verify(h, signature):
        signature_file = open(f+sig_ext, 'wb')
        pickle.dump(signature, signature_file, protocol=2)

