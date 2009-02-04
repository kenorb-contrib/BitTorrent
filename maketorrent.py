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

# Written by Matt Chisholm and Greg Hazel

from __future__ import division

app_name = "BitTorrent"
from BTL.translation import _

import os
import sys

assert sys.version_info >= (2, 3), _("Install Python %s or greater") % '2.3'

from threading import Event

from BitTorrent import version
from BitTorrent import configfile
from BitTorrent.GUI_wx import BTApp
from BitTorrent.GUI_wx.MakeTorrent import MakeTorrentWindow
from BitTorrent.UI import Size
from BitTorrent.defaultargs import get_defaults
from BitTorrent.makemetafile import make_meta_files
from BitTorrent.parseargs import makeHelp
from BitTorrent.platform import btspawn

import wx
import wx.grid

defaults = get_defaults('maketorrent')


def run(argv=[]):
    config, args = configfile.parse_configuration_and_args(defaults,
                                    'maketorrent', argv, 0, None)
    # BUG: hack to make verbose mode be the default
    config['verbose'] = not config['verbose']
    MainLoop(config)



class MainLoop(BTApp):

    def __init__(self, config):
        self.config = config
        self.main_window = None
        BTApp.__init__(self, 0)
        self.MainLoop()


    def OnInit(self):
        BTApp.OnInit(self)
        self.main_window = MakeTorrentWindow(None, self.config)
        return True




if __name__ == '__main__':
    run(argv=sys.argv[1:])
