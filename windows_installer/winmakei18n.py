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

# Written by Matt Chisholm

import os
import sys
from BitTorrent import languages, language_names
GNUWIN_BIN = r'C:\Program Files\GnuWin32\bin'

if os.name != 'nt':
    print "This script is only for use on Win32. Use makei18n.sh to regenerate locales on a Unix OS."
    sys.exit()

for l in languages:
    print l
    #os.system(r'"%s\msgmerge.exe" --no-fuzzy-matching po\%s.po messages.po > locale\%s\LC_MESSAGES\messages.po' % (GNUWIN_BIN,l,l))
    path = 'locale\%s\LC_MESSAGES' % l
    if not os.access(path, os.F_OK):
        os.system('mkdir %s' % path)
    if not os.path.exists(r'po\%s.po' % (l)):
        print r'Warning: po\%s.po does not exist.' % (l)
    else:
        os.system(r'copy po\%s.po %s\bittorrent.po' % (l, path))
        os.system(r'"%s\msgfmt.exe" -o %s\bittorrent.mo %s\bittorrent.po' % (GNUWIN_BIN, path, path))
        os.remove(r'%s\bittorrent.po' % (path,))




    
