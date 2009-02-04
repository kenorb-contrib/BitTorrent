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

# Written by Greg Hazel
# based on code by Matt Chisholm

import os
from BitTorrent import version

def make_id():
    myid = 'M' + version.split()[0].replace('.', '-')
    padded = myid[:8] + '-' * (8 - len(myid))
    myid = padded + os.urandom(6).encode('hex')
    return myid
