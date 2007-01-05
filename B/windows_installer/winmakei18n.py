# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

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




    
