# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
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
import shutil
import threading
import traceback


from BitTorrent.platform import bttime
from BitTorrent.download import Feedback, Multitorrent
from BitTorrent.bencode import bdecode
from BitTorrent.ConvertedMetainfo import ConvertedMetainfo
from BitTorrent.prefs import Preferences

from BitTorrent.BandwidthManager import BandwidthManager

from BitTorrent import BTFailure, BTShutdown, INFO, WARNING, ERROR, CRITICAL
from BitTorrent import configfile
from BitTorrent import FAQ_URL
#from BitTorrent.QueueButler import QueueButler
from BitTorrent import zurllib
import BitTorrent


RUNNING = 0
RUN_QUEUED = 1
QUEUED = 2
KNOWN = 3
ASKING_LOCATION = 4

state_dict = {RUNNING   : 'running',
              RUN_QUEUED: 'paused',
              QUEUED    : 'waiting',
              KNOWN     : "``known''",
              ASKING_LOCATION: "Dude, use the new TQ",}

class TorrentInfo(object):

    def __init__(self, config):
        self.metainfo = None
        self.dl = None
        self.state = None
        self.completion = None
        self.finishtime = None
        self.uptotal = 0
        self.uptotal_old = 0
        self.downtotal = 0
        self.downtotal_old = 0
        self.config = config

    def _set_dlpath(self, value):
        self.config['save_as'] = value

    def _get_dlpath(self):
        return self.config['save_as']

    dlpath = property(_get_dlpath, _set_dlpath)


def decode_position(l, pred, succ, default=None):
    if default is None:
        default = len(l)
    if pred is None and succ is None:
        return default
    if pred is None:
        return 0
    if succ is None:
        return len(l)
    try:
        if l[0] == succ and pred not in l:
            return 0
        if l[-1] == pred and succ not in l:
            return len(l)
        i = l.index(pred)
        if l[i+1] == succ:
            return i+1
    except (ValueError, IndexError):
        pass
    return default

