#!/usr/bin/env python

# Written by Bram Cohen and Myers Carpenter
# Modifications by various people
# see LICENSE.txt for license information

from BitTorrent import PSYCO
if PSYCO.psyco:
    try:
        import psyco
        assert psyco.__version__ >= 0x010100f0
        psyco.full()
    except:
        pass

from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

from BitTorrent.download import Download
from BitTorrent.ConnChoice import *
from BitTorrent.ConfigReader import configReader
from BitTorrent.bencode import bencode
from threading import Event, Thread
from os.path import *
from os import getcwd
from wxPython.wx import *
from time import strftime, time, localtime
from webbrowser import open_new
from traceback import print_exc
from StringIO import StringIO
from sha import sha
import re
import sys, os
from BitTorrent import version

true = 1
false = 0

PROFILER = false

basepath=os.path.abspath(os.path.dirname(sys.argv[0]))

def hours(n):
    if n == -1:
        return '<unknown>'
    if n == 0:
        return 'complete!'
    n = int(n)
    h, r = divmod(n, 60 * 60)
    m, sec = divmod(r, 60)
    if h > 1000000:
        return '<unknown>'
    if h > 0:
        return '%d hour(s) %02d min %02d sec' % (h, m, sec)
    else:
        return '%d min %02d sec' % (m, sec)

def size_format(s):
    if (s < 1024):
        r = str(s) + 'B'
    elif (s < 1048576):
        r = str(int(s/1024)) + 'KiB'
    elif (s < 1073741824L):
        r = str(int(s/1048576)) + 'MiB'
    elif (s < 1099511627776L):
        r = str(int((s/1073741824.0)*100.0)/100.0) + 'GiB'
    else:
        r = str(int((s/1099511627776.0)*100.0)/100.0) + 'TiB'
    return(r)

def comma_format(s):
    r = str(s)
    for i in range(len(r)-3, 0, -3):
        r = r[:i]+','+r[i:]
    return(r)

wxEVT_INVOKE = wxNewEventType()

def EVT_INVOKE(win, func):
    win.Connect(-1, -1, wxEVT_INVOKE, func)

class InvokeEvent(wxPyEvent):
    def __init__(self, func = None, args = None, kwargs = None):
        wxPyEvent.__init__(self)
        self.SetEventType(wxEVT_INVOKE)
        self.func = func
        self.args = args
        self.kwargs = kwargs

def pr(event):
    print 'augh!'


class DownloadInfoFrame:
    def __init__(self, flag, configfile):
        try:
            self.FONT = configfile.configfileargs['gui_font']
            self.default_font = wxFont(self.FONT, wxDEFAULT, wxNORMAL, wxNORMAL, false)
            frame = wxFrame(None, -1, 'BitTorrent ' + version + ' download')
            self.aaa = 0
            self.flag = flag
            self.uiflag = Event()
            self.fin = false
            self.aboutBox = None
            self.detailBox = None
            self.advBox = None
            self.creditsBox = None
            self.statusIconHelpBox = None
            self.reannouncelast = 0
            self.spinlock = 0
            self.scrollock = 0
            self.lastError = 0
            self.spewwait = time()
            self.config = None
            self.updateSpinnerFlag = 0
            self.updateSliderFlag = 0
            self.statusIconValue = ' '
            self.iconized = 0
            self.checking = None
            self.activity = 'Starting up...'
            self.firstupdate = true
            self.shuttingdown = false
            self.ispaused = false
            self.bgalloc_periods = 0
            self.gui_lastupdate = time()
            self.gui_fractiondone = None
            self.fileList = None
            self.lastexternalannounce = ''
            self.refresh_details = false
            self._errorwindow = None
            self.lastuploadsettings = 0
            self.filename = None
            if sys.platform == 'win32':
                self.invokeLaterEvent = InvokeEvent()
                self.invokeLaterList = []

            wxInitAllImageHandlers()
            self.statusIcons={
                'startup':wxIcon(os.path.join(basepath,'white.ico'), wxBITMAP_TYPE_ICO),
                'disconnected':wxIcon(os.path.join(basepath,'black.ico'), wxBITMAP_TYPE_ICO),
                'noconnections':wxIcon(os.path.join(basepath,'red.ico'), wxBITMAP_TYPE_ICO),
                'nocompletes':wxIcon(os.path.join(basepath,'blue.ico'), wxBITMAP_TYPE_ICO),
                'noincoming':wxIcon(os.path.join(basepath,'yellow.ico'), wxBITMAP_TYPE_ICO),
                'allgood':wxIcon(os.path.join(basepath,'green.ico'), wxBITMAP_TYPE_ICO)
                }

            self.filestatusIcons = wxImageList(16, 16)
            self.filestatusIcons.Add(wxBitmap(os.path.join(basepath,'black1.ico'),wxBITMAP_TYPE_ICO))
            self.filestatusIcons.Add(wxBitmap(os.path.join(basepath,'yellow1.ico'), wxBITMAP_TYPE_ICO))
            self.filestatusIcons.Add(wxBitmap(os.path.join(basepath,'green1.ico'), wxBITMAP_TYPE_ICO))

            self.allocbuttonBitmap = wxBitmap(os.path.join(basepath,'alloc.gif'), wxBITMAP_TYPE_GIF)

            if (sys.platform == 'win32'):
                self.icon = wxIcon(os.path.join(basepath,'icon_bt.ico'), wxBITMAP_TYPE_ICO)
            self.starttime = time ()

            self.frame = frame
            if (sys.platform == 'win32'):
                self.frame.SetIcon(self.icon)

            panel = wxPanel(frame, -1)

            def StaticText(text, font = self.FONT, underline = false, color = None, panel = panel):
                x = wxStaticText(panel, -1, text, style = wxALIGN_LEFT)
                x.SetFont(wxFont(font, wxDEFAULT, wxNORMAL, wxNORMAL, underline))
                if color is not None:
                    x.SetForegroundColour(color)
                return x

            colSizer = wxFlexGridSizer(cols = 1, vgap = 3)

            border = wxBoxSizer(wxHORIZONTAL)
            border.Add(colSizer, 1, wxEXPAND | wxALL, 4)
            panel.SetSizer(border)
            panel.SetAutoLayout(true)

            topboxsizer = wxFlexGridSizer(cols = 3, vgap = 0)
            topboxsizer.AddGrowableCol (0)

            fnsizer = wxFlexGridSizer(cols = 1, vgap = 0)
            fnsizer.AddGrowableCol (0)
            fnsizer.AddGrowableRow (1)

            fileNameText = StaticText('', self.FONT+4)
            fnsizer.Add(fileNameText, 1, wxALIGN_BOTTOM|wxEXPAND)
            self.fileNameText = fileNameText

            fnsizer2 = wxFlexGridSizer(cols = 8, vgap = 0)
            fnsizer2.AddGrowableCol (0)

            fileSizeText = StaticText('')
            fnsizer2.Add(fileSizeText, 1, wxALIGN_BOTTOM|wxEXPAND)
            self.fileSizeText = fileSizeText

            fileDetails = StaticText('Details', self.FONT, true, 'Blue')
            fnsizer2.Add(fileDetails, 0, wxALIGN_BOTTOM)                                     

            fnsizer2.Add(StaticText('  '))

            advText = StaticText('Advanced', self.FONT, true, 'Blue')
            fnsizer2.Add(advText, 0, wxALIGN_BOTTOM)
            fnsizer2.Add(StaticText('  '))

            prefsText = StaticText('Prefs', self.FONT, true, 'Blue')
            fnsizer2.Add(prefsText, 0, wxALIGN_BOTTOM)
            fnsizer2.Add(StaticText('  '))

            aboutText = StaticText('About', self.FONT, true, 'Blue')
            fnsizer2.Add(aboutText, 0, wxALIGN_BOTTOM)

            fnsizer2.Add(StaticText('  '))
            fnsizer.Add(fnsizer2,0,wxEXPAND)
            topboxsizer.Add(fnsizer,0,wxEXPAND)
            topboxsizer.Add(StaticText('  '))

            self.statusIcon = wxEmptyBitmap(32,32)
            statidata = wxMemoryDC()
            statidata.SelectObject(self.statusIcon)
            statidata.SetPen(wxTRANSPARENT_PEN)
            statidata.SetBrush(wxBrush(wx.wxSystemSettings_GetColour(wxSYS_COLOUR_MENU),wxSOLID))
            statidata.DrawRectangle(0,0,32,32)
            self.statusIconPtr = wxStaticBitmap(panel, -1, self.statusIcon)
            topboxsizer.Add(self.statusIconPtr)

            self.fnsizer = fnsizer
            self.fnsizer2 = fnsizer2
            self.topboxsizer = topboxsizer
            colSizer.Add(topboxsizer, 0, wxEXPAND)

            self.gauge = wxGauge(panel, -1, range = 1000, style = wxGA_SMOOTH)
            colSizer.Add(self.gauge, 0, wxEXPAND)
