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

import os

can_open_files = False
posix_browsers = ('gnome-open','konqueror',) #gmc, gentoo only work on dirs
default_posix_browser = ''

def openpath_nt(path):
    os.startfile(path)

def openpath_mac(path):
    # BUG: this is untested
    os.spawnlp(os.P_NOWAIT, 'open', 'open', path)

def openpath_posix(path):
    if default_posix_browser:
        os.spawnlp(os.P_NOWAIT, default_posix_browser,
                   default_posix_browser, path)

def openpath(path):
    pass

def opendir(path):
    if os.path.isdir(path):
        openpath(path)

if os.name == 'nt':
    can_open_files = True
    openpath = openpath_nt
elif os.name == 'mac':
    can_open_files = True
    openpath = openpath_mac
elif os.name == 'posix':
    for b in posix_browsers:
        if os.system('which %s >/dev/null'%b) == 0:
            can_open_files = True
            default_posix_browser = b
            openpath = openpath_posix
            break

