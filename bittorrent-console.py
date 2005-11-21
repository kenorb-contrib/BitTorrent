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

# Written by Bram Cohen, Uoti Urpala and John Hoffman

from __future__ import division

from BitTorrent.platform import install_translation
install_translation()

import sys
import os
import threading
from time import time, strftime
from cStringIO import StringIO

from BitTorrent.download import Feedback, Multitorrent
from BitTorrent.defaultargs import get_defaults
from BitTorrent.parseargs import printHelp
from BitTorrent.zurllib import urlopen
from BitTorrent.bencode import bdecode
from BitTorrent.ConvertedMetainfo import ConvertedMetainfo
from BitTorrent.prefs import Preferences
from BitTorrent import configfile
from BitTorrent import BTFailure
from BitTorrent import version
from BitTorrent import GetTorrent


def fmttime(n):
    if n == 0:
        return _("download complete!")
    try:
        n = int(n)
        assert n >= 0 and n < 5184000  # 60 days
    except:
        return _("<unknown>")
    m, s = divmod(n, 60)
    h, m = divmod(m, 60)
    return _("finishing in %d:%02d:%02d") % (h, m, s)

def fmtsize(n):
    s = str(n)
    size = s[-3:]
    while len(s) > 3:
        s = s[:-3]
        size = '%s,%s' % (s[-3:], size)
    if n > 999:
        unit = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
        i = 1
        while i + 1 < len(unit) and (n >> 10) >= 999:
            i += 1
            n >>= 10
        n /= (1 << 10)
        size = '%s (%.0f %s)' % (size, n, unit[i])
    return size


class HeadlessDisplayer(object):

    def __init__(self, doneflag):
        self.doneflag = doneflag

        self.done = False
        self.percentDone = ''
        self.timeEst = ''
        self.downRate = '---'
        self.upRate = '---'
        self.shareRating = ''
        self.seedStatus = ''
        self.peerStatus = ''
        self.errors = []
        self.file = ''
        self.downloadTo = ''
        self.fileSize = ''
        self.numpieces = 0

    def set_torrent_values(self, name, path, size, numpieces):
        self.file = name
        self.downloadTo = path
        self.fileSize = fmtsize(size)
        self.numpieces = numpieces

    def finished(self):
        self.done = True
        self.downRate = '---'
        self.display({'activity':_("download succeeded"), 'fractionDone':1})

    def error(self, errormsg):
        newerrmsg = strftime('[%H:%M:%S] ') + errormsg
        self.errors.append(newerrmsg)
        self.display({})

    def display(self, statistics):
        fractionDone = statistics.get('fractionDone')
        activity = statistics.get('activity')
        timeEst = statistics.get('timeEst')
        downRate = statistics.get('downRate')
        upRate = statistics.get('upRate')
        spew = statistics.get('spew')

        print '\n\n\n\n'
        if spew is not None:
            self.print_spew(spew)

        if timeEst is not None:
            self.timeEst = fmttime(timeEst)
        elif activity is not None:
            self.timeEst = activity

        if fractionDone is not None:
            self.percentDone = str(int(fractionDone * 1000) / 10)
        if downRate is not None:
            self.downRate = '%.1f KB/s' % (downRate / (1 << 10))
        if upRate is not None:
            self.upRate = '%.1f KB/s' % (upRate / (1 << 10))
        downTotal = statistics.get('downTotal')
        if downTotal is not None:
            upTotal = statistics['upTotal']
            if downTotal <= upTotal / 100:
                self.shareRating = _("oo  (%.1f MB up / %.1f MB down)") % (
                    upTotal / (1<<20), downTotal / (1<<20))
            else:
                self.shareRating = _("%.3f  (%.1f MB up / %.1f MB down)") % (
                   upTotal / downTotal, upTotal / (1<<20), downTotal / (1<<20))
            numCopies = statistics['numCopies']
            nextCopies = ', '.join(["%d:%.1f%%" % (a,int(b*1000)/10) for a,b in
                    zip(xrange(numCopies+1, 1000), statistics['numCopyList'])])
            if not self.done:
                self.seedStatus = _("%d seen now, plus %d distributed copies "
                                    "(%s)") % (statistics['numSeeds' ],
                                               statistics['numCopies'],
                                               nextCopies)
            else:
                self.seedStatus = _("%d distributed copies (next: %s)") % (
                    statistics['numCopies'], nextCopies)
            self.peerStatus = _("%d seen now") % statistics['numPeers']

        for err in self.errors[-4:]:
            print _("ERROR:\n") + err + '\n'
        print _("saving:        "), self.file
        print _("file size:     "), self.fileSize
        print _("percent done:  "), self.percentDone
        print _("time left:     "), self.timeEst
        print _("download to:   "), self.downloadTo
        print _("download rate: "), self.downRate
        print _("upload rate:   "), self.upRate
        print _("share rating:  "), self.shareRating
        print _("seed status:   "), self.seedStatus
        print _("peer status:   "), self.peerStatus

    def print_spew(self, spew):
        s = StringIO()
        s.write('\n\n\n')
        for c in spew:
            s.write('%20s ' % c['ip'])
            if c['initiation'] == 'L':
                s.write('l')
            else:
                s.write('r')
            total, rate, interested, choked = c['upload']
            s.write(' %10s %10s ' % (str(int(total/10485.76)/100),
                                     str(int(rate))))
            if c['is_optimistic_unchoke']:
                s.write('*')
            else:
                s.write(' ')
            if interested:
                s.write('i')
            else:
                s.write(' ')
            if choked:
                s.write('c')
            else:
                s.write(' ')

            total, rate, interested, choked, snubbed = c['download']
            s.write(' %10s %10s ' % (str(int(total/10485.76)/100),
                                     str(int(rate))))
            if interested:
                s.write('i')
            else:
                s.write(' ')
            if choked:
                s.write('c')
            else:
                s.write(' ')
            if snubbed:
                s.write('s')
            else:
                s.write(' ')
            s.write('\n')
        print s.getvalue()


