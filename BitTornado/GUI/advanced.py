# Written by Myers Carpenter and John Hoffman
# Modifications by various people
# see LICENSE.txt for license information

from wxPython.wx import *
from common import FONT, ICON, _StaticText
from exception import exception
from BitTornado.clock import clock

try:
    True
except:
    True = 1
    False = 0

class ReannounceLast:
    last = 0
    def check(self):
        if self.last+60 < clock():
            self.last = clock()
            return True
        return False
reannouncelast = ReannounceLast()

def comma_format(s):
    r = str(s)
    for i in range(len(r)-3, 0, -3):
        r = r[:i]+','+r[i:]
    return(r)

class ExternalAnnounceBox:
    
    def __init__(self, reannounce)
        self.reannouncefunc = reannouncefunc
        self.lastexternalannounce = ''
        
        self.frame = wxFrame(None, -1, 'External Announce', size = (1,1))
        if ICON():
            self.frame.SetIcon(ICON())

        panel = wxPanel(self.frame, -1)

        fullsizer = wxFlexGridSizer(cols = 1, vgap = 13)
        msg = wxStaticText(panel, -1, "Enter tracker anounce URL:")
#            msg.SetFont(FONT())
        fullsizer.Add(msg)

        self.advexturl = wxTextCtrl(parent = panel, id = -1, value = '',
                            size = (255, 20), style = wxTE_PROCESS_TAB)
        self.advexturl.SetFont(FONT())
        self.advexturl.SetValue(self.lastexternalannounce)
        fullsizer.Add(self.advexturl)

        buttonSizer = wxFlexGridSizer (cols = 2, hgap = 10)

        okButton = wxButton(panel, -1, 'OK')
#            okButton.SetFont(FONT())
        buttonSizer.Add (okButton)

        cancelButton = wxButton(panel, -1, 'Cancel')
#            cancelButton.SetFont(FONT())
        buttonSizer.Add (cancelButton)

        fullsizer.Add (buttonSizer, 0, wxALIGN_CENTER)

        border = wxBoxSizer(wxHORIZONTAL)
        border.Add(fullsizer, 1, wxEXPAND | wxALL, 4)

        panel.SetSizer(border)
        panel.SetAutoLayout(True)

        EVT_BUTTON(self.advextannouncebox, okButton.GetId(), self.ok)
        EVT_BUTTON(self.advextannouncebox, cancelButton.GetId(), self.close)
        EVT_CLOSE(self.advextannouncebox, self.close)

        self.frame.Show()
        fullsizer.Fit(panel)
        self.frame.Fit()

    
    def ok(self, evt):
        try:
            special = self.advexturl.GetValue()
            if special:
                self.lastexternalannounce = special
                if reannouncelast.check():
                    self.reannouncefunc(special)
            self.close()
        except:
            exception()

    def close(self, evt=None):
        if self.frame:
            self.frame.Destroy()
            self.frame = None



class AdvancedInfoBox:

    def __init__(self, reannouncefunc = None, bgallocfunc = None, closefunc = None):
        self.reannouncefunc = reannouncefunc
        self.bgallocfunc = bgallocfunc
        self.closefunc = closefunc
        self.advextannouncebox = None
        
        self.frame = wxFrame(None, -1, 'BitTorrent Advanced', size = wxSize(200,200))
        if ICON():
            self.frame.SetIcon(ICON())

        panel = wxPanel(self.frame, -1, size = wxSize (200,200))

        StaticText = _StaticText(panel)

        colSizer = wxFlexGridSizer (cols = 1, vgap = 1)
        colSizer.Add (StaticText('Advanced Info for ' + self.filename, +4))

        try:    # get system font width
            fw = wxSystemSettings_GetFont(wxSYS_DEFAULT_GUI_FONT).GetPointSize()+1
        except:
            fw = wxSystemSettings_GetFont(wxSYS_SYSTEM_FONT).GetPointSize()+1

        spewList = wxListCtrl(panel, -1, wxPoint(-1,-1), (fw*66,350), wxLC_REPORT|wxLC_HRULES|wxLC_VRULES)
        self.spewList = spewList
        spewList.SetAutoLayout (True)

        colSizer.Add(spewList, -1, wxEXPAND)

        colSizer.Add(StaticText(''))
        self.storagestats1 = StaticText('')
        self.storagestats2 = StaticText('')
        colSizer.Add(self.storagestats1, -1, wxEXPAND)
        colSizer.Add(self.storagestats2, -1, wxEXPAND)
        colSizer.Add(StaticText(''))

        buttonSizer = wxFlexGridSizer (cols = 5, hgap = 20)

        reannounceButton = wxButton(panel, -1, 'Manual Announce')
