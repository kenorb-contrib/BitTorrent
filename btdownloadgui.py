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
        return '%d hour %02d min %02d sec' % (h, m, sec)
    else:
        return '%d min %02d sec' % (m, sec)

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
    win.Connect(-1, -1, wxEVT_ERROR_STATUS, func)

class ErrorEvent(wxPyEvent):
    def __init__(self, errormsg):
        wxPyEvent.__init__(self)
        self.SetEventType(wxEVT_ERROR_STATUS)
        self.errormsg = errormsg

class DownloadInfoFrame:
    def __init__(self, flag):
        frame = wxFrame(None, -1, 'BitTorrent download', size = wxSize(550, 300))
        self.frame = frame
        self.flag = flag
        self.fin = false
        self.shown = false

        panel = wxPanel(frame, -1)
        colSizer = wxFlexGridSizer(cols = 1, vgap = 7)

        colSizer.Add(wxStaticText(panel, -1, 'Saving:'), 0, wxEXPAND)

        self.fileNameText = wxStaticText(panel, -1, '', style = wxALIGN_LEFT)
        colSizer.Add(self.fileNameText, 0, wxEXPAND)

        self.gauge = wxGauge(panel, -1, range = 1000, style = wxGA_SMOOTH)
        colSizer.Add(self.gauge, 0, wxEXPAND)

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

        colSizer.Add(gridSizer, 0, wxEXPAND)

        colSizer.Add(1, 1, 1, wxEXPAND)
        self.cancelButton = wxButton(panel, -1, 'Cancel')
        colSizer.Add(self.cancelButton, 0, wxALIGN_CENTER)
        colSizer.AddGrowableCol(0)
        colSizer.AddGrowableRow(4)

        border = wxBoxSizer(wxHORIZONTAL)
        border.Add(colSizer, 1, wxEXPAND | wxALL, 25)
        panel.SetSizer(border)
        panel.SetAutoLayout(true)
        
        EVT_CLOSE(frame, self.done)
        EVT_BUTTON(frame, self.cancelButton.GetId(), self.done)
        EVT_CHOOSE_FILE(frame, self.onChooseFile)
        EVT_UPDATE_STATUS(frame, self.onUpdateStatus)
        EVT_FINISH_STATUS(frame, self.onFinishEvent)
        EVT_FAIL_STATUS(frame, self.onFailEvent)
        EVT_ERROR_STATUS(frame, self.onErrorEvent)
        
    def updateStatus(self, fractionDone = None,
            timeEst = None, downRate = None, upRate = None,
            activity=None):
        if self.flag.isSet():
            return
        wxPostEvent(self.frame, UpdateStatusEvent(fractionDone, timeEst, downRate, upRate, activity))

    def onUpdateStatus(self, event):
        if self.flag.isSet():
            return
        if event.fractionDone is not None:
            self.gauge.SetValue(int(event.fractionDone * 1000))
        if event.timeEst is not None:
            self.timeEstText.SetLabel(hours(event.timeEst))
        if event.activity is not None and not self.fin:
            self.timeEstText.SetLabel(event.activity)
        if event.downRate is not None:
            self.downRateText.SetLabel('%.1f K/s' % (float(event.downRate) / (1 << 10)))
        if event.upRate is not None:
            self.upRateText.SetLabel('%.1f K/s' % (float(event.upRate) / (1 << 10)))

    def finished(self):
        if self.flag.isSet():
            return
        self.fin = true
        wxPostEvent(self.frame, FinishEvent())

    def failed(self):
        if self.flag.isSet():
            return
        self.fin = true
        wxPostEvent(self.frame, FailEvent())

    def error(self, errormsg):
        if self.flag.isSet():
            return
        wxPostEvent(self.frame, ErrorEvent(errormsg))

    def onFinishEvent(self, event):
        if self.flag.isSet():
            return
        self.timeEstText.SetLabel('Download Succeeded!')
        self.cancelButton.SetLabel('Finish')
        self.gauge.SetValue(1000)
        self.downRateText.SetLabel('')

    def onFailEvent(self, event):
        if self.flag.isSet():
            return
        self.timeEstText.SetLabel('Failed!')
        self.cancelButton.SetLabel('Close')
        self.gauge.SetValue(0)
        self.downRateText.SetLabel('')

    def onErrorEvent(self, event):
        if self.flag.isSet():
            return
        if not self.shown:
            self.frame.Show(true)
        dlg = wxMessageDialog(self.frame, message = event.errormsg, 
            caption = 'Download Error', style = wxOK | wxICON_ERROR)
        dlg.Fit()
        dlg.Center()
        dlg.Show(true)

    def chooseFile(self, default, size, saveas, dir):
        if self.flag.isSet():
            return ''
        f = Event()
        bucket = [None]
        wxPostEvent(self.frame, ChooseFileEvent(default, bucket, f, size, dir))
        f.wait()
        return bucket[0]
    
    def onChooseFile(self, event):
        if self.flag.isSet():
            return
        if event.dir:
            dl = wxDirDialog(self.frame, 'Choose a directory to save to, pick a partial download to resume', 
                join(getcwd(), event.default), style = wxDD_DEFAULT_STYLE | wxDD_NEW_DIR_BUTTON)
        else:
            dl = wxFileDialog(self.frame, 'Choose file to save as, pick a partial download to resume', '', event.default, '*.*', wxSAVE)
        if dl.ShowModal() != wxID_OK:
            self.done(None)
        else:
            event.bucket[0] = dl.GetPath()
            self.fileNameText.SetLabel('%s (%.1f MB)' % (event.default, float(event.size) / (1 << 20)))
            self.timeEstText.SetLabel('Starting up...')
            self.fileDestText.SetLabel(dl.GetPath())
            self.shown = true
            self.frame.Show(true)
        event.flag.set()

    def done(self, event):
        self.flag.set()
        self.frame.Destroy()

class btWxApp(wxApp):
    def __init__(self, x, params):
        self.params = params
        wxApp.__init__(self, x)

    def OnInit(self):
        doneflag = Event()
        d = DownloadInfoFrame(doneflag)
        self.SetTopWindow(d.frame)
        thread = Thread(target = next, args = [self.params, d, doneflag])
        thread.setDaemon(false)
        thread.start()
        return 1

def run(params):
    app = btWxApp(0, params)
    app.MainLoop()

def next(params, d, doneflag):
    download(params, d.chooseFile, d.updateStatus, d.finished, d.error, doneflag, 100)
    if not d.fin:
        d.failed()

if __name__ == '__main__':
    run(argv[1:])
