#!/usr/bin/env python

# Written by Bram Cohen
# this file is public domain

from sys import argv, version
assert version >= '2', "Install Python 2.0 or greater"

from BitTorrent.download import download, downloadurl, defaults
from BitTorrent.parseargs import parseargs, formatDefinitions
from threading import Event, Thread
from wxPython.wx import *
from threading import Thread

class DisplayInfo(wxFrame):
    def __init__(self, flag):
        self.flag = flag
        wxFrame.__init__(self, None, -1, 'BitTorrent download', size=(200, 200))
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

        EVT_CLOSE(self, self.done)
        EVT_BUTTON(self, 1010, self.done)
        self.displayed = 0

    def set(self, a, b):
        self.text.SetLabel(a)
        self.button.SetLabel(' ' + b + ' ')
        if not self.displayed:
            self.displayed = 1
            self.Show(1)

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

def run(configDictionary, files, prefetched = None):
    doneflag = Event()
    d = DisplayInfo(doneflag)
    app = MyApp(0, d)
    def getname(default, d = d):
        dl = wxFileDialog(d, 'choose file to save as, pick a partial download to resume', '.', default, '*.*', wxSAVE)
        if dl.ShowModal() != wxID_OK:
            return ''
        return dl.GetPath()
    Thread(target = next, kwargs = {'files': files, 'prefetched': prefetched, 'getname': getname, 'd': d, 'doneflag': doneflag, 'configDictionary': configDictionary}).start()
    app.MainLoop()

def next(files, prefetched, getname, d, doneflag, configDictionary):
    if prefetched is None:
        downloadurl(files[0], getname, d.set, doneflag, configDictionary)
    else:
        download(prefetched, getname, d.set, doneflag, configDictionary)
    if not d.displayed:
        d.Destroy()

if __name__ == '__main__':
    if len(argv) == 1:
        print "usage: %s [options] <url> <file>" % argv[0]
        print formatDefinitions(configDefinitions)
    else:
        config, files = parseargs(argv[1:], defaults, 1, 1) 
        run(config, files)
