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

# Written by Matt Chisholm and Greg Hazel

from __future__ import division

import os
import sys
try:
    from BitTorrent.translation import _
except ImportError:
    if os.name == 'posix':
        # Ugly Idiot-proofing -- this should stop ALL bug reports from
        # people unable to run BitTorrent after installation on Debian
        # and RedHat based systems.
        pythonversion = sys.version[:3]
        py24 = os.path.exists('/usr/lib/python2.4/site-packages/BitTorrent/')
        py23 = os.path.exists('/usr/lib/python2.3/site-packages/BitTorrent/')
        if not py24 and not py23:
            print "There is no BitTorrent package installed on this system."
        elif py24 and py23:
            print """
There is more than one BitTorrent package installed on this system,
at least one under Python 2.3 and at least one under Python 2.4."""
        else:
            print """
A BitTorrent package for the wrong version of Python is installed on this 
system.  The default version of Python on this system is %s.  However, the
BitTorrent package is installed under Python %s.""" % (pythonversion, (py24 and '2.4' or '2.3'))
        print """
        To install BitTorrent correctly you must first:

        * Remove *all* versions of BitTorrent currently installed.

        Then, you have two options:

        * Download and install the .deb or .rpm package for
          BitTorrent & Python %s
        * Download the source .tar.gz and follow the directions for
          installing under Python %s

        Visit http://www.bittorrent.com/ to download BitTorrent.
        """ % (pythonversion, pythonversion)
        sys.exit(1)
    else:
        raise


import time
import BitTorrent.stackthreading as threading
import random
from BitTorrent import atexit_threads
import logging

assert sys.version_info >= (2, 3), _("Install Python %s or greater") % '2.3'

from BitTorrent import BTFailure, app_name, inject_main_logfile, old_stderr

from BitTorrent import configfile

from BitTorrent.defer import DeferredEvent
from BitTorrent.defaultargs import get_defaults
from BitTorrent.IPC import ipc_interface
from BitTorrent.prefs import Preferences
from BitTorrent.platform import os_version, is_frozen_exe
from BitTorrent.RawServer_twisted import RawServer
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

    try:
        import psyco
        psyco.profile()
    except ImportError:
        pass

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

    # make sure we clean up the ipc when everything is done
    atexit_threads.register_verbose(ipc.stop)

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

    core_doneflag = DeferredEvent()

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

        rawserver_doneflag = DeferredEvent()
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
            mainloop.attach_multitorrent(ThreadProxy.ThreadProxy(multitorrent,
                                                                 gui_wrap),
                                         core_doneflag)

            ipc.start(mainloop.external_command)
            rawserver.associate_thread()

            def shutdown():
                df = multitorrent.shutdown()
                set_flag = lambda *a : rawserver_doneflag.set()
                df.addCallbacks(set_flag, set_flag)
                    
            rawserver.add_task(0, core_doneflag.addCallback, lambda r: rawserver.external_add_task(0, shutdown))
            rawserver.listen_forever(rawserver_doneflag)
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
