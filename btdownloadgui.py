#!/usr/bin/env python

# Written by Bram Cohen and Myers Carpenter
# see LICENSE.txt for license information

from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

from BitTorrent.download import download
from threading import Event, Thread
from os.path import join
from os import getcwd
from wxPython.wx import *

def kify(n):
    return str(long((float(n) / (2 ** 10)) * 10) / 10.0)

def mbfy(n):
    return str(long((float(n) / (2 ** 20)) * 10) / 10.0)

def ex(n):
    if n >= 10:
        return str(n)
    else:
        return '0' + str(n)

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
        return str(h) + ' hour ' + ex(m) + ' min ' + ex(sec) + ' sec'
    else:
        return str(m) + ' min ' + ex(sec) + ' sec'

wxEVT_CHOOSE_FILE = wxNewId()

def EVT_CHOOSE_FILE(win, func):
    win.Connect(-1, -1, wxEVT_CHOOSE_FILE, func)

class ChooseFileEvent(wxPyEvent):
    def __init__(self, default, bucket, flag, size, dir):
        wxPyEvent.__init__(self)
        self.SetEventType(wxEVT_CHOOSE_FILE)
        self.default = default
        self.bucket = bucket
        self.flag = flag
        self.size = size
        self.dir = dir

wxEVT_UPDATE_STATUS = wxNewId()

def EVT_UPDATE_STATUS(win, func):
    win.Connect(-1, -1, wxEVT_UPDATE_STATUS, func)

class UpdateStatusEvent(wxPyEvent):
    def __init__(self, fractionDone, timeEst, downRate, upRate,
            activity):
        
        wxPyEvent.__init__(self)
        self.SetEventType(wxEVT_UPDATE_STATUS)
        self.fractionDone = fractionDone
        self.timeEst = timeEst
        self.downRate = downRate
        self.upRate = upRate
        self.activity = activity

wxEVT_FINISH_STATUS = wxNewId()

def EVT_FINISH_STATUS(win, func):
    win.Connect(-1, -1, wxEVT_FINISH_STATUS, func)

class FinishEvent(wxPyEvent):
    def __init__(self):
        wxPyEvent.__init__(self)
        self.SetEventType(wxEVT_FINISH_STATUS)

wxEVT_FAIL_STATUS = wxNewId()

def EVT_FAIL_STATUS(win, func):
    win.Connect(-1, -1, wxEVT_FAIL_STATUS, func)

class FailEvent(wxPyEvent):
    def __init__(self):
        wxPyEvent.__init__(self)
        self.SetEventType(wxEVT_FAIL_STATUS)

wxEVT_ERROR_STATUS = wxNewId()

def EVT_ERROR_STATUS(win, func):
    win.Connect(-1, -1, wxEVT_FINISH_STATUS, func)

class ErrorEvent(wxPyEvent):
    def __init__(self, errormsg):
        wxPyEvent.__init__(self)
        self.SetEventType(wxEVT_ERROR_STATUS)
        self.errormsg = errormsg

