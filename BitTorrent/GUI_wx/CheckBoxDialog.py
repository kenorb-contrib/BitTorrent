# by Greg Hazel

import sys

from BitTorrent.GUI_wx import BTDialog, ElectroStaticText
from BitTorrent.GUI_wx import SPACING
import wx

class CheckBoxDialog(BTDialog):

    def __init__(self, parent, title, label, checkbox_label, checkbox_value):
	style=wx.DEFAULT_DIALOG_STYLE
	if sys.platform == 'darwin':
	    # no system menu or close box on the mac
	    style = wx.CAPTION|wx.CLOSE_BOX
        BTDialog.__init__(self, parent=parent, id=wx.ID_ANY, title=title, style=style)
        self.text = ElectroStaticText(self, label=label)

        self.checkbox = wx.CheckBox(self, label=checkbox_label)
        self.checkbox.SetValue(checkbox_value)

        try:
            bmp = wx.ArtProvider.GetBitmap(wx.ART_QUESTION,
                                           wx.ART_MESSAGE_BOX, (32, 32))
        except:
            bmp = wx.EmptyBitmap(32, 32)
            dc = wx.MemoryDC()
            dc.SelectObject(bmp)
            dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
            dc.Clear()
            dc.SelectObject(wx.NullBitmap)
        
        bmp = wx.StaticBitmap(self, wx.ID_ANY, bmp)
        
        # sizers
        self.button_sizer = self.CreateStdDialogButtonSizer(flags=wx.OK|wx.CANCEL)

        self.vsizer = wx.BoxSizer(wx.VERTICAL)
        self.hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        if '__WXMSW__' in wx.PlatformInfo:
            self.vsizer.Add(self.text, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_CENTER, border=5)
            self.vsizer.Add(self.checkbox, flag=wx.LEFT|wx.RIGHT|wx.TOP|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT, border=5)
            self.hsizer.Add(bmp)
            self.hsizer.Add(self.vsizer, flag=wx.LEFT|wx.TOP, border=12)
            self.sizer.Add(self.hsizer, flag=wx.ALL, border=11)
            self.sizer.Add(self.button_sizer, flag=wx.ALIGN_CENTER_HORIZONTAL|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=8)
        else:
            self.vsizer.Add(self.text, flag=wx.ALIGN_CENTER|wx.BOTTOM, border=SPACING)
            self.vsizer.Add(self.checkbox, flag=wx.ALIGN_LEFT, border=SPACING)
            self.hsizer.Add(bmp)
            self.hsizer.Add(self.vsizer, flag=wx.LEFT, border=SPACING)
            self.sizer.Add(self.hsizer, flag=wx.TOP|wx.LEFT|wx.RIGHT, border=SPACING)
            self.sizer.Add(self.button_sizer, flag=wx.ALIGN_RIGHT|wx.ALL, border=SPACING)

        self.SetSizer(self.sizer)
        self.Fit()


def LaunchCheckBoxDialog(parent, title, label, checkbox_label,
                         checkbox_value):
    """ default way to get a checkbox dialog and the value.
        returns:
          Cancel => wx.ID_CANCEL
          OK + checked => True
          OK + unchecked => False
    """
    dialog = CheckBoxDialog(parent, title, label, checkbox_label, checkbox_value)
    if dialog.ShowModal() == wx.ID_CANCEL:
        return wx.ID_CANCEL
    return dialog.checkbox.GetValue()
