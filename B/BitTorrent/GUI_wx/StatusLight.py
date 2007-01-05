# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Matt Chisholm

import wx

from BitTorrent.StatusLight import StatusLight as _StatusLight

class StatusLight(wx.Panel, _StatusLight):

    def __init__(self, parent, wxid=wx.ID_ANY):
        images = {}
        tips = {}
        a = wx.GetApp()
        for k in self.states.keys():
            i = a.theme_library.get(('statuslight', self.states[k][0]))
            b = wx.BitmapFromImage(i)
            images[k] = b

        _StatusLight.__init__(self)
        wx.Panel.__init__(self, parent, id=wxid, style=wx.NO_BORDER)
        self.SetSize(wx.Size(24,24))
        self.bitmap = wx.StaticBitmap(self, wx.ID_ANY)

        self.images = images
        self.tips = tips

        self.Fit()

        self.change_state()


    def change_state(self):
        state = self.mystate
        assert self.states.has_key(state)

        self.bitmap.SetBitmap(self.images[state])
        self.SetToolTipString(self.get_tip())
        
class StatusLabel(_StatusLight):
    pass    
