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

# written by Matt Chisholm

import os

from __init__ import get_home_dir

desktop = None

homedir = get_home_dir()
if homedir == None :
    if os.name == 'nt':
        desktop = 'C:\\'
    else:
        desktop = '/tmp/'

else:
    desktop = homedir
    if os.name in ('mac', 'posix', 'nt'):

        tmp_desktop = os.path.join(homedir, 'Desktop')
        if os.access(tmp_desktop, os.R_OK|os.W_OK):
            desktop = tmp_desktop + os.sep

        if os.name == 'nt':
            #from win32com.shell import shell, shellcon
            #desktop = shell.SHGetPathFromIDList(shell.SHGetSpecialFolderLocation(0, shellcon.CSIDL_DESKTOPDIRECTORY))
            reg_desktop = None
            import _winreg as wreg
            try: 
                key = wreg.OpenKey(wreg.HKEY_CURRENT_USER,
                               r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders')
                d = wreg.QueryValueEx(key, 'Desktop')
                reg_desktop = os.path.expandvars(d, os.environ)
            except:
                pass

            if reg_desktop is not None and os.access(reg_desktop, os.R_OK|os.W_OK):
                desktop = reg_desktop
