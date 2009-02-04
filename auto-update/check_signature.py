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

from common import sig_ext, pub_key_path

import sys
import pickle
from sha import sha

public_key_file = open(pub_key_path, 'rb')

public_key = pickle.load(public_key_file)

for f in sys.argv[1:]:
    c = open(f, 'rb').read()
    h = sha(c).digest()
    signature = pickle.load(open(f+sig_ext, 'rb'))
    print f, ':',
    if public_key.verify(h, signature):
        print 'success!'
    else:
        print 'fail!'

