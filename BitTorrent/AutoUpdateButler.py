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
from sha import sha
import pickle
import logging
from BitTorrent.translation import _

from BitTorrent import zurllib
from BitTorrent import GetTorrent
from BitTorrent import app_name, version, BTFailure

from BitTorrent.ConvertedMetainfo import ConvertedMetainfo
from BitTorrent.bencode import bdecode, bencode
from BitTorrent.platform import osx, get_temp_dir, doc_root, os_version
from BitTorrent.yielddefer import launch_coroutine
from BitTorrent.defer import Deferred, ThreadedDeferred
from BitTorrent.platform import osx, get_temp_dir, doc_root
from BitTorrent.yielddefer import launch_coroutine, _wrap_task
from BitTorrent.MultiTorrent import TorrentAlreadyRunning, TorrentAlreadyInQueue, UnknownInfohash
from BitTorrent.obsoletepythonsupport import set

from TorrentButler import TorrentButler
from NewVersion import Version


version_host = 'http://version.bittorrent.com/'
download_url = 'http://bittorrent.com/download.html'

DEBUG = False

class AutoUpdateButler(TorrentButler):

    def __init__(self, multitorrent, rawserver, 
                 test_new_version=None, test_current_version=None):
        TorrentButler.__init__(self, multitorrent)

        self.runs = 0

        self.rawserver = rawserver
        self.estate = set()

        self.log_root = "core.AutoUpdateButler"
        self.logger = logging.getLogger(self.log_root)

        self.installable_version = None
        self.available_version   = None

        self.current_version = Version.from_str(version)

        self.debug_mode = DEBUG
        if test_new_version:
            test_new_version = Version.from_str(test_new_version)
            self.debug_mode = True
            self.debug('__init__() turning debug on')
            def _hack_get_available(url):
                self.debug('_hack_get_available() run#%d: returning %s' % (self.runs, str(test_new_version)))
                return test_new_version
            self._get_available = _hack_get_available
        if test_current_version:
            self.debug_mode = True
            self.current_version = Version.from_str(test_current_version)

        self.version_site = version_host
        # The version URL format is:
        # http:// VERSION_SITE / OS_NAME / (LEGACY /) BETA or STABLE

        # LEGACY means that the user is on a version of an OS that has
        # been deemed "legacy", and as such the latest client version
        # for their OS version may be different than the latest client
        # version for the OS in general.  For example, if we are going
        # to roll a version that requires WinXP/2K or greater, or a
        # version that requires OSX 10.5 or greater, we may maintain
        # an older version for Win98 or OSX 10.4 in OS_NAME/legacy/.

        if os.name == 'nt':
            self.version_site += 'win32/'
            if os_version not in ('XP', '2000', '2003'):
                self.version_site += 'legacy/'
        elif osx:
            self.version_site += 'osx/'
        elif self.debug_mode:
            self.version_site += 'win32/'

        self.installer_dir = self._calc_installer_dir()


    def get_auto_update_status(self):
        r = None, None
        if not self._can_install():
            # Auto-update doesn't work here, so just notify the user
            # of the new available version.
            r = self.available_version, None
            self.available_version = None
        elif self.installable_version is not None:
            # Auto-update is done, notify the user of the version
            # ready to install.
            r = self.available_version, self.installable_version
            self.available_version = None
        else:
            # Auto-update is in progress, don't tell the user
            # anything, and don't reset anything.
            r = None, None
        return r


    def butle(self):
        for i in list(self.estate):
            try:
                t = self.multitorrent.get_torrent(i)
                if t.state == 'initialized':
                    self.multitorrent.start_torrent(t)
                state, policy, completed, status = self.multitorrent.torrent_status(i)
                if completed:
                    self.finished(t)
            except UnknownInfohash:
                self.debug('butle() removing' + i.short())
                self.estate.remove(i)
                self.installable_version = None
                self.available_version = None


    def butles(self, torrent):
        return torrent.infohash in self.estate and torrent.is_initialized()


    def started(self, torrent):
        """Only run the most recently added torrent"""
        if self.butles(torrent):
            removable = self.estate - set([torrent.infohash])
            for i in removable:
                self.estate.discard(i)
                self.multitorrent.remove_torrent(i)
                # BUG: remove unfinished download of obsolete auto-update from disk


    def finished(self, torrent):
        """Launch the auto-updater"""
        self.debug('finished() called for '+torrent.infohash.short())
        if self.butles(torrent):
            self.debug('finished() setting installable version to '+ torrent.infohash.short())
            self.installable_version = torrent.infohash


    # Auto-update specific methods
    def debug(self, message):
        if self.debug_mode:
            self.logger.warning(message)


    def _can_install(self):
        """Return True if this OS supports auto-updates."""
        if self.debug_mode:
            return True
        if self.installer_dir is None:
            return False
        
        if os.name == 'nt':
            return True
        elif osx:
            return True
        else:
            return False


    def _calc_installer_name(self, available_version):
        """Figure out the name of the installer for this OS."""
        if os.name == 'nt' or self.debug_mode:
            ext = 'exe'
        elif osx:
            ext = 'dmg'
        elif os.name == 'posix': 
            ext = 'tar.gz' 
        else:
            return
        
        parts = [app_name, str(available_version)]
        if available_version.is_beta():
            parts.append('Beta')
        name = '-'.join(parts)
        name += '.' + ext
        return name


    def _calc_installer_dir(self):
        """Find a place to store the installer while it's being downloaded."""        
        temp_dir = get_temp_dir()
        return temp_dir


    def _get_available(self, url):
        """Get the available version from the version site.  The
        command line option --new_version X.Y.Z overrides this method
        and returns 'X.Y.Z' instead."""
        self.debug('_get_available() run#%d: hitting url %s' % (self.runs, url))
        try:
            u = zurllib.urlopen(url)
            s = u.read()
            s = s.strip()
        except:
            raise BTFailure(_("Could not get latest version from %s")%url)
        try:
            assert len(s) == 5
            available_version = Version.from_str(s)
        except:
            raise BTFailure(_("Could not parse new version string from %s")%url)        

        return available_version


    def _get_torrent(self, installer_url):
        """Get the .torrent file from the version site."""
        torrentfile = None
        try:
            torrentfile = GetTorrent.get_url(installer_url)
        except GetTorrent.GetTorrentException, e:
            self.debug('_get_torrent() run#%d: failed to download torrent file %s: %s' %
                       (self.runs, installer_url, str(e)))
            pass
        return torrentfile


    def _get_signature(self, installer_url):
        """Get the signature (.sign) file from the version site, and
        unpickle the signature.  The sign file is a signature of the
        .torrent file created with the auto-update tool in
        auto-update/sign_file.py."""
        signature = None
        try:
            signfile = zurllib.urlopen(installer_url + '.sign')
        except:
            self.debug('_get_signature() run#%d: failed to download signfile %s.sign' %
                       (self.runs, installer_url))
            pass
        else:
            try:
                signature = pickle.load(signfile)
            except:
                self.debug('_get_signature() run#%d: failed to unpickle signfile %s' %
                           (self.runs, signfile))
                pass
        return signature


    def _check_signature(self, torrentfile, signature):
        """Check the torrent file's signature using the public key."""
        public_key_file = open(os.path.join(doc_root, 'public.key'), 'rb')
        public_key = pickle.load(public_key_file)
        public_key_file.close()
        h = sha(torrentfile).digest()
        return public_key.verify(h, signature)


    def check_version(self):
        """Launch the actual version check code in a coroutine since
        it needs to make three (or four, in beta) http requests, one
        disk read, and one decryption."""
        df = launch_coroutine(_wrap_task(self.rawserver.external_add_task),
                              self._check_version)
        def errback(e):
            from traceback import format_exc
            self.debug('check_version() run #%d: '%self.runs + format_exc(e))
        df.addErrback(errback)


    def _check_version(self):
        """Actually check for an auto-update:
        1.  Check the version number from the file on the version site.
        2.  Check the stable version number from the file on the version site.
        3.  Notify the user and stop if they are on an OS with no installer.
        4.  Get the torrent file from the version site.
        5.  Get the signature from the version site.
        6.  Check the signature against the torrent file using the public key.
        7a. Start the torrent if it's not in the client.
        7b. Restart the torrent if it's in the client but not running.
        8.  Put the infohash of the torrent into estate so the butler knows
            to butle it.
        9.  AutoUpdateButler.started() ensures that only the most recent
            auto-update torrent is running.
        10. AutoUpdateButler.finished() initiates the user feedback when
            it's time to launch the installer.

        Whether an auto-update was found and started or not, requeue
        the call to check_version() to run a day later.  This means
        that the version check runs at startup, and once a day.  It
        also means that the user is asked to restart the client and
        let the installer run, or notified of a new version, once a
        day.
        """
        debug_prefix = '_check_version() run#%d: '%self.runs
        self.debug(debug_prefix + 'starting')

        url = self.version_site + self.current_version.name()

        df = ThreadedDeferred(_wrap_task(self.rawserver.external_add_task),
                              self._get_available, url)
        yield df
        try:
            available_version = df.getResult()
        except BTFailure, e:
            self.debug(debug_prefix + 'failed to load %s' % url)
            self._restart()
            return

        if available_version.is_beta():
            if available_version[1] != self.current_version[1]:
                available_version = self.current_version 
        if self.current_version.is_beta():
            stable_url = self.version_site + 'stable'
            df = ThreadedDeferred(_wrap_task(self.rawserver.external_add_task),
                                  self._get_available, stable_url)
            yield df
            try:
                available_stable_version = df.getResult()
            except BTFailure, e:
                self.debug(debug_prefix + 'failed to load %s' % url)
                self._restart()
                return

            if available_stable_version > available_version:
                available_version = available_stable_version
        self.debug(debug_prefix + 'got %s' % str(available_version))


        if available_version <= self.current_version:
            self.debug(debug_prefix + 'not updating old version %s' %
                       str(available_version))
            self._restart()
            return

        if not self._can_install():
            self.debug(debug_prefix + 'cannot install on this os')
            self.available_version = available_version
            self._restart()
            return

        installer_name = self._calc_installer_name(available_version)
        installer_url  = self.version_site + installer_name + '.torrent'
        installer_path = unicode(os.path.join(self.installer_dir, installer_name))

        df = ThreadedDeferred(_wrap_task(self.rawserver.external_add_task),
                              self._get_torrent, installer_url)
        yield df
        torrentfile = df.getResult()

        df = ThreadedDeferred(_wrap_task(self.rawserver.external_add_task),
                              self._get_signature, installer_url)
        yield df
        signature = df.getResult()

        if torrentfile and signature:
            df = ThreadedDeferred(_wrap_task(self.rawserver.external_add_task),
                                  self._check_signature, torrentfile, signature)
            yield df
            checked = df.getResult()
            if checked:
                self.debug(debug_prefix + 'signature verified successfully.')
                b = bdecode(torrentfile)
                metainfo = ConvertedMetainfo(b)
                infohash = metainfo.infohash
                self.available_version = available_version
                try:
                    df = self.multitorrent.create_torrent(metainfo, installer_path, installer_path)
                    yield df
                    df.getResult()
                except TorrentAlreadyRunning:
                    self.debug(debug_prefix + 'found auto-update torrent already running')
                except TorrentAlreadyInQueue:
                    self.debug(debug_prefix + 'found auto-update torrent queued')
                else:
                    self.debug(debug_prefix + 'starting auto-update download')

                self.debug(debug_prefix + 'adding to estate '+infohash.short())
                self.estate.add(infohash)

            else:
                self.debug(debug_prefix + 'torrent file signature failed to verify.')
                pass


        else:
            self.debug(debug_prefix + 'couldn\'t get both torrentfile %s and signature %s' %
                       (str(type(torrentfile)), str(type(signature))))

        self._restart()


    def _restart(self):
        """Run the auto-update check once a day, or every ten seconds
        in debug mode."""
        self.runs += 1
        delay = 60*60*24
        if self.debug_mode:
            delay = 10
        self.rawserver.external_add_task(delay, self.check_version)
