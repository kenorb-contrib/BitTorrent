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
