#!/usr/bin/env python

# Written by Bram Cohen
# This file is public domain
# The authors disclaim all liability for any damages resulting from
# any use of this software.

from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

from BitTorrent.download import download
from threading import Event, Thread
from wxPython.wx import *
from threading import Thread

wxEVT_UPDATE_FILE = 19238

def EVT_UPDATE_FILE(win, func):
    win.Connect(-1, -1, wxEVT_UPDATE_FILE, func)

class UpdateFileEvent(wxPyEvent):
    def __init__(self, default, bucket, flag):
        wxPyEvent.__init__(self)
        self.SetEventType(wxEVT_UPDATE_FILE)
        self.default = default
        self.bucket = bucket
        self.flag = flag

wxEVT_UPDATE_STATUS = 19239

def EVT_UPDATE_STATUS(win, func):
    win.Connect(-1, -1, wxEVT_UPDATE_STATUS, func)

class UpdateStatusEvent(wxPyEvent):
    def __init__(self, a, b):
        wxPyEvent.__init__(self)
        self.SetEventType(wxEVT_UPDATE_STATUS)
        self.a = a
        self.b = b

class DisplayInfo(wxFrame):
    def __init__(self, flag):
        self.flag = flag
        wxFrame.__init__(self, None, -1, 'BitTorrent download', size = wxSize(400, 300))
        self.SetAutoLayout(true)
        self.text = wxStaticText(self, -1, 'garbage', wxPoint(10, 10))
        self.text.SetPosition(wxPoint(10, 10))

        self.button = wxButton(self, 1010, ' garbage ')

        lc = wxLayoutConstraints()
        lc.centreX.SameAs(self, wxCentreX)
        lc.centreY.SameAs(self, wxBottom, -20)
        lc.height.AsIs()
        lc.width.PercentOf(self, wxWidth, 50)
        self.button.SetConstraints(lc);

        self.displayed = 0
        EVT_CLOSE(self, self.done)
        EVT_BUTTON(self, 1010, self.done)
        EVT_UPDATE_FILE(self, self.onfile)
        EVT_UPDATE_STATUS(self, self.onstatus)

    def set(self, a, b):
        self.displayed = 1
        wxPostEvent(self, UpdateStatusEvent(a, b))

    def onstatus(self, event):
        self.text.SetLabel(event.a)
        self.button.SetLabel(' ' + event.b + ' ')
        self.Show(1)

    def onfile(self, event):
        dl = wxFileDialog(self, 'choose file to save as, pick a partial download to resume', '.', event.default, '*.*', wxSAVE)
        if dl.ShowModal() != wxID_OK:
            event.bucket.append('')
        else:
            event.bucket.append(dl.GetPath())
        event.flag.set()

    def done(self, event):
        self.flag.set()
        self.Destroy()

class MyApp(wxApp):
    def __init__(self, x, d):
        self.d = d
        wxApp.__init__(self, x)

    def OnInit(self):
        self.SetTopWindow(self.d)
        return 1

def run(params):
    doneflag = Event()
    d = DisplayInfo(doneflag)
    app = MyApp(0, d)
    Thread(target = next, args = [params, d, doneflag]).start()
    app.MainLoop()

def next(params, d, doneflag):
    def getname(default, d = d):
        f = Event()
        bucket = []
        wxPostEvent(d, UpdateFileEvent(default, bucket, f))
        f.wait()
        return bucket[0]
    download(params, getname, d.set, doneflag, 100)

    if not d.displayed:
        d.Destroy()

if __name__ == '__main__':
    run(argv[1:])
