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

app_name = "BitTorrent"

import os
import sys
try:
    from BitTorrent.translation import _
except ImportError, e:
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
import BTL.stackthreading as threading
import logging
debug=False
#debug=True
from BTL import atexit_threads

assert sys.version_info >= (2, 3), _("Install Python %s or greater") % '2.3'

from BitTorrent import BTFailure, inject_main_logfile
from BitTorrent import configfile

from BTL.defer import DeferredEvent, wrap_task
from BitTorrent.defaultargs import get_defaults
from BitTorrent.IPC import ipc_interface
from BitTorrent.prefs import Preferences
from BitTorrent.RawServer_twisted import RawServer
if os.name == 'nt':
    from BitTorrent.platform import win_version_num
from BitTorrent import zurllib

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

    psyco = None
    try:
        # 95, 98, and ME seem to have problems with psyco
        # so only import it on NT and up
        # and only if we're not using python 2.5, becuase it's broken
        if (os.name == 'nt' and win_version_num >= (2, 4, 0) and
            sys.version_info < (2, 5)):
            import psyco_BROKEN
            import traceback
            psyco.cannotcompile(traceback.print_stack)
            psyco.cannotcompile(traceback.format_stack)
            psyco.cannotcompile(traceback.extract_stack)
            #psyco.full(memory=10)
            psyco.bind(RawServer.listen_forever)
            from BTL import sparse_set
            psyco.bind(sparse_set.SparseSet)
            from BitTorrent import PiecePicker
            psyco.bind(PiecePicker.PieceBuckets)
            psyco.bind(PiecePicker.PiecePicker)
            from BitTorrent import PieceSetBuckets
            psyco.bind(PieceSetBuckets.PieceSetBuckets)
            psyco.bind(PieceSetBuckets.SortedPieceBuckets)
            psyco.profile(memorymax=30000) # that's 30MB for the whole process
            #psyco.log()
            # see below for more
    except ImportError:
        pass

    zurllib.add_unsafe_thread()

    try:
        config, args = configfile.parse_configuration_and_args(defaults,
                                        'bittorrent', sys.argv[1:], 0, None)
        if debug:
            config['upnp'] = False
            config['one_connection_per_ip'] = False

    except BTFailure, e:
        print unicode(e.args[0])
        sys.exit(1)

    config = Preferences().initWithDict(config)
    # bug set in DownloadInfoFrame

    rawserver = RawServer(config)
    zurllib.set_zurllib_rawserver(rawserver)
    rawserver.install_sigint_handler()

    ipc = ipc_interface(rawserver, config, "controlsocket")

    # make sure we clean up the ipc when everything is done
    atexit_threads.register_verbose(ipc.stop)

    # this could be on the ipc object
    ipc_master = True
    try:
        if not config['use_factory_defaults']:
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
from BTL.ThreadProxy import ThreadProxy
from BitTorrent.TorrentButler import DownloadTorrentButler, SeedTorrentButler
from BitTorrent.AutoUpdateButler import AutoUpdateButler
from BitTorrent.GUI_wx.DownloadManager import MainLoop
from BitTorrent.GUI_wx import gui_wrap

def gmtime():
    return time.mktime(time.gmtime())

if __name__ == '__main__':

    #import memleak_detection
    #memleak_detection.begin_sampling('memleak_sample.log')

    if psyco:
        psyco.bind(MainLoop.run)

    config['start_time'] = gmtime()
    mainloop = MainLoop(config)

    def init_core(mainloop):

        core_doneflag = DeferredEvent()

        class UILogger(logging.Handler):
            def emit(self, record):
                msg = "[%s] %s" % (record.name, self.format(record))
                gui_wrap(mainloop.do_log, record.levelno, msg)

        logging.getLogger('').addHandler(UILogger())

        try:
            multitorrent = MultiTorrent(config, rawserver, config['data_dir'],
                                        listen_fail_ok=True,
                                        init_torrents=False)

            # Butlers            
            multitorrent.add_policy(DownloadTorrentButler(multitorrent))
            multitorrent.add_policy(SeedTorrentButler(multitorrent))
            auto_update_butler = AutoUpdateButler(multitorrent, rawserver,
                                                  test_new_version=config['new_version'],
                                                  test_current_version=config['current_version'])
            multitorrent.add_auto_update_policy(auto_update_butler)

            # attach to the UI
            tpm = ThreadProxy(multitorrent,
                              gui_wrap,
                              wrap_task(rawserver.external_add_task))
            mainloop.attach_multitorrent(tpm, core_doneflag)
            ipc.start(mainloop.external_command)
            #rawserver.associate_thread()

            # register shutdown action
            def shutdown():
                df = multitorrent.shutdown()
                stop_rawserver = lambda r : rawserver.stop()
                df.addCallbacks(stop_rawserver, stop_rawserver)
            rawserver.add_task(0, core_doneflag.addCallback,
                               lambda r: rawserver.external_add_task(0, shutdown))

            rawserver.listen_forever()

        except:
            # oops, we failed.
            # one message for the log w/ exception info
            global_logger.exception("BitTorrent core initialization failed!")
            # one message for the user w/o info
            global_logger.critical("BitTorrent core initialization failed!")

            core_doneflag.set()
            rawserver.stop()
            try:
                gui_wrap(mainloop.ExitMainLoop)
            except:
                pass
            try:
                gui_wrap(mainloop.doneflag.set)
            except:
                pass
            raise


    threading.Thread(target=init_core, args=(mainloop,)).start()
    
    mainloop.append_external_torrents(*args)

##    # cause memleak stuff to be imported
##    import code
##    import sizer
##    
##    from sizer import annotate
##    from sizer import formatting
##    from sizer import operations
##    from sizer import rules
##    from sizer import scanner
##    from sizer import set
##    from sizer import sizes
##    from sizer import wrapper
    
    try:
        mainloop.run()
    except KeyboardInterrupt:
        # the gui main loop is closed in MainLoop
        pass
