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
