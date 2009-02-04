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
import codecs

# we do this first, since BitTorrent/__init__.py installs a stderr proxy.

# py2exe'd Blackholes don't have encoding
encoding = getattr(sys.stdout, "encoding", None) 
# and sometimes encoding is None anyway
if encoding is not None:
    stdout_writer = codecs.getwriter(encoding)
    # don't fail if we can't write a value in the sydout encoding
    sys.stdout = stdout_writer(sys.stdout, 'replace')
    stderr_writer = codecs.getwriter(encoding)
    sys.stderr = stderr_writer(sys.stderr, 'replace')

from BitTorrent.platform import install_translation
install_translation(unicode=True)
_ = _ # not a typo