#        self.gauge.SetForegroundColour(wx.wxSystemSettings_GetColour(wxSYS_COLOUR_3DSHADOW))

            timeSizer = wxFlexGridSizer(cols = 2)
            timeSizer.Add(StaticText('Time elapsed / estimated : '))
            self.timeText = StaticText(self.activity+'                    ')
            timeSizer.Add(self.timeText)
            timeSizer.AddGrowableCol(1)
            colSizer.Add(timeSizer)

            destSizer = wxFlexGridSizer(cols = 2, hgap = 8)
            self.fileDestLabel = StaticText('Download to:')
            destSizer.Add(self.fileDestLabel)
            self.fileDestText = StaticText('')
            destSizer.Add(self.fileDestText, flag = wxEXPAND)
            destSizer.AddGrowableCol(1)
            colSizer.Add(destSizer, flag = wxEXPAND)
            self.destSizer = destSizer

            statSizer = wxFlexGridSizer(cols = 3, hgap = 8)

            self.ratesSizer = wxFlexGridSizer(cols = 2)
            self.infoSizer = wxFlexGridSizer(cols = 2)

            self.ratesSizer.Add(StaticText('   Download rate: '))
            self.downRateText = StaticText('0 kB/s       ')
            self.ratesSizer.Add(self.downRateText, flag = wxEXPAND)

            self.downTextLabel = StaticText('Downloaded: ')
            self.infoSizer.Add(self.downTextLabel)
            self.downText = StaticText('0.00 MiB        ')
            self.infoSizer.Add(self.downText, flag = wxEXPAND)

            self.ratesSizer.Add(StaticText('   Upload rate: '))
            self.upRateText = StaticText('0 kB/s       ')
            self.ratesSizer.Add(self.upRateText, flag = wxEXPAND)

            self.upTextLabel = StaticText('Uploaded: ')
            self.infoSizer.Add(self.upTextLabel)
            self.upText = StaticText('0.00 MiB        ')
            self.infoSizer.Add(self.upText, flag = wxEXPAND)

            shareSizer = wxFlexGridSizer(cols = 2, hgap = 8)
            shareSizer.Add(StaticText('Share rating:'))
            self.shareRatingText = StaticText('')
            shareSizer.AddGrowableCol(1)
            shareSizer.Add(self.shareRatingText, flag = wxEXPAND)

            statSizer.Add(self.ratesSizer)
            statSizer.Add(self.infoSizer)
            statSizer.Add(shareSizer, flag = wxALIGN_CENTER_VERTICAL)
            colSizer.Add (statSizer)

            torrentSizer = wxFlexGridSizer(cols = 1)
            self.peerStatusText = StaticText('')
            torrentSizer.Add(self.peerStatusText, 0, wxEXPAND)
            self.seedStatusText = StaticText('')
            torrentSizer.Add(self.seedStatusText, 0, wxEXPAND)
            torrentSizer.AddGrowableCol(0)
            colSizer.Add(torrentSizer, 0, wxEXPAND)
            self.torrentSizer = torrentSizer

            self.errorTextSizer = wxFlexGridSizer(cols = 1)
            self.errorText = StaticText('', self.FONT, false, 'Red')
            self.errorTextSizer.Add(self.errorText, 0, wxEXPAND)
            colSizer.Add(self.errorTextSizer, 0, wxEXPAND)

            cancelSizer=wxGridSizer(cols = 2, hgap = 40)
            self.pauseButton = wxButton(panel, -1, 'Pause')
#        self.pauseButton.SetFont(self.default_font)
            cancelSizer.Add(self.pauseButton, 0, wxALIGN_CENTER)

            self.cancelButton = wxButton(panel, -1, 'Cancel')