#        reannounceButton.SetFont(FONT())
        buttonSizer.Add (reannounceButton)

        extannounceButton = wxButton(panel, -1, 'External Announce')
#        extannounceButton.SetFont(FONT())
        buttonSizer.Add (extannounceButton)

        bgallocButton = wxButton(panel, -1, 'Finish Allocation')
#        bgallocButton.SetFont(FONT())
        buttonSizer.Add (bgallocButton)

        buttonSizer.Add(StaticText(''))

        okButton = wxButton(panel, -1, 'Ok')
#        okButton.SetFont(FONT())
        buttonSizer.Add (okButton)

        colSizer.Add (buttonSizer, 0, wxALIGN_CENTER)
#        colSizer.SetMinSize ((578,350))
        colSizer.AddGrowableCol(0)
        colSizer.AddGrowableRow(1)

        panel.SetSizer(colSizer)
        panel.SetAutoLayout(True)

        spewList.InsertColumn(0, "Optimistic Unchoke", format=wxLIST_FORMAT_CENTER, width=fw*2)
        spewList.InsertColumn(1, "Peer ID", width=0)
        spewList.InsertColumn(2, "IP", width=fw*11)
        spewList.InsertColumn(3, "Local/Remote", format=wxLIST_FORMAT_CENTER, width=fw*3)
        spewList.InsertColumn(4, "Up", format=wxLIST_FORMAT_RIGHT, width=fw*6)
        spewList.InsertColumn(5, "Interested", format=wxLIST_FORMAT_CENTER, width=fw*2)
        spewList.InsertColumn(6, "Choking", format=wxLIST_FORMAT_CENTER, width=fw*2)
        spewList.InsertColumn(7, "Down", format=wxLIST_FORMAT_RIGHT, width=fw*6)
        spewList.InsertColumn(8, "Interesting", format=wxLIST_FORMAT_CENTER, width=fw*2)
        spewList.InsertColumn(9, "Choked", format=wxLIST_FORMAT_CENTER, width=fw*2)
        spewList.InsertColumn(10, "Snubbed", format=wxLIST_FORMAT_CENTER, width=fw*2)
        spewList.InsertColumn(11, "Downloaded", format=wxLIST_FORMAT_RIGHT, width=fw*7)
        spewList.InsertColumn(12, "Uploaded", format=wxLIST_FORMAT_RIGHT, width=fw*7)
        spewList.InsertColumn(13, "Completed", format=wxLIST_FORMAT_RIGHT, width=fw*6)
        spewList.InsertColumn(14, "Peer Download Speed", format=wxLIST_FORMAT_RIGHT, width=fw*6)

        EVT_BUTTON(self.frame, reannounceButton.GetId(), self.reannounce)
        EVT_BUTTON(self.frame, extannounceButton.GetId(), self.reannounce_external)
        EVT_BUTTON(self.frame, bgallocButton.GetId(), self.bgalloc)
        EVT_BUTTON(self.frame, okButton.GetId(), self.close)
        EVT_CLOSE(self.frame, self.close)

        self.frame.Show ()
        colSizer.Fit(panel)
        self.frame.Fit()

    def reannounce(self, evt):
        try:
            if reannouncelast.check():
                self.reannouncefunc()
        except:
            exception()

    def reannounce_external(self, evt):
        try:
            if self.advextannouncebox:
                self.advextannouncebox.close()
            self.advextannouncebox = ExternalAnnounceBox(self.reannouncefunc)
        except:
            exception()

    def bgalloc(self, evt):
        try:
            if self.bgallocfunc:
                self.bgallocfunc()
        except:
            exception()

    def close(self, evt=None):
        if self.frame:
            self.frame.Destroy()
            self.frame = None
        if self.advextannouncebox:
            self.advextannouncebox.close()
            self.advextannouncebox = None
        if self.closefunc:
            self.closefunc()


    def update_spew(self, spew, kicked = [], banned = []):
        if not self.frame:
            return

        spewList = self.spewList
        spewlen = len(spew)+2
        if statistics is not None:
            kickbanlen = len(kicked)+len(banned)
            if kickbanlen:
                spewlen += kickbanlen+1
        else:
            kickbanlen = 0
        while spewlen < spewList.GetItemCount():
            i = wxListItem()
