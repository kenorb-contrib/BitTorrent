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

import wx
import sys
from BTL.ebencode import ebdecode

class GuiStats(object):

    def __init__(self, filename):
        data = open(filename, 'rb').read()
        self.data = ebdecode(data)
        
    def gui_print(self, tree, root):
        current_child = None
        for node in self.data:
            label = ' - '.join([ str(x) for x in node['l'] ])
            current_child = tree.AppendItem(root, label)
            for c in node['c']:
                label = ' - '.join([ str(x) for x in c ])
                tree.AppendItem(current_child, label)
                

class ProfileApp(wx.App):

    def __init__(self):
        wx.App.__init__(self, 0)

    def OnInit(self):
        f = wx.Frame(None)
        t = wx.TreeCtrl(f, style=0
                           | wx.TR_HAS_BUTTONS
                           | wx.TR_TWIST_BUTTONS
                           | wx.TR_FULL_ROW_HIGHLIGHT
                           #| wx.TR_HIDE_ROOT 
                           #| wx.TR_ROW_LINES
                           | wx.TR_MULTIPLE
                           | wx.TR_EXTENDED
                           #| wx.TR_NO_LINES
                           #| wx.NO_FULL_REPAINT_ON_RESIZE
                           | wx.CLIP_CHILDREN
                          ,)
            
        
        r = t.AddRoot("Profile")

        g = GuiStats(sys.argv[1])
        g.gui_print(t, r)
    
        t.Expand(r)
        f.Show(True)


        
        return True

if __name__ == '__main__':
    p = ProfileApp()
    
    p.MainLoop()