#        self.cancelButton.SetFont(self.default_font)
            cancelSizer.Add(self.cancelButton, 0, wxALIGN_CENTER)
            colSizer.Add(cancelSizer, 0, wxALIGN_CENTER)

            # Setting options

            slideSizer = wxFlexGridSizer(cols = 7, hgap = 0, vgap = 5)

            # dropdown

            self.connChoiceLabel = StaticText('Settings for ')
            slideSizer.Add (self.connChoiceLabel, 0, wxALIGN_LEFT|wxALIGN_CENTER_VERTICAL)
            self.connChoice = wxChoice (panel, -1, (-1, -1), (self.FONT*11, -1),
                                        choices = connChoiceList)
            self.connChoice.SetFont(self.default_font)
            self.connChoice.SetSelection(0)
            slideSizer.Add (self.connChoice, 0, wxALIGN_CENTER)
            self.rateSpinnerLabel = StaticText(' Upload rate (kB/s) ')
            slideSizer.Add (self.rateSpinnerLabel, 0, wxALIGN_RIGHT|wxALIGN_CENTER_VERTICAL)

            # max upload rate

            self.rateSpinner = wxSpinCtrl (panel, -1, "", (-1,-1), (50, -1))
            self.rateSpinner.SetFont(self.default_font)
            self.rateSpinner.SetRange(0,5000)
            self.rateSpinner.SetValue(0)
            slideSizer.Add (self.rateSpinner, 0, wxALIGN_CENTER|wxALIGN_CENTER_VERTICAL)

            self.rateLowerText = StaticText('  %5d' % (0))
            self.rateUpperText = StaticText('%5d' % (5000))
            self.rateslider = wxSlider(panel, -1, 0, 0, 5000, (-1, -1), (80, -1))

            slideSizer.Add(self.rateLowerText, 0, wxALIGN_RIGHT|wxALIGN_CENTER_VERTICAL)
            slideSizer.Add(self.rateslider,    0, wxALIGN_CENTER|wxALIGN_CENTER_VERTICAL)
            slideSizer.Add(self.rateUpperText, 0, wxALIGN_LEFT|wxALIGN_CENTER_VERTICAL)

            slideSizer.Add(StaticText(''), 0, wxALIGN_LEFT)

            self.bgallocText = StaticText('', self.FONT+2, false, 'Red')
            slideSizer.Add(self.bgallocText, 0, wxALIGN_LEFT)

            # max uploads

            self.connSpinnerLabel = StaticText(' Max uploads ')
            slideSizer.Add (self.connSpinnerLabel, 0, wxALIGN_RIGHT|wxALIGN_CENTER_VERTICAL)
            self.connSpinner = wxSpinCtrl (panel, -1, "", (-1,-1), (50, -1))
            self.connSpinner.SetFont(self.default_font)
            self.connSpinner.SetRange(4,100)
            self.connSpinner.SetValue(4)
            slideSizer.Add (self.connSpinner, 0, wxALIGN_CENTER|wxALIGN_CENTER_VERTICAL)

            self.connLowerText = StaticText('  %5d' % (4))
            self.connUpperText = StaticText('%5d' % (100))
            self.connslider = wxSlider(panel, -1, 4, 4, 100, (-1, -1), (80, -1))

            slideSizer.Add(self.connLowerText, 0, wxALIGN_RIGHT|wxALIGN_CENTER_VERTICAL)
            slideSizer.Add(self.connslider,    0, wxALIGN_CENTER|wxALIGN_CENTER_VERTICAL)
            slideSizer.Add(self.connUpperText, 0, wxALIGN_LEFT|wxALIGN_CENTER_VERTICAL)

            colSizer.Add(slideSizer, 1, wxALL|wxALIGN_CENTER|wxEXPAND, 0)

            self.unlimitedLabel = StaticText('0 kB/s means unlimited. Tip: your download rate is proportional to your upload rate', self.FONT-2)
            colSizer.Add(self.unlimitedLabel, 0, wxALIGN_CENTER)

            EVT_LEFT_DOWN(aboutText, self.about)
            EVT_LEFT_DOWN(fileDetails, self.details)
            EVT_LEFT_DOWN(self.statusIconPtr,self.statusIconHelp)
            EVT_LEFT_DOWN(advText, self.advanced)
            EVT_LEFT_DOWN(prefsText, self.openConfigMenu)
            EVT_CLOSE(frame, self.done)
            EVT_BUTTON(frame, self.pauseButton.GetId(), self.pause)
            EVT_BUTTON(frame, self.cancelButton.GetId(), self.done)
            EVT_INVOKE(frame, self.onInvoke)
            EVT_SCROLL(self.rateslider, self.onRateScroll)
            EVT_SCROLL(self.connslider, self.onConnScroll)
            EVT_CHOICE(self.connChoice, -1, self.onConnChoice)
            EVT_SPINCTRL(self.connSpinner, -1, self.onConnSpinner)
            EVT_SPINCTRL(self.rateSpinner, -1, self.onRateSpinner)
            if (sys.platform == 'win32'):
                EVT_ICONIZE(self.frame, self.onIconify)

            colSizer.AddGrowableCol (0)
            colSizer.AddGrowableRow (6)
            self.frame.Show()
            border.Fit(panel)
            self.frame.Fit()
            self.panel = panel
            self.border = border
            self.addwidth = aboutText.GetBestSize().GetWidth() + fileDetails.GetBestSize().GetWidth() + (self.FONT*14)
            self.fnsizer = fnsizer
            self.colSizer = colSizer
            minsize = self.colSizer.GetSize()
            minsize.SetWidth (minsize.GetWidth())
            minsize.SetHeight (minsize.GetHeight())
            self.colSizer.SetMinSize (minsize)
            self.colSizer.Fit(self.frame)
            colSizer.Fit(frame)
        except:
            self.exception()

    if sys.platform == 'win32':     # windows-only optimization
        def onInvoke(self, event):
            while self.invokeLaterList:
                func,args,kwargs = self.invokeLaterList[0]
                if self.uiflag.isSet():
                    return
                try:
                    apply(func,args,kwargs)
                except:
                    self.exception()
                del self.invokeLaterList[0]

        def invokeLater(self, func, args = [], kwargs = {}):
            if not self.uiflag.isSet():
                self.invokeLaterList.append((func,args,kwargs))
                if len(self.invokeLaterList) == 1:
                    wxPostEvent(self.frame, self.invokeLaterEvent)
    else:
        def onInvoke(self, event):
            if not self.uiflag.isSet():
                try:
                    apply(event.func, event.args, event.kwargs)
                except:
                    self.exception()

        def invokeLater(self, func, args = [], kwargs = {}):
            if not self.uiflag.isSet():
                wxPostEvent(self.frame, InvokeEvent(func, args, kwargs))


    def setStatusIcon(self, name):
        if name != self.statusIconValue:
            self.statusIconValue = name;
            statidata = wxMemoryDC()
            statidata.SelectObject(self.statusIcon)
            statidata.BeginDrawing()
            statidata.DrawIcon(self.statusIcons[name],0,0)
            statidata.EndDrawing()
            statidata.SelectObject(wxNullBitmap)
            self.statusIconPtr.Refresh()


    def createStatusIcon(self, name):
        iconbuffer = wxEmptyBitmap(32,32)
        bbdata = wxMemoryDC()
        bbdata.SelectObject(iconbuffer)
        bbdata.SetPen(wxTRANSPARENT_PEN)
        bbdata.SetBrush(wxBrush(wx.wxSystemSettings_GetColour(wxSYS_COLOUR_MENU),wxSOLID))
        bbdata.DrawRectangle(0,0,32,32)
        bbdata.DrawIcon(self.statusIcons[name],0,0)
        return iconbuffer


    def onIconify(self, evt):
        try:
            if self.configfile.configfileargs['win32_taskbar_icon']:
                if not hasattr(self.frame, "tbicon"):
                    self.frame.tbicon = wxTaskBarIcon()
                    self.frame.tbicon.SetIcon(self.icon, "BitTorrent")
                    # setup a taskbar icon, and catch some events from it
                    EVT_TASKBAR_LEFT_DCLICK(self.frame.tbicon, self.onTaskBarActivate)
                    EVT_TASKBAR_RIGHT_UP(self.frame.tbicon, self.onTaskBarMenu)
                    EVT_MENU(self.frame.tbicon, self.TBMENU_RESTORE, self.onTaskBarActivate)
                    EVT_MENU(self.frame.tbicon, self.TBMENU_CLOSE, self.done)
                self.frame.Hide()
            else:
                EVT_ICONIZE(self.frame, self.onIconifyDummy)
                if self.iconized:
                    self.frame.Iconize(false)
                    self.iconized = false
                else:
                    self.frame.Iconize(true)
                    self.iconized = true
                EVT_ICONIZE(self.frame, self.onIconify)
                # rant here -- why in god's name can't a function called by an event
                # trigger the event without calling itself?
                # self.frame.Iconize(not self.frame.IsIconized()) should do this job...
        except:
            self.exception()

    def onIconifyDummy(self, evt):
        return

    def onTaskBarActivate(self, evt):
        try:
            if self.frame.IsIconized():
                self.frame.Iconize(false)
            if not self.frame.IsShown():
                self.frame.Show(true)
                self.frame.Raise()
            if hasattr(self.frame, "tbicon"):
                del self.frame.tbicon
        except:
            self.exception()

    TBMENU_RESTORE = 1000
    TBMENU_CLOSE   = 1001

    def onTaskBarMenu(self, evt):
        menu = wxMenu()
        menu.Append(self.TBMENU_RESTORE, "Restore BitTorrent")
        menu.Append(self.TBMENU_CLOSE,   "Close")
        self.frame.tbicon.PopupMenu(menu)
        menu.Destroy()


    def _try_get_config(self):
        if self.config is None:
            self.config = self.dow.getConfig()
        return self.config != None


    def onRateScroll(self, event):
        try:
            if (self.scrollock == 0):
                self.scrollock = 1
                if not self._try_get_config():
                    return
                self.updateSpinnerFlag = 1
                self.dow.setUploadRate(self.rateslider.GetValue() * 1000
                            * connChoices[self.connChoice.GetSelection()]['rate'].get('div',1))
                self.scrollock = 0
        except:
            self.exception()

    def onConnScroll(self, event):
        try:
            if not self._try_get_config():
                return
            self.connSpinner.SetValue (self.connslider.GetValue ())
            self.dow.setConns(self.connslider.GetValue())
        except:
            self.exception()

    def onRateSpinner(self, event):
        try:
            if not self._try_get_config():
                return
            if (self.spinlock == 0):
                self.spinlock = 1
                spinnerValue = self.rateSpinner.GetValue()
                div = connChoices[self.connChoice.GetSelection()]['rate'].get('div',1)
                if div > 1:
                    if spinnerValue > (self.config['max_upload_rate']/1000):
                        round_up = div - 1
                    else:
                        round_up = 0
                    newValue = int((spinnerValue + round_up) / div) * div
                    if newValue != spinnerValue:
                        self.rateSpinner.SetValue(newValue)
                else:
                    newValue = spinnerValue
                self.dow.setUploadRate(newValue * 1000)
                self.updateSliderFlag = 1
                self.spinlock = 0
        except:
            self.exception()

    def onConnSpinner(self, event):
        try:
            if not self._try_get_config():
                return
            self.connslider.SetValue (self.connSpinner.GetValue())
            self.dow.setConns(self.connslider.GetValue())
        except:
            self.exception()

    def onConnChoice(self, event):
        try:
            if not self._try_get_config():
                return
            num = self.connChoice.GetSelection()
            if connChoices[num].has_key('super-seed'):  # selecting super-seed is now a toggle
                self.dow.set_super_seed()               # one way change, don't go back
                num = self.lastuploadsettings
                self.connChoice.SetSelection(num)
                return
            self.lastuploadsettings = num
            self.rateSpinner.SetRange (connChoices[num]['rate']['min'],
                                   connChoices[num]['rate']['max'])
            self.rateSpinner.SetValue (connChoices[num]['rate']['def'])
            self.rateslider.SetRange (
                connChoices[num]['rate']['min']/connChoices[num]['rate'].get('div',1),
                connChoices[num]['rate']['max']/connChoices[num]['rate'].get('div',1))
            self.rateslider.SetValue (
                connChoices[num]['rate']['def']/connChoices[num]['rate'].get('div',1))
            self.rateLowerText.SetLabel ('  %d' % (connChoices[num]['rate']['min']))
            self.rateUpperText.SetLabel ('%d' % (connChoices[num]['rate']['max']))
            self.connSpinner.SetRange (connChoices[num]['conn']['min'],
                                       connChoices[num]['conn']['max'])
            self.connSpinner.SetValue (connChoices[num]['conn']['def'])
            self.connslider.SetRange (connChoices[num]['conn']['min'],
                                      connChoices[num]['conn']['max'])
            self.connslider.SetValue (connChoices[num]['conn']['def'])
            self.connLowerText.SetLabel ('  %d' % (connChoices[num]['conn']['min']))
            self.connUpperText.SetLabel ('%d' % (connChoices[num]['conn']['max']))
            self.onConnScroll (0)
            self.onRateScroll (0)
            self.dow.setInitiate(connChoices[num].get('initiate', 40))
        except:
            self.exception()


    def about(self, event):
        try:
            if (self.aboutBox is not None):
                try:
                    self.aboutBox.Close ()
                except wxPyDeadObjectError, e:
                    self.aboutBox = None

            self.aboutBox = wxFrame(None, -1, 'About BitTorrent', size = (1,1))
            if (sys.platform == 'win32'):
                self.aboutBox.SetIcon(self.icon)

            panel = wxPanel(self.aboutBox, -1)

            def StaticText(text, font = self.FONT, underline = false, color = None, panel = panel):
                x = wxStaticText(panel, -1, text, style = wxALIGN_LEFT)
                x.SetFont(wxFont(font, wxDEFAULT, wxNORMAL, wxNORMAL, underline))
                if color is not None:
                    x.SetForegroundColour(color)
                return x

            colSizer = wxFlexGridSizer(cols = 1, vgap = 3)

            titleSizer = wxBoxSizer(wxHORIZONTAL)
            aboutTitle = StaticText('BitTorrent ' + version + '  ', self.FONT+4)
            titleSizer.Add (aboutTitle)
            linkDonate = StaticText('Donate to Bram', self.FONT, true, 'Blue')
            titleSizer.Add (linkDonate, 1, wxALIGN_BOTTOM&wxEXPAND)
            colSizer.Add(titleSizer, 0, wxEXPAND)

            colSizer.Add(StaticText('created by Bram Cohen, Copyright 2001-2003,'))
            colSizer.Add(StaticText('experimental version maintained by John Hoffman 2003'))
            colSizer.Add(StaticText('modified from experimental version by Eike Frost 2003'))
            credits = StaticText('full credits\n', self.FONT, true, 'Blue')
            colSizer.Add(credits);

            si = ( 'exact Version String: ' + version + '\n' +
                   'Python version: ' + sys.version + '\n' +
                   'wxWindows version: ' + wxVERSION_STRING + '\n' )
            try:
                si += 'Psyco version: ' + hex(psyco.__version__)[2:] + '\n'
            except:
                pass
            colSizer.Add(StaticText(si))

            babble1 = StaticText(
             'This is an experimental, unofficial build of BitTorrent.\n' +
             'It is Free Software under an MIT-Style license.')
            babble2 = StaticText('BitTorrent Homepage (link)', self.FONT, true, 'Blue')
            babble3 = StaticText("TheSHAD0W's Client Homepage (link)", self.FONT, true, 'Blue')
            babble4 = StaticText("Eike Frost's Client Homepage (link)", self.FONT, true, 'Blue')
            babble6 = StaticText('License Terms (link)', self.FONT, true, 'Blue')
            colSizer.Add (babble1)
            colSizer.Add (babble2)
            colSizer.Add (babble3)
            colSizer.Add (babble4)
            colSizer.Add (babble6)

            okButton = wxButton(panel, -1, 'Ok')
