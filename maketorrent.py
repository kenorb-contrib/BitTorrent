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