#                   i.SetFont(self.default_font)
            spewList.InsertItem(i)
        while spewlen > spewList.GetItemCount():
            spewList.DeleteItem(len(spew)+1)

        tot_uprate = 0.0
        tot_downrate = 0.0
        for x in range(len(spew)):
            if (spew[x]['optimistic'] == 1):
                a = '*'
            else:
                a = ' '
            spewList.SetStringItem(x, 0, a)
            spewList.SetStringItem(x, 1, spew[x]['id'])
            spewList.SetStringItem(x, 2, spew[x]['ip'])
            spewList.SetStringItem(x, 3, spew[x]['direction'])
            if spew[x]['uprate'] > 100:
                spewList.SetStringItem(x, 4, '%.0f kB/s' % (float(spew[x]['uprate']) / 1000))
            else:
                spewList.SetStringItem(x, 4, ' ')
            tot_uprate += spew[x]['uprate']
            if (spew[x]['uinterested'] == 1):
                a = '*'
            else:
                a = ' '
            spewList.SetStringItem(x, 5, a)
            if (spew[x]['uchoked'] == 1):
                a = '*'
            else:
                a = ' '
            spewList.SetStringItem(x, 6, a)

            if spew[x]['downrate'] > 100:
                spewList.SetStringItem(x, 7, '%.0f kB/s' % (float(spew[x]['downrate']) / 1000))
            else:
                spewList.SetStringItem(x, 7, ' ')
            tot_downrate += spew[x]['downrate']

            if (spew[x]['dinterested'] == 1):
                a = '*'
            else:
                a = ' '
            spewList.SetStringItem(x, 8, a)
            if (spew[x]['dchoked'] == 1):
                a = '*'
            else:
                a = ' '
            spewList.SetStringItem(x, 9, a)
            if (spew[x]['snubbed'] == 1):
                a = '*'
            else:
                a = ' '
            spewList.SetStringItem(x, 10, a)
            spewList.SetStringItem(x, 11, '%.2f MiB' % (float(spew[x]['dtotal']) / (1 << 20)))
            if spew[x]['utotal'] is not None:
                a = '%.2f MiB' % (float(spew[x]['utotal']) / (1 << 20))
            else:
                a = ''
            spewList.SetStringItem(x, 12, a)
            spewList.SetStringItem(x, 13, '%.1f%%' % (float(int(spew[x]['completed']*1000))/10))
            if spew[x]['speed'] is not None:
                a = '%.0f kB/s' % (float(spew[x]['speed']) / 1000)
            else:
                a = ''
            spewList.SetStringItem(x, 14, a)
        
        x = len(spew)
        for i in range(15):
            spewList.SetStringItem(x, i, '')

        x += 1
        spewList.SetStringItem(x, 2, '         TOTALS:')
        spewList.SetStringItem(x, 4, '%.0f kB/s' % (float(tot_uprate) / 1000))
        spewList.SetStringItem(x, 7, '%.0f kB/s' % (float(tot_downrate) / 1000))
        if statistics is not None:
            spewList.SetStringItem(x, 11, '%.2f MiB' % (float(statistics.downTotal) / (1 << 20)))
            spewList.SetStringItem(x, 12, '%.2f MiB' % (float(statistics.upTotal) / (1 << 20)))
        else:
            spewList.SetStringItem(x, 11, '')
            spewList.SetStringItem(x, 12, '')
        for i in [0,1,3,5,6,8,9,10,13,14]:
            spewList.SetStringItem(x, i, '')

        if kickbanlen:
            x += 1
            for i in range(14):
                spewList.SetStringItem(x, i, '')

            for peer in kicked:
                x += 1
                spewList.SetStringItem(x, 2, peer[0])
                spewList.SetStringItem(x, 1, peer[1])
                spewList.SetStringItem(x, 4, 'KICKED')
                for i in [0,3,5,6,7,8,9,10,11,12,13,14]:
                    spewList.SetStringItem(x, i, '')

            for peer in banned:
                x += 1
                spewList.SetStringItem(x, 2, peer[0])
                spewList.SetStringItem(x, 1, peer[1])
                spewList.SetStringItem(x, 4, 'BANNED')
                for i in [0,3,5,6,7,8,9,10,11,12,13,14]:
                    spewList.SetStringItem(x, i, '')


    def update_stats(self, stats):
        if not self.frame:
            return

        l1 = ( '          ' +
               'currently downloading %d pieces (%d just started), ' +
               '%d pieces partially retrieved'
               % ( statistics.storage_active,
                   statistics.storage_new,
                   statistics.storage_dirty ) )
        if statistics.storage_isendgame:
                    l1 += ', endgame mode'
        self.storagestats2.SetLabel(l1)
        l2 = ( '          ' +
               '%d of %d pieces complete (%d just downloaded), ' +
               '%d failed hash check, %sKiB redundant data discarded'
               % ( statistics.storage_numcomplete,
                   statistics.storage_totalpieces,
                   statistics.storage_justdownloaded,
                   statistics.storage_numflunked,
                   comma_format(int(statistics.discarded/1024)) ) )
        self.storagestats1.SetLabel(l2)

