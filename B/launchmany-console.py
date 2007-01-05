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
import logging
from logging import ERROR, WARNING, INFO
from BitTorrent import console, old_stderr, STDERR

exceptions = []

class HeadlessDisplayer:
    def display(self, data):
        # formats the data and dumps it to the root logger.
        #print ''
        if not data:
            logging.getLogger('launchmany-console').info( _("no torrents"))
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
        if config['save_in'] == platform.get_save_dir():
            config['save_in'] = config['torrent_dir']
    except BTFailure, e:
        print _("error: ") + unicode(e.args[0]) + \
              _("\nrun with no args for parameter explanations")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)

    d = HeadlessDisplayer()
    
    # BitTorrent.__init__ installs a StderrProxy that replaces sys.stderr
    # and outputs all stderr output to the logger.  Output error log to
    # original stderr to avoid infinite loop.
    stderr_console = logging.StreamHandler(old_stderr)
    stderr_console.setLevel(STDERR)
    stderr_console.setFormatter(bt_log_fmt)
    logging.getLogger('').addHandler(stderr_console)
    logging.getLogger().setLevel(STDERR)
    logging.getLogger().removeHandler(console)

    # more liberal with logging launchmany-console specific output.
    lmany_logger = logging.getLogger('launchmany-console')
    lmany_handler = logging.StreamHandler(old_stderr)
    lmany_handler.setFormatter(bt_log_fmt)
    lmany_handler.setLevel(INFO)
    lmany_logger.setLevel(INFO)
    lmany_logger.addHandler(lmany_handler)
    
    config = Preferences().initWithDict(config)
    LaunchMany(config, d.display, 'launchmany-console')
