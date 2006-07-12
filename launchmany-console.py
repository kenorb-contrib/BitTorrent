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

if __name__ == '__main__':
    from BitTorrent.translation import _

import sys
import os

from BitTorrent.launchmanycore import LaunchMany
from BitTorrent.defaultargs import get_defaults
from BitTorrent.parseargs import parseargs, printHelp
from BitTorrent.prefs import Preferences
from BitTorrent import configfile
from BitTorrent import version
from BitTorrent import platform
from BitTorrent.platform import encode_for_filesystem, decode_from_filesystem
from BitTorrent import BTFailure
from BitTorrent import bt_log_fmt
import logging
from logging import ERROR, WARNING, INFO
from BitTorrent import console, old_stderr

exceptions = []

class HeadlessDisplayer:
    def display(self, data):
        # formats the data and dumps it to the root logger.
        print ''
        if not data:
            print _("no torrents")
        for x in data:
            ( name, status, progress, peers, seeds, seedsmsg, dist,
              uprate, dnrate, upamt, dnamt, size, t, msg ) = x
            logging.getLogger('').info(
                '"%s": "%s" (%s) - %sP%s%s%.3fD u%0.1fK/s-d%0.1fK/s u%dK-d%dK "%s"' % (
                name, status, progress, peers, seeds, seedsmsg, dist,
                uprate/1000, dnrate/1000, upamt/1024, dnamt/1024, msg))
        return False


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
        data_dir = [[name, value,doc] for (name, value, doc) in defaults
                        if name == "data_dir"][0]
        defaults = [(name, value,doc) for (name, value, doc) in defaults
                        if not name == "data_dir"]        
        ddir = os.path.join( platform.get_dot_dir(), "launchmany-console" )
        data_dir[1] = decode_from_filesystem(ddir)
        defaults.append( tuple(data_dir) )
        config, args = configfile.parse_configuration_and_args(defaults,
                                      uiname, sys.argv[1:], 0, 1)
        if args:
            torrent_dir = args[0]
            config['torrent_dir'] = \
                platform.decode_from_filesystem(torrent_dir)
        else:
            torrent_dir = config['torrent_dir']
            torrent_dir,bad = platform.encode_from_filesystem(torrent_dir)
            if bad:
              raise BTFailure(_("Warning: ")+config['torrent_dir']+
                              _(" is not a directory"))
            
        if not os.path.isdir(torrent_dir):
            raise BTFailure(_("Warning: ")+torrent_dir+
                            _(" is not a directory"))
    except BTFailure, e:
        print _("error: ") + unicode(e.args[0]) + \
              _("\nrun with no args for parameter explanations")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)

    d = HeadlessDisplayer()
    
    # install logger.
    #class LogHandler(logging.Handler):
    #    def __init__(self, level=logging.NOTSET):
    #        logging.Handler.__init__(self,level)
    #  
    #    def emit(self, record):
    #        print "LogHandler.emit ", record.getMessage()
    #        global d
    #        if record.exc_info is not None:
    #            print "LogHandler.emit: record.exc_info is not None."
    #            #d.exception( " %s: %s" % 
    #            #    ( str(record.exc_info[0]), str(record.exc_info[1])))
    #            tb = record.exc_info[2]
    #            stack = traceback.extract_tb(tb)
    #            l = traceback.format_list(stack)
    #            for s in l:
    #                d.exception(s)
    #        d.exception( record.getMessage() )

    #class LogFilter(logging.Filter):
    #    def filter( self, record):
    #        if record.name == "NatTraversal":
    #            return 0
    #        return 1  # allow.
    #
    #root_logger = logging.getLogger('')
    ##log_handler = LogHandler(0)
    #log_handler = logging.StreamHandler()
    #log_handler.setFormatter(bt_log_fmt)
    #log_handler.addFilter(LogFilter())
    #root_logger.addHandler(log_handler)

    # BitTorrent.__init__ installs a StderrProxy that replaces sys.stderr
    # and outputs all stderr output to the logger.  Output error log to
    # original stderr to avoid infinite loop.
    stderr_console = logging.StreamHandler(old_stderr)
    #stderr_console.setLevel(STDERR)
    stderr_console.setLevel(0)
    stderr_console.setFormatter(bt_log_fmt)
    logging.getLogger('').addHandler(stderr_console)
    config = Preferences().initWithDict(config)
    print "LaunchMany"

    #logging.getLogger().setLevel(INFO)
    logging.getLogger('').setLevel(0)
    
    LaunchMany(config, d.display, 'launchmany-console')