class DL(Feedback):

    def __init__(self, metainfo, config):
        self.doneflag = threading.Event()
        self.metainfo = metainfo
        self.config = Preferences().initWithDict(config)

    def run(self):
        self.d = HeadlessDisplayer(self.doneflag)
        try:
            self.multitorrent = Multitorrent(self.config, self.doneflag,
                                             self.global_error)
            # raises BTFailure if bad
            metainfo = ConvertedMetainfo(bdecode(self.metainfo))
            torrent_name = metainfo.name_fs
            if config['save_as']:
                if config['save_in']:
                    raise BTFailure(_("You cannot specify both --save_as and "
                                      "--save_in"))
                saveas = config['save_as']
            elif config['save_in']:
                saveas = os.path.join(config['save_in'], torrent_name)
            else:
                saveas = torrent_name

            self.d.set_torrent_values(metainfo.name, os.path.abspath(saveas),
                                metainfo.total_bytes, len(metainfo.hashes))
            self.torrent = self.multitorrent.start_torrent(metainfo,
                                Preferences(self.config), self, saveas)
        except BTFailure, e:
            print str(e)
            return
        self.get_status()
        self.multitorrent.rawserver.install_sigint_handler()
        self.multitorrent.rawserver.listen_forever()
        self.d.display({'activity':_("shutting down"), 'fractionDone':0})
        self.torrent.shutdown()

    def reread_config(self):
        try:
            newvalues = configfile.get_config(self.config, 'bittorrent-console')
        except Exception, e:
            self.d.error(_("Error reading config: ") + str(e))
            return
        self.config.update(newvalues)
        # The set_option call can potentially trigger something that kills
        # the torrent (when writing this the only possibility is a change in
        # max_files_open causing an IOError while closing files), and so
        # the self.failed() callback can run during this loop.
        for option, value in newvalues.iteritems():
            self.multitorrent.set_option(option, value)
        for option, value in newvalues.iteritems():
            self.torrent.set_option(option, value)

    def get_status(self):
        self.multitorrent.rawserver.add_task(self.get_status,
                                             self.config['display_interval'])
        status = self.torrent.get_status(self.config['spew'])
        self.d.display(status)

    def global_error(self, level, text):
        self.d.error(text)

    def error(self, torrent, level, text):
        self.d.error(text)

    def failed(self, torrent, is_external):
        self.doneflag.set()

    def finished(self, torrent):
        self.d.finished()


if __name__ == '__main__':
    uiname = 'bittorrent-console'
    defaults = get_defaults(uiname)

    metainfo = None
    if len(sys.argv) <= 1:
        printHelp(uiname, defaults)
        sys.exit(1)
    try:
        config, args = configfile.parse_configuration_and_args(defaults,
                                       uiname, sys.argv[1:], 0, 1)

        torrentfile = None
        if len(args):
            torrentfile = args[0]
        for opt in ('responsefile', 'url'):
            if config[opt]:
                print '"--%s"' % opt, _("deprecated, do not use")
                torrentfile = config[opt]
        if torrentfile is not None:
            metainfo, errors = GetTorrent.get(torrentfile)
            if errors:
                raise BTFailure(_("Error reading .torrent file: ") + '\n'.join(errors))
        else:
            raise BTFailure(_("you must specify a .torrent file"))
    except BTFailure, e:
        print str(e)
        sys.exit(1)

    dl = DL(metainfo, config)
    dl.run()
