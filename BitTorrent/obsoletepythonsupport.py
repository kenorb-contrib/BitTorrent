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

from __future__ import generators

import sys
if sys.version_info < (2, 3):
    # Allow int() to create numbers larger than "small ints".
    # This is NOT SAFE if int is used as the name of the type instead
    # (as in "type(x) in (int, long)").
    int = long

    def enumerate(x):
        i = 0
        for y in x:
            yield (i, y)
            i += 1

    def sum(seq):
        r = 0
        for x in seq:
            r += x
        return r

del sys
