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
import pickle
import zurllib
import BitTorrent.stackthreading as threading
import logging
from BitTorrent.hash import sha
from BitTorrent.translation import _

DEBUG = False

from BitTorrent import BTFailure, version, app_name
from BitTorrent import GetTorrent
from BitTorrent.bencode import bdecode, bencode
from BitTorrent.platform import os_version, spawn, get_temp_dir, doc_root, is_frozen_exe, osx
from BitTorrent.ConvertedMetainfo import ConvertedMetainfo


if osx:
    from Foundation import NSAutoreleasePool
    
if is_frozen_exe or DEBUG:
    # needed for py2exe to include the public key lib
    from Crypto.PublicKey import DSA

version_host = 'http://version.bittorrent.com/'
download_url = 'http://www.bittorrent.com/download.html'

# based on Version() class from ShellTools package by Matt Chisholm,
# used with permission
class Version(list):
    def __str__(self):
        return '.'.join(map(str, self))

    def is_beta(self):
        return self[1] % 2 == 1

    def from_str(self, text):
        return Version( [int(t) for t in text.split('.')] )

    def name(self):
        if self.is_beta():
            return 'beta'
        else:
            return 'stable'
    
    from_str = classmethod(from_str)

currentversion = Version.from_str(version)

availableversion = None

