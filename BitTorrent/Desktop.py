# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
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

from __init__ import get_home_dir, get_registry_dir

desktop = None

homedir = get_home_dir()
if homedir == None :
    if os.name == 'nt':
        desktop = os.path.splitdrive(sys.executable)[0]
        if desktop[-1] != os.sep:
            desktop += os.sep

        reg_dir = get_registry_dir('Desktop')
        if reg_dir is not None:
            desktop = reg_dir
        else:
            tmp_desktop = os.path.join(desktop, 'WINDOWS', 'Desktop')
            if os.access(tmp_desktop, os.R_OK|os.W_OK):
                desktop = tmp_desktop
    else:
        desktop = '/tmp/'

else:
    desktop = homedir
    if os.name in ('mac', 'posix', 'nt'):

        tmp_desktop = os.path.join(homedir, 'Desktop')
        if os.access(tmp_desktop, os.R_OK|os.W_OK):
            desktop = tmp_desktop + os.sep

            reg_dir = get_registry_dir('Desktop')
            if reg_dir is not None:
                desktop = reg_dir