class TorrentQueue(Feedback):

    def __init__(self, config, ui_options, rawserver, ipc):
        self.ui_options = ui_options
        self.rawserver = rawserver
        self.ipc = ipc
        self.config = config
        self.config['def_running_torrents'] = 100 # !@# XXX
        self.config['max_running_torrents'] = 100 # !@# XXX
        self.doneflag = threading.Event()
        self.torrents = {}
        self.starting_torrent = None
        self.running_torrents = []
        self.queue = []
        self.other_torrents = []
        self.last_save_time = 0
        self.last_version_check = 0
        self.initialized = 0

    # TEMP TEMP TEMP
    def _get_total_rates(self):
        u = 0.0
        d = 0.0
        for torrent in self.torrents.values():
            if torrent is None:
                continue
            if torrent.dl is None:
                continue
            status = torrent.dl.get_status(False, False)
            #print status
            u += status.get('upRate', 0)
            d += status.get('downRate', 0)
        return u,d

    def send_gui_rates(self, callback):
        self.run_ui_task(callback, *self._get_total_rates())

    def run(self, ui, ui_wrap, startflag):
        zurllib.add_unsafe_thread()
        self.rawserver.associate_thread()
        startflag.set()

        try:
            self.ui = ui
            self.run_ui_task = ui_wrap
            self.multitorrent = Multitorrent(self.config, self.doneflag,
                                             self.rawserver, self.global_error,
                                             listen_fail_ok=True)

            #upload_like_crazy.init(self.rawserver)
            #self.rawserver.add_task(0, upload_like_crazy.queue_connections)
            #def get_rates():
            #    rate, delivered = upload_like_crazy.measure.get_last_rate()
            #    return rate, 0
            self.bwm = BandwidthManager(external_add_task=self.rawserver.external_add_task,
                                        config=self.config,
                                        set_config=self.set_config,
                                        get_remote_endpoints=self.rawserver.get_remote_endpoints,
                                        get_rates=self._get_total_rates)
                                        #get_rates=get_rates)


            self.ipc.start(self.external_command)
            #qb = QueueButler(self.rawserver, self)
            #qb.update()
            try:
                self._restore_state()
            except BTFailure, e:
                self.torrents = {}
                self.running_torrents = []
                self.queue = []
                self.other_torrents = []
                self.global_error(ERROR, _("Could not load saved state: ")+str(e))
            else:
                for infohash in self.running_torrents + self.queue + \
                        self.other_torrents:
                    t = self.torrents[infohash]
                    if t.dlpath is not None:
                        t.completion = self.multitorrent.get_completion(
                            self.config, t.metainfo, t.dlpath)
                    state = t.state
                    if state == RUN_QUEUED:
                        state = RUNNING
                    self.run_ui_task(self.ui.new_displayed_torrent, infohash,
                                     t.metainfo, t.dlpath, state, t.config,
                                     t.completion, t.uptotal, t.downtotal, )
            self._check_queue()
            self.initialized = 1
        except Exception, e:
            # dump a normal exception traceback
            traceback.print_exc()
            # set the error flag
            self.initialized = -1
            # signal the gui thread to stop waiting
            startflag.set()
            return

        self._queue_loop()
        self.multitorrent.rawserver.listen_forever(self.doneflag)
        if self.doneflag.isSet():
            # this is where GUI cleanup used to be; now it does nothing
            pass
        self.multitorrent.close_listening_socket()
        self.ipc.stop()
        for infohash in list(self.running_torrents):
            t = self.torrents[infohash]
            if t.state == RUN_QUEUED:
                continue
            t.dl.shutdown()
            if t.dl is not None:  # possibly set to none by failed()
                totals = t.dl.get_total_transfer()
                t.uptotal = t.uptotal_old + totals[0]
                t.downtotal = t.downtotal_old + totals[1]
        self._dump_state()

    def _check_version(self):
        now = bttime()
        if self.last_version_check > 0 and \
               self.last_version_check > now - 24*60*60:
            return
        self.last_version_check = now
        self.run_ui_task(self.ui.check_version)

    def _dump_config(self):
        configfile.save_ui_config(self.config, 'bittorrent',
                               self.ui_options, self.global_error)
        for infohash,t in self.torrents.items():
            ec = lambda level, message: self.error(t.metainfo, level, message)
            config = t.config.getDict()
            if config:
                configfile.save_torrent_config(self.config['data_dir'],
                                               infohash, config, ec)

    def _dump_state(self):
        self.last_save_time = bttime()
        r = []
        def write_entry(infohash, t):
            if t.dlpath is None:
                assert t.state == ASKING_LOCATION
                r.append(infohash.encode('hex') + '\n')
            else:
                r.append(infohash.encode('hex') + ' ' +
                         str(t.uptotal)         + ' ' +
                         str(t.downtotal)       + '\n')
        r.append('BitTorrent UI state file, version 4\n')
        r.append('Running torrents\n')
        for infohash in self.running_torrents:
            write_entry(infohash, self.torrents[infohash])
        #r.append('Queued torrents\n')
        for infohash in self.queue:
            write_entry(infohash, self.torrents[infohash])
        #r.append('Known torrents\n')
        for infohash in self.other_torrents:
            write_entry(infohash, self.torrents[infohash])
        r.append('Queued torrents\n')
        r.append('Known torrents\n')
        r.append('End\n')
        f = None
        try:
            filename = os.path.join(self.config['data_dir'], 'ui_state')
            f = file(filename + '.new', 'wb')
            f.write(''.join(r))
            f.close()
            shutil.move(filename + '.new', filename)
        except Exception, e:
            self.global_error(ERROR, _("Could not save UI state: ") + str(e))
            if f is not None:
                f.close()

    def _restore_state(self):
        def decode_line(line):
            hashtext = line[:40]
            try:
                infohash = hashtext.decode('hex')
            except:
                raise BTFailure(_("Invalid state file contents"))
            if len(infohash) != 20:
                raise BTFailure(_("Invalid state file contents"))
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
                self.global_error(ERROR,
                                  (_("Error reading file \"%s\".") % path) +
                                  " (" + str(e)+ "), " +
                                  _("cannot restore state completely"))
                return None
            if infohash in self.torrents:
                raise BTFailure(_("Invalid state file (duplicate entry)"))
            t = TorrentInfo(Preferences(self.config))
            self.torrents[infohash] = t
            try:
                t.metainfo = ConvertedMetainfo(bdecode(data))
            except Exception, e:
                self.global_error(ERROR,
                                  (_("Corrupt data in \"%s\", cannot restore torrent.") % path) +
                                  '('+str(e)+')')
                return None
            t.metainfo.reported_errors = True # suppress redisplay on restart
            if infohash != t.metainfo.infohash:
                self.global_error(ERROR,
                                  (_("Corrupt data in \"%s\", cannot restore torrent.") % path) +
                                  _("(infohash mismatch)"))
                return None
            if len(line) == 41:
                t.dlpath = None
                return infohash, t
            try:
                if version < 2:
                    t.dlpath = line[41:-1].decode('string_escape')
                elif version == 3:
                    up, down, dlpath = line[41:-1].split(' ', 2)
                    t.uptotal = t.uptotal_old = int(up)
                    t.downtotal = t.downtotal_old = int(down)
                    t.dlpath = dlpath.decode('string_escape')
                elif version >= 4:
                    up, down = line[41:-1].split(' ', 1)
                    t.uptotal = t.uptotal_old = int(up)
                    t.downtotal = t.downtotal_old = int(down)
            except ValueError:  # unpack, int(), decode()
                raise BTFailure(_("Invalid state file (bad entry)"))
            # save_as workaround
            self.config['save_as'] = ''
            config = configfile.read_torrent_config(self.config,
                                                    self.config['data_dir'],
                                                    infohash, self.global_error)
            t.config.update(config)
            # save_as workaround
            del self.config['save_as']
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
                raise BTFailure(_("Bad UI state file"))
            try:
                version = int(version[len(txt):-1])
            except:
                raise BTFailure(_("Bad UI state file version"))
            if version > 4:
                raise BTFailure(_("Unsupported UI state file version (from "
                                  "newer client version?)"))
            if version < 3:
                if i.next() != 'Running/queued torrents\n':
                    raise BTFailure(_("Invalid state file contents"))
            else:
                if i.next() != 'Running torrents\n':
                    raise BTFailure(_("Invalid state file contents"))
                while True:
                    line = i.next()
                    if line == 'Queued torrents\n':
                        break
                    t = decode_line(line)
                    if t is None:
                        continue
                    infohash, t = t
                    if t.dlpath is None:
                        raise BTFailure(_("Invalid state file contents (dlpath is None)"))
                    t.state = RUN_QUEUED
                    self.running_torrents.append(infohash)
            while True:
                line = i.next()
                if line == 'Known torrents\n':
                    break
                t = decode_line(line)
                if t is None:
                    continue
                infohash, t = t
                if t.dlpath is None:
                    raise BTFailure(_("Invalid state file contents"))
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
            raise BTFailure(_("Invalid state file contents"))

    def _queue_loop(self):
        if self.doneflag.isSet():
            return
        self.rawserver.add_task(20, self._queue_loop)
        now = bttime()
        self._check_version()
        if self.queue and self.starting_torrent is None:
            mintime = now - self.config['next_torrent_time'] * 60
            minratio = self.config['next_torrent_ratio'] / 100
            if self.config['seed_forever']:
                minratio = 1e99
        else:
            mintime = 0
            minratio = self.config['last_torrent_ratio'] / 100
            if self.config['seed_last_forever']:
                minratio = 1e99
            if minratio >= 1e99:
                return
        for infohash in self.running_torrents:
            t = self.torrents[infohash]
            myminratio = minratio
            if t.dl:
                if self.queue and t.dl.config['seed_last_forever']:
                    myminratio = 1e99
                elif t.dl.config['seed_forever']:
                    myminratio = 1e99
            if t.state == RUN_QUEUED:
                continue
            totals = t.dl.get_total_transfer()
            # not updated for remaining torrents if one is stopped, who cares
            t.uptotal = t.uptotal_old + totals[0]
            t.downtotal = t.downtotal_old + totals[1]
            if t.finishtime is None or t.finishtime > now - 120:
                continue
            if t.finishtime > mintime:
                if t.uptotal < t.metainfo.total_bytes * myminratio:
                    continue
            self.change_torrent_state(infohash, RUNNING, KNOWN)
            break
        if self.running_torrents and self.last_save_time < now - 300:
            self._dump_state()

    def _check_queue(self):
        if self.starting_torrent is not None or self.config['pause']:
            return
        for infohash in self.running_torrents:
            if self.torrents[infohash].state == RUN_QUEUED:
                self.starting_torrent = infohash
                t = self.torrents[infohash]
                t.state = RUNNING
                t.finishtime = None
                t.dl = self.multitorrent.start_torrent(t.metainfo, t.config,
                                                       self, t.dlpath)
                return
        if not self.queue or len(self.running_torrents) >= \
               self.config['def_running_torrents']:
            return
        infohash = self.queue.pop(0)
        self.starting_torrent = infohash
        t = self.torrents[infohash]
        assert t.state == QUEUED
        t.state = RUNNING
        t.finishtime = None
        self.running_torrents.append(infohash)
        t.dl = self.multitorrent.start_torrent(t.metainfo, t.config, self,
                                               t.dlpath)
        self._send_state(infohash)

    def _send_state(self, infohash):
        t = self.torrents[infohash]
        state = t.state
        if state == RUN_QUEUED:
            state = RUNNING
        pos = None
        if state in (KNOWN, RUNNING, QUEUED):
            l = self._get_list(state)
            if l[-1] != infohash:
                pos = l.index(infohash)
        self.run_ui_task(self.ui.torrent_state_changed, infohash, t.dlpath,
                     state, t.completion, t.uptotal_old, t.downtotal_old, pos)

    def _stop_running(self, infohash):
        t = self.torrents[infohash]
        if t.state == RUN_QUEUED:
            self.running_torrents.remove(infohash)
            t.state = KNOWN
            return True
        assert t.state == RUNNING
        shutdown_succeded = t.dl.shutdown()
        if not shutdown_succeded:
            self.run_ui_task(self.ui.open_log)
            self.error(t.metainfo, ERROR, "Unable to stop torrent.  Please send this application log to bugs@bittorrent.com .")
            return False
        if infohash == self.starting_torrent:
            self.starting_torrent = None
        try:
            self.running_torrents.remove(infohash)
        except ValueError:
            self.other_torrents.remove(infohash)
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
            return True

    def external_command(self, action, *datas):
        if action == 'start_torrent':
            assert len(datas) == 2
            # BUG: passing raw data over controlsocket instead of
            # metainfo because we can't pass metainfo over control
            # socket, bummer
            self.start_new_torrent_raw(datas[0], save_as=datas[1])
        elif action == 'show_error':
            assert len(datas) == 1
            self.global_error(ERROR, datas[0])
        elif action == 'no-op':
            pass

    def remove_torrent(self, infohash):
        if infohash not in self.torrents:
            return
        state = self.torrents[infohash].state
        if state == QUEUED:
            self.queue.remove(infohash)
        elif state in (RUNNING, RUN_QUEUED):
            self._stop_running(infohash)
            self._check_queue()
        else:
            self.other_torrents.remove(infohash)
        self.run_ui_task(self.ui.removed_torrent, infohash)
        del self.torrents[infohash]

        for d in ['metainfo', 'resume']:
            filename = os.path.join(self.config['data_dir'], d,
                                         infohash.encode('hex'))
            try:
                os.remove(filename)
            except Exception, e:
                self.global_error(WARNING,
                                  (_("Could not delete cached %s file:")%d) +
                                  str(e))
        ec = lambda level, message: self.global_error(level, message)
        configfile.remove_torrent_config(self.config['data_dir'],
                                         infohash, ec)
        self._dump_state()

    def set_save_location(self, infohash, dlpath):
        torrent = self.torrents.get(infohash)
        if torrent is None or torrent.state == RUNNING:
            return
        torrent.dlpath = dlpath
        self._dump_config()
        torrent.completion = self.multitorrent.get_completion(self.config,
                                                   torrent.metainfo, dlpath)
        if torrent.state == ASKING_LOCATION:
            torrent.state = KNOWN
            self.change_torrent_state(infohash, KNOWN, QUEUED)
        else:
            self._send_state(infohash)
            self._dump_state()

    def start_new_torrent_raw(self, data, save_as=None):
        try:
            metainfo = ConvertedMetainfo(bdecode(data))
            self.start_new_torrent(metainfo, save_as=save_as)
        except Exception, e:
            self.global_error(ERROR, _("This is not a valid torrent file. (%s)")
                              % str(e))

    def start_new_torrent(self, metainfo, save_as=None):
        t = TorrentInfo(Preferences(self.config))
        t.metainfo = metainfo
        infohash = t.metainfo.infohash
        if infohash in self.torrents:
            real_state = self.torrents[infohash].state
            if real_state in (RUNNING, RUN_QUEUED):
                self.error(t.metainfo, ERROR,
                           _("This torrent (or one with the same contents) is "
                             "already running."))
            elif real_state == QUEUED:
                self.error(t.metainfo, ERROR,
                           _("This torrent (or one with the same contents) is "
                             "already waiting to run."))
            elif real_state == ASKING_LOCATION:
                pass
            elif real_state == KNOWN:
                self.change_torrent_state(infohash, KNOWN, newstate=QUEUED)
            else:
                raise BTFailure(_("Torrent in unknown state %d") % real_state)
            return

        path = os.path.join(self.config['data_dir'], 'metainfo',
                            infohash.encode('hex'))
        try:
            f = file(path+'.new', 'wb')
            f.write(metainfo.to_data())
            f.close()
            shutil.move(path+'.new', path)
        except Exception, e:
            try:
                f.close()
            except:
                pass
            self.global_error(ERROR, _("Could not write file ") + path +
                              ' (' + str(e) + '), ' +
                              _("torrent will not be restarted "
                                "correctly on client restart"))

        config = configfile.read_torrent_config(self.config,
                                                self.config['data_dir'],
                                                infohash, self.global_error)
        if config:
            t.config.update(config)
        if save_as:
            t.dlpath = save_as
            # save_as is removed until it is properly implelented
