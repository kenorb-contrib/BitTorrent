#!/usr/bin/env python

# Written by Bram Cohen and Myers Carpenter
# see LICENSE.txt for license information

from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

from BitTorrent.download import download
from threading import Event, Thread
from wxPython.wx import *

wxEVT_CHOOSE_FILE = wxNewId()

def EVT_CHOOSE_FILE(win, func):
    win.Connect(-1, -1, wxEVT_CHOOSE_FILE, func)

class ChooseFileEvent(wxPyEvent):
    def __init__(self, default, bucket, flag):
        wxPyEvent.__init__(self)
        self.SetEventType(wxEVT_CHOOSE_FILE)
        self.default = default
        self.bucket = bucket
        self.flag = flag

wxEVT_UPDATE_STATUS = wxNewId()

def EVT_UPDATE_STATUS(win, func):
    win.Connect(-1, -1, wxEVT_UPDATE_STATUS, func)

class UpdateStatusEvent(wxPyEvent):
    def __init__(self, fileName = None, percentDone = None, 
        timeEst = None, fileDest = None, downRate = None, upRate = None):
        
        wxPyEvent.__init__(self)
        self.SetEventType(wxEVT_UPDATE_STATUS)
        self.fileName = fileName
        self.percentDone = percentDone
        self.timeEst = timeEst
        self.fileDest = fileDest
        self.downRate = downRate
        self.upRate = upRate

wxEVT_DOWNLOAD_ERROR = wxNewId()

def EVT_DOWNLOAD_ERROR(win, func):
    win.Connect(-1, -1, wxEVT_DOWNLOAD_ERROR, func)

class DownloadErrorEvent(wxPyEvent):
    def __init__(self, errorMsg):
        wxPyEvent.__init__(self)
        self.SetEventType(wxEVT_DOWNLOAD_ERROR)
        self.errorMsg = errorMsg

class DownloadInfoFrame(wxFrame):
    def __init__(self, flag):
        wxFrame.__init__(self, None, -1, 'BitTorrent download', size = wxSize(375, 260), 
            style = wxDEFAULT_FRAME_STYLE | wxMAXIMIZE_BOX)
        self.errorDlgShown = Event()
        self.errorDlgShown.set()
        self.flag = flag
        self.drawGUI()
#        self.openButton.Enable(false)
#        self.openFolderButton.Enable(false)

        EVT_CLOSE(self, self.done)
        EVT_BUTTON(self, self.cancelButton.GetId(), self.done)
        EVT_CHOOSE_FILE(self, self.onChooseFile)
        EVT_UPDATE_STATUS(self, self.onUpdateStatus)
        EVT_DOWNLOAD_ERROR(self, self.onDownloadError)
        
    def drawGUI(self):
        superSizer = wxBoxSizer(wxVERTICAL)
        
        colSizer = wxBoxSizer(wxVERTICAL)
        
#        self.animatedImage = wxStaticBitmap(self, -1, wxEmptyBitmap(350, 50), size = (350, 50))
#        colSizer.Add(self.animatedImage, 0, wxALIGN_CENTER_HORIZONTAL)

        colSizer.Add(wxStaticText(self, -1, 'Saving:'), 0, wxALIGN_LEFT|wxTOP, 7)

        self.fileNameText = wxStaticText(self, -1, '', style = wxALIGN_LEFT)
        colSizer.Add(self.fileNameText, 0, wxALIGN_LEFT|wxTOP, 4)

        self.gauge = wxGauge(self, -1, range = 100)
        self.gauge.SetBezelFace(3)
        self.gauge.SetShadowWidth(3)
        colSizer.Add(self.gauge, 1, wxEXPAND|wxALIGN_LEFT|wxTOP, 7)

        gridSizer = wxFlexGridSizer(cols = 2, vgap = 7, hgap = 8)
        
        gridSizer.Add(wxStaticText(self, -1, 'Estimated time left:'))
        self.timeEstText = wxStaticText(self, -1, '', style = wxALIGN_LEFT)
        gridSizer.Add(self.timeEstText)

        gridSizer.Add(wxStaticText(self, -1, 'Download to:'))
        self.fileDestText = wxStaticText(self, -1, '', style = wxALIGN_LEFT)
        gridSizer.Add(self.fileDestText, 1)

        gridSizer.Add(wxStaticText(self, -1, 'Download rate:'))
        self.downRateText = wxStaticText(self, -1, '', style = wxALIGN_LEFT)
        gridSizer.Add(self.downRateText, 1)

        gridSizer.Add(wxStaticText(self, -1, 'Upload rate:'))
        self.upRateText = wxStaticText(self, -1, '', style = wxALIGN_LEFT)
        gridSizer.Add(self.upRateText, 1)

        colSizer.Add(gridSizer, 0, wxALIGN_LEFT|wxTOP, 7)

        self.closeAfterCheckbox = wxCheckBox(self, -1, 'Close this dialog box when download completes')
        colSizer.Add(self.closeAfterCheckbox, 0, wxALIGN_LEFT|wxTOP, 7)
        
        rowSizer = wxBoxSizer(wxHORIZONTAL)
