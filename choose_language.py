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

app_name = "BitTorrent"
from BitTorrent.translation import _


import os

from BitTorrent.GUI_wx import BTApp, BTFrameWithSizer
from BitTorrent.GUI_wx.LanguageSettings import LanguageSettings

import wx

class Frame(BTFrameWithSizer):
    panel_class = LanguageSettings

    def __init__(self, *a, **k):
        BTFrameWithSizer.__init__(self, *a, **k)
        self.Fit()


class App(BTApp):

    def OnInit(self):
        ret = BTApp.OnInit(self)
        f = Frame(None, wx.ID_ANY, "%s Language" % app_name,
                  style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.SYSTEM_MENU|wx.CAPTION|wx.CLOSE_BOX|wx.CLIP_CHILDREN|wx.RESIZE_BORDER)
        f.Show()
        return ret


a = App()
a.MainLoop()
