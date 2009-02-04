#
#  Generate.py
#  BitTorrent
#
#  Created by Drue Loewenstern on Sun Feb 15 2004.
#  Copyright (c) 2004 __MyCompanyName__. All rights reserved.
#

from threading import Event
from traceback import print_exc
import sys
sys.argv = ["BitTorrent.app"]
import os

from Foundation import *
from AppKit import *
from PyObjCTools import NibClassBuilder
from objc import selector
import objc
NibClassBuilder.extractClasses("Metainfo")

#from btmakemetafile import makeinfo
#from btcompletedir import completedir
from BitTorrent.makemetafile import make_meta_file, make_meta_file_dht, calcsize
from BitTorrent.bencode import bencode, bdecode

ANNOUNCEKEY = "AnnounceString"
GWINKEY= "GenerateFrame"
COMPLETEDIRKEY = "CompleteDir"
SWITCHKEY = "TrackerSwitch"

TRACKER = 0
TLAUTO = 1
TLNODES = 2

# how many trackers should we remember?
NUM_TRACKERS = 8

# tag -> piece size
tags ={0:18,
       1:19,
       2:20,
       3:21,
       4:22
       }
defaults = NSUserDefaults.standardUserDefaults()

class Generate(NibClassBuilder.AutoBaseClass):
    gWindow = objc.IBOutlet('gWindow')
    gButton = objc.IBOutlet('gButton')
    announce = objc.IBOutlet('announce')
    iconWell = objc.IBOutlet('iconWell')
    subCheck = objc.IBOutlet('subCheck')
    progressMeter = objc.IBOutlet('progressMeter')
    fileField = objc.IBOutlet('fileField')
    
    def init(self):
        self = super(Generate, self).init()
        appDefaults = {ANNOUNCEKEY:bencode([]), COMPLETEDIRKEY:0, GWINKEY:"", SWITCHKEY:1}
        defaults.registerDefaults_(appDefaults)

        x=defaults.objectForKey_(ANNOUNCEKEY)
        try:
            self.trackers = bdecode(x)
        except ValueError:
            if x[:7] == "http://":
                self.trackers = [str(x.encode("utf-8"))]
            else:
                self.trackers = []
            defaults.setObject_forKey_(bencode(self.trackers), ANNOUNCEKEY)

    
        NSBundle.loadNibNamed_owner_("Metainfo", self)
        self.fname = None
        self.done = 0
        self.gWindow.registerForDraggedTypes_([NSFilenamesPboardType])
                
        self.gWindow.setFrameAutosaveName_(GWINKEY)
        self.gWindow.setFrameUsingName_(GWINKEY)
        
        try:
            self.announce.setStringValue_(self.trackers[0])
        except IndexError:
            pass
        self.subCheck.setState_(defaults.objectForKey_(COMPLETEDIRKEY))
        self.trackerPop.selectItemAtIndex_(defaults.objectForKey_(SWITCHKEY))
        self.popped_(self.trackerPop)
        return self
    
    ## combobox datasource methods
    def comboBox_completedString_(self, cb, s):
        for i in self.trackers:
            if i[:len(s)] == str(s.encode("utf-8")):
                return i
        return s

    def comboBox_indexOfItemWithStringValue_(self, cb, s):
        try:
            i = self.trackers.index(str(s.encode("utf-8")))
        except ValueError:
            i = NSNotFound
        return i
        
    def comboBox_objectValueForItemAtIndex_(self, cb, i):
        return self.trackers[i]
                
    def numberOfItemsInComboBox_(self, cb):
        return len(self.trackers)

    def sheetDidEnd_returnCode_contextInfo_(self, sheet, ret, ctx):
        pass
    
    def generate_(self, sender):
        panel = NSSavePanel.savePanel()
        switch = self.trackerPop.selectedItem().tag()
        self.gButton.setEnabled_(0)
        if switch != TLAUTO and self.announce.stringValue() == "":
            if switch == TRACKER:
                self.gButton.setEnabled_(1)
                NSRunAlertPanel(NSLocalizedString("Invalid Tracker URL", ""), NSLocalizedString("You must enter the tracker URL.  Contact the tracker administrator for the URL.", ""), None, None, None)
                return
            elif switch == TLNODES:
                self.gButton.setEnabled_(1)
                NSRunAlertPanel(NSLocalizedString("Invalid Trackerless Nodes", ""), NSLocalizedString("To use this option, you must enter the IP-address:Port of one or more stable nodes.", ""), None, None, None)
                return
        elif self.fname == None:
            self.gButton.setEnabled_(1)
            NSRunAlertPanel(NSLocalizedString("Invalid File", "invalid file chose for generate"),
                              NSLocalizedString("You must drag a file or folder into the generate window first.",
                                                "empty file for generate"), None, None, None)
            return
        else:
            try:
                self.trackers.remove(str(self.announce.stringValue().encode("utf-8")))
            except ValueError:
                pass
        self.trackers.insert(0, str(self.announce.stringValue().encode("utf-8")))
        if len(self.trackers) > NUM_TRACKERS:
            self.trackers.pop()
        defaults.setObject_forKey_(bencode(map(lambda a: str(a.encode("utf-8")), self.trackers)), ANNOUNCEKEY)
        defaults.setObject_forKey_(self.subCheck.state(), COMPLETEDIRKEY)
        defaults.setObject_forKey_(self.trackerPop.selectedItem().tag(), SWITCHKEY)
        path, file = os.path.split(self.fname)
        base, ext = os.path.splitext(file)
        if self.subCheck.isEnabled() and self.subCheck.state():
            self.prepareGenerateSaveFile_(self.fname)
        else:
            panel.beginSheetForDirectory_file_modalForWindow_modalDelegate_didEndSelector_contextInfo_(path, base+".torrent", 
                                                                                                            self.gWindow, self, 
                                                                                                            self.savePanelDidEnd_returnCode_contextInfo_, 0)
    
    def savePanelDidEnd_returnCode_contextInfo_(self, sheet, code, info):
        if code == 1:
            self.prepareGenerateSaveFile_(sheet.filename())
        else:
            self.gButton.setEnabled_(1)
    savePanelDidEnd_returnCode_contextInfo_ = selector(savePanelDidEnd_returnCode_contextInfo_, signature="v@:@ii")
    
    
    def prepareGenerateSaveFile_(self, f):
        self.flag = Event()
        self.done = 0
        self.target = f
        d = {'f':f, 'fname':self.fname,
             'complete':self.subCheck.isEnabled() and self.subCheck.state(),
             'flag':self.flag
             }
        switch = self.trackerPop.selectedItem().tag()
        if switch == TRACKER:
            d['url'] = self.announce.stringValue()
        elif switch == TLNODES:
            d['nodes'] = self.announce.stringValue()
        else:
            d['nodes'] = 'router.bittorrent.com:6881'
            
        self.subCheck.setEnabled_(0)
        self.gWindow.unregisterDraggedTypes()
        
        self.gButton.setTitle_(NSLocalizedString("Cancel", "cancel"))
        self.gButton.setAction_(self.cancel_)
        
        NSThread.detachNewThreadSelector_toTarget_withObject_(self.doGenerate_, self, d)
        
    def doGenerate_(self, d):
        f = d['f']
        fname = d['fname']
        complete = d['complete']
        flag = d['flag']
        
        try:
            pool = NSAutoreleasePool.alloc().init()
            self.total = calcsize(fname) * 1.0
            self.prog = 0
            if d.has_key('url'):
                info = make_meta_file(fname.encode('utf8'), target=f,
                                      url=d['url'].encode('utf8'),
                                      piece_len_exp=tags[self.pieceSize.selectedCell().tag()],
                                      flag=flag, progress=self.display, encoding='utf8')
            else:
                info = make_meta_file_dht(fname.encode('utf8'), target=f,
                                      nodes=d['nodes'].encode('utf8'),
                                      piece_len_exp=tags[self.pieceSize.selectedCell().tag()],
                                      flag=flag, progress=self.display, encoding='utf8', data_dir=NSApp().delegate().config['data_dir'])
            #completedir(map(lambda a: str(os.path.join(fname, a)), os.listdir(fname)), str(url.encode('utf8')), flag, self.display, self.displayFname, 18)
            self.endGenerate()
            pool.release()
        except Exception, e:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(self.err, e, 0)


    def err(self, val):
        NSRunInformationalAlertPanel(NSLocalizedString("File Error", "file error"),NSLocalizedString("Failed to make torrent file.  Error message: %s", "file error in generate message") % val, NSLocalizedString("OK", "OK"), None, None)
        self.cancel_(self)
        
    def display(self, val):
        pool = NSAutoreleasePool.alloc().init()
        self.performSelectorOnMainThread_withObject_waitUntilDone_(self.do_display, val, 0)
        
    def displayFname(self, val):
        pool = NSAutoreleasePool.alloc().init()
        self.performSelectorOnMainThread_withObject_waitUntilDone_(self.do_displayFname, val, 0)
        
    def endGenerate(self):
        pool = NSAutoreleasePool.alloc().init()
        self.performSelectorOnMainThread_withObject_waitUntilDone_(self.do_endGenerate, dict, 0)
        
    def do_display(self, val):
        self.prog += val
        if not self.done:
            self.progressMeter.setDoubleValue_(self.prog / self.total)
            self.gButton.setEnabled_(1)
            
    def do_displayFname(self, val):
        self.displayFile_(val)
        
    def do_endGenerate(self):
        fm = NSFileManager.defaultManager()
        wk = NSWorkspace.sharedWorkspace()
        
        d = fm.fileAttributesAtPath_traverseLink_(self.fname, 1)
        self.displayFile_(self.fname)
        if d['NSFileType'] == "NSFileTypeDirectory" and not wk.isFilePackageAtPath_(self.fname):
            self.subCheck.setEnabled_(1)
        else:
            self.subCheck.setEnabled_(0)

        self.progressMeter.setDoubleValue_(100.0)
        self.gWindow.registerForDraggedTypes_([NSFilenamesPboardType])
        self.gButton.setTitle_(NSLocalizedString("Generate", "Generate"))
        self.gButton.setEnabled_(1)
        self.gButton.setAction_(self.generate_)
        c = NSApp().delegate()
        dl = c.loadDLWindow(self.target)
        dl.savepath = self.fname
        dl.startDLThread()
        self.done = 1
        
    def cancel_(self, sender):
        self.do_cancel_(sender)
        
    def do_cancel_(self, sender):
        self.done = 1
        self.flag.set()
        self.progressMeter.setDoubleValue_(0.0)
        self.do_endGenerate()
        
    def open(self):
        self.gWindow.makeKeyAndOrderFront_(self)
    
    def displayFile_(self, f):
        icon = NSWorkspace.sharedWorkspace().iconForFile_(f)
        self.iconWell.setImage_(icon)
        self.fileField.setStringValue_(f)
        
    def draggingEntered_(self, sender):
        board = sender.draggingPasteboard()
        names = board.propertyListForType_('NSFilenamesPboardType')
        if len(names) > 0:
            f = names[0]
            self.displayFile_(f)
            self.progressMeter.setDoubleValue_(0.0)
            return NSDragOperationGeneric
        return NSDragOperationNone
        
    def draggingExited_(self, sender):
        if self.fname == None:
            self.iconWell.setImage_(None)
            self.fileField.setStringValue_("")
        else:
            self.displayFile_(self.fname)
        
    def performDragOperation_(self, sender):
        fm = NSFileManager.defaultManager()
        wk = NSWorkspace.sharedWorkspace()
        
        self.fname = self.fileField.stringValue()
        
        dict = fm.fileAttributesAtPath_traverseLink_(self.fname, 1)
        
        if dict['NSFileType'] == "NSFileTypeDirectory" and not wk.isFilePackageAtPath_(self.fname):
            self.subCheck.setEnabled_(1)
        else:
            self.subCheck.setEnabled_(0)
            
        return 1

    def popped_(self, sender):
        switch = sender.selectedItem().tag()
        if switch == TLAUTO:
            self.announce.setEnabled_(False)
        else:
            self.announce.setEnabled_(True)            
