# Written by Bram Cohen
# see LICENSE.txt for license information

import BitTorrent.download
from threading import Event

def dummychoose(default, size):
    return default

def dummydisplay(fractionDone, timeEst, downRate, upRate, activity):
    pass

def download(url, file):
    ev = Event()
    w = Event()
    def fin(worked, errormsg, ev = ev, w = w):
        ev.set()
        if worked:
            w.set()
    BitTorrent.download.download(['--url=' + url, '--saveas=' + file], 
        dummychoose, dummydisplay, fin, ev, 80)
    return w.isSet()