#        self.openButton = wxButton(self, -1, 'Open', size = (93, -1))
#        rowSizer.Add(self.openButton, 0, wxALIGN_RIGHT|wxLEFT, 62)
#        self.openFolderButton = wxButton(self, -1, 'Open Folder', size = (93, -1))
#        rowSizer.Add(self.openFolderButton, 0, wxALIGN_RIGHT|wxLEFT, 5)
        rowSizer.Add(258, 1, 1, wxEXPAND)
        self.cancelButton = wxButton(self, -1, 'Cancel', size = (93, -1))
        rowSizer.Add(self.cancelButton, 0, wxALIGN_RIGHT|wxLEFT, 5)
        colSizer.Add(rowSizer, 0, wxALIGN_BOTTOM|wxALIGN_LEFT|wxTOP, 21)

        superSizer.Add(colSizer, 0, wxALL, 12)

        self.SetSizer(superSizer)
        superSizer.Layout()
        superSizer.Fit(self)
        
    def updateStatus(self, fileName = None, percentDone = None,
        timeEst = None, fileDest = None, downRate = None, upRate = None):
        
        wxPostEvent(self, UpdateStatusEvent(fileName, percentDone, timeEst, fileDest, downRate, upRate))

    def onUpdateStatus(self, event):
        if event.fileName:
            self.fileNameText.SetLabel(event.fileName)
        if event.percentDone:
            self.gauge.SetValue(event.percentDone)
        if event.timeEst:
            self.timeEstText.SetLabel(event.timeEst)
        if event.fileDest:
            self.fileDestText.SetLabel(event.fileDest)
        if event.downRate:
            self.downRateText.SetLabel(event.downRate)
        if event.upRate:
            self.upRateText.SetLabel(event.upRate)

    def downloadError(self, errorMsg):
        self.errorDlgShown.clear()
        wxPostEvent(self, DownloadErrorEvent(errorMsg))

    def onDownloadError(self, event):
        dlg = wxMessageDialog(self, message = event.errorMsg, 
            caption = 'Download Error', style = wxOK | wxICON_ERROR)
        dlg.Fit()
        dlg.Center()
        dlg.ShowModal()
        self.errorDlgShown.set()

    def chooseFile(self, default):
        f = Event()
        bucket = []
        wxPostEvent(self, ChooseFileEvent(default, bucket, f))
        f.wait()
        return bucket[0]
    
    def onChooseFile(self, event):
        dl = wxFileDialog(self, 'Choose file to save as, pick a partial download to resume', '.', event.default, '*.*', wxSAVE)
        if dl.ShowModal() != wxID_OK:
            event.bucket.append('')
        else:
            event.bucket.append(dl.GetPath())
        self.fileNameText.SetLabel(event.default)
        self.timeEstText.SetLabel('Starting up...')
        self.fileDestText.SetLabel(dl.GetPath()) 
        self.Show(true)
        event.flag.set()

    def done(self, event):
        self.errorDlgShown.wait()
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
    download(params, d.chooseFile, d.updateStatus, d.downloadError, doneflag, 100)

    d.done(None)

if __name__ == '__main__':
    run(argv[1:])
