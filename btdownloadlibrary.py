# Written by Bram Cohen
# see LICENSE.txt for license information

import BitTorrent.download
from threading import Event

def dummychoose(default, size, saveas, dir):
    return saveas

def dummydisplay(fractionDone = None, timeEst = None, 
        downRate = None, upRate = None, activity = None):
    pass

def download(url, file):
    ev = Event()
    w = Event()
    def fin(worked, errormsg, ev = ev, w = w):
        ev.set()
        if worked:
            w.set()
    BitTorrent.download.download(['--url', url, '--saveas', file], 
        dummychoose, dummydisplay, fin, ev, 80)
    return w.isSet()