#        okButton.SetFont(self.default_font)
            colSizer.Add(okButton, 0, wxALIGN_RIGHT)
            colSizer.AddGrowableCol(0)

            border = wxBoxSizer(wxHORIZONTAL)
            border.Add(colSizer, 1, wxEXPAND | wxALL, 4)
            panel.SetSizer(border)
            panel.SetAutoLayout(true)

            def donatelink(self):
                Thread(target = open_new('https://www.paypal.com/cgi-bin/webscr?cmd=_xclick&business=bram@bitconjurer.org&item_name=BitTorrent&amount=5.00&submit=donate')).start()
            EVT_LEFT_DOWN(linkDonate, donatelink)
            def aboutlink(self):
                Thread(target = open_new('http://bitconjurer.org/BitTorrent/')).start()
            EVT_LEFT_DOWN(babble2, aboutlink)
            def shadlink(self):
                Thread(target = open_new('http://bt.degreez.net/')).start()
            EVT_LEFT_DOWN(babble3, shadlink)
            def explink(self):
                Thread(target = open_new('http://ei.kefro.st/projects/btclient/')).start()
            EVT_LEFT_DOWN(babble4, explink)
            def licenselink(self):
                Thread(target = open_new('http://ei.kefro.st/projects/btclient/LICENSE.TXT')).start()
            EVT_LEFT_DOWN(babble6, licenselink)
            EVT_LEFT_DOWN(credits, self.credits)

            def closeAbout(self, frame = self):
                frame.aboutBox.Close ()
            EVT_BUTTON(self.aboutBox, okButton.GetId(), closeAbout)
            def kill(self, frame = self):
                frame.aboutBox.Destroy()
                frame.aboutBox = None
            EVT_CLOSE(self.aboutBox, kill)

            self.aboutBox.Show ()
            border.Fit(panel)
            self.aboutBox.Fit()
        except:
            self.exception()


    def details(self, event):
        try:
            metainfo = self.dow.getResponse()
            if metainfo is None:
                return
            if metainfo.has_key('announce'):
                announce = metainfo['announce']
            else:
                announce = None
            if metainfo.has_key('announce-list'):
                announce_list = metainfo['announce-list']
            else:
                announce_list = None
            info = metainfo['info']
            info_hash = sha(bencode(info))
            piece_length = info['piece length']

            if (self.detailBox is not None):
                try:
                    self.detailBox.Close ()
                except wxPyDeadObjectError, e:
                    self.detailBox = None

            self.detailBox = wxFrame(None, -1, 'Torrent Details ', size = wxSize(405,230))
            if (sys.platform == 'win32'):
                self.detailBox.SetIcon(self.icon)

            panel = wxPanel(self.detailBox, -1, size = wxSize (400,220))

            def StaticText(text, font = self.FONT, underline = false, color = None, panel = panel):
                x = wxStaticText(panel, -1, text, style = wxALIGN_CENTER_VERTICAL)
                x.SetFont(wxFont(font, wxDEFAULT, wxNORMAL, wxNORMAL, underline))
                if color is not None:
                    x.SetForegroundColour(color)
                return x

            colSizer = wxFlexGridSizer(cols = 1, vgap = 3)
            colSizer.AddGrowableCol(0)

            titleSizer = wxBoxSizer(wxHORIZONTAL)
            aboutTitle = StaticText('Details about ' + self.filename, self.FONT+4)

            titleSizer.Add (aboutTitle)
            colSizer.Add (titleSizer)

            detailSizer = wxFlexGridSizer(cols = 2, vgap = 6)

            if info.has_key('length'):
                detailSizer.Add(StaticText('file name :'))
                detailSizer.Add(StaticText(info['name']))
                if info.has_key('md5sum'):
                    detailSizer.Add(StaticText('MD5 hash :'))
                    detailSizer.Add(StaticText(info['md5sum']))
                file_length = info['length']
                name = "file size"
            else:
                detail1Sizer = wxFlexGridSizer(cols = 1, vgap = 6)
                detail1Sizer.Add(StaticText('directory name : ' + info['name']))
                colSizer.Add (detail1Sizer)
                bgallocButton = wxBitmapButton(panel, -1, self.allocbuttonBitmap, size = (52,20))
                def bgalloc(self, frame = self):
                    if frame.dow.storagewrapper is not None:
                        frame.dow.storagewrapper.bgalloc()
                EVT_BUTTON(self.detailBox, bgallocButton.GetId(), bgalloc)

                bgallocbuttonSizer = wxFlexGridSizer(cols = 3, hgap = 4, vgap = 0)
                bgallocbuttonSizer.Add(StaticText('(finish allocation)'), -1, wxALIGN_CENTER_VERTICAL)
                bgallocbuttonSizer.Add(bgallocButton, -1, wxALIGN_CENTER)
                colSizer.Add(bgallocbuttonSizer, -1, wxALIGN_RIGHT)

                file_length = 0

                fileList = wxListCtrl(panel, -1, wxPoint(-1,-1), (325,100), wxLC_REPORT)
                self.fileList = fileList
                fileList.SetImageList(self.filestatusIcons, wxIMAGE_LIST_SMALL)

                fileList.SetAutoLayout (true)
                fileList.InsertColumn(0, "file")
                fileList.InsertColumn(1, "", format=wxLIST_FORMAT_RIGHT, width=55)
                fileList.InsertColumn(2, "")

                for i in range(len(info['files'])):
                    x = wxListItem()
#                x.SetFont(self.default_font)
                    fileList.InsertItem(x)

                x = 0
                for file in info['files']:
                    path = ' '
                    for item in file['path']:
                        if (path != ''):
                            path = path + "/"
                        path = path + item
                    path += ' (' + str(file['length']) + ')'
                    fileList.SetStringItem(x, 0, path)
                    if file.has_key('md5sum'):
                        fileList.SetStringItem(x, 2, '    [' + str(file['md5sum']) + ']')
                    x += 1
                    file_length += file['length']
                fileList.SetColumnWidth(0,wxLIST_AUTOSIZE)
                fileList.SetColumnWidth(2,wxLIST_AUTOSIZE)

                name = 'archive size'
                colSizer.Add(fileList, 1, wxEXPAND)
                colSizer.AddGrowableRow(3)

            detailSizer.Add(StaticText('info_hash :'),0,wxALIGN_CENTER_VERTICAL)
            detailSizer.Add(wxTextCtrl(panel, -1, info_hash.hexdigest(), size = (325, -1), style = wxTE_READONLY))
            num_pieces = int((file_length+piece_length-1)/piece_length)
            detailSizer.Add(StaticText(name + ' : '))
            detailSizer.Add(StaticText('%s (%s bytes)' % (size_format(file_length), comma_format(file_length))))
            detailSizer.Add(StaticText('pieces : '))
            if num_pieces > 1:
                detailSizer.Add(StaticText('%i (%s bytes each)' % (num_pieces, comma_format(piece_length))))
            else:
                detailSizer.Add(StaticText('1'))

            if announce_list is None:
                detailSizer.Add(StaticText('announce url : '),0,wxALIGN_CENTER_VERTICAL)
                detailSizer.Add(wxTextCtrl(panel, -1, announce, size = (325, -1), style = wxTE_READONLY))
            else:
                detailSizer.Add(StaticText(''))
                trackerList = wxListCtrl(panel, -1, wxPoint(-1,-1), (325,75), wxLC_REPORT)
                trackerList.SetAutoLayout (true)
                trackerList.InsertColumn(0, "")
                trackerList.InsertColumn(1, "announce urls")

                for tier in range(len(announce_list)):
                    for t in range(len(announce_list[tier])):
                        i = wxListItem()
#                    i.SetFont(self.default_font)
                        trackerList.InsertItem(i)
                if announce is not None:
                    for l in [1,2]:
                        i = wxListItem()
#                    i.SetFont(self.default_font)
                        trackerList.InsertItem(i)

                x = 0
                for tier in range(len(announce_list)):
                    for t in range(len(announce_list[tier])):
                        if t == 0:
                            trackerList.SetStringItem(x, 0, 'tier '+str(tier)+':')
                        trackerList.SetStringItem(x, 1, announce_list[tier][t])
                        x += 1
                if announce is not None:
                    trackerList.SetStringItem(x+1, 0, 'single:')
                    trackerList.SetStringItem(x+1, 1, announce)
                trackerList.SetColumnWidth(0,wxLIST_AUTOSIZE)
                trackerList.SetColumnWidth(1,wxLIST_AUTOSIZE)
                detailSizer.Add(trackerList)

            if announce is None and announce_list is not None:
                announce = announce_list[0][0]
            if announce is not None:
                detailSizer.Add(StaticText('likely tracker :'))
                p = re.compile( '(.*/)[^/]+')
                turl = p.sub (r'\1', announce)
                trackerUrl = StaticText(turl, self.FONT, true, 'Blue')
                detailSizer.Add(trackerUrl)
            if metainfo.has_key('comment'):
                detailSizer.Add(StaticText('comment :'))
                detailSizer.Add(StaticText(metainfo['comment']))
            if metainfo.has_key('creation date'):
                detailSizer.Add(StaticText('creation date :'))
                try:
                    detailSizer.Add(StaticText(
                        strftime('%x %X',localtime(metainfo['creation date']))))
                except:
                    try:
                        detailSizer.Add(StaticText(metainfo['creation date']))
                    except:
                        detailSizer.Add(StaticText('<cannot read date>'))

            detailSizer.AddGrowableCol(1)
            colSizer.Add (detailSizer, 1, wxEXPAND)

            okButton = wxButton(panel, -1, 'Ok')