##            self.run_ui_task(self.ui.set_config, 'save_as', save_as)
        else:
            save_as = None

        self.torrents[infohash] = t
        t.state = QUEUED

        # HACK because TQ is very broken
        self.queue.append(infohash)
        #self.other_torrents.append(infohash)

        self._dump_state()
        self.run_ui_task(self.ui.new_displayed_torrent, infohash,
                         t.metainfo, save_as, t.state, t.config)

        def show_error(level, text):
            self.run_ui_task(self.ui.error, infohash, level, text)
        t.metainfo.show_encoding_errors(show_error)

        # HACK because TQ is very broken
        self.change_torrent_state(infohash, QUEUED, RUNNING)

        # HACK because TQ is very broken
        self._dump_config()

    def set_config(self, option, value, ihash=None):
        if not ihash:
            oldvalue = self.config[option]
            self.config[option] = value
            self.multitorrent.set_option(option, value)
            if option == 'pause':
                if value:# and not oldvalue:
                    self.set_zero_running_torrents()
                elif not value:# and oldvalue:
                    self._check_queue()
            elif option == 'max_upload_rate':
                # This has a terrible bug, which is that it triggers
                # set_max_upload_rate which in turn calls this again.
                # The result is a flickering slider.
                #self.run_ui_task(self.ui.mainwindow.rate_slider_box.set_slider, value)
                pass
        else:
            torrent = self.torrents[ihash]
            if torrent.state == RUNNING:
                torrent.dl.set_option(option, value)
                if option in ('forwarded_port', 'maxport'):
                    torrent.dl.change_port()
            torrent.config[option] = value
        self._dump_config()

    def set_file_priority(self, infohash, filename, priority):
        torrent = self.torrents.get(infohash)
        if torrent is None or torrent.state != RUNNING:
            return
        torrent.dl.set_file_priority(filename, priority)

    def request_status(self, infohash, want_spew, want_fileinfo):
        torrent = self.torrents.get(infohash)
        if torrent is None or torrent.state != RUNNING:
            return
        status = torrent.dl.get_status(want_spew, want_fileinfo)
        if torrent.finishtime is not None:
            now = bttime()
            uptotal = status['upTotal'] + torrent.uptotal_old
            downtotal = status['downTotal'] + torrent.downtotal_old
            ulspeed = status['upRate2']
            if self.queue:
                ratio = torrent.dl.config['next_torrent_ratio'] / 100
                if torrent.dl.config['seed_forever']:
                    ratio = 1e99
            else:
                ratio = torrent.dl.config['last_torrent_ratio'] / 100
                if torrent.dl.config['seed_last_forever']:
                    ratio = 1e99
            if ulspeed <= 0 or ratio >= 1e99:
                rem = 1e99
            elif downtotal == 0:
                rem = (torrent.metainfo.total_bytes * ratio - uptotal) / ulspeed
            else:
                rem = (downtotal * ratio - uptotal) / ulspeed
            if self.queue and not torrent.dl.config['seed_forever']:
                rem = min(rem, torrent.finishtime +
                          torrent.dl.config['next_torrent_time'] * 60 - now)
            rem = max(rem, torrent.finishtime + 120 - now)
            if rem <= 0:
                rem = 1
            if rem >= 1e99:
                rem = None
            status['timeEst'] = rem
        self.run_ui_task(self.ui.update_status, infohash, status)

    def _get_list(self, state):
        if state == KNOWN:
            return self.other_torrents
        elif state == QUEUED:
            return self.queue
        elif state in (RUNNING, RUN_QUEUED):
            return self.running_torrents
        assert False

    def change_torrent_state(self, infohash, oldstate, newstate=None,
                     pred=None, succ=None, replaced=None, force_running=False):
        t = self.torrents.get(infohash)
        if t is None or (t.state != oldstate and not (t.state == RUN_QUEUED and
                                                      oldstate == RUNNING)):
            return
        if newstate is None:
            newstate = oldstate
        assert oldstate in (KNOWN, QUEUED, RUNNING)
        assert newstate in (KNOWN, QUEUED, RUNNING)
        pos = None
        if oldstate != RUNNING and newstate == RUNNING and replaced is None:
            if len(self.running_torrents) >= (force_running and self.config[
               'max_running_torrents'] or self.config['def_running_torrents']):
                if force_running:
                    self.global_error(ERROR,
                                      _("Can't run more than %d torrents "
                                        "simultaneously. For more info see the"
                                        " FAQ at %s.")%
                                      (self.config['max_running_torrents'],
                                       FAQ_URL))
                newstate = QUEUED
                pos = 0
        l = self._get_list(newstate)
        if newstate == oldstate:
            try:
                origpos = l.index(infohash)
            except IndexError, e:
                states = ['KNOWN', 'QUEUED', 'RUNNING']
                raise IndexError('%s: %s is not %s' % (e, infohash.encode('hex'), states[newstate]))
            del l[origpos]
            if pos is None:
                pos = decode_position(l, pred, succ, -1)
            if pos == -1 or l == origpos:
                l.insert(origpos, infohash)
                return
            l.insert(pos, infohash)
            self._dump_state()
            self.run_ui_task(self.ui.reorder_torrent, infohash, pos)
            return
        if pos is None:
            pos = decode_position(l, pred, succ)
        if newstate == RUNNING:
            newstate = RUN_QUEUED
            if replaced and len(self.running_torrents) >= \
               self.config['def_running_torrents']:
                t2 = self.torrents.get(replaced)
                if t2 is None or t2.state not in (RUNNING, RUN_QUEUED):
                    return
                if self.running_torrents.index(replaced) < pos:
                    pos -= 1
                if self._stop_running(replaced):
                    t2.state = QUEUED
                    self.queue.insert(0, replaced)
                    self._send_state(replaced)
                else:
                    self.other_torrents.append(replaced)
        if oldstate == RUNNING:
            if newstate == QUEUED and len(self.running_torrents) <= \
                   self.config['def_running_torrents'] and pos == 0:
                return
            if not self._stop_running(infohash):
                if newstate == KNOWN:
                    self.other_torrents.insert(pos, infohash)
                    self.run_ui_task(self.ui.reorder_torrent, infohash, pos)
                else:
                    self.other_torrents.append(infohash)
                return
        else:
            self._get_list(oldstate).remove(infohash)
        t.state = newstate
        l.insert(pos, infohash)
        self._check_queue()  # sends state if it starts the torrent from queue
        if t.state != RUNNING or newstate == RUN_QUEUED:
            self._send_state(infohash)
        self._dump_state()

    def set_zero_running_torrents(self):
        newrun = []
        for infohash in list(self.running_torrents):
            t = self.torrents[infohash]
            if self._stop_running(infohash):
                newrun.append(infohash)
                t.state = RUN_QUEUED
            else:
                self.other_torrents.append(infohash)
        self.running_torrents = newrun

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

    def failed(self, torrent, is_external):
        infohash = torrent.infohash
        if infohash == self.starting_torrent:
            self.starting_torrent = None
        self.running_torrents.remove(infohash)
        t = self.torrents[infohash]
        t.state = KNOWN
        if is_external:
            t.completion = self.multitorrent.get_completion(
                self.config, t.metainfo, t.dlpath)
        else:
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
        """called when a download reaches 100%"""
        infohash = torrent.infohash
        t = self.torrents[infohash]
        totals = t.dl.get_total_transfer()
        if t.downtotal == 0 and t.downtotal_old == 0 and totals[1] == 0:
            self.set_config('seed_forever', True, infohash)
            self.set_config('seed_last_forever', True, infohash)
            self.request_status(infohash, False, False)

        if infohash == self.starting_torrent:
            t = self.torrents[infohash]
            if self.queue:
                ratio = t.config['next_torrent_ratio'] / 100
                if t.config['seed_forever']:
                    ratio = 1e99
                msg = _("Not starting torrent as there are other torrents "
                        "waiting to run, and this one already meets the "
                        "settings for when to stop seeding.")
            else:
                ratio = t.config['last_torrent_ratio'] / 100
                if t.config['seed_last_forever']:
                    ratio = 1e99
                msg = _("Not starting torrent as it already meets the "
                        "settings for when to stop seeding the last "
                        "completed torrent.")
            if ratio < 1e99 and t.uptotal >= t.metainfo.total_bytes * ratio:
                raise BTShutdown(msg)
        self.torrents[torrent.infohash].finishtime = bttime()

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
        self.wrapped.rawserver.external_add_task(0, dummy)

    def __getattr__(self, attr):
        if attr in ('change_torrent_state', 'check_completion',
                    'remove_torrent', 'request_status',
                    'set_config', 'set_save_location',
                    'set_file_priority',
                    'start_new_torrent',
                    'send_gui_rates'):
            method = getattr(self.wrapped, attr)
            return lambda *a: self.wrapped.rawserver.external_add_task(0, method, *a)
