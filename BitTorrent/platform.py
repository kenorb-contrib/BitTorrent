# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
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
import gettext
import locale
if os.name == 'nt':
    import win32api
    from win32com.shell import shellcon, shell
elif os.name == 'posix' and os.uname()[0] == 'Darwin':
    has_pyobjc = False
    try:
        from Foundation import NSBundle
        has_pyobjc = True
    except ImportError:
        pass
    
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
          (2, 5,  0): "2000",
          (2, 5,  1): "XP"  ,
          (2, 5,  2): "2003",
          }
    wv = sys.getwindowsversion()
    wk = (wv[3], wv[0], wv[1])
    if wh.has_key(wk):
        os_version = wh[wk]
    del wh, wv, wk
elif os_name == 'posix':
    os_version = os.uname()[0]

user_agent = "M" + version.replace('.', '-') + "--(%s/%s)" % (os_name, os_version)

def calc_unix_dirs():
    appdir = '%s-%s'%(app_name, version)
    ip = os.path.join('share', 'pixmaps', appdir)
    dp = os.path.join('share', 'doc'    , appdir)
    lp = os.path.join('share', 'locale')
    return ip, dp, lp

app_root = os.path.split(os.path.abspath(sys.argv[0]))[0]
doc_root = app_root
osx = False
if os.name == 'posix':
    if os.uname()[0] == "Darwin":
        doc_root = app_root = app_root.encode('utf8')
        if has_pyobjc:
            doc_root = NSBundle.mainBundle().resourcePath()
            osx = True
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

# a cross-platform way to get user's config directory
def get_config_dir():    
    shellvars = ['${APPDATA}', '${HOME}', '${USERPROFILE}']
    dir_root = get_dir_root(shellvars)

    if (dir_root is None) and (os.name == 'nt'):
        app_dir = get_shell_dir(shellcon.CSIDL_APPDATA)
        if app_dir is not None:
            dir_root = app_dir

    if dir_root is None and os.name == 'nt':
        tmp_dir_root = os.path.split(sys.executable)[0]
        if os.access(tmp_dir_root, os.R_OK|os.W_OK):
            dir_root = tmp_dir_root

    return dir_root

def get_cache_dir():
    dir = None
    if os.name == 'nt':
        dir = get_shell_dir(shellcon.CSIDL_INTERNET_CACHE)
    return dir

def get_home_dir():
    shellvars = ['${HOME}', '${USERPROFILE}']
    dir_root = get_dir_root(shellvars)

    if (dir_root is None) and (os.name == 'nt'):
        dir = get_shell_dir(shellcon.CSIDL_PROFILE)
        if dir is None:
            # there's no clear best fallback here
            # MS discourages you from writing directly in the home dir,
            # and sometimes (i.e. win98) there isn't one
            dir = get_shell_dir(shellcon.CSIDL_DESKTOPDIRECTORY)
            
        dir_root = dir

    return dir_root

def get_temp_dir():
    shellvars = ['${TMP}', '${TEMP}']
    dir_root = get_dir_root(shellvars, default_to_home=False)

    #this method is preferred to the envvars
    if os.name == 'nt':
        try_dir_root = win32api.GetTempPath()
        if try_dir_root is not None:
            dir_root = try_dir_root
    
    if dir_root is None:
        try_dir_root = None
        if os.name == 'nt':
            # this should basically never happen. GetTempPath always returns something
            try_dir_root = r'C:\WINDOWS\Temp'
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

# this function is the preferred way to get windows' paths
def get_shell_dir(value):
    dir = None
    if os.name == 'nt':
        try:
            dir = shell.SHGetFolderPath(0, value, 0, 0)
            dir = dir.encode('mbcs')
        except:
            pass
    return dir

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
        argstr = ' '.join(args[1:])
        # use ShellExecute instead of spawn*() because we don't want
        # handles (like the controlsocket) to be duplicated        
        win32api.ShellExecute(0, "open", args[0], argstr, None, 1) # 1 == SW_SHOW
    else:
        if os.access(path, os.X_OK):
            forkback = os.fork()
            if forkback == 0:
                if torrentqueue is not None:
                    #BUG: should we do this?
                    #torrentqueue.set_done()
                    torrentqueue.wrapped.controlsocket.close_socket()
                os.execl(path, *args)
        else:
            #BUG: what should we do here?
            pass
        

def _gettext_install(domain, localedir=None, languages=None, unicode=False):
    # gettext on win32 does not use locale.getdefaultlocale() by default
    # other os's will fall through and gettext.find() will do this task
    if os_name == 'nt':
        # this code is straight out of gettext.find()
        if languages is None:
            languages = []
            for envar in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
                val = os.environ.get(envar)
                if val:
                    languages = val.split(':')
                    break

            # this is the important addition - since win32 does not typically
            # have any enironment variable set, append the default locale before 'C'
            languages.append(locale.getdefaultlocale()[0])
            
            if 'C' not in languages:
                languages.append('C')

    # this code is straight out of gettext.install        
    t = gettext.translation(domain, localedir, languages=languages, fallback=True)
    t.install(unicode)


def language_path():
    config_dir = get_config_dir()
    lang_file_name = os.path.join(config_dir, '.bittorrent', 'data', 'language')
    return lang_file_name


def read_language_file():
    lang_file_name = language_path()
    lang = None
    if os.access(lang_file_name, os.F_OK|os.R_OK):
        mode = 'r'
        if sys.version_info >= (2, 3):
            mode = 'U'
        lang_file = open(lang_file_name, mode)
        lang_line = lang_file.readline()
        lang_file.close()
        if lang_line:
            lang = ''
            for i in lang_line[:5]:
                if not i.isalpha() and i != '_':
                    break
                lang += i
            if lang == '':
                lang = None
    return lang


def write_language_file(lang):
    lang_file_name = language_path()
    lang_file = open(lang_file_name, 'w')
    lang_file.write(lang)
    lang_file.close()


def install_translation():
    languages = None
    try:
        lang = read_language_file()
        if lang is not None:
            languages = [lang,]
    except:
        #pass
        from traceback import print_exc
        print_exc()
    _gettext_install('bittorrent', locale_root, languages=languages)
