#!/usr/bin/env python

# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by John Hoffman

import sys
import os

from BitTorrent.launchmanycore import LaunchMany
from BitTorrent.defaultargs import get_defaults
from BitTorrent.parseargs import parseargs, printHelp
from BitTorrent import configfile
from BitTorrent import version
from BitTorrent import BTFailure

exceptions = []

class HeadlessDisplayer:
    def display(self, data):
        print ''
        if not data:
            self.message('no torrents')
        for x in data:
            ( name, status, progress, peers, seeds, seedsmsg, dist,
              uprate, dnrate, upamt, dnamt, size, t, msg ) = x
            print '"%s": "%s" (%s) - %sP%s%s%.3fD u%0.1fK/s-d%0.1fK/s u%dK-d%dK "%s"' % (
                        name, status, progress, peers, seeds, seedsmsg, dist,
                        uprate/1000, dnrate/1000, upamt/1024, dnamt/1024, msg)
        return False

    def message(self, s):
        print "### "+s

    def exception(self, s):
        exceptions.append(s)
        self.message('SYSTEM ERROR - EXCEPTION GENERATED')


if __name__ == '__main__':
    uiname = 'btlaunchmany'
    defaults = get_defaults(uiname)
    try:
        if len(sys.argv) < 2:
            printHelp(uiname, defaults)
            sys.exit(1)
        config, args = configfile.parse_configuration_and_args(defaults,
                                      uiname, sys.argv[1:], 0, 1)
        if args:
            config['torrent_dir'] = args[0]
        if not os.path.isdir(config['torrent_dir']):
            raise BTFailure("Warning: "+args[0]+" is not a directory")
    except BTFailure, e:
        print 'error: ' + str(e) + '\nrun with no args for parameter explanations'
        sys.exit(1)

    LaunchMany(config, HeadlessDisplayer(), 'btlaunchmany')
    if exceptions:
        print '\nEXCEPTION:'
        print exceptions[0]
