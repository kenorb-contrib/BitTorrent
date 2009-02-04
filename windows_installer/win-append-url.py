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
import os
app_name = "BitTorrent"
from BitTorrent import version
from BitTorrent.NewVersion import Version

currentversion = Version.from_str(version)
version_str = version
if currentversion.is_beta():
    version_str = version_str + '-Beta'

max_url_len = 2048
default_url = ""
filename = "%s-%s.exe" % (app_name, version_str)

if len(sys.argv) > 1:
    default_url = sys.argv[1]

f = open(filename, 'ab')
try:
    f.write(default_url)
    f.write(' ' * (max_url_len - len(default_url)))
finally:
    f.close()
