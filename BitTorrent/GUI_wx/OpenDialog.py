import wx
from BTL.translation import _
from BitTorrent.GUI_wx import BTDialog, text_wrappable, ElectroStaticBitmap

ID_COMBOBOX = wx.NewId()
ID_BROWSE = wx.NewId()

class OpenDialog(BTDialog):
    
    def __init__(self, parent, bitmap, browse, history, *a, **kw):
        BTDialog.__init__(self, parent, *a, **kw)

        itemDialog1 = self
        self.browse_func = browse

        itemFlexGridSizer2 = wx.FlexGridSizer(3, 1, 3, 0)
        itemFlexGridSizer2.AddGrowableCol(0)
        itemDialog1.SetSizer(itemFlexGridSizer2)

        itemFlexGridSizer3 = wx.FlexGridSizer(2, 2, 21, 0)
        itemFlexGridSizer3.AddGrowableCol(1)
        itemFlexGridSizer2.Add(itemFlexGridSizer3, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        itemStaticBitmap4Bitmap = bitmap
        #itemStaticBitmap4 = wx.StaticBitmap(itemDialog1, wx.ID_STATIC, itemStaticBitmap4Bitmap)
        itemStaticBitmap4 = ElectroStaticBitmap(itemDialog1, itemStaticBitmap4Bitmap)
        itemFlexGridSizer3.Add(itemStaticBitmap4, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        itemStaticText5 = wx.StaticText( itemDialog1, wx.ID_STATIC, _("Enter the URL or path to a torrent file on the Internet, your computer, or your network that you want to add."), wx.DefaultPosition, wx.DefaultSize, 0 )
        if text_wrappable: itemStaticText5.Wrap(286)
        itemFlexGridSizer3.Add(itemStaticText5, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.ADJUST_MINSIZE, 7)

        itemStaticText6 = wx.StaticText( itemDialog1, wx.ID_STATIC, _("Open:"), wx.DefaultPosition, wx.DefaultSize, 0 )
        itemFlexGridSizer3.Add(itemStaticText6, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.ADJUST_MINSIZE, 5)

        choiceboxStrings = history
        self.choicebox = wx.ComboBox( itemDialog1, ID_COMBOBOX, choices=choiceboxStrings, size=(267, -1), style=wx.CB_DROPDOWN|wx.TE_PROCESS_ENTER )
        self.choicebox.Bind(wx.EVT_TEXT, self.OnText)
        self.choicebox.Bind(wx.EVT_COMBOBOX, self.OnComboBox)
        self.choicebox.Bind(wx.EVT_TEXT_ENTER, self.OnTextEnter)
        itemFlexGridSizer3.Add(self.choicebox, 1, wx.ALIGN_CENTER_HORIZONTAL|wx.GROW|wx.ALL, 5)

        itemBoxSizer8 = wx.BoxSizer(wx.HORIZONTAL)
        itemFlexGridSizer2.Add(itemBoxSizer8, 0, wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM|wx.TOP|wx.BOTTOM, 1)

        itemFlexGridSizer9 = wx.FlexGridSizer(2, 3, 0, 2)
        itemFlexGridSizer9.AddGrowableRow(0)
        itemBoxSizer8.Add(itemFlexGridSizer9, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 7)

        itemBoxSizer10 = wx.BoxSizer(wx.HORIZONTAL)
        itemFlexGridSizer9.Add(itemBoxSizer10, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 2)

        self.okbutton = wx.Button(itemDialog1, wx.ID_OK)
        itemBoxSizer10.Add(self.okbutton, 0, wx.GROW|wx.ALL|wx.SHAPED, 0)

        itemBoxSizer12 = wx.BoxSizer(wx.HORIZONTAL)
        itemFlexGridSizer9.Add(itemBoxSizer12, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 2)

        itemButton13 = wx.Button(itemDialog1, wx.ID_CANCEL)
        itemBoxSizer12.Add(itemButton13, 0, wx.GROW|wx.ALL|wx.SHAPED, 0)

        itemBoxSizer14 = wx.BoxSizer(wx.HORIZONTAL)
        itemFlexGridSizer9.Add(itemBoxSizer14, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 2)

        itemButton15 = wx.Button( itemDialog1, ID_BROWSE, _("&Browse"), wx.DefaultPosition, wx.DefaultSize, 0 )
        itemButton15.Bind(wx.EVT_BUTTON, self.browse)
        itemBoxSizer14.Add(itemButton15, 0, wx.GROW|wx.ALL|wx.SHAPED, 0)

        self.okbutton.Disable()
        self.Fit()

    def _OnChange(self, v):
        self.okbutton.Enable(bool(v))

    def OnText(self, event):
        self._OnChange(self.GetValue())

    def OnComboBox(self, event):
        wx.CallAfter(self._OnChange, event.GetString())

    def OnTextEnter(self, event):
        v = self.GetValue()
        if v:
            self.EndModal(wx.ID_OK)

    def GetValue(self):
        return self.choicebox.GetValue()

    def browse(self, event):
        self.EndModal(wx.ID_CANCEL)
        self.browse_func()

