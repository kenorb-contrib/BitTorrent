# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

app_name = "BitTorrent"
version = '4.0.2'

URL = 'http://www.bittorrent.com/'
DONATE_URL = URL + 'donate.html'
FAQ_URL = URL + 'FAQ.html'
HELP_URL = URL + 'documentation.html'

import sys
assert sys.version_info >= (2, 2, 1), "Python 2.2.1 or newer required"
import os
import re

def calc_unix_dirs():
    appdir = '%s-%s'%(app_name, version)
    ip = os.path.join('share', 'pixmaps', appdir)
    dp = os.path.join('share', 'doc'    , appdir)
    return ip, dp

app_root = os.path.split(os.path.abspath(sys.argv[0]))[0]
image_root = os.path.join(app_root, 'images')
doc_root = app_root

if not os.access(image_root, os.F_OK):
    # probably we are installed on *nix
    # I have no idea whether this is right or not
    if app_root[-4:] == '/bin':
        # yep, installed on *nix
        installed_prefix = app_root[:-4]
        image_root, doc_root = map(
            lambda p: os.path.join(installed_prefix, p), calc_unix_dirs()
            )


# a cross-platform way to get user's home directory
def get_config_dir():
    shellvars = ['${APPDATA}', '${HOME}', '${USERPROFILE}']
    dir_root = get_dir_root(shellvars)
    if dir_root is None:
        reg_dir = get_registry_dir('AppData')
        if reg_dir is not None:
            dir_root = reg_dir
    return dir_root

def get_home_dir():
    shellvars = ['${HOME}', '${USERPROFILE}']
    dir_root = get_dir_root(shellvars)
    return dir_root

def get_dir_root(shellvars):
    def check_sysvars(x):
        y = os.path.expandvars(x)
        if y != x and os.path.isdir(y):
            return y
        return None

    dir_root = None
    for d in shellvars:
        dir_root = check_sysvars(d)
        if dir_root is not None:
            break
    else:
        dir_root = os.path.expanduser('~')
        if dir_root == '~' or not os.path.isdir(dir_root):
            dir_root = None
    return dir_root


def get_registry_dir(value):
    reg_dir = None 

    find_pat = re.compile('%([A-Z_]+)%')
    repl_pat = '${\\1}'
    
    if os.name == 'nt':
        #from win32com.shell import shell, shellcon
        #desktop = shell.SHGetPathFromIDList(shell.SHGetSpecialFolderLocation(0, shellcon.CSIDL_DESKTOPDIRECTORY))
        import _winreg as wreg
        try: 
            key = wreg.OpenKey(wreg.HKEY_CURRENT_USER,
                               r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders')
            d = wreg.QueryValueEx(key, value)
            reg_dir, a_random_number = os.path.expandvars(d)
            reg_dir = find_pat.sub(repl_pat, reg_dir)
            reg_dir = os.path.expandvars(reg_dir)
            reg_dir = reg_dir.encode('mbcs')
        except Exception, e:
            pass

        if reg_dir is not None and os.access(reg_dir, os.R_OK|os.W_OK):
            pass
        else:
            reg_dir = None
    return reg_dir

def path_wrap(path):
    return path

if os.name == 'nt':
    def path_wrap(path):
        return path.decode('mbcs').encode('utf-8')


is_frozen_exe = (os.name == 'nt') and hasattr(sys, 'frozen') and (sys.frozen == 'windows_exe')

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

del sys

INFO = 0
WARNING = 1
ERROR = 2
CRITICAL = 3

class BTFailure(Exception):
    pass

class BTShutdown(BTFailure):
    pass
