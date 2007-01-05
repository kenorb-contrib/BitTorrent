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
