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

# LaunchPath -- a cross platform way to "open," "launch," or "start"
# files and directories

# written by Matt Chisholm

import os
import sys

can_launch_dirs  = False
can_launch_files = False
posix_browsers = ('gnome-open','konqueror',)
posix_dir_browsers = ('gmc', 'gentoo',) # these only work on dirs
default_posix_browser = ''

def launchpath_nt(path):
    os.startfile(path)

def launchfile_nt(path):
    do_launchdir = True
    if can_launch_files and not os.path.isdir(path):
        f, ext = os.path.splitext(path)
        ext = ext.upper()
        path_ext = os.environ.get('PATH_EXT')
        blacklist = []
        if path_ext:
            blacklist = path_ext.split(';')
        if ext not in blacklist:
            try:
                launchpath_nt(path)
            except: # WindowsError
                pass
            else:
                do_launchdir = False
                
    if do_launchdir:
        p, f = os.path.split(path)
        launchdir(p)

def launchpath_mac(path):
    os.spawnlp(os.P_NOWAIT, 'open', 'open', path)

def launchpath_posix(path):
    if default_posix_browser:
        os.spawnlp(os.P_NOWAIT, default_posix_browser,
                   default_posix_browser, path)

def launchpath(path):
    pass

def launchdir(path):
    if can_launch_dirs and os.path.isdir(path):
        launchpath(path)

def launchfile(path):
    if can_launch_files and not os.path.isdir(path):
        launchpath(path)
    else:
        p, f = os.path.split(path)
        launchdir(p)

if os.name == 'nt':
    can_launch_dirs  = True
    can_launch_files = True
    launchpath = launchpath_nt
    launchfile = launchfile_nt
elif sys.platform == "darwin":
    can_launch_dirs  = True
    can_launch_files = True
    launchpath = launchpath_mac
elif os.name == 'posix':
    for b in posix_browsers:
        if os.system("which '%s' >/dev/null 2>&1" % b.replace("'","\\'")) == 0:
            can_launch_dirs  = True
            can_launch_files = True
            default_posix_browser = b
            launchpath = launchpath_posix
            break
    else:
        for b in posix_dir_browsers:
            can_launch_dirs = True
            default_posix_browser = b
            launchpath = launchpath_posix
            break