#        okButton.SetFont(self.default_font)
            colSizer.Add(okButton, 0, wxALIGN_RIGHT)
            colSizer.AddGrowableCol(0)

            if not self.configfile.configfileargs['gui_stretchwindow']:
                aboutTitle.SetSize((400,-1))
            else:
                panel.SetAutoLayout(true)

            border = wxBoxSizer(wxHORIZONTAL)
            border.Add(colSizer, 1, wxEXPAND | wxALL, 4)
            panel.SetSizer(border)
            panel.SetAutoLayout(true)

            def closeDetail(self, frame = self):
                frame.detailBox.Close ()
            EVT_BUTTON(self.detailBox, okButton.GetId(), closeDetail)
            def kill(self, frame = self):
                frame.detailBox.Destroy()
                frame.detailBox = None
                frame.fileList = None
                frame.dow.filedatflag.clear()
            EVT_CLOSE(self.detailBox, kill)

            def trackerurl(self, turl = turl):
                Thread(target = open_new(turl)).start()

            EVT_LEFT_DOWN(trackerUrl, trackerurl)

            self.detailBox.Show ()
            border.Fit(panel)
            self.detailBox.Fit()

            self.refresh_details = true
            self.dow.filedatflag.set()
        except:
            self.exception()


    def credits(self, event):
        try:
            if (self.creditsBox is not None):
                try:
                    self.creditsBox.Close ()
                except wxPyDeadObjectError, e:
                    self.creditsBox = None

            self.creditsBox = wxFrame(None, -1, 'Credits', size = (1,1))
            if (sys.platform == 'win32'):
                self.creditsBox.SetIcon(self.icon)

            panel = wxPanel(self.creditsBox, -1)        

            def StaticText(text, font = self.FONT, underline = false, color = None, panel = panel):
                x = wxStaticText(panel, -1, text, style = wxALIGN_LEFT)
                x.SetFont(wxFont(font, wxDEFAULT, wxNORMAL, wxNORMAL, underline))
                if color is not None:
                    x.SetForegroundColour(color)
                return x

            colSizer = wxFlexGridSizer(cols = 1, vgap = 3)

            titleSizer = wxBoxSizer(wxHORIZONTAL)
            aboutTitle = StaticText('Credits', self.FONT+4)
            titleSizer.Add (aboutTitle)
            colSizer.Add (titleSizer)
            colSizer.Add (StaticText(
              'The following people have all helped with this\n' +
              'version of BitTorrent in some way (in no particular order) -\n'));
            creditSizer = wxFlexGridSizer(cols = 3)
            creditSizer.Add(StaticText(
              'Bill Bumgarner\n' +
              'David Creswick\n' +
              'Andrew Loewenstern\n' +
              'Ross Cohen\n' +
              'Jeremy Avnet\n' +
              'Greg Broiles\n' +
              'Barry Cohen\n' +
              'Bram Cohen\n' +
              'sayke\n' +
              'Steve Jenson\n' +
              'Myers Carpenter\n' +
              'Francis Crick\n' +
              'Petru Paler\n' +
              'Jeff Darcy\n' +
              'John Gilmore\n' +
              'Xavier Bassery\n' +
              'Pav Lucistnik'))
            creditSizer.Add(StaticText('  '))
            creditSizer.Add(StaticText(
              'Yann Vernier\n' +
              'Pat Mahoney\n' +
              'Boris Zbarsky\n' +
              'Eric Tiedemann\n' +
              'Henry "Pi" James\n' +
              'Loring Holden\n' +
              'Robert Stone\n' +
              'Michael Janssen\n' +
              'Eike Frost\n' +
              'Andrew Todd\n' +
              'otaku\n' +
              'Edward Keyes\n' +
              'John Hoffman\n' +
              'Uoti Urpala\n' +
              'Jon Wolf\n' +
              'Christoph Hohmann'))
            colSizer.Add (creditSizer, flag = wxALIGN_CENTER_HORIZONTAL)
            okButton = wxButton(panel, -1, 'Ok')
#        okButton.SetFont(self.default_font)
            colSizer.Add(okButton, 0, wxALIGN_RIGHT)
            colSizer.AddGrowableCol(0)

            border = wxBoxSizer(wxHORIZONTAL)
            border.Add(colSizer, 1, wxEXPAND | wxALL, 4)
            panel.SetSizer(border)
            panel.SetAutoLayout(true)

            def closeCredits(self, frame = self):
                frame.creditsBox.Close ()
            EVT_BUTTON(self.creditsBox, okButton.GetId(), closeCredits)
            def kill(self, frame = self):
                frame.creditsBox.Destroy()
                frame.creditsBox = None
            EVT_CLOSE(self.creditsBox, kill)

            self.creditsBox.Show()
            border.Fit(panel)
            self.creditsBox.Fit()
        except:
            self.exception()


    def statusIconHelp(self, event):
        try:
            if (self.statusIconHelpBox is not None):
                try:
                    self.statusIconHelpBox.Close ()
                except wxPyDeadObjectError, e:
                    self.statusIconHelpBox = None

            self.statusIconHelpBox = wxFrame(None, -1, 'Help with the BitTorrent Status Light', size = (1,1))
            if (sys.platform == 'win32'):
                self.statusIconHelpBox.SetIcon(self.icon)

            panel = wxPanel(self.statusIconHelpBox, -1)

            def StaticText(text, font = self.FONT, underline = false, color = None, panel = panel):
                x = wxStaticText(panel, -1, text, style = wxALIGN_LEFT)
                x.SetFont(wxFont(font, wxDEFAULT, wxNORMAL, wxNORMAL, underline))
                if color is not None:
                    x.SetForegroundColour(color)
                return x

            fullsizer = wxFlexGridSizer(cols = 1, vgap = 13)
            colsizer = wxFlexGridSizer(cols = 2, hgap = 13, vgap = 13)

            disconnectedicon=self.createStatusIcon('disconnected')
            colsizer.Add(wxStaticBitmap(panel, -1, disconnectedicon))
            colsizer.Add(StaticText(
                'Waiting to connect to the tracker.\n' +
                'If the status light stays black for a long time the tracker\n' +
                'you are trying to connect to may not be working.  Unless you\n' +
                'are receiving a message telling you otherwise, please wait,\n' +
                'and BitTorrent will automatically try to reconnect for you.'), 1, wxALIGN_CENTER_VERTICAL)

            noconnectionsicon=self.createStatusIcon('noconnections')
            colsizer.Add(wxStaticBitmap(panel, -1, noconnectionsicon))
            colsizer.Add(StaticText(
                'You have no connections with other clients.\n' +
                'Please be patient.  If after several minutes the status\n' +
                'light remains red, this torrent may be old and abandoned.'), 1, wxALIGN_CENTER_VERTICAL)

            noincomingicon=self.createStatusIcon('noincoming')
            colsizer.Add(wxStaticBitmap(panel, -1, noincomingicon))
            colsizer.Add(StaticText(
                'You have not received any incoming connections from others.\n' +
                'It may only be because no one has tried.  If you never see\n' +
                'the status light turn green, it may indicate your system\n' +
                'is behind a firewall or proxy server.  Please look into\n' +
                'routing BitTorrent through your firewall in order to receive\n' +
                'the best possible download rate.'), 1, wxALIGN_CENTER_VERTICAL)

            nocompletesicon=self.createStatusIcon('nocompletes')
            colsizer.Add(wxStaticBitmap(panel, -1, nocompletesicon))
            colsizer.Add(StaticText(
                'There are no complete copies among the clients you are\n' +
                'connected to.  Don\'t panic, other clients in the torrent\n' +
                "you can't see may have the missing data.\n" +
                'If the status light remains blue, you may have problems\n' +
                'completing your download.'), 1, wxALIGN_CENTER_VERTICAL)

            allgoodicon=self.createStatusIcon('allgood')
            colsizer.Add(wxStaticBitmap(panel, -1, allgoodicon))
            colsizer.Add(StaticText(
                'The torrent is operating properly.'), 1, wxALIGN_CENTER_VERTICAL)

            fullsizer.Add(colsizer, 0, wxALIGN_CENTER)
            colsizer2 = wxFlexGridSizer(cols = 1, hgap = 13)

            colsizer2.Add(StaticText(
                'Please note that the status light is not omniscient, and that it may\n' +
                'be wrong in many instances.  A torrent with a blue light may complete\n' +
                "normally, and an occasional yellow light doesn't mean your computer\n" +
                'has suddenly become firewalled.'), 1, wxALIGN_CENTER_VERTICAL)

            colspacer = StaticText('  ')
            colsizer2.Add(colspacer)

            okButton = wxButton(panel, -1, 'Ok')
#        okButton.SetFont(self.default_font)
            colsizer2.Add(okButton, 0, wxALIGN_CENTER)
            fullsizer.Add(colsizer2, 0, wxALIGN_CENTER)

            border = wxBoxSizer(wxHORIZONTAL)
            border.Add(fullsizer, 1, wxEXPAND | wxALL, 4)

            panel.SetSizer(border)
            panel.SetAutoLayout(true)


            def closeHelp(self, frame = self):
                frame.statusIconHelpBox.Close ()
            EVT_BUTTON(self.statusIconHelpBox, okButton.GetId(), closeHelp)

            self.statusIconHelpBox.Show ()
            border.Fit(panel)
            self.statusIconHelpBox.Fit()
        except:
            self.exception()


    def openConfigMenu(self, event):
        try:
            self.configfile.configMenu(self)
        except:
            self.exception()


    def advanced(self, event):
        try:
            if self.filename is None:
                return
            if (self.advBox is not None):
                try:
                    self.advBox.Close ()
                except wxPyDeadObjectError, e:
                    self.advBox = None

            self.advBox = wxFrame(None, -1, 'BitTorrent Advanced', size = wxSize(200,200))
            if (sys.platform == 'win32'):
                self.advBox.SetIcon(self.icon)

            panel = wxPanel(self.advBox, -1, size = wxSize (200,200))

            def StaticText(text, font = self.FONT, underline = false, color = None, panel = panel):
                x = wxStaticText(panel, -1, text, style = wxALIGN_LEFT)
                x.SetFont(wxFont(font, wxDEFAULT, wxNORMAL, wxNORMAL, underline))
                if color is not None:
                    x.SetForegroundColour(color)
                return x

            colSizer = wxFlexGridSizer (cols = 1, vgap = 1)
            colSizer.Add (StaticText('Advanced Info for ' + self.filename, self.FONT+4))

            try:    # get system font width
                fw = wxSystemSettings_GetFont(wxSYS_DEFAULT_GUI_FONT).GetPointSize()+1
            except:
                fw = wxSystemSettings_GetFont(wxSYS_SYSTEM_FONT).GetPointSize()+1

            spewList = wxListCtrl(panel, -1, wxPoint(-1,-1), (fw*66,350), wxLC_REPORT|wxLC_HRULES|wxLC_VRULES)
            self.spewList = spewList
            spewList.SetAutoLayout (true)

            colSizer.Add(spewList, -1, wxEXPAND)

            colSizer.Add(StaticText(''))
            self.storagestats1 = StaticText('')
            self.storagestats2 = StaticText('')
            colSizer.Add(self.storagestats1, -1, wxEXPAND)
            colSizer.Add(self.storagestats2, -1, wxEXPAND)
            colSizer.Add(StaticText(''))

            buttonSizer = wxFlexGridSizer (cols = 5, hgap = 20)

            reannounceButton = wxButton(panel, -1, 'Manual Announce')
