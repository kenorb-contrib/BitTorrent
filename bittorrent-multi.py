#!/usr/bin/env python

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

# Written by Greg Hazel

from __future__ import division

app_name = "BitTorrent"
import os
import sys
import time
import shutil
import logging
from BitTorrent.translation import _
assert sys.version_info >= (2, 4), _("Install Python %s or greater") % '2.4'
import BTL.stackthreading as threading
from BTL import atexit_threads
from BTL.defer import DeferredEvent
from BTL.yielddefer import wrap_task
from BTL.platform import efs2
from BitTorrent import zurllib
from BitTorrent import configfile
from BitTorrent import BTFailure, inject_main_logfile
from BitTorrent.IPC import ipc_interface
from BitTorrent.prefs import Preferences
from BitTorrent.platform import no_really_makedirs
from BitTorrent.defaultargs import get_defaults
from BitTorrent.RawServer_twisted import RawServer
from twisted.internet import task

defaults = get_defaults('bittorrent')
defaults.extend((('donated' , '', ''), # the version that the user last donated for
                 ('notified', '', ''), # the version that the user was last notified of
                 ))

defconfig = dict([(name, value) for (name, value, doc) in defaults])
del name, value, doc

inject_main_logfile()
global_logger = logging.getLogger('')
rawserver = None
from BitTorrent import stderr_console
stderr_console.setLevel(0)

NUM_PEERS = 10

if __name__ == '__main__':

    zurllib.add_unsafe_thread()

    try:
        config, args = configfile.parse_configuration_and_args(defaults,
                                        'bittorrent', sys.argv[1:], 0, None)
        config['upnp'] = False
        config['one_connection_per_ip'] = False
        config['log_tracker_info'] = True
        config['rerequest_interval'] = 5
        config['min_peers'] = NUM_PEERS # -1 for self but +1 for the http seed
        config['start_trackerless_client'] = False
        config['max_download_rate'] = 180*1024
        config['max_upload_rate'] = 30*1024
        config['max_files_open'] = 1
    except BTFailure, e:
        print unicode(e.args[0])
        sys.exit(1)

    rawserver = RawServer(Preferences().initWithDict(dict(config)))
    zurllib.set_zurllib_rawserver(rawserver)
    rawserver.install_sigint_handler()



from BitTorrent.MultiTorrent import MultiTorrent
from BTL.ThreadProxy import ThreadProxy
from BitTorrent.TorrentButler import DownloadTorrentButler, SeedTorrentButler
from BTL.formatters import Rate, Size, Duration

class ODict(dict):
    def __getattr__(self, attr):
        return self.get(attr)

def format_status(status):
    s = ODict(status)
    spew = s.get('spew') or []
    return ('%.2f%% eta:%s dr:%s ur:%s d:%s u:%s p%s' %
            (s.fractionDone * 100.0,
             str(Duration(s.timeEst)).split(' ', 1)[0],
             str(Rate(s.downRate)).replace(' ', ''),
             str(Rate(s.upRate)).replace(' ', ''),
             str(Size(s.downTotal)).replace(' ', ''),
             str(Size(s.upTotal)).replace(' ', ''),
             len(spew)))

def print_status(ms):
    print '-' * 79
    for m in ms:
        #print m._id
        for t in m.get_torrents():
            status = t.get_status(config.get('spew', True))
            print m._id, m.singleport_listener.port,
            print t.metainfo.name, t.state[0], format_status(status)

def create_multitorrent(config, rawserver, i):
    config = Preferences().initWithDict(dict(config))
    config['data_dir'] = config['data_dir'] + ("_%s" % i)
    if os.path.exists(config['data_dir']):
        shutil.rmtree(config['data_dir'])
    for d in ('', 'resume', 'metainfo', 'torrents'):
        ddir = os.path.join(config['data_dir'], d)
        no_really_makedirs(ddir)
    multitorrent = MultiTorrent(config, rawserver, config['data_dir'],
                                init_torrents=False)

    # Butlers
    multitorrent.add_policy(DownloadTorrentButler(multitorrent))
    multitorrent.add_policy(SeedTorrentButler(multitorrent))

    # register shutdown action
    def shutdown():
        df = multitorrent.shutdown()
        stop_rawserver = lambda r : rawserver.stop()
        df.addCallbacks(stop_rawserver, stop_rawserver)
    rawserver.add_task(0, core_doneflag.addCallback,
                       lambda r: rawserver.external_add_task(0, shutdown))
    return multitorrent

if __name__ == '__main__':
    print rawserver.reactor

    try:
        import psyco
        import traceback
        psyco.cannotcompile(traceback.print_stack)
        psyco.cannotcompile(traceback.format_stack)
        psyco.cannotcompile(traceback.extract_stack)
        psyco.bind(RawServer.listen_forever)
        from BTL import sparse_set
        psyco.bind(sparse_set.SparseSet)
        from BitTorrent import PiecePicker
        psyco.bind(PiecePicker.PieceBuckets)
        psyco.bind(PiecePicker.PiecePicker)
        from BitTorrent import PieceSetBuckets
        psyco.bind(PieceSetBuckets.PieceSetBuckets)
        psyco.bind(PieceSetBuckets.SortedPieceBuckets)
        from BTL import bitfield
        psyco.bind(bitfield.Bitfield)
    except ImportError:
        pass

    #import memleak_detection
    #memleak_detection.begin_sampling('memleak_sample.log')

    config['start_time'] = time.time()

    core_doneflag = DeferredEvent()

    ms = []
    try:
        print args
        for i in xrange(NUM_PEERS):
            multitorrent = create_multitorrent(config, rawserver, i)
            multitorrent._id = i
            ms.append(multitorrent)
            for t in args:
                p = multitorrent.config['data_dir']
                p = os.path.join(p, '%s.dat' % i)
                multitorrent.create_torrent_non_suck(efs2(t), efs2(p))

        task.LoopingCall(print_status, ms).start(5)

        rawserver.listen_forever()

    except:
        for m in ms:
            ddir = m.config['data_dir']
            if os.path.exists(ddir):
                shutil.rmtree(ddir)

        # oops, we failed.
        # one message for the log w/ exception info
        global_logger.exception("BitTorrent core initialization failed!")
        # one message for the user w/o info
        global_logger.critical("BitTorrent core initialization failed!")

        core_doneflag.set()
        rawserver.stop()
        raise


