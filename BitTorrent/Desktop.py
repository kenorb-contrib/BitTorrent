# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# written by Matt Chisholm

import os
import sys

from BitTorrent.platform import get_home_dir, get_shell_dir
if os.name == 'nt':
    from win32com.shell import shellcon
    
desktop = None

if os.name == 'nt':
    desktop = get_shell_dir(shellcon.CSIDL_DESKTOPDIRECTORY)
else:
    homedir = get_home_dir()
    if homedir == None :
        desktop = '/tmp/'
    else:
        desktop = homedir
        if os.name in ('mac', 'posix'):
            tmp_desktop = os.path.join(homedir, 'Desktop')
            if os.access(tmp_desktop, os.R_OK|os.W_OK):
                desktop = tmp_desktop + os.sep