#        reannounceButton.SetFont(self.default_font)
            buttonSizer.Add (reannounceButton)

            extannounceButton = wxButton(panel, -1, 'External Announce')
#        extannounceButton.SetFont(self.default_font)
            buttonSizer.Add (extannounceButton)

            bgallocButton = wxButton(panel, -1, 'Finish Allocation')
#        bgallocButton.SetFont(self.default_font)
            buttonSizer.Add (bgallocButton)

            buttonSizer.Add(StaticText(''))

            okButton = wxButton(panel, -1, 'Ok')
#        okButton.SetFont(self.default_font)
            buttonSizer.Add (okButton)

            colSizer.Add (buttonSizer, 0, wxALIGN_CENTER)
#        colSizer.SetMinSize ((578,350))
            colSizer.AddGrowableCol(0)
            colSizer.AddGrowableRow(1)

            panel.SetSizer(colSizer)
            panel.SetAutoLayout(true)

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

            def reannounce(self, frame = self):
                if (time () - frame.reannouncelast > 60):
                    frame.reannouncelast = time ()
                    frame.dow.reannounce()
            EVT_BUTTON(self.advBox, reannounceButton.GetId(), reannounce)

            self.advextannouncebox = None
            def reannounce_external(self, frame = self):
                if (frame.advextannouncebox is not None):
                    try:
                        frame.advextannouncebox.Close ()
                    except wxPyDeadObjectError, e:
                        frame.advextannouncebox = None

                frame.advextannouncebox = wxFrame(None, -1, 'External Announce', size = (1,1))
                if (sys.platform == 'win32'):
                    frame.advextannouncebox.SetIcon(frame.icon)

                panel = wxPanel(frame.advextannouncebox, -1)

                fullsizer = wxFlexGridSizer(cols = 1, vgap = 13)
                msg = wxStaticText(panel, -1, "Enter tracker anounce URL:")
                msg.SetFont(frame.default_font)
                fullsizer.Add(msg)

                frame.advexturl = wxTextCtrl(parent = panel, id = -1, value = '',
                                    size = (255, 20), style = wxTE_PROCESS_TAB)
                frame.advexturl.SetFont(frame.default_font)
                frame.advexturl.SetValue(frame.lastexternalannounce)
                fullsizer.Add(frame.advexturl)

                buttonSizer = wxFlexGridSizer (cols = 2, hgap = 10)

                okButton = wxButton(panel, -1, 'OK')
#            okButton.SetFont(frame.default_font)
                buttonSizer.Add (okButton)

                cancelButton = wxButton(panel, -1, 'Cancel')
#            cancelButton.SetFont(frame.default_font)
                buttonSizer.Add (cancelButton)

                fullsizer.Add (buttonSizer, 0, wxALIGN_CENTER)

                border = wxBoxSizer(wxHORIZONTAL)
                border.Add(fullsizer, 1, wxEXPAND | wxALL, 4)

                panel.SetSizer(border)
                panel.SetAutoLayout(true)

                def ok(self, frame = frame):
                    special = frame.advexturl.GetValue()
                    if special:
                        frame.lastexternalannounce = special
                        if (time () - frame.reannouncelast > 60):
                            frame.reannouncelast = time ()
                            frame.dow.reannounce(special)
                    frame.advextannouncebox.Close()
                EVT_BUTTON(frame.advextannouncebox, okButton.GetId(), ok)

                def cancel(self, frame = frame):
                    frame.advextannouncebox.Close()
                EVT_BUTTON(frame.advextannouncebox, cancelButton.GetId(), cancel)

                def kill(self, frame = frame):
                    frame.advextannouncebox.Destroy()
                    frame.advextannouncebox = None
                EVT_CLOSE(frame.advextannouncebox, kill)

                frame.advextannouncebox.Show ()
                fullsizer.Fit(panel)
                frame.advextannouncebox.Fit()

            EVT_BUTTON(self.advBox, extannounceButton.GetId(), reannounce_external)

            def bgalloc(self, frame = self):
                if frame.dow.storagewrapper is not None:
                    frame.dow.storagewrapper.bgalloc()
            EVT_BUTTON(self.advBox, bgallocButton.GetId(), bgalloc)

            def closeAdv(self, frame = self):
                frame.advBox.Close ()
            def killAdv(self, frame = self):
                frame.dow.spewflag.clear()
                frame.advBox.Destroy()
                frame.advBox = None
                if (frame.advextannouncebox is not None):
                    try:
                        frame.advextannouncebox.Close ()
                    except wxPyDeadObjectError, e:
                        pass
                    frame.advextannouncebox = None
            EVT_BUTTON(self.advBox, okButton.GetId(), closeAdv)
            EVT_CLOSE(self.advBox, killAdv)

            self.advBox.Show ()
            colSizer.Fit(panel)
            self.advBox.Fit()
            self.dow.spewflag.set()
        except:
            self.exception()


    def displayUsage(self, text):
        try:
            start = self.dow.getUsageText()
            if text[:len(start)] != start:
                return false

            self.done(None)
            self.usageBox = wxFrame(None, -1, 'Usage', size = (480,400))
            if (sys.platform == 'win32'):
                self.usageBox.SetIcon(self.icon)

            panel = wxScrolledWindow(self.usageBox, -1)
            colSizer = wxFlexGridSizer(cols = 1)

            colSizer.Add (wxStaticText(panel, -1, text))
            okButton = wxButton(panel, -1, 'Ok')
