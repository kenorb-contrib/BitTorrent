#!/usr/bin/env python

# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Uoti Urpala and Matt Chisholm

from __future__ import division

from BitTorrent.translation import _

import sys
import os
import BitTorrent.stackthreading as threading
import random
import atexit
import logging

assert sys.version_info >= (2, 3), _("Install Python %s or greater") % '2.3'

from BitTorrent import BTFailure, app_name, inject_main_logfile, old_stderr

from BitTorrent import configfile

from BitTorrent.defaultargs import get_defaults
from BitTorrent.IPC import ipc_interface
from BitTorrent.prefs import Preferences
from BitTorrent.platform import os_version, is_frozen_exe
from BitTorrent.RawServer_twisted import RawServer, task
from BitTorrent import zurllib
from BitTorrent import GetTorrent

defaults = get_defaults('bittorrent')
defaults.extend((('donated' , '', ''), # the version that the user last donated for
                 ('notified', '', ''), # the version that the user was last notified of
                 ))

defconfig = dict([(name, value) for (name, value, doc) in defaults])
del name, value, doc

inject_main_logfile()
global_logger = logging.getLogger('')
rawserver = None

if __name__ == '__main__':

    #try:
    #    import psyco
    #    psyco.profile()
    #except ImportError:
    #    pass

    zurllib.add_unsafe_thread()

    try:
        config, args = configfile.parse_configuration_and_args(defaults,
                                        'bittorrent', sys.argv[1:], 0, None)
    except BTFailure, e:
        print str(e)
        sys.exit(1)

    config = Preferences().initWithDict(config)
    # bug set in DownloadInfoFrame

    rawserver = RawServer(config, tos=config['peer_socket_tos'])
    zurllib.set_zurllib_rawserver(rawserver)
    rawserver.install_sigint_handler()

    ipc = ipc_interface(rawserver, config, "controlsocket")

    # make sure we clean up the ipc when we close
    atexit.register(ipc.stop)

    # this could be on the ipc object
    ipc_master = True
    try:
        ipc.create()
    except BTFailure, e:
        ipc_master = False
        try:
            ipc.send_command('no-op')
            if config['publish']:
                assert len(args) == 1
                ipc.send_command('publish_torrent', args[0], config['publish'])
                sys.exit(0)
                
            elif args:
                for arg in args:
                    ipc.send_command('start_torrent', arg)
                sys.exit(0)

            ipc.send_command('show_error', _("%s already running")%app_name)

        except BTFailure:
            global_logger.error((_("Failed to communicate with another %s process "
                                     "but one seems to be running.") % app_name) +
                                   (_(" Closing all %s windows may fix the problem.")
                                    % app_name))
        sys.exit(1)



from BitTorrent.MultiTorrent import MultiTorrent
from BitTorrent import ThreadProxy
from BitTorrent.TorrentButler import DownloadTorrentButler, SeedTorrentButler
from BitTorrent.AutoUpdateButler import AutoUpdateButler
from BitTorrent.GUI_wx.DownloadManager import MainLoop
from BitTorrent.GUI_wx import gui_wrap
from BitTorrent import platform
#from BitTorrent.GUI_gtk import MainLoop, gui_wrap
#from BitTorrent.FeedManager import FeedManager

if __name__ == '__main__':

    #import memleak_detection
    #memleak_detection.begin_sampling('memleak_sample.log')

    core_doneflag = threading.Event()

    mainloop = MainLoop(config)

    def init_core(mainloop):
        # BUG figure out feed config situation
        #feedmanager = FeedManager({}, gui_wrap)

        class UILogger(logging.Handler):
            def emit(self, record):
                # prevent feedback. this can go away when the UI logs directly
                # to the logging system, and the wx calls are just used to
                # display all the message this handler receives.
                msg = "[%s] " % record.name
                msg += self.format(record)
                gui_wrap(mainloop.do_log, record.levelno, msg)

        logging.getLogger('').addHandler(UILogger())

        data_dir = config['data_dir']

        rawserver_doneflag = threading.Event()
        try:
            multitorrent = MultiTorrent(config, core_doneflag, rawserver,
                                        data_dir, listen_fail_ok=True,
                                        init_torrents=False)
            multitorrent.add_policy(DownloadTorrentButler(multitorrent))
            multitorrent.add_policy(SeedTorrentButler(multitorrent))

            auto_update_butler = AutoUpdateButler(multitorrent, rawserver,
                                                  test_new_version=config['new_version'],
                                                  test_current_version=config['current_version'])
            multitorrent.add_auto_update_policy(auto_update_butler)
            rawserver.add_task(0, auto_update_butler.check_version)
            gui_wrap(mainloop.attach_multitorrent,
                     ThreadProxy.ThreadProxy(multitorrent, gui_wrap),
                     core_doneflag)

            ipc.start(mainloop.external_command)
            rawserver.associate_thread()

            l = None
            def shutdown():
                if core_doneflag.isSet():
                    df = multitorrent.shutdown()
                    set_flag = lambda *a : rawserver_doneflag.set()
                    df.addCallbacks(set_flag, set_flag)
                    l.stop()
                    
            l = task.LoopingCall(shutdown)
            rawserver.add_task(0, l.start, 1)
            rawserver.listen_forever(rawserver_doneflag)

            ipc.stop()
        except:
            # oops, we failed.
            # one message for the log w/ exception info
            global_logger.exception("BitTorrent core initialization failed!")
            # one message for the user w/o info
            global_logger.critical("BitTorrent core initialization failed!")
            
            core_doneflag.set()
            rawserver_doneflag.set()
            try:
                gui_wrap(mainloop.ExitMainLoop)
            except:
                pass
            try:
                gui_wrap(mainloop.doneflag.set)
            except:
                pass
            raise


    corethread = threading.Thread(target = init_core,
                                  args = (mainloop,))

    corethread.setDaemon(False)
    corethread.start()

    mainloop.append_external_torrents(*args)

    try:
        mainloop.run()
    except KeyboardInterrupt:
        # the gui main loop is closed in MainLoop
        pass

