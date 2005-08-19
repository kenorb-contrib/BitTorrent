# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

app_name = 'BitTorrent'
version = '4.1.4'

URL = 'http://www.bittorrent.com/'
DONATE_URL = URL + 'donate.html'
FAQ_URL = URL + 'FAQ.html'
HELP_URL = URL + 'documentation.html'
SEARCH_URL = 'http://search.bittorrent.com/search.jsp?query=%s'

import sys
assert sys.version_info >= (2, 2, 1), _("Python 2.2.1 or newer required")
import os

from BitTorrent.platform import get_home_dir, is_frozen_exe

languages = 'af,ar,bg,cs,da,de,es,es_MX,et,fi,fr,gr,he_IL,hr,hu,it,ja,ko,lt,ms,nl,nb_NO,pl,pt,pt_BR,ro,ru,sk,sl,sq,sv,tr,vi,zh_CN,zh_TW'.split(',')

if os.name == 'posix':
    if os.uname()[0] == "Darwin":
        import gettext
        gettext.install('bittorrent', 'locale')
    

# hackery to get around bug in py2exe that tries to write log files to
# application directories, which may not be writable by non-admin users
if is_frozen_exe:
    baseclass = sys.stderr.__class__
    class Stderr(baseclass):
        logroot = get_home_dir()
        if logroot is None:
            logroot = os.path.splitdrive(sys.executable)[0]
            if logroot[-1] != os.sep:
                logroot += os.sep
        logname = os.path.splitext(os.path.split(sys.executable)[1])[0] + '_errors.log'
        logpath = os.path.join(logroot, logname)
        def write(self, text, alert=None, fname=logpath):
            if 'GtkWarning' not in text:
                baseclass.write(self, text, fname=fname)
    sys.stderr = Stderr()

del sys, get_home_dir, is_frozen_exe

INFO = 0
WARNING = 1
ERROR = 2
CRITICAL = 3

class BTFailure(Exception):
    pass

class BTShutdown(BTFailure):
    pass