class Updater(object):
    def __init__(self, threadwrap, newversionfunc, startfunc, installfunc,
                 errorfunc, test_new_version='', test_current_version=''):
        self.threadwrap     = threadwrap  # for calling back to UI from thread
        self.newversionfunc = newversionfunc # alert to new version UI function
        self.startfunc      = startfunc   # start torrent UI function
        self.installfunc    = installfunc # install torrent UI function
        self.errorfunc      = errorfunc   # report error UI function
        self.infohash = None
        self.version = currentversion
        self.currentversion = currentversion
        self.asked_for_install = False
        self.version_site = version_host
        if os.name == 'nt':
            self.version_site += 'win32/'
            if os_version not in ('XP', '2000', '2003'):
                self.version_site += 'legacy/'
        elif osx:
            self.version_site += 'osx/'
        self.debug_mode = DEBUG
        if test_new_version:
            test_new_version = Version.from_str(test_new_version)
            self.debug_mode = True
            def _hack_get_available(url):
                return test_new_version
            self._get_available = _hack_get_available
        if test_current_version:
            self.debug_mode = True
            self.currentversion = Version.from_str(test_current_version)


    def debug(self, message):
        if self.debug_mode:
            self.threadwrap(self.errorfunc, logging.WARNING, message)


    def _get_available(self, url):
        self.debug('Updater.get_available() hitting url %s' % url)
        try:
            u = zurllib.urlopen(url)
            s = u.read()
            s = s.strip()
        except:
            raise BTFailure(_("Could not get latest version from %s")%url)
        try:
            assert len(s) == 5
            availableversion = Version.from_str(s)
        except:
            raise BTFailure(_("Could not parse new version string from %s")%url)        
        return availableversion


    def get_available(self):
        url = self.version_site + self.currentversion.name()
        availableversion = self._get_available(url)
        if availableversion.is_beta():
            if availableversion[1] != self.currentversion[1]:
                availableversion = self.currentversion 
        if self.currentversion.is_beta():
            stable_url = self.version_site + 'stable'
            available_stable_version = self._get_available(stable_url)
            if available_stable_version > availableversion:
                availableversion = available_stable_version
        self.version = availableversion
        self.debug('Updater.get_available() got %s' % str(self.version))
        return self.version


    def get(self):
        try:
            self.get_available()
        except BTFailure, e:
            self.threadwrap(self.errorfunc, logging.WARNING, e)
            return 

        if self.version <= self.currentversion:
            self.debug('Updater.get() not updating old version %s' % str(self.version))
            return

        if not self.can_install():
            self.debug('Updater.get() cannot install on this os')
            return

        self.installer_name = self.calc_installer_name()
        self.installer_url  = self.version_site + self.installer_name + '.torrent'
        self.installer_dir  = self.calc_installer_dir()

        self.torrentfile = None
        try:
            self.torrentfile = GetTorrent.get_url(self.installer_url)
        except GetTorrent.GetTorrentException, e:
            terrors = [unicode(e.args[0])]

        signature = None
        try:
            signfile = zurllib.urlopen(self.installer_url + '.sign')
        except:
            self.debug('Updater.get() failed to get signfile %s.sign' % self.installer_url)
        else:
            try:
                signature = pickle.load(signfile)
            except:
                self.debug('Updater.get() failed to load signfile %s' % signfile)
        
        if terrors:
            self.threadwrap(self.errorfunc, logging.WARNING, '\n'.join(terrors))

        if torrentfile and signature:
            public_key_file = open(os.path.join(doc_root, 'public.key'), 'rb')
            public_key = pickle.load(public_key_file)
            h = sha(torrentfile).digest()
            if public_key.verify(h, signature):
                self.torrentfile = torrentfile
                b = bdecode(torrentfile)
                self.infohash = sha(bencode(b['info'])).digest()
                self.total_size = b['info']['length']
                self.debug('Updater.get() got torrent file and signature')
            else:
                self.debug('Updater.get() torrent file signature failed to verify.')
                pass
        else:
            self.debug('Updater.get() doesn\'t have torrentfile %s and signature %s' %
                       (str(type(torrentfile)), str(type(signature))))

    def installer_path(self):
        if self.installer_dir is not None:
            return os.path.join(self.installer_dir,
                                self.installer_name)
        else:
            return None
        
    def check(self):
        t = threading.Thread(target=self._check,
                             args=())
        t.setDaemon(True)
        t.start()

    def _check(self):
        if osx:
            pool = NSAutoreleasePool.alloc().init()
        self.get()
        if self.version > self.currentversion:
            self.threadwrap(self.newversionfunc, self.version, download_url)

    def can_install(self):
        if self.debug_mode:
            return True
        if os.name == 'nt':
            return True
        elif osx:
            return True
        else:
            return False

    def calc_installer_name(self):
        if os.name == 'nt':
            ext = 'exe'
        elif osx:
            ext = 'dmg'
        elif os.name == 'posix' and self.debug_mode: 
            ext = 'tar.gz' 
        else:
            return
        
        parts = [app_name, str(self.version)]
        if self.version.is_beta():
            parts.append('Beta')
        name = '-'.join(parts)
        name += '.' + ext
        return name

    def set_installer_dir(self, path):
        self.installer_dir = path
        
    def calc_installer_dir(self):
        if hasattr(self, 'installer_dir'):
            return self.installer_dir
        
        temp_dir = get_temp_dir()
        if temp_dir is not None:
            return temp_dir
        else:
            self.errorfunc(logging.WARNING,
                           _("Could not find a suitable temporary location to "
                             "save the %s %s installer.") % (app_name, self.version))

    def installer_downloaded(self):
        if self.installer_path() and os.access(self.installer_path(), os.F_OK):
            size = os.stat(self.installer_path())[6]
            if size == self.total_size:
                return True
            else:
                #print 'installer is wrong size, is', size, 'should be', self.total_size
                return False
        else:
            #print 'installer does not exist'
            return False

    def download(self):
        if self.torrentfile is not None:
            self.startfunc(self.torrentfile, self.installer_path())
        else:
            self.errorfunc(logging.WARNING, _("No torrent file available for %s %s "
                                      "installer.")%(app_name, self.version))

    def start_install(self):
        if not self.asked_for_install:
            if self.installer_downloaded():
                self.asked_for_install = True
                self.installfunc()
            else:
                self.errorfunc(logging.WARNING,
                               _("%s %s installer appears to be incomplete, "
                                 "missing, or corrupt.")%(app_name,
                                                          self.version))

    def launch_installer(self, torrentqueue):
        if os.name == 'nt':
            spawn(torrentqueue, self.installer_path(), "/S")
        else:
            self.errorfunc(logging.WARNING, _("Cannot launch installer on this OS"))