#        okButton.SetFont(self.default_font)
            colSizer.Add(okButton, 0, wxALIGN_RIGHT)
            colSizer.AddGrowableCol(0)


            def closeUsage(self, frame = self):
                frame.usageBox.Close()
            EVT_BUTTON(self.usageBox, okButton.GetId(), closeUsage)
            def kill(self, frame = self):
                frame.usageBox.Destroy()
                frame.usageBox = None
            EVT_CLOSE(self.usageBox, kill)

            self.usageBox.Show ()
            panel.FitInside()
            panel.SetSizer(colSizer)
            panel.SetAutoLayout(true)
            panel.SetScrollRate(0,1)
            self.usageBox.Fit()

            return true        
        except:
            self.exception()


    def updateStatus(self, fractionDone = None,
            timeEst = None, downRate = None, upRate = None,
            activity = None, statistics = None, spew = None, sizeDone = None,
            **kws):
        if activity is not None:
            self.activity = activity
        if fractionDone is not None:
            self.gui_fractiondone = fractionDone
        if self.gui_lastupdate + 0.05 > time():   # refreshing too fast, skip it
            return
        if not self.ispaused:
            self.invokeLater(self.onUpdateStatus,
                     [timeEst, downRate, upRate, statistics, spew, sizeDone])

    def onUpdateStatus(self, timeEst, downRate, upRate, statistics, spew, sizeDone):
        if self.gui_lastupdate + 0.05 > time():   # refreshing too fast, skip it
            return

        if self.firstupdate:
            self.connChoice.SetStringSelection(self.configfile.configfileargs['gui_ratesettingsdefault'])
            self.onConnChoice(0)         # force config selection for default value
            self.gauge.SetForegroundColour(self.configfile.checkingcolor)
            self.firstupdate = false

        if statistics is None:
            self.setStatusIcon('startup')
        elif statistics.numPeers + statistics.numSeeds + statistics.numOldSeeds == 0:
            if statistics.last_failed:
                self.setStatusIcon('disconnected')
            else:
                self.setStatusIcon('noconnections')
        elif ( not statistics.external_connection_made
            and not self.configfile.configfileargs['gui_forcegreenonfirewall'] ):
            self.setStatusIcon('noincoming')
        elif ( (statistics.numSeeds + statistics.numOldSeeds == 0)
               and ( (self.fin and statistics.numCopies < 1)
                    or (not self.fin and statistics.numCopies2 < 1) ) ):
            self.setStatusIcon('nocompletes')
        else:
            self.setStatusIcon('allgood')

        if self.updateSliderFlag == 1:
            self.updateSliderFlag = 0
            newValue = (self.rateSpinner.GetValue()
                         / connChoices[self.connChoice.GetSelection()]['rate'].get('div',1))
            if self.rateslider.GetValue() != newValue:
                self.rateslider.SetValue(newValue)

        if self.updateSpinnerFlag == 1:
            self.updateSpinnerFlag = 0
            cc = connChoices[self.connChoice.GetSelection()]
            if cc.has_key('rate'):
                newValue = (self.rateslider.GetValue() * cc['rate'].get('div',1))
                if self.rateSpinner.GetValue() != newValue:
                    self.rateSpinner.SetValue(newValue)
        if self.fin:
            if statistics is not None:
                if statistics.numOldSeeds > 0 or statistics.numCopies > 1:
                    self.gauge.SetValue(1000)
                else:
                    self.gauge.SetValue(int(1000*statistics.numCopies))
        elif self.gui_fractiondone is not None:
            gaugelevel = int(self.gui_fractiondone * 1000)
            self.gauge.SetValue(gaugelevel)
            if statistics is not None and statistics.downTotal is not None:
                if self.configfile.configfileargs['gui_displaymiscstats']:
                    self.frame.SetTitle('%.1f%% (%.2f MiB) %s - BitTorrent %s' % (float(gaugelevel)/10, float(sizeDone) / (1<<20), self.filename, version))
                else:
                    self.frame.SetTitle('%.1f%% %s - BitTorrent %s' % (float(gaugelevel)/10, self.filename, version))
                self.gauge.SetForegroundColour(self.configfile.downloadcolor)
            else:
                self.frame.SetTitle('%.0f%% %s - BitTorrent %s' % (float(gaugelevel)/10, self.filename, version))
        if timeEst is not None:
            self.timeText.SetLabel(hours(time () - self.starttime) + ' / ' + hours(timeEst))
        else:
            if self.fin:
                self.timeText.SetLabel(self.activity)
            else:
                self.timeText.SetLabel(hours(time () - self.starttime) + ' / ' + self.activity)
        if downRate is not None:
            self.downRateText.SetLabel('%.0f kB/s' % (float(downRate) / 1000))
        if upRate is not None:
            self.upRateText.SetLabel('%.0f kB/s' % (float(upRate) / 1000))
        if hasattr(self.frame, "tbicon"):
            icontext='BitTorrent '
            if self.gui_fractiondone is not None and not self.fin:
                if statistics is not None and statistics.downTotal is not None:
                    icontext=icontext+' %.1f%% (%.2f MiB)' % (self.gui_fractiondone*100, float(sizeDone) / (1<<20))
                else:
                    icontext=icontext+' %.0f%%' % (self.gui_fractiondone*100)
            if upRate is not None:
                icontext=icontext+' u:%.0f kB/s' % (float(upRate) / 1000)
            if downRate is not None:
                icontext=icontext+' d:%.0f kB/s' % (float(downRate) / 1000)
            icontext+=' %s' % self.filename
            self.frame.tbicon.SetIcon(self.icon,icontext)
        if statistics is not None:
            if self.configfile.configfileargs['gui_displaymiscstats']:
                self.downText.SetLabel('%.2f MiB' % (float(statistics.downTotal) / (1 << 20)))
                self.upText.SetLabel('%.2f MiB' % (float(statistics.upTotal) / (1 << 20)))
            if (statistics.shareRating < 0) or (statistics.shareRating > 1000):
                self.shareRatingText.SetLabel('oo :-D')
                self.shareRatingText.SetForegroundColour('Forest Green')
            else:
                shareSmiley = ''
                color = 'Black'
                if ((statistics.shareRating >= 0) and (statistics.shareRating < 0.5)):
                    shareSmiley = ':-('
                    color = 'Red'
                else:
                    if ((statistics.shareRating >= 0.5) and (statistics.shareRating < 1.0)):
                        shareSmiley = ':-|'
                        color = 'Orange'
                    else:
                        if (statistics.shareRating >= 1.0):
                            shareSmiley = ':-)'
                            color = 'Forest Green'
                self.shareRatingText.SetLabel('%.3f %s' % (statistics.shareRating, shareSmiley))
                self.shareRatingText.SetForegroundColour(color)

            if self.configfile.configfileargs['gui_displaystats']:
                if not self.fin:
                    self.seedStatusText.SetLabel('connected to %d seeds; also seeing %.3f distributed copies' % (statistics.numSeeds,0.001*int(1000*statistics.numCopies2)))
                else:
                    self.seedStatusText.SetLabel('%d seeds seen recently; also seeing %.3f distributed copies' % (statistics.numOldSeeds,0.001*int(1000*statistics.numCopies)))
                self.peerStatusText.SetLabel('connected to %d peers with an average of %.1f%% completed (total speed %.0f kB/s)' % (statistics.numPeers,statistics.percentDone,float(statistics.torrentRate) / (1000)))
        if ((time () - self.lastError) > 300):
            self.errorText.SetLabel('')

        if ( self.configfile.configfileargs['gui_displaymiscstats']
            and statistics is not None and statistics.backgroundallocating ):
            self.bgalloc_periods += 1
            if self.bgalloc_periods > 3:
                self.bgalloc_periods = 0
            self.bgallocText.SetLabel('ALLOCATING'+(' .'*self.bgalloc_periods))
        elif self.dow.superseedflag.isSet():
            self.bgallocText.SetLabel('SUPER-SEED')
        else:
            self.bgallocText.SetLabel('')


        if spew is not None and (time()-self.spewwait>1):
            if (self.advBox is not None):
                self.spewwait = time()
                spewList = self.spewList
                spewlen = len(spew)+2
                if statistics is not None:
                    kickbanlen = len(statistics.peers_kicked)+len(statistics.peers_banned)
                    if kickbanlen:
                        spewlen += kickbanlen+1
                else:
                    kickbanlen = 0
                for x in range(spewlen-spewList.GetItemCount()):
                    i = wxListItem()
