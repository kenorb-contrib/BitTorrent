#!/usr/bin/env python

# Written by Bram Cohen and Myers Carpenter
# see LICENSE.txt for license information

from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

from BitTorrent import version
from BitTorrent.download import download
from threading import Event, Thread
from os.path import join
from os import getcwd
from wxPython.wx import *
from time import strftime
from webbrowser import open_new

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

wxEVT_INVOKE = wxNewEventType()

def EVT_INVOKE(win, func):
    win.Connect(-1, -1, wxEVT_INVOKE, func)

class InvokeEvent(wxPyEvent):
    def __init__(self, func, args, kwargs):
        wxPyEvent.__init__(self)
        self.SetEventType(wxEVT_INVOKE)
        self.func = func
        self.args = args
        self.kwargs = kwargs

def pr(event):
    print 'augh!'

class DownloadInfoFrame:
    def __init__(self, flag):
        frame = wxFrame(None, -1, 'BitTorrent ' + version + ' download', size = wxSize(400, 250))
        self.frame = frame
        self.flag = flag
        self.fin = false
        self.shown = false

        panel = wxPanel(frame, -1)
        colSizer = wxFlexGridSizer(cols = 1, vgap = 3)

        fnsizer = wxBoxSizer(wxHORIZONTAL)

        self.fileNameText = wxStaticText(panel, -1, '', style = wxALIGN_LEFT)
        fnsizer.Add(self.fileNameText, 1, wxALIGN_BOTTOM)
        self.aboutText = wxStaticText(panel, -1, 'about', style = wxALIGN_RIGHT)
        self.aboutText.SetForegroundColour('Blue')
        self.aboutText.SetFont(wxFont(14, wxNORMAL, wxNORMAL, wxNORMAL, true))
        fnsizer.Add(self.aboutText, 0, wxEXPAND)
        colSizer.Add(fnsizer, 0, wxEXPAND)

        self.gauge = wxGauge(panel, -1, range = 1000, style = wxGA_SMOOTH)
        colSizer.Add(self.gauge, 0, wxEXPAND)

        gridSizer = wxFlexGridSizer(cols = 2, vgap = 3, hgap = 8)
        
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

        self.errorText = wxStaticText(panel, -1, '', style = wxALIGN_LEFT)
        self.errorText.SetForegroundColour('Red')
        colSizer.Add(self.errorText, 0, wxEXPAND)
        self.cancelButton = wxButton(panel, -1, 'Cancel')
        colSizer.Add(self.cancelButton, 0, wxALIGN_CENTER)
        colSizer.AddGrowableCol(0)
        colSizer.AddGrowableRow(3)

        border = wxBoxSizer(wxHORIZONTAL)
        border.Add(colSizer, 1, wxEXPAND | wxALL, 4)
        panel.SetSizer(border)
        panel.SetAutoLayout(true)
        
        EVT_LEFT_DOWN(self.aboutText, self.donate)
        EVT_CLOSE(frame, self.done)
        EVT_BUTTON(frame, self.cancelButton.GetId(), self.done)
        EVT_INVOKE(frame, self.onInvoke)

    def donate(self, event):
        Thread(target = self.donate2).start()

    def donate2(self):
        open_new('http://bitconjurer.org/BitTorrent/donate.html')

    def onInvoke(self, event):
        if not self.flag.isSet():
            apply(event.func, event.args, event.kwargs)

    def invokeLater(self, func, args = [], kwargs = {}):
        if not self.flag.isSet():
            wxPostEvent(self.frame, InvokeEvent(func, args, kwargs))

    def updateStatus(self, fractionDone = None,
            timeEst = None, downRate = None, upRate = None,
            activity=None):
        self.invokeLater(self.onUpdateStatus, [fractionDone, timeEst, downRate, upRate, activity])

    def onUpdateStatus(self, fractionDone, timeEst, downRate, upRate, activity):
        if fractionDone is not None and not self.fin:
            self.gauge.SetValue(int(fractionDone * 1000))
            self.frame.SetTitle('%d%% %s - BitTorrent %s' % (int(fractionDone*100), self.filename, version))
        if timeEst is not None:
            self.timeEstText.SetLabel(hours(timeEst))
        if activity is not None and not self.fin:
            self.timeEstText.SetLabel(activity)
        if downRate is not None:
            self.downRateText.SetLabel('%.0f kB/s' % (float(downRate) / (1 << 10)))
        if upRate is not None:
            self.upRateText.SetLabel('%.0f kB/s' % (float(upRate) / (1 << 10)))

    def finished(self):
        self.fin = true
        self.invokeLater(self.onFinishEvent)

    def failed(self):
        self.fin = true
        self.invokeLater(self.onFailEvent)

    def error(self, errormsg):
        self.invokeLater(self.onErrorEvent, [errormsg])

    def onFinishEvent(self):
        self.timeEstText.SetLabel('Download Succeeded!')
        self.cancelButton.SetLabel('Finish')
        self.gauge.SetValue(1000)
        self.frame.SetTitle('%s - Upload - BitTorrent %s' % (self.filename, version))
        self.downRateText.SetLabel('')

    def onFailEvent(self):
        self.timeEstText.SetLabel('Failed!')
        self.cancelButton.SetLabel('Close')
        self.gauge.SetValue(0)
        self.downRateText.SetLabel('')

    def onErrorEvent(self, errormsg):
        if not self.shown:
            self.frame.Show(true)
        self.errorText.SetLabel(strftime('ERROR (%I:%M %p) -\n') + errormsg)

    def chooseFile(self, default, size, saveas, dir):
        f = Event()
        bucket = [None]
        self.invokeLater(self.onChooseFile, [default, bucket, f, size, dir])
        f.wait()
        return bucket[0]
    
    def onChooseFile(self, default, bucket, f, size, dir):
        if dir:
            dl = wxDirDialog(self.frame, 'Choose a directory to save to, pick a partial download to resume', 
                join(getcwd(), default), style = wxDD_DEFAULT_STYLE | wxDD_NEW_DIR_BUTTON)
        else:
            dl = wxFileDialog(self.frame, 'Choose file to save as, pick a partial download to resume', '', default, '*.*', wxSAVE)
        if dl.ShowModal() != wxID_OK:
            self.done(None)
        else:
            bucket[0] = dl.GetPath()
            self.fileNameText.SetLabel('%s (%.1f MB)' % (default, float(size) / (1 << 20)))
            self.timeEstText.SetLabel('Starting up...')
            self.fileDestText.SetLabel(dl.GetPath())
            self.filename = default
            self.frame.SetTitle(default + '- BitTorrent ' + version)
            self.shown = true
            self.frame.Show(true)
        f.set()

    def newpath(self, path):
        self.fileDestText.SetLabel(path)

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
    download(params, d.chooseFile, d.updateStatus, d.finished, d.error, doneflag, 100, d.newpath)
    if not d.fin:
        d.failed()

if __name__ == '__main__':
    run(argv[1:])
