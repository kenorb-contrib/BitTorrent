# -*- coding: UTF-8 -*-
# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

app_name = 'BitTorrent'
version = '4.4.0'

URL = 'http://www.bittorrent.com/'
DONATE_URL = URL + 'donate.html'
FAQ_URL = URL + 'FAQ.html'
HELP_URL = URL + 'documentation.html'
SEARCH_URL = 'http://search.bittorrent.com/search.jsp?client=%(client)s&query=%(query)s'

import sys
assert sys.version_info >= (2, 2, 1), _("Python %s or newer required") % '2.2.1'
import os
import time

branch = None
if os.access('.cdv', os.F_OK):
    branch = os.path.split(os.path.realpath(os.path.split(sys.argv[0])[0]))[1]

from BitTorrent.language import languages, language_names
from BitTorrent.platform import get_home_dir, is_frozen_exe

if os.name == 'posix':
    if os.uname()[0] == "Darwin":
        from BitTorrent.platform import install_translation
        install_translation()

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

        def __init__(self):        
            self.just_wrote_newline = True
        
        def write(self, text, alert=None, fname=logpath):
            output = text

            if self.just_wrote_newline and not text.startswith('[%s ' % version):
                output = '[%s %s] %s' % (version, time.strftime('%Y-%m-%d %H:%M:%S'), text)
                
            if 'GtkWarning' not in text:
                baseclass.write(self, output, fname=fname)

            if output[-1] == '\n':
                self.just_wrote_newline = True
            else:
                self.just_wrote_newline = False
                
    sys.stderr = Stderr()

del sys, get_home_dir, is_frozen_exe

INFO = 0
WARNING = 1
ERROR = 2
CRITICAL = 3

status_dict = {INFO: 'info',
               WARNING: 'warning',
               ERROR: 'error',
               CRITICAL: 'critical'}

class BTFailure(Exception):
    pass
        
class BTShutdown(BTFailure):
    pass