#                   i.SetFont(self.default_font)
                    spewList.InsertItem(i)
                for x in range(spewlen,spewList.GetItemCount()):
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

                    for peer in statistics.peers_kicked:
                        x += 1
                        spewList.SetStringItem(x, 2, peer[0])
                        spewList.SetStringItem(x, 1, peer[1])
                        spewList.SetStringItem(x, 4, 'KICKED')
                        for i in [0,3,5,6,7,8,9,10,11,12,13,14]:
                            spewList.SetStringItem(x, i, '')

                    for peer in statistics.peers_banned:
                        x += 1
                        spewList.SetStringItem(x, 2, peer[0])
                        spewList.SetStringItem(x, 1, peer[1])
                        spewList.SetStringItem(x, 4, 'BANNED')
                        for i in [0,3,5,6,7,8,9,10,11,12,13,14]:
                            spewList.SetStringItem(x, i, '')

                if statistics is not None:
                    self.storagestats1.SetLabel(
                        '          currently downloading %d pieces (%d just started), %d pieces partially retrieved'
                                        % ( statistics.storage_active,
                                            statistics.storage_new,
                                            statistics.storage_dirty ) )
                    self.storagestats2.SetLabel(
                        '          %d of %d pieces complete (%d just downloaded), %d failed hash check'
                                        % ( statistics.storage_numcomplete,
                                            statistics.storage_totalpieces,
                                            statistics.storage_justdownloaded,
                                            statistics.storage_numflunked ) )

        if ( self.fileList is not None and statistics is not None
                and (statistics.filelistupdated or self.refresh_details) ):
            self.refresh_details = false
            statistics.filelistupdated = false
            for i in range(len(statistics.filecomplete)):
                if statistics.fileinplace[i]:
                    self.fileList.SetItemImage(i,2,2)
                    self.fileList.SetStringItem(i,1,"done")
                elif statistics.filecomplete[i]:
                    self.fileList.SetItemImage(i,1,1)
                    self.fileList.SetStringItem(i,1,"100%")
                else:
                    frac = int((len(statistics.filepieces2[i])-len(statistics.filepieces[i]))*100
                            /len(statistics.filepieces2[i]))
                    if frac > 0:
                        self.fileList.SetStringItem(i,1,'%d%%' % (frac))

        if self.configfile.configReset:     # whoopee!  Set everything invisible! :-)
            self.configfile.configReset = false

            self.dow.config['security'] = self.configfile.configfileargs['security']

            statsdisplayflag = self.configfile.configfileargs['gui_displaymiscstats']
            self.downTextLabel.Show(statsdisplayflag)
            self.upTextLabel.Show(statsdisplayflag)
            self.fileDestLabel.Show(statsdisplayflag)
            self.fileDestText.Show(statsdisplayflag)
            self.colSizer.Layout()

            self.downText.SetLabel('')          # blank these to flush them
            self.upText.SetLabel('')
            self.seedStatusText.SetLabel('')
            self.peerStatusText.SetLabel('')

            ratesettingsmode = self.configfile.configfileargs['gui_ratesettingsmode']
            ratesettingsflag1 = true    #\ settings
            ratesettingsflag2 = false   #/ for 'basic'
            if ratesettingsmode == 'none':
                ratesettingsflag1 = false
            elif ratesettingsmode == 'full':
                ratesettingsflag2 = true
            self.connChoiceLabel.Show(ratesettingsflag1)
            self.connChoice.Show(ratesettingsflag1)
            self.rateSpinnerLabel.Show(ratesettingsflag2)
            self.rateSpinner.Show(ratesettingsflag2)
            self.rateLowerText.Show(ratesettingsflag2)
            self.rateUpperText.Show(ratesettingsflag2)
            self.rateslider.Show(ratesettingsflag2)
            self.connSpinnerLabel.Show(ratesettingsflag2)
            self.connSpinner.Show(ratesettingsflag2)
            self.connLowerText.Show(ratesettingsflag2)
            self.connUpperText.Show(ratesettingsflag2)
            self.connslider.Show(ratesettingsflag2)
            self.unlimitedLabel.Show(ratesettingsflag2)

            if statistics is None or statistics.downTotal is None:
                self.gauge.SetForegroundColour(self.configfile.checkingcolor)
                self.gauge.SetBackgroundColour(wx.wxSystemSettings_GetColour(wxSYS_COLOUR_MENU))
            elif self.fin:
                self.gauge.SetForegroundColour(self.configfile.seedingcolor)
                self.gauge.SetBackgroundColour(self.configfile.downloadcolor)
            else:
                self.gauge.SetForegroundColour(self.configfile.downloadcolor)
                self.gauge.SetBackgroundColour(wx.wxSystemSettings_GetColour(wxSYS_COLOUR_MENU))

        self.frame.Layout()
        self.frame.Refresh()

        self.gui_lastupdate = time()
        self.gui_fractiondone = None


    def finished(self):
        self.fin = true
        self.invokeLater(self.onFinishEvent)

    def failed(self):
        self.fin = true
        self.invokeLater(self.onFailEvent)

    def error(self, errormsg):
        self.invokeLater(self.onErrorEvent, [errormsg])

    def onFinishEvent(self):
        self.activity = hours(time () - self.starttime) + ' / ' +'Download Succeeded!'
        self.cancelButton.SetLabel('Finish')
        self.gauge.SetBackgroundColour(self.configfile.downloadcolor)
        self.gauge.SetValue(0)
        self.gauge.SetForegroundColour(self.configfile.seedingcolor)
        self.frame.SetTitle('%s - Upload - BitTorrent %s' % (self.filename, version))
        if (sys.platform == 'win32'):
            self.icon = wxIcon(os.path.join(basepath,'icon_done.ico'), wxBITMAP_TYPE_ICO)
            self.frame.SetIcon(self.icon)
        if hasattr(self.frame, "tbicon"):
            self.frame.tbicon.SetIcon(self.icon, "BitTorrent - Finished")
        self.downRateText.SetLabel('')

    def onFailEvent(self):
        if not self.shuttingdown:
            self.timeText.SetLabel(hours(time () - self.starttime) + ' / ' +'Failed!')
            self.activity = 'Failed!'
            self.cancelButton.SetLabel('Close')
            self.gauge.SetValue(0)
            self.downRateText.SetLabel('')
            self.setStatusIcon('startup')

    def onErrorEvent(self, errormsg):
        if not self.displayUsage(errormsg):
            if errormsg[:2] == '  ':    # indent at least 2 spaces means a warning message
                self.errorText.SetLabel(errormsg)
                self.lastError = time ()
            else:
                self.errorText.SetLabel(strftime('ERROR (%I:%M %p) -\n') + errormsg)
                self.lastError = time ()


    def chooseFile(self, default, size, saveas, dir):
        f = Event()
        bucket = [None]
        self.invokeLater(self.onChooseFile, [default, bucket, f, size, dir, saveas])
        f.wait()
        return bucket[0]

    def onChooseFile(self, default, bucket, f, size, dir, saveas):
        if saveas == '':
            if self.configfile.configfileargs['gui_default_savedir'] != '':
                start_dir = self.configfile.configfileargs['gui_default_savedir']
            else:
                start_dir = self.configfile.configfileargs['last_saved']
            if not isdir(start_dir):    # if it's not set properly
                start_dir = '/'    # yes, this hack does work in Windows
            if dir:
                if isdir(join(start_dir,default)):
                    start_dir = join(start_dir,default)
                dl = wxDirDialog(self.frame,
                        'Choose a directory to save to, pick a partial download to resume',
                        defaultPath = start_dir, style = wxDD_DEFAULT_STYLE | wxDD_NEW_DIR_BUTTON)
            else:
                dl = wxFileDialog(self.frame,
                        'Choose file to save as, pick a partial download to resume', 
                        defaultDir = start_dir, defaultFile = default, wildcard = '*',
                        style = wxSAVE)

            if dl.ShowModal() != wxID_OK:
                f.set()
                self.done(None)
                return

            d = dl.GetPath()
            bucket[0] = d
            d1,d2 = split(d)
            if d2 == default:
                d = d1
            self.configfile.WriteLastSaved(d)

        else:
            bucket[0] = saveas
            default = basename(saveas)

        self.fileNameText.SetLabel('%s' % (default))
        self.fileSizeText.SetLabel('(%.2f MiB)' % (float(size) / (1 << 20)))
        self.timeText.SetLabel(hours(time () - self.starttime) + ' / ' + self.activity)
        self.fileDestText.SetLabel(bucket[0])
        self.filename = default
        self.frame.SetTitle(default + '- BitTorrent ' + version)

        minsize = self.fileNameText.GetBestSize()
        if (not self.configfile.configfileargs['gui_stretchwindow'] or
                            minsize.GetWidth() < self.addwidth):
            minsize.SetWidth(self.addwidth)
        self.fnsizer.SetMinSize (minsize)
        minsize.SetHeight(self.fileSizeText.GetBestSize().GetHeight())
        self.fnsizer2.SetMinSize (minsize)
        minsize.SetWidth(minsize.GetWidth()+(self.FONT*8))
        minsize.SetHeight(self.fileNameText.GetBestSize().GetHeight()+self.fileSizeText.GetBestSize().GetHeight())
        minsize.SetHeight(2*self.errorText.GetBestSize().GetHeight())
        self.errorTextSizer.SetMinSize(minsize)
        self.topboxsizer.SetMinSize(minsize)

        # Kludge to make details and about catch the event
        self.frame.SetSize ((self.frame.GetSizeTuple()[0]+1, self.frame.GetSizeTuple()[1]+1))
        self.frame.SetSize ((self.frame.GetSizeTuple()[0]-1, self.frame.GetSizeTuple()[1]-1))
        self.colSizer.Fit(self.frame)
        self.frame.Layout()
        self.frame.Refresh()
        f.set()

    def newpath(self, path):
        self.invokeLater(self.onNewpath, [path])

    def onNewpath(self, path):
        self.fileDestText.SetLabel(path)

    def pause(self, event):
        self.invokeLater(self.onPause)

    def onPause(self):
        if self.ispaused:
            self.ispaused = false
            self.pauseButton.SetLabel('Pause')
            self.dow.Unpause()
        else:
            if self.dow.Pause():
                self.ispaused = true
                self.pauseButton.SetLabel('Resume')
                self.downRateText.SetLabel(' ')
                self.upRateText.SetLabel(' ')
                self.seedStatusText.SetLabel(' ')
                self.peerStatusText.SetLabel(' ')
                self.setStatusIcon('startup')

    def done(self, event):
        self.uiflag.set()
        self.flag.set()
        self.shuttingdown = true
        if hasattr(self.frame, "tbicon"):
            self.frame.tbicon.Destroy()
            del self.frame.tbicon
        if self.ispaused:
            self.dow.Unpause()
        if (self.detailBox is not None):
            try:
                self.detailBox.Close ()
            except wxPyDeadObjectError, e:
                self.detailBox = None
        if (self.aboutBox is not None):
            try:
                self.aboutBox.Close ()
            except wxPyDeadObjectError, e:
                self.aboutBox = None
        if (self.creditsBox is not None):
            try:
                self.creditsBox.Close ()
            except wxPyDeadObjectError, e:
                self.creditsBox = None
        if (self.advBox is not None):
            try:
                self.advBox.Close ()
            except wxPyDeadObjectError, e:
                self.advBox = None

        if (self.statusIconHelpBox is not None):
            try:
                self.statusIconHelpBox.Close ()
            except wxPyDeadObjectError, e:
                self.statusIconHelpBox = None
        self.configfile.Close()
        self.frame.Destroy()

    def exception(self):
        data = StringIO()
        print_exc(file = data)
        print data.getvalue()   # report exception here too
        self.on_errorwindow(data.getvalue())

    def errorwindow(self, err):
        self.invokeLater(self.on_errorwindow,[err])

    def on_errorwindow(self, err):
        if self._errorwindow is None:
            w = wxFrame(None, -1, 'BITTORRENT ERROR', size = (1,1))
            panel = wxPanel(w, -1)
            sizer = wxFlexGridSizer(cols = 1)

            t = ( 'BitTorrent ' + version + '\n' +
                  'OS: ' + sys.platform + '\n' +
                  'Python version: ' + sys.version + '\n' +
                  'wxWindows version: ' + wxVERSION_STRING + '\n' )

            try:
                t += 'Psyco version: ' + hex(psyco.__version__)[2:] + '\n'
            except:
                pass
            try:
                t += 'Allocation method: ' + self.config['alloc_type']
                if self.dow.storagewrapper.bgalloc_active:
                    t += '*'
                t += '\n'
            except:
                pass

            sizer.Add(wxTextCtrl(panel, -1, t + '\n' + err,
                                size = (500,300), style = wxTE_READONLY|wxTE_MULTILINE))

            sizer.Add(wxStaticText(panel, -1,
                    '\nHelp us iron out the bugs in the engine!' +
                    '\nPlease report this error to info@degreez.net'))

            border = wxBoxSizer(wxHORIZONTAL)
            border.Add(sizer, 1, wxEXPAND | wxALL, 4)

            panel.SetSizer(border)
            panel.SetAutoLayout(true)

            w.Show()
            border.Fit(panel)
            w.Fit()
            self._errorwindow = w


class btWxApp(wxApp):
    def __init__(self, x, params):
        self.params = params
        self.configfile = configReader()
        wxApp.__init__(self, x)

    def OnInit(self):
        doneflag = Event()
        d = DownloadInfoFrame(doneflag, self.configfile)
        self.SetTopWindow(d.frame)
        if len(self.params) == 0:
            b = wxFileDialog (d.frame, 'Choose .torrent file to use',
                        defaultDir = '', defaultFile = '', wildcard = '*.torrent',
                        style = wxOPEN)

            if b.ShowModal() == wxID_OK:
                self.params.append (b.GetPath())

        thread = Thread(target = next, args = [self.params, d, doneflag, self.configfile])
        thread.setDaemon(false)
        thread.start()
        return 1

def run(params):
    app = btWxApp(0, params)
    app.MainLoop()

def next(params, d, doneflag, configfile):
    if PROFILER:
        import profile, pstats
        p = profile.Profile()
        p.runcall(_next, params, d, doneflag, configfile)
        log = open('profile_data.'+strftime('%y%m%d%H%M%S')+'.txt','a')
        normalstdout = sys.stdout
        sys.stdout = log
#        pstats.Stats(p).strip_dirs().sort_stats('cumulative').print_stats()
        pstats.Stats(p).strip_dirs().sort_stats('time').print_stats()
        sys.stdout = normalstdout
    else:
        _next(params, d, doneflag, configfile)

def _next(params, d, doneflag, configfile):
    dow = Download()
    d.dow = dow
    configfile.setDownloadDefaults(dow.getDefaults())
    d.configfile = configfile
    d.configfileargs = d.configfile.configfileargs
    try:
        dow.download(params, d.chooseFile, d.updateStatus, d.finished, d.error, doneflag, 100,
                     d.newpath, d.configfileargs, d.errorwindow)
    except:
        data = StringIO()
        print_exc(file = data)
        print data.getvalue()   # report exception here too
        d.errorwindow(data.getvalue())
    if not d.fin:
        d.failed()


if __name__ == '__main__':
    if argv[1:] == ['--version']:
        print version
        sys.exit(0)
    run(argv[1:])