class DownloadInfoFrame(wxFrame):
    def __init__(self, flag):
        wxFrame.__init__(self, None, -1, 'BitTorrent download', size = wxSize(550, 260))
        self.flag = flag
        self.fin = false
        self.shown = false
        self.drawGUI()

        EVT_CLOSE(self, self.done)
        EVT_BUTTON(self, self.cancelButton.GetId(), self.done)
        EVT_CHOOSE_FILE(self, self.onChooseFile)
        EVT_UPDATE_STATUS(self, self.onUpdateStatus)
        EVT_FINISH_STATUS(self, self.onFinishEvent)
        EVT_FAIL_STATUS(self, self.onFailEvent)
        EVT_ERROR_STATUS(self, self.onErrorEvent)
        
    def drawGUI(self):
        panel = wxPanel(self, -1)
        colSizer = wxBoxSizer(wxVERTICAL)

        colSizer.Add(wxStaticText(panel, -1, 'Saving:'), 0, wxALIGN_LEFT|wxTOP, 7)

        self.fileNameText = wxStaticText(panel, -1, '', style = wxALIGN_LEFT)
        colSizer.Add(self.fileNameText, 0, wxEXPAND, 4)

        self.gauge = wxGauge(panel, -1, range = 1000)
        self.gauge.SetBezelFace(5)
        self.gauge.SetShadowWidth(5)
        colSizer.Add(self.gauge, 0, wxEXPAND, 7)

        gridSizer = wxFlexGridSizer(cols = 2, vgap = 7, hgap = 8)
        
        gridSizer.Add(wxStaticText(panel, -1, 'Estimated time left:'))
        self.timeEstText = wxStaticText(panel, -1, '')
        gridSizer.Add(self.timeEstText, 0, wxEXPAND)

        gridSizer.Add(wxStaticText(panel, -1, 'Download to:'))
        self.fileDestText = wxStaticText(panel, -1, '')
        gridSizer.Add(self.fileDestText, 0, wxEXPAND)

        gridSizer.Add(wxStaticText(panel, -1, 'Download rate:'))
        self.downRateText = wxStaticText(panel, -1, '')
        gridSizer.Add(self.downRateText, 0, wxEXPAND)

        gridSizer.Add(wxStaticText(panel, -1, 'Upload rate:'))
        self.upRateText = wxStaticText(panel, -1, '')
        gridSizer.Add(self.upRateText, 0, wxEXPAND)
        gridSizer.AddGrowableCol(1)

        colSizer.Add(gridSizer, 0, wxEXPAND, 7)
        
        self.cancelButton = wxButton(panel, -1, 'Cancel')
        colSizer.Add(self.cancelButton, 0, wxALIGN_RIGHT, 5)
        colSizer.Add(wxStaticText(panel, -1, ''), 1, wxEXPAND)

        border = wxBoxSizer(wxHORIZONTAL)
        border.Add(colSizer, 1, wxALL, 25)
        panel.SetSizer(border)
        panel.SetAutoLayout(true)
        
    def updateStatus(self, fractionDone = None,
            timeEst = None, downRate = None, upRate = None,
            activity=None):
        assert activity is None or not self.fin
        wxPostEvent(self, UpdateStatusEvent(fractionDone, timeEst, downRate, upRate, activity))

    def onUpdateStatus(self, event):
        if event.fractionDone is not None:
            self.gauge.SetValue(int(event.fractionDone * 1000))
        if event.timeEst is not None:
            self.timeEstText.SetLabel(hours(event.timeEst))
        if event.activity is not None and not self.fin:
            self.timeEstText.SetLabel(event.activity)
        if event.downRate is not None:
            self.downRateText.SetLabel('%s kB/s' % kify(event.downRate))
        if event.upRate is not None:
            self.upRateText.SetLabel('%s kB/s' % kify(event.upRate))

    def finished(self):
        self.fin = true
        wxPostEvent(self, FinishEvent())

    def failed(self):
        self.fin = true
        wxPostEvent(self, FailEvent())

    def error(self, errormsg):
        wxPostEvent(self, ErrorEvent(errormsg))

    def onFinishEvent(self, event):
        self.timeEstText.SetLabel('Download Succeeded!')
        self.cancelButton.SetLabel('Finish')
        self.gauge.SetValue(1000)
        self.downRateText.SetLabel('')

    def onFailEvent(self, event):
        self.timeEstText.SetLabel('Failed!')
        self.cancelButton.SetLabel('Close')
        self.gauge.SetValue(0)
        self.downRateText.SetLabel('')

    def onErrorEvent(self, event):
        if not self.shown:
            self.Show(true)
        dlg = wxMessageDialog(self, message = event.errormsg, 
            caption = 'Download Error', style = wxOK | wxICON_ERROR)
        dlg.Fit()
        dlg.Center()
        dlg.ShowModal()

    def chooseFile(self, default, size, saveas, dir):
        f = Event()
        bucket = [None]
        wxPostEvent(self, ChooseFileEvent(default, bucket, f, size, dir))
        f.wait()
        return bucket[0]
    
    def onChooseFile(self, event):
        if event.dir:
            dl = wxDirDialog(self, 'Choose a directory to save to, pick a partial download to resume', join(getcwd(), event.default))
        else:
            dl = wxFileDialog(self, 'Choose file to save as, pick a partial download to resume', '', event.default, '*.*', wxSAVE)
        if dl.ShowModal() != wxID_OK:
            self.done(None)
        else:
            event.bucket[0] = dl.GetPath()
            self.fileNameText.SetLabel(event.default + ' (' + mbfy(event.size) + ' MB)')
            self.timeEstText.SetLabel('Starting up...')
            self.fileDestText.SetLabel(dl.GetPath())
            self.shown = true
            self.Show(true)
        event.flag.set()

    def done(self, event):
        self.flag.set()
        self.Destroy()

class btWxApp(wxApp):
    def __init__(self, x, d):
        self.d = d
        wxApp.__init__(self, x)

    def OnInit(self):
        self.SetTopWindow(self.d)
        return 1

def run(params):
    doneflag = Event()
    d = DownloadInfoFrame(doneflag)
    app = btWxApp(0, d)
    thread = Thread(target = next, args = [params, d, doneflag])
    thread.setDaemon(false)
    thread.start()
    
    app.MainLoop()

def next(params, d, doneflag):
    download(params, d.chooseFile, d.updateStatus, d.finished, d.error, doneflag, 100)
    if not d.fin:
        d.failed()

if __name__ == '__main__':
    run(argv[1:])
