# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Uoti Urpala

from __future__ import division

import os
import sys
import threading

from time import time

from BitTorrent.download import Feedback, Multitorrent
from BitTorrent.controlsocket import ControlSocket
from BitTorrent.bencode import bdecode
from BitTorrent.ConvertedMetainfo import ConvertedMetainfo
from BitTorrent import BTFailure, INFO, WARNING, ERROR, CRITICAL
from BitTorrent import configfile
import BitTorrent

# check if dns library from http://www.dnspython.org/ is either installed
# or the dns subdirectory has been copied to BitTorrent/dns
HAVE_DNS = False
try:
    from BitTorrent import dns
    sys.modules['dns'] = dns
    import dns.resolver
    HAVE_DNS = True
except:
    try:
        import dns.resolver
        HAVE_DNS = True
    except:
        pass

RUNNING = 0
QUEUED = 1
KNOWN = 2
ASKING_LOCATION = 3


class TorrentInfo(object):

    def __init__(self):
        self.metainfo = None
        self.dlpath = None
        self.dl = None
        self.state = None
        self.completion = None
        self.finishtime = None
        self.uptotal = 0
        self.uptotal_old = 0
        self.downtotal = 0
        self.downtotal_old = 0


class TorrentQueue(Feedback):

    def __init__(self, config, ui_options, controlsocket):
        self.config = dict(config)
        self.ui_options = ui_options
        self.controlsocket = controlsocket
        self.config['max_running_torrents'] = 1 # !@# XXX
        self.saved_max_torrents = None
        self.doneflag = threading.Event()
        self.torrents = {}
        self.starting_torrent = None
        self.running_torrents = []
        self.queue = []
        self.other_torrents = []
        self.last_save_time = 0
        self.last_version_check = 0

    def run(self, ui, ui_wrap, startflag):
        self.ui = ui
        self.run_ui_task = ui_wrap
        self.multitorrent = Multitorrent(self.config, self.doneflag,
                                        self.global_error, listen_fail_ok=True)
        self.rawserver = self.multitorrent.rawserver
        self.controlsocket.set_rawserver(self.rawserver)
        self.controlsocket.start_listening(self.external_command)
        try:
            self._restore_state()
        except BTFailure, e:
            self.queue = []
            self.other_torrents = []
            self.torrents = {}
            self.global_error(ERROR, "Could not load saved state: "+str(e))
        else:
            for infohash in self.queue + self.other_torrents:
                t = self.torrents[infohash]
                if t.dlpath is not None:
                    t.completion = self.multitorrent.get_completion(
                        self.config, t.metainfo, t.dlpath)
                self.run_ui_task(self.ui.new_displayed_torrent, infohash,
                                 t.metainfo, t.dlpath, t.state, t.completion,
                                 t.uptotal, t.downtotal)
            self._check_queue()
        startflag.set()
        self._queue_loop()
        self._check_version()
        self.multitorrent.rawserver.listen_forever()
        self.multitorrent.close_listening_socket()
        self.controlsocket.close_socket()
        for infohash in list(self.running_torrents):
            t = self.torrents[infohash]
            t.dl.shutdown()
            if t.dl is not None:  # possibly set to none by failed()
                totals = t.dl.get_total_transfer()
                t.uptotal = t.uptotal_old + totals[0]
                t.downtotal = t.downtotal_old + totals[1]
        self._dump_state()

    def _check_version(self):
        now = time()
        if self.last_version_check > now - 24*3600:
            return
        self.last_version_check = now
        if not HAVE_DNS:
            self.global_error(WARNING, "Version check failed: no DNS library")
            return
        threading.Thread(target=self._version_thread).start()

    def _version_thread(self):
        def error(level, text):
            def f():
                self.global_error(level, text)
            self.rawserver.external_add_task(f, 0)
        try:
            try:
                a = dns.resolver.query('version.bittorrent.com', 'TXT')
            except:
                # the exceptions from the library have empty str(),
                # just different classes...
                raise BTFailure('DNS query failed')
            if len(a) != 1:
                raise BTFailure('number of received TXT fields is not 1')
            value = iter(a).next() # the object doesn't support a[0]
            if len(value.strings) != 1:
                raise BTFailure('number of strings in reply is not 1?')
            if value.strings[0] != BitTorrent.version:
                download_url = 'http://bittorrent.com/download.html'
                if hasattr(self.ui, 'new_version'):
                    self.run_ui_task(self.ui.new_version, value.strings[0], download_url)
                else:
                    error(ERROR, "A newer version of BitTorrent is available.\nYou can always get the latest version from \n%s." % download_url)
        except Exception, e:
            error(WARNING, "Version check failed: " + str(e))

    def _dump_config(self):
        configfile.save_ui_config(self.config, 'btdownloadgui',
                               self.ui_options, self.global_error)

    def _dump_state(self):
        self.last_save_time = time()
        r = []
        def write_entry(infohash, t):
            if t.dlpath is None:
                assert t.state == ASKING_LOCATION
                r.append(infohash.encode('hex') + '\n')
            else:
                r.append(infohash.encode('hex') + ' ' + str(t.uptotal) + ' ' +
                    str(t.downtotal)+' '+t.dlpath.encode('string_escape')+'\n')
        r.append('BitTorrent UI state file, version 2\n')
        r.append('Running/queued torrents\n')
        for infohash in self.running_torrents:
            write_entry(infohash, self.torrents[infohash])
        for infohash in self.queue:
            write_entry(infohash, self.torrents[infohash])
        r.append('Known torrents\n')
        for infohash in self.other_torrents:
            write_entry(infohash, self.torrents[infohash])
        r.append('End\n')
        f = None
        try:
            f = file(os.path.join(self.config['data_dir'], 'ui_state'), 'wb')
            f.write(''.join(r))
            f.close()
        except Exception, e:
            self.global_error(ERROR, 'Could not save UI state: ' + str(e))
            if f is not None:
                f.close()

    def _restore_state(self):
        def decode_line(line):
            hashtext = line[:40]
            try:
                infohash = hashtext.decode('hex')
            except:
                raise BTFailure("Invalid state file contents")
            if len(infohash) != 20:
                raise BTFailure("Invalid state file contents")
            try:
                path = os.path.join(self.config['data_dir'], 'metainfo',
                                    hashtext)
                f = file(path, 'rb')
                data = f.read()
                f.close()
            except Exception, e:
                try:
                    f.close()
                except:
                    pass
                self.global_error(ERROR,"Error reading file "+path+" ("+str(e)+
                                  "), cannot restore state completely")
                return None
            if infohash in self.torrents:
                raise BTFailure("Invalid state file (duplicate entry)")
            t = TorrentInfo()
            self.torrents[infohash] = t
            try:
                t.metainfo = ConvertedMetainfo(bdecode(data))
            except Exception, e:
                self.global_error(ERROR, "Corrupt data in "+path+
                                  " , cannot restore torrent ("+str(e)+")")
                return None
            t.metainfo.reported_errors = True # suppress redisplay on restart
            if infohash != t.metainfo.infohash:
                self.global_error(ERROR, "Corrupt data in "+path+
                                  " , cannot restore torrent ("+str(e)+")")
                return None
            if len(line) == 41:
                t.dlpath = None
                return infohash, t
            try:
                if version < 2:
                    t.dlpath = line[41:-1].decode('string_escape')
                else:
                    up, down, dlpath = line[41:-1].split(' ', 2)
                    t.uptotal = t.uptotal_old = int(up)
                    t.downtotal = t.downtotal_old = int(down)
                    t.dlpath = dlpath.decode('string_escape')
            except ValueError:  # unpack, int(), decode()
                raise BTFailure('Invalid state file (bad entry)')
            return infohash, t
        filename = os.path.join(self.config['data_dir'], 'ui_state')
        if not os.path.exists(filename):
            return
        f = None
        try:
            f = file(filename, 'rb')
            lines = f.readlines()
            f.close()
        except Exception, e:
            if f is not None:
                f.close()
            raise BTFailure(str(e))
        i = iter(lines)
        try:
            txt = 'BitTorrent UI state file, version '
            version = i.next()
            if not version.startswith(txt):
                raise BTFailure('Bad UI state file')
            try:
                version = int(version[len(txt):-1])
            except:
                raise BTFailure('Bad UI state file version')
            if version > 2:
                raise BTFailure('Unsupported UI state file version (from '
                                'newer client version?')
            if i.next() != "Running/queued torrents\n":
                raise BTFailure("Invalid state file contents")
            while True:
                line = i.next()
                if line == 'Known torrents\n':
                    break
                t = decode_line(line)
                if t is None:
                    continue
                infohash, t = t
                if t.dlpath is None:
                    raise BTFailure("Invalid state file contents")
                t.state = QUEUED
                self.queue.append(infohash)
            while True:
                line = i.next()
                if line == 'End\n':
                    break
                t = decode_line(line)
                if t is None:
                    continue
                infohash, t = t
                if t.dlpath is None:
                    t.state = ASKING_LOCATION
                else:
                    t.state = KNOWN
                self.other_torrents.append(infohash)
        except StopIteration:
            raise BTFailure("Invalid state file contents")

    def _queue_loop(self):
        if self.doneflag.isSet():
            return
        self.rawserver.add_task(self._queue_loop, 20)
        now = time()
        if self.queue and self.starting_torrent is None:
            mintime = now - self.config['next_torrent_time'] * 60
            minratio = self.config['next_torrent_ratio']
        else:
            mintime = 0
            minratio = self.config['last_torrent_ratio']
            if not minratio:
                return
        for infohash in self.running_torrents:
            t = self.torrents[infohash]
            totals = t.dl.get_total_transfer()
            # not updated for remaining torrents if one is stopped, who cares
            t.uptotal = t.uptotal_old + totals[0]
            t.downtotal = t.downtotal_old + totals[1]
            if t.finishtime is None or t.finishtime > now - 120:
                continue
            if t.finishtime > mintime:
                ratio = t.uptotal / (t.downtotal + 1)
                if ratio < minratio / 100:
                    continue
            self.stop_torrent(infohash)
            break
        if self.running_torrents and self.last_save_time < now - 300:
            self._dump_state()

    def _check_queue(self):
        if self.starting_torrent is not None or not self.queue:
            return
        if len(self.running_torrents) >= self.config['max_running_torrents']:
            return
        new = self.queue.pop(0)
        self._start_torrent(new)

    def _start_torrent(self, infohash):
        assert self.starting_torrent is None
        self.starting_torrent = infohash
        t = self.torrents[infohash]
        assert t.state == QUEUED
        t.state = RUNNING
        t.finishtime = None
        self.running_torrents.append(infohash)
        t.dl = self.multitorrent.start_torrent(t.metainfo, self.config, self,
                                               t.dlpath)
        self._send_state(infohash)

    def _send_state(self, infohash, queuepos=None):
        t = self.torrents[infohash]
        self.run_ui_task(self.ui.torrent_state_changed, infohash, t.state,
                        t.completion, t.uptotal_old, t.downtotal_old, queuepos)

    def start_torrent(self, infohash):
        self._check_version()
        torrent = self.torrents.get(infohash)
        if torrent is None:
            return
        if torrent.state != KNOWN:
            return
        self.other_torrents.remove(infohash)
        torrent.state = QUEUED
        self.queue.append(infohash)
        self._check_queue()
        self._dump_state()
        if torrent.state == QUEUED:  # if RUNNING, sent already
            self._send_state(infohash)

    def external_command(self, action, data):
        if action == 'start_torrent':
            self.start_new_torrent(data)
        elif action == 'show_error':
            self.global_error(ERROR, data)
        elif action == 'no-op':
            pass

    def remove_torrent(self, infohash):
        if infohash not in self.torrents:
            return
        state = self.torrents[infohash].state
        if state == QUEUED:
            self.queue.remove(infohash)
        elif state == RUNNING:
            self._stop_running(infohash)
            self.other_torrents.remove(infohash)
            self._check_queue()
        else:
            self.other_torrents.remove(infohash)
        self.run_ui_task(self.ui.removed_torrent, infohash)
        del self.torrents[infohash]
        filename = os.path.join(self.config['data_dir'], 'metainfo',
                                infohash.encode('hex'))
        try:
            os.remove(filename)
        except Exception, e:
            self.global_error(WARNING, 'Could not delete cached metainfo file:'
                              + str(e))
        self._dump_state()

    def set_save_location(self, infohash, dlpath):
        torrent = self.torrents.get(infohash)
        if torrent is None or torrent.state == RUNNING:
            return
        torrent.dlpath = dlpath
        torrent.completion = self.multitorrent.get_completion(self.config,
                                                   torrent.metainfo, dlpath)
        if torrent.state == ASKING_LOCATION:
            torrent.state = KNOWN
            self.start_torrent(infohash)
        else:
            self._send_state(infohash)
        self._dump_state()

    def start_new_torrent(self, data):
        t = TorrentInfo()
        try:
            t.metainfo = ConvertedMetainfo(bdecode(data))
        except Exception, e:
            self.global_error(ERROR, "This is not a valid torrent file. (%s)"
                              % str(e))
            return
        infohash = t.metainfo.infohash
        if infohash in self.torrents:
            self.global_error(ERROR, "Cannot start another torrent with the "
                              "same contents (infohash) as an existing one")
            return
        path = os.path.join(self.config['data_dir'], 'metainfo',
                            infohash.encode('hex'))
        try:
            f = file(path, 'wb')
            f.write(data)
            f.close()
        except Exception, e:
            try:
                f.close()
            except:
                pass
            self.global_error(ERROR, 'Could not write file '+path+' ('+str(e)+
                              '), torrent will not be restarted correctly on '
                              'client restart')
        self.torrents[infohash] = t
        t.state = ASKING_LOCATION
        self.other_torrents.append(infohash)
        self._dump_state()
        self.run_ui_task(self.ui.new_displayed_torrent, infohash,
                         t.metainfo, None, ASKING_LOCATION)
        def show_error(level, text):
            self.run_ui_task(self.ui.error, infohash, level, text)
        t.metainfo.show_encoding_errors(show_error)

    def set_config(self, option, value):
        self.config[option] = value
        self.multitorrent.set_option(option, value)
        for infohash in list(self.running_torrents):
            self.torrents[infohash].dl.set_option(option, value)
        self._dump_config()

    def request_status(self, infohash, want_spew, want_fileinfo):
        torrent = self.torrents.get(infohash)
        if torrent is None or torrent.state != RUNNING:
            return
        status = torrent.dl.get_status(want_spew, want_fileinfo)
        if torrent.finishtime is not None:
            now = time()
            uptotal = status['upTotal'] + torrent.uptotal_old
            downtotal = status['downTotal'] + torrent.downtotal_old
            ulspeed = status['upRate']
            if self.queue:
                ratio = self.config['next_torrent_ratio'] / 100
            else:
                ratio = self.config['last_torrent_ratio'] / 100
            if ratio <= 0 or ulspeed <= 0:
                rem = 1e99
            else:
                rem = (downtotal * ratio - uptotal) / ulspeed
            if self.queue:
                rem = min(rem, torrent.finishtime +
                          self.config['next_torrent_time'] * 60 - now)
            rem = max(rem, torrent.finishtime + 120 - now)
            if rem <= 0:
                rem = 1
            if rem == 1e99:
                rem = None
            status['timeEst'] = rem
        self.run_ui_task(self.ui.update_status, infohash, status)

    def unqueue_torrent(self, infohash):
        t = self.torrents.get(infohash)
        if t is None or t.state != QUEUED:
            return
        t.state = KNOWN
        self.queue.remove(infohash)
        self.other_torrents.append(infohash)
        self._dump_state()
        self._send_state(infohash)

    def _stop_running(self, infohash):
        t = self.torrents[infohash]
        assert t.state == RUNNING
        t.dl.shutdown()
        if infohash == self.starting_torrent:
            self.starting_torrent = None
        try:
            self.running_torrents.remove(infohash)
        except ValueError:
            return False
        else:
            t.state = KNOWN
            totals = t.dl.get_total_transfer()
            t.uptotal_old += totals[0]
            t.uptotal = t.uptotal_old
            t.downtotal_old += totals[1]
            t.downtotal = t.downtotal_old
            t.dl = None
            t.completion = self.multitorrent.get_completion(self.config,
                                               t.metainfo, t.dlpath)
            self.other_torrents.append(infohash)
            return True

    def requeue_running_torrent(self, infohash):
        # the > test only matters if max_running_torrents changes
        if not (self.queue or len(self.running_torrents) >
                self.config['max_running_torrents']):
            return
        t = self.torrents.get(infohash)
        if t is None or t.state != RUNNING:
            return
        # if the torrent failed during shutdown, don't requeue now
        if self._stop_running(infohash):
            self.start_torrent(infohash)

    def replace_running_torrent(self, infohash):
        if len(self.running_torrents) < self.config['max_running_torrents']:
            self.start_torrent(infohash)
            return
        if self.config['max_running_torrents'] != 1 or \
               len(self.running_torrents) != 1:
            return
        torrent = self.torrents.get(infohash)
        if torrent is None:
            return
        if torrent.state == KNOWN:
            self.other_torrents.remove(infohash)
        elif torrent.state == QUEUED:
            self.queue.remove(infohash)
        else:
            return
        self.queue.insert(0, infohash)
        torrent.state = QUEUED
        old = self.running_torrents[0]
        if self._stop_running(old):
            self._check_queue()
            self.other_torrents.remove(old)
            self.queue.insert(0, old)
            self.torrents[old].state = QUEUED
            self._send_state(old, 0)
            self._dump_state()

    def stop_torrent(self, infohash):
        t = self.torrents.get(infohash)
        if t is None or t.state != RUNNING:
            return
        if self._stop_running(infohash):
            self._send_state(infohash)
            self._check_queue()
            self._dump_state()

    def reorder_queue(self, neworder):
        newqueue = []
        for infohash in neworder:
            t = self.torrents.get(infohash)
            if t is None or t.state != QUEUED:
                continue
            newqueue.append(infohash)
        for infohash in self.queue:
            if infohash not in newqueue:
                newqueue.append(infohash)
        self.queue = newqueue
        self._dump_state()
        self.run_ui_task(self.ui.update_queue, self.queue)

    def set_zero_running_torrents(self):
        if self.saved_max_torrents is not None:
            return
        self.saved_max_torrents = self.config['max_running_torrents']
        self.config['max_running_torrents'] = 0
        for infohash in list(self.running_torrents):
            t = self.torrents[infohash]
            if self._stop_running(infohash):
                self.other_torrents.remove(infohash)
                t.state = QUEUED
                self.queue.insert(0, infohash)
                self._send_state(infohash, 0)

    def unset_zero_running_torrents(self):
        if self.saved_max_torrents is None:
            return
        self.config['max_running_torrents'] = self.saved_max_torrents
        self.saved_max_torrents = None
        self._check_queue()

    def check_completion(self, infohash, filelist=False):
        t = self.torrents.get(infohash)
        if t is None:
            return
        r = self.multitorrent.get_completion(self.config, t.metainfo,
                                             t.dlpath, filelist)
        if r is None or not filelist:
            self.run_ui_task(self.ui.update_completion, infohash, r)
        else:
            self.run_ui_task(self.ui.update_completion, infohash, *r)

    def global_error(self, level, text):
        self.run_ui_task(self.ui.global_error, level, text)

    # callbacks from torrent instances

    def failed(self, torrent):
        infohash = torrent.infohash
        if infohash == self.starting_torrent:
            self.starting_torrent = None
        self.running_torrents.remove(infohash)
        t = self.torrents[infohash]
        t.state = KNOWN
        t.completion = None
        totals = t.dl.get_total_transfer()
        t.uptotal_old += totals[0]
        t.uptotal = t.uptotal_old
        t.downtotal_old += totals[1]
        t.downtotal = t.downtotal_old
        t.dl = None
        self.other_torrents.append(infohash)
        self._send_state(infohash)
        if not self.doneflag.isSet():
            self._check_queue()
            self._dump_state()

    def finished(self, torrent):
        self.torrents[torrent.infohash].finishtime = time()

    def started(self, torrent):
        infohash = torrent.infohash
        assert infohash == self.starting_torrent
        self.starting_torrent = None
        self._check_queue()

    def error(self, torrent, level, text):
        self.run_ui_task(self.ui.error, torrent.infohash, level, text)


class ThreadWrappedQueue(object):

    def __init__(self, wrapped):
        self.wrapped = wrapped

    def set_done(self):
        self.wrapped.doneflag.set()
        # add a dummy task to make sure the thread wakes up and notices flag
        def dummy():
            pass
        self.wrapped.rawserver.external_add_task(dummy, 0)

def _makemethod(methodname):
    def wrapper(self, *args, **kws):
        def f():
            getattr(self.wrapped, methodname)(*args, **kws)
        self.wrapped.rawserver.external_add_task(f, 0)
    return wrapper

for methodname in "request_status set_config start_torrent start_new_torrent stop_torrent unqueue_torrent remove_torrent set_save_location requeue_running_torrent replace_running_torrent reorder_queue set_zero_running_torrents unset_zero_running_torrents check_completion".split():
    setattr(ThreadWrappedQueue, methodname, _makemethod(methodname))
del _makemethod, methodname
