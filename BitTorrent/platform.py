# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Matt Chisholm and Uoti Urpala

# This module is strictly for cross platform compatibility items and
# should not import anything from other BitTorrent modules.

import os
import re
import sys
import time

from BitTorrent import app_name, version

if sys.platform.startswith('win'):
    bttime = time.clock
else:
    bttime = time.time

is_frozen_exe = (os.name == 'nt') and hasattr(sys, 'frozen') and (sys.frozen == 'windows_exe')

os_name = os.name
os_version = None
if os_name == 'nt':
    wh = {(1, 4,  0): "95",
          (1, 4, 10): "98",
          (1, 4, 90): "ME",
          (2, 4,  0): "NT",
          (2, 5,  0): "2K",
          (2, 5,  1): "XP"}
    wv = sys.getwindowsversion()
    os_version = wh[(wv[3], wv[0], wv[1])]
    del wh, wv

def calc_unix_dirs():
    appdir = '%s-%s'%(app_name, version)
    ip = os.path.join('share', 'pixmaps', appdir)
    dp = os.path.join('share', 'doc'    , appdir)
    lp = os.path.join('share', 'locale')
    return ip, dp, lp

app_root = os.path.split(os.path.abspath(sys.argv[0]))[0]
if os.name == 'posix':
    if os.uname()[0] == "Darwin":
        app_root = app_root.encode('utf8')
doc_root = app_root
image_root  = os.path.join(app_root, 'images')
locale_root = os.path.join(app_root, 'locale')

if not os.access(image_root, os.F_OK) or not os.access(locale_root, os.F_OK):
    # we guess that probably we are installed on *nix in this case
    # (I have no idea whether this is right or not -- matt)
    if app_root[-4:] == '/bin':
        # yep, installed on *nix
        installed_prefix = app_root[:-4]
        image_root, doc_root, locale_root = map(
            lambda p: os.path.join(installed_prefix, p), calc_unix_dirs()
            )


# a cross-platform way to get user's home, config, and temp directories
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

def get_temp_dir():
    shellvars = ['${TMP}', '${TEMP}']
    dir_root = get_dir_root(shellvars, default_to_home=False)
    if dir_root is None:
        try_dir_root = None
        if os.name == 'nt':
            try_dir_root = r'C:\WINDOWS\TEMP'
        elif os.name == 'posix':
            try_dir_root = '/tmp'
        if (try_dir_root is not None and
            os.path.isdir(try_dir_root) and
            os.access(try_dir_root, os.R_OK|os.W_OK)):
            dir_root = try_dir_root
    return dir_root

def get_dir_root(shellvars, default_to_home=True):
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
        if default_to_home:
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

def spawn(torrentqueue, cmd, *args):
    ext = ''
    if is_frozen_exe:
        ext = '.exe'
    path = os.path.join(app_root,cmd+ext)
    if not os.access(path, os.F_OK):
        if os.access(path+'.py', os.F_OK):
            path = path+'.py'
    args = [path] + list(args) # $0
    if os.name == 'nt':
        # do proper argument quoting since exec/spawn on Windows doesn't
        args = ['"%s"'%a.replace('"', '\"') for a in args]
        if len(args) == 1:
            os.startfile(args[0])
        else:
            # Note: if you get "OSError [Errno 8] Exec format error"
            # on win32 here, it means you haven't set up your python
            # files to be executable, but this should still work after
            # building an exe with pygtk.
            # P_NOWAIT, P_NOWAITO, P_DETACH all behave the same
            pid = os.spawnl(os.P_NOWAIT, path, *args)
    else:
        forkback = os.fork()
        if forkback == 0:
            if torrentqueue is not None:
                #BUG: should we do this?
                #torrentqueue.set_done()
                torrentqueue.wrapped.controlsocket.close_socket()
            pid = os.execl(path, *args)

