## some python code to handle managing multiple DL's at once
import callbacks
from BitTorrent.download import download
from threading import Event
from thread import start_new_thread


# this class encapsulates an ID and returns it with each callback, to keep the DL callbacks seperate!
class CallbackProxy:
    def __init__(self, id, chooseFile, display, finished):
	self.id = id
	self.xchooseFile = chooseFile
	self.xdisplay = display
	self.xfinished = finished
	
    def chooseFile(self, defs = None, size = 0, saveas = None, dir = 0):
	return self.xchooseFile(self.id, defs, size, saveas, dir)
    def display(self, fractionDone = 0.0, timeEst = 0.0, upRate = 0.0, downRate = 0.0, activity="" ):
	return self.xdisplay(self.id, fractionDone, timeEst, upRate, downRate, activity)
    def finished(self, fin = 0, errmsg = None):
	return self.xfinished(self.id, fin, errmsg)
	
	
## this class manages multiple downloads and keeps track of the flag objects for concelling
class DLManager:
    def __init__(self):
	self.flags = {}
    
    def newDlWithUrl(self, id, url):
	flag = Event()
	self.flags[id] = flag
	prox = CallbackProxy(id, callbacks.chooseFile, callbacks.display, callbacks.finished)
	start_new_thread(download, (['--url=%s' % url], prox.chooseFile, prox.display, prox.finished, flag, 80))
    def newDlWithFile(self, id, file):
	flag = Event()
	self.flags[id] = flag
	prox = CallbackProxy(id, callbacks.chooseFile, callbacks.display, callbacks.finished)
	start_new_thread(download, (['--responsefile=%s' % file], prox.chooseFile, prox.display, prox.finished, flag, 80))
	
    def cancelDlWithId(self, id):
	self.flags[id].set()
	del(self.flags[id])
