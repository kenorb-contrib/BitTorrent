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

# Written by John Hoffman
# Updated to 4.20 by David Harrison

app_name = "BitTorrent"
if __name__ == '__main__':
    from BTL.translation import _

import sys
import os

from BitTorrent import platform
from BitTorrent.launchmanycore import LaunchMany
from BitTorrent.defaultargs import get_defaults
from BitTorrent.parseargs import parseargs, printHelp
from BitTorrent.prefs import Preferences
from BitTorrent import configfile
from BitTorrent import version
from BTL.platform import encode_for_filesystem, decode_from_filesystem
from BitTorrent import BTFailure
from BitTorrent import bt_log_fmt
from BTL.log import injectLogger
import logging
from logging import ERROR, WARNING, INFO
from BitTorrent import console, old_stderr, STDERR

exceptions = []

log = logging.getLogger('launchmany-console')

class HeadlessDisplayer:
    def display(self, data):
        # formats the data and dumps it to the root logger.
        if not data:
            log.info( _("no torrents"))
        elif type(data) == str:
            log.info(data)
        else:
            for x in data:
                ( name, status, progress, peers, seeds, seedsmsg,
                  uprate, dnrate, upamt, dnamt, size, t, msg ) = x
                logging.getLogger('launchmany-console').info(
                    '"%s": "%s" (%s) - %sP%s%s u%0.1fK/s-d%0.1fK/s u%dK-d%dK "%s"' % (
                    name, status, progress, peers, seeds, seedsmsg,
                    uprate/1000, dnrate/1000, upamt/1024, dnamt/1024, msg))
        return False

def modify_default( defaults_tuplelist, key, newvalue ):
    name,value,doc = [(n,v,d) for (n,v,d) in defaults_tuplelist if n == key][0]
    defaults_tuplelist = [(n,v,d) for (n,v,d) in defaults_tuplelist
                    if not n == key]
    defaults_tuplelist.append( (key,newvalue,doc) )
    return defaults_tuplelist


if __name__ == '__main__':
    uiname = 'launchmany-console'
    defaults = get_defaults(uiname)
    try:
        if len(sys.argv) < 2:
            printHelp(uiname, defaults)
            sys.exit(1)

        # Modifying default values from get_defaults is annoying...
        # Implementing specific default values for each uiname in
        # defaultargs.py is even more annoying.  --Dave
        ddir = os.path.join( platform.get_dot_dir(), "launchmany-console" )
        ddir = decode_from_filesystem(ddir)
        modify_default(defaults, 'data_dir', ddir)
        config, args = configfile.parse_configuration_and_args(defaults,
                                      uiname, sys.argv[1:], 0, 1)

        # returned from here config['save_in'] is /home/dave/Desktop/...
        if args:
            torrent_dir = args[0]
            config['torrent_dir'] = torrent_dir
        else:
            torrent_dir = config['torrent_dir']
            torrent_dir,bad = encode_for_filesystem(torrent_dir)
            if bad:
              raise BTFailure(_("Warning: ")+config['torrent_dir']+
                              _(" is not a directory"))

        if not os.path.isdir(torrent_dir):
            raise BTFailure(_("Warning: ")+torrent_dir+
                            _(" is not a directory"))

        # the default behavior is to save_in files to the platform
        # get_save_dir.  For launchmany, if no command-line argument
        # changed the save directory then use the torrent directory.
        #if config['save_in'] == platform.get_save_dir():
        #    config['save_in'] = config['torrent_dir']
        if '--save_in' in sys.argv:
            print "Don't use --save_in for launchmany-console.  Saving files from " \
                  "many torrents in the same directory can result in filename collisions."
            sys.exit(1)
        # The default 'save_in' is likely to be something like /home/myname/BitTorrent Downloads
        # but we would prefer that the 'save_in' be an empty string so that
        # LaunchMany will save the file in the same location as the destination for the file.
        # When downloading or seeding a large number of files we want to be sure there are
        # no file name collisions which can occur when the same save_in directory is used for
        # all torrents.  When 'save in' is empty, the destination of the filename is used, which
        # for save_as style 4 (the default) will be in the same directory as the .torrent file.
        # If each .torrent file is in its own directory then filename collisions cannot occur.
        config['save_in'] = u""

    except BTFailure, e:
        print _("error: ") + unicode(e.args[0]) + \
              _("\nrun with no args for parameter explanations")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)

    d = HeadlessDisplayer()
    config = Preferences().initWithDict(config)
    injectLogger(use_syslog = False, capture_output = True, verbose = True,
                 log_level = logging.INFO, log_twisted = False )
    logging.getLogger('').removeHandler(console)  # remove handler installed by BitTorrent.__init__.
    LaunchMany(config, d.display, 'launchmany-console')

    logging.getLogger("").critical( "After return from LaunchMany" )

    # Uncomment the following if it looks like threads are hanging around.
    # monitor_thread can be found in cdv://cdv.bittorrent.com:6602/python-scripts
    #import threading
    #nondaemons = [d for d in threading.enumerate() if not d.isDaemon()]
    #if len(nondaemons) > 1:
    #    import time
    #    from monitor_thread import print_stacks
    #    time.sleep(4)
    #    nondaemons = [d for d in threading.enumerate() if not d.isDaemon()]
    #    if len(nondaemons) > 1:
    #        print_stacks()


