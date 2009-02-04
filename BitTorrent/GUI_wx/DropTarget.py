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

# simple, proper file drop target

import wx

class FileDropTarget(wx.FileDropTarget):
    def __init__(self, window, callback):
        wx.FileDropTarget.__init__(self)
        self.window = window
        self.callback = callback

    def OnDragOver(self, a, b, c):
        self.window.SetCursor(wx.StockCursor(wx.CURSOR_COPY_ARROW))
        return wx.DragCopy

    def OnEnter(self, x, y, d):
        self.window.SetCursor(wx.StockCursor(wx.CURSOR_COPY_ARROW))

    def OnLeave(self):
        self.window.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))

    def OnDropFiles(self, x, y, filenames):
        self.window.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
        for file in filenames:
            self.callback(file)
