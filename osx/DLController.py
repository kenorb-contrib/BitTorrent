# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from traceback import print_exc
import string
from os import path

from Foundation import *
from AppKit import *
from PyObjCTools import NibClassBuilder
from objc import selector, IBOutlet
from Preferences import *
from TorrentInspector import TorrentInspector

from sha import sha
from time import sleep, time
from traceback import print_exc
from ServiceDelegate import ServiceDelegate
from BitTorrent.ConvertedMetainfo import ConvertedMetainfo
from BitTorrent.RateMeasure import RateMeasure
from BitTorrent.prefs import Preferences as BTPreferences
import sys
import utils
import os

import BitTorrent

from BitTorrent.bencode import bdecode,bencode

from BitTorrent import BTFailure, INFO, WARNING, ERROR, CRITICAL

LASTDIR ="LastSaveDir"
STALL_TIME = 5 * 60 # five minutes


appDefaults = {LASTDIR:NSHomeDirectory()}
defaults = NSUserDefaults.standardUserDefaults()
defaults.registerDefaults_(appDefaults)
        
        
NibClassBuilder.extractClasses("DLView")

class MalformedTorrentFile(Exception):
    pass
class TorrentFileMissing(Exception):
    pass

class DLController (NibClassBuilder.AutoBaseClass):
    def init(self):
        self = super(DLController, self).init()
        self.commands = []
        self.errors = []
        self.done = 0
        self.lastDisplay = 0.0
        self.ICR = False
        self.totalsize = None
        self.timeEst = ""
        self.listen_port = self.peer_id = self.info_hash = None
        self.savepath = None
        self.torrent = None
        self.up = self.oup = self.gup = 0
        self.down = self.odown = self.gdown = 0
        self.uprate = 0.0
        self.downrate = 0.0
        self.frac = 0.0
        self.activity = ''
        self.seedMeasure = None

        self.rsized = 1
        self._state = 'stopped'
        self.spew = None
        
        self.flag = None
        self.sdel = None
        self.starttime = self.completed = 0
        self.seenpeers = self.numPeers = 0
        self.torrent_path = ''
        self.torrent_data = ''
        self.ICR = False
        
        NSBundle.loadNibNamed_owner_("DLView", self)
        self.upfield.setStringValue_("")
        self.downfield.setStringValue_("")
        self.upratefield.setStringValue_("")
        self.downratefield.setStringValue_("")
        self.timefield.setStringValue_("")
        self.statusfield.setStringValue_("")
        self.statefield.setStringValue_("")        
        self.progressbar.setHidden_(True)
        self.upArrow.setHidden_(True)
        self.downArrow.setHidden_(True)

        self.app = NSApplication.sharedApplication().delegate()

        config = self.app.config

        self.QUEUESTOP = defaults.integerForKey_(QUEUESTOP)
        self.STOPTIME = defaults.integerForKey_(STOPTIME)
        self.STOPRATIO = defaults.floatForKey_(STOPRATIO)

        self.max_upload_rate = 0
        self.max_uploads = config['max_uploads']
        self.max_initiate = config['max_initiate']
        self.max_allow_in = config['max_allow_in']

        self.selected = 0
        self.stalled = False
        return self

    def initWithTorrentFile_(self, path):
        self.init()
        self.torrent_path = path
        try:
            data = open(path).read()
        except IOError, e:
            #XXX
            x = NSRunAlertPanel(NSLocalizedString("File Error", "file error"), 
                                NSLocalizedString("Error: %s", "normal error") % str(e), 
                                None, None, None)
        return self._initWithTorrentData_(data)

    def initWithTorrentData_(self, data):
        self.init()
        return self._initWithTorrentData_(data)
    
    def _initWithTorrentData_(self, data):
        try:
            s = bdecode(data)
            self.metainfo_data = data
        except Exception, e:
            raise MalformedTorrentFile, e
        self.torrent_data = data
        self.metainfo = ConvertedMetainfo(s)
        self.filefield.setStringValue_(unicode(self.metainfo.name_fs, 'utf-8'))
        self.statusfield.setStringValue_(utils.formSize(self.metainfo.total_bytes))
        return self

    def setHighlight(self, tog):
        if tog:
            self.upfield.setTextColor_(NSColor.selectedTextColor())
            self.downfield.setTextColor_(NSColor.selectedTextColor())
            self.upratefield.setTextColor_(NSColor.selectedTextColor())
            self.downratefield.setTextColor_(NSColor.selectedTextColor())
            self.filefield.setTextColor_(NSColor.selectedTextColor())
            self.timefield.setTextColor_(NSColor.selectedTextColor())
            self.statusfield.setTextColor_(NSColor.selectedTextColor())
            self.statefield.setTextColor_(NSColor.selectedTextColor())            
        else:
            self.upfield.setTextColor_(NSColor.controlTextColor())
            self.downfield.setTextColor_(NSColor.controlTextColor())
            self.upratefield.setTextColor_(NSColor.controlTextColor())
            self.downratefield.setTextColor_(NSColor.controlTextColor())
            self.filefield.setTextColor_(NSColor.controlTextColor())
            self.timefield.setTextColor_(NSColor.controlTextColor())
            self.statusfield.setTextColor_(NSColor.controlTextColor())            
            self.statefield.setTextColor_(NSColor.controlTextColor())                       

    
    def encodeWithCoder_(self, c):
        c.encodeObject_forKey_(1.2, "VERSION")
        c.encodeObject_forKey_(self.savepath, "savepath")
        c.encodeObject_forKey_(self._state, "state")
        c.encodeObject_forKey_(`long(self.up + self.oup)`, "up")
        c.encodeObject_forKey_(`long(self.down + self.odown)`, "down")
        c.encodeInt_forKey_(self.max_uploads, "max_uploads")
        c.encodeInt_forKey_(self.max_upload_rate, "max_upload_rate")
        c.encodeInt_forKey_(self.max_initiate, "max_initiate")
        c.encodeInt_forKey_(self.max_allow_in, "max_allow_in")
        c.encodeInt_forKey_(self.completed, "completed")
        c.encodeInt_forKey_(self.QUEUESTOP, "QUEUESTOP")
        c.encodeInt_forKey_(self.STOPTIME, "STOPTIME")
        c.encodeFloat_forKey_(self.STOPRATIO, "STOPRATIO")
        c.encodeObject_forKey_(self.torrent_path, "torrent")        
        c.encodeObject_forKey_(self.torrent_data.encode('base64'), "torrent_data")

    def initWithCoder_(self, c):
        self.init()
        if c.containsValueForKey_("VERSION"):
            version = c.decodeObjectForKey_("VERSION")
        else:
            version = 1.0
        
        self._state = c.decodeObjectForKey_("state")
        self.oup = long(c.decodeObjectForKey_("up"))
        self.odown = long(c.decodeObjectForKey_("down"))
        self.max_upload_rate = c.decodeIntForKey_("max_upload_rate")
        self.max_uploads = c.decodeIntForKey_("max_uploads")

        if c.containsValueForKey_("max_allow_in"):
            self.max_allow_in = c.decodeIntForKey_("max_allow_in")
        if c.containsValueForKey_("max_initiate"):
            self.max_initiate = c.decodeIntForKey_("max_initiate")

        if c.containsValueForKey_("STOPRATIO"):
            self.STOPRATIO = c.decodeFloatForKey_("STOPRATIO")
        if c.containsValueForKey_("QUEUESTOP"):
            self.QUEUESTOP = c.decodeIntForKey_("QUEUESTOP")
        if c.containsValueForKey_("max_initiate"):
            self.STOPTIME = c.decodeIntForKey_("STOPTIME")

        self.completed = c.decodeIntForKey_("completed")

        self.torrent_path = c.decodeObjectForKey_("torrent")
        if version >= 1.2:
            self.torrent_data = str(c.decodeObjectForKey_("torrent_data")).decode('base64')

        self.savepath = c.decodeObjectForKey_("savepath")

        self.filefield.setStringValue_(os.path.split(self.savepath)[-1])

        self.metainfo = None
        if self.torrent_path and not os.path.exists(self.torrent_path) and not self.torrent_data:
            self._state = 'failed'
            self.statefield.setStringValue_(NSLocalizedString("Error", "error stopped status"))
            self.statusfield.setStringValue_(NSLocalizedString("Torrent file missing.", "couldn't find torrent file error message"))
            return self
        elif self.torrent_path:
            data = open(self.torrent_path, 'rb').read()
        else:
            data = self.torrent_data

        try:
            self.metainfo = ConvertedMetainfo(bdecode(data))
        except:
            self._state = 'failed'
            self.timefield.setStringValue_(NSLocalizedString("Error", "error stopped status"))
            self.statusfield.setStringValue_(NSLocalizedString("Torrent file corrupted.", "torrent file not in bencode format or unreadable"))
            return self

        self.statusfield.setStringValue_(utils.formSize(self.metainfo.total_bytes))

        if version == 1.0 and self.metainfo.is_batch and os.path.split(self.savepath)[-1] != unicode(self.metainfo.name_fs, 'utf8'):
            # 3.4.2 would save it with or without the folder name and BT would figure it out, now BT expects the folder name
            self.savepath = os.path.join(self.savepath, unicode(self.metainfo.name_fs, 'utf8'))

        if self._state == 'running':
            self.done = 0
            self.startDLThread()
        else:
            self.dlExited()
        
        return self
 
    def clearDisplay(self):
        self.upfield.setStringValue_("")
        self.downfield.setStringValue_("")
        self.upratefield.setStringValue_("")
        self.downratefield.setStringValue_("")
        self.timefield.setStringValue_("")
        self.uprate = 0.0
        self.downrate = 0.0
                
        # save how much we've transferred
        self.oup += self.up
        self.odown += self.down
        
        self.up = self.gup = 0
        self.down = self.gdown = 0

        self.progressbar.setDoubleValue_(0.0)
        self.progressbar.setHidden_(True)
        self.upArrow.setHidden_(True)
        self.downArrow.setHidden_(True)
        self.remainingfield.setHidden_(True)
        self.spew = None
        
    def cancelDL(self, sender):
        if not self.isRunning():
            return
        
        self._state = 'canceled'
        self.statefield.setStringValue_(NSLocalizedString("Canceled", "canceled timefield status"))
        #self.statusfield.setStringValue_(NSLocalizedString("Shutting down...", "waiting for torrent to exit status"))

        self.sdel = None
        
        self.clearDisplay()

        if self.torrent:
            self.torrent._rawserver.external_add_task(0, self.torrent.shutdown, context=self.torrent)
            #self.dlExited()
        self._error((INFO, NSLocalizedString("Download stopped.", "cancelled dl")))
        NSNotificationCenter.defaultCenter().postNotificationName_object_("TorrentStatusChanged", self)
        
    def getTimeView(self):
        return self.timeView
    def getFileView(self):
        return self.fileView
    def getXFerView(self):
        return self.xferView
        
    def errorList(self):
        return self.errors
        
    def setConnection_(self, nc):
        self.conn = nc
    
    def backToPanel(self):
        self.owindow.contentView().addSubview_(self.fileView)
        self.owindow.contentView().addSubview_(self.timeView)
        self.owindow.contentView().addSubview_(self.xferView)
        
    
    def savePath(self):
        return self.savepath
        
    def _choose(self, str, size,saveas, directory):
        pool = NSAutoreleasePool.alloc().init()
        return self.savepath
        
    def choose(self):
        str, size, saveas, directory = unicode(self.metainfo.name_fs, 'utf-8'), self.metainfo.total_bytes, None, self.metainfo.is_batch
        try:
            panel = NSOpenPanel.openPanel()
            
            panel.setCanChooseDirectories_(1)
            if self.metainfo.is_batch:
                panel.setCanChooseFiles_(0)
            else:
                panel.setCanChooseFiles_(1)
                
            self.window.setTitle_(NSLocalizedString("Choose directory for %s", "Torrent window title when saving") % str)
            panel.setPrompt_(NSLocalizedString("Save", "save directory prompt"))
            panel.beginSheetForDirectory_file_modalForWindow_modalDelegate_didEndSelector_contextInfo_(defaults.objectForKey_(LASTDIR),
                                                                                        str, self.window, self,
                                                                                        self.openPanelDidEnd_returnCode_contextInfo_,
                                                                                        0)
        except:
            print_exc()
            
    def openPanelDidEnd_returnCode_contextInfo_(self, sheet, returnCode, contextInfo):
        if returnCode == NSOKButton:
            defaults.setObject_forKey_(sheet.directory(), LASTDIR)
            self.savepath = sheet.filename()
            name = unicode(self.metainfo.name_fs, 'utf8')

            if self.metainfo.is_batch:
                l = os.listdir(self.savepath)
                if name in l:
                    n = NSRunAlertPanel(NSLocalizedString("The folder %s already exists, attempt to resume? ", "dir resume") % name, 
                            NSLocalizedString("Resuming may overwrite the files with different data", "resume dir detail"), 
                            NSLocalizedString("Resume", "resume"), NSLocalizedString("Cancel", "cancel"), None)
                    if n != NSAlertDefaultReturn:
                        return self.performSelectorOnMainThread_withObject_waitUntilDone_(self.choose, (), 0)
                    self.savepath = os.path.join(self.savepath, name)
                else:
                    # torrent files, stripped of everything but the first directory
                    f = [unicode(a.split('/')[0], 'utf8') for a in self.metainfo.files_fs]
                    # figure out how many of the torrents files are present in l
                    n = len([a for a in f if a not in l])
                    if n:
                        # missing files, tack on name
                        self.savepath = os.path.join(self.savepath, name)
                    else:
                        # warn and save over
                        n = NSRunAlertPanel(NSLocalizedString("All of the files named in the torrent already exist in the folder \"%s\", attempt to resume?", "dir resume") % os.path.split(self.savepath)[-1], 
                                            NSLocalizedString("Resuming may overwrite the files with different data", "resume dir detail"), 
                                            NSLocalizedString("Resume", "resume"), NSLocalizedString("Cancel", "cancel"), None)
                        if n != NSAlertDefaultReturn:
                            return self.performSelectorOnMainThread_withObject_waitUntilDone_(self.choose, (), 0)
            else:
                if os.path.isdir(self.savepath):
                    l = os.listdir(self.savepath)
                    if name in l:
                        n = NSRunAlertPanel(NSLocalizedString("The file '%s' already exists, attempt to resume the torrent?", "filedir resume") % name, 
                                            NSLocalizedString("Resuming may overwrite the file with different data", "resume filedir detail"), 
                                            NSLocalizedString("Resume", "resume"), NSLocalizedString("Cancel", "cancel"), None)
                        if n != NSAlertDefaultReturn:
                            return self.performSelectorOnMainThread_withObject_waitUntilDone_(self.choose, (), 0)
                    self.savepath = os.path.join(self.savepath, name)
                else:
                    # warn and save over
                    n = NSRunAlertPanel(NSLocalizedString('Attempt to resume torrent using file "%s"?', "filedir resume") % os.path.split(self.savepath)[-1], 
                                        NSLocalizedString("Resuming may overwrite the file with different data", "resume filedir detail"), 
                                        NSLocalizedString("Resume", "resume"), NSLocalizedString("Cancel", "cancel"), None)
                    if n != NSAlertDefaultReturn:
                        return self.performSelectorOnMainThread_withObject_waitUntilDone_(self.choose, (), 0)
            self.filefield.setStringValue_(os.path.split(self.savepath)[-1])
        else:
            # user cancelled
            self.cancelDL(self)
            self.app.removeTorrent(self)
        self.window.setTitle_(NSLocalizedString("BitTorrent OSX", "torrent window title"))
        self.enqueue()
        NSNotificationCenter.defaultCenter().postNotificationName_object_("DoneChoosingTorrent", self)
    openPanelDidEnd_returnCode_contextInfo_ = selector(openPanelDidEnd_returnCode_contextInfo_, signature="v@:@ii")


    def enqueue(self):
        if defaults.objectForKey_(DOQUEUE):
            self.statefield.setStringValue_(NSLocalizedString("Waiting", "queued status"))
        else:
            self.startDLThread()


    def display(self):
        try:
            if self.torrent is None:
                raise AttributeError
            dict = self.torrent.get_status()
        except AttributeError:
            return

        if dict['activity'].split(':') == 'download failed':
            return

        if self._state == 'canceled' and dict['activity'] == 'shut down':
            return self.dlExited()
        elif self._state == 'canceled':
            return

        if not self.isRunning():
            return

        justpeers = peers = NSLocalizedString("0 peers", "zero peers")
        
        try:
            activity = None
            self.activity = dict['activity']
            if not self.done:
                try:
                    est = dict['timeEst']
                    if est > 0:
                        self.timeEst = utils.formTimeLeft(est)
                    else:
                        self.timeEst = '--'
                    self.remainingfield.setHidden_(False)
                except KeyError:
                    pass
                try:
                    if self.activity != 'downloading':
                        self.timeEst = '--'
                    else:
                        self.statefield.setStringValue_(NSLocalizedString("Downloading", "downloading state"))

                    if self.activity == 'downloading':
                        self.progressbar.setHidden_(False)
                    else:
                        self.progressbar.setHidden_(True)
                        
                except KeyError:
                    pass
                try:
                    self.frac = dict['fractionDone']
                    t = time()
                    if (t - self.lastDisplay) >= 1.0 or self.activity != 'checking existing file':
                        self.lastDisplay = t
                        self.progressbar.setDoubleValue_(self.frac)
                    else:
                        return
                except KeyError:
                    pass
                
                
            try:
                self.downrate = dict['downRate']
            except KeyError:
                pass

            try:
                self.down = dict['downTotal']
            except KeyError:
                pass
            
            try:
                self.uprate = dict['upRate']
            except KeyError:
                pass

            try:
                self.up = dict['upTotal']
            except KeyError:
                pass
            
            try:
                seeds = dict['numSeeds']
            except KeyError:
                seeds = 0

            try:
                self.numPeers = dict['numPeers'] + dict['numSeeds']
                if seeds != 1:
                    peers = NSLocalizedString("%d seeds in %d peers", "num connected seeds and peers info string") % (seeds, self.numPeers)
                else:
                    peers = NSLocalizedString("%d seed in %d peers", "single seed and peers info string") % (seeds, self.numPeers)
                    
                justpeers = NSLocalizedString("%d peers", "num connected peers info string") % self.numPeers
            except KeyError:
                pass

            
            """
            try:
                self.listen_port = dict['listen_port']
            except KeyError:
                pass
            """

            
            size =  NSLocalizedString("%s of %s", "size string") % (utils.formSize(self.metainfo.total_bytes * self.frac), utils.formSize(self.metainfo.total_bytes))

            if self.activity in ['seeding', 'downloading'] and not self.sdel and self.torrent._connection_manager:
                self.startRendezvous()
                
            if self.activity and self.activity == 'checking existing file':
                c =  NSLocalizedString("Checking existing file, %s of %s", "checking existing file") % (utils.formSize(self.metainfo.total_bytes * self.frac), utils.formSize(self.metainfo.total_bytes))
                self.statusfield.setStringValue_(c)
            elif not self.done:
                self.downfield.setStringValue_(utils.formSize(self.down + self.odown))
                self.downratefield.setStringValue_(utils.formRate(self.downrate))
                self.upfield.setStringValue_(utils.formSize(self.up + self.oup))
                self.upratefield.setStringValue_(utils.formRate(self.uprate))
                if self.activity != 'downloading':
                    self.statusfield.setStringValue_("%s - %s" % (self.activity, peers))                    
                else:
                    self.statusfield.setStringValue_("%s - %s" % (size, peers))
            else:
                self.upfield.setStringValue_(utils.formSize(self.up + self.oup))
                self.upratefield.setStringValue_(utils.formRate(self.uprate))
                self.statefield.setStringValue_(NSLocalizedString("Seeding" , "finished status"))
                if self.activity == 'seeding':
                    if defaults.objectForKey_(DOQUEUE) == 0:
                        self.statusfield.setStringValue_(NSLocalizedString("%s - %s", "seeding status") % (utils.formSize(self.metainfo.total_bytes), justpeers))
                        self.remainingfield.setHidden_(True)
                        self.timeEst = ""
                    elif self.isSeed():
                        self.statusfield.setStringValue_(NSLocalizedString("%s - %s", "seeding status") % (utils.formSize(self.metainfo.total_bytes), justpeers))
                        self.timeEst = NSLocalizedString("Nonstop" , "no autostop state")
                        self.remainingfield.setHidden_(True)                        
                    else:
                        self.statusfield.setStringValue_(NSLocalizedString("%s - %s", "seeding status") % (utils.formSize(self.metainfo.total_bytes), justpeers))
                        # figure out how much time left for seeding
                        if not self.seedMeasure:
                            self.seedMeasure = RateMeasure((((self.odown + self.down) * self.STOPRATIO) - (self.up + self.oup)))
                            self.lup = self.up + self.oup

                        self.seedMeasure.data_came_in((self.up + self.oup) - self.lup)
                        self.lup = self.up+self.oup
                        rl = self.seedMeasure.get_time_left()

                        tl = max((self.STOPTIME * 60) - (time() - self.completed), 0)
                        self.lastSeedDisplay = time()

                        x = self.QUEUESTOP
                        if x == 0: # ratio
                            seedTimeLeft = rl
                        elif x == 1: # time
                            seedTimeLeft = tl
                        elif x == 2: # first
                            seedTimeLeft = min(rl, tl)
                        elif x == 3: # last
                            seedTimeLeft = max(rl, tl)
                        if seedTimeLeft:
                            self.timeEst = utils.formTimeLeft(seedTimeLeft)
                        else:
                            self.timeEst = "--"
                        self.remainingfield.setHidden_(False)
            self.timefield.setStringValue_(self.timeEst)

            NSNotificationCenter.defaultCenter().postNotificationName_object_("TorrentDisplayed", self)
        except:
            print_exc()

        return
        
    def isSeed(self):
        if self.QUEUESTOP == 4:
            return True
        else:
            return False

    def isRunning(self):
        if self._state == 'stopped' or self._state == 'failed':
            return False
        if not self.torrent:
            return False
        status = self.torrent.get_status()['activity']
        if status not in ['Initial startup', 'seeding', 'downloading', 'checking existing file']:
            return False
        return True
        
    def isActive(self):
        if not self.isRunning():
            return False
        t = time()
        status = self.torrent.get_status()['activity']
        if status == 'checking existing file':
            return True
        elif status == 'seeding' and self.uprate > 0:
            self.seenpeers = t
        elif status == 'downloading' and self.downrate > 0:
            self.seenpeers = t

        if t - self.starttime > STALL_TIME and t - self.seenpeers > STALL_TIME:
            if not self.stalled:
                self.app.performSelector_withObject_afterDelay_(self.app.statusChanged, None, 0)
            self.stalled = True
            return False
        self.stalled = False
        return True
        
    def checkAutostop(self):
        if not self.isRunning():
            return False
        status = self.torrent.get_status()['activity']
        if status == 'downloading':
            return False
        elif status == 'seeding':
            if self.isSeed():
                # manually started seed
                return False
            if self.odown + self.down == 0:
                ratio = 1
            else:
                ratio = ((self.oup + self.up * 1.0) / (self.odown + self.down) ) >= self.STOPRATIO
            t = ((time() - self.completed) / 60) >= self.STOPTIME
            x = self.QUEUESTOP
            if x == 0:  # ratio
                if ratio:
                    return True
            elif x == 1:  # time
                if t:
                    return True
            elif x == 2:  # first
                if t or ratio:
                    return True
            elif x == 3:  # last
                if t and ratio:
                    return True
        return False

    def checkAutostart(self):
        if self.completed:
            return 0
        elif self.isRunning():
            return 0
        elif self.torrent and self._state == 'failed':
            return 0
        elif not self.savepath:
            return 0
        return 1
    
    def startRendezvous(self):
        if not self.torrent:
            return
        self.sdel = ServiceDelegate.alloc().init(self.torrent._connection_manager.start_connection)
        try:
            if self.torrent._singleport_listener.port and self.torrent._connection_manager.my_id and self.metainfo.infohash:
                self.sdel.publish(self.metainfo.infohash, self.torrent._connection_manager.my_id, self.torrent._singleport_listener.port)
        except:
            print_exc()
        
    ### Feedback protocol
    def error(self, torrent, level, text):
        pool = NSAutoreleasePool.alloc().init()
        self.performSelectorOnMainThread_withObject_waitUntilDone_(self._error, (level, text), 0)
        
    def _error(self, tup):
        level, text = tup
        if level == CRITICAL:
            err = (level, time(), NSLocalizedString("Critical: %s", "critical error") % text)
        elif level == ERROR:
            err = (level, time(), NSLocalizedString("Error: %s", "normal error") % text)
        else:
            err = (level, time(), text)
        self.errors.append(err)
        NSNotificationCenter.defaultCenter().postNotificationName_object_("DLControllerError", (self,) + err)

    def exception(self, torrent, text):
        self.error(torrent, CRITICAL, text)

    def finished(self, torrent):
        self.performSelectorOnMainThread_withObject_waitUntilDone_(self._finished, None, 0)

    def _finished(self):
        self.done = 1
        self.completed = time()
        self.timeEst = NSLocalizedString("Complete", "complete")
        self.progressbar.setDoubleValue_(100.0)
        self.progressbar.setHidden_(True)
        self.downArrow.setHidden_(True)
        self.statusfield.setStringValue_(self.timeEst)
        self.statusfield.setStringValue_("")
        self.downfield.setStringValue_("")
        self.downratefield.setStringValue_("")
        self.downrate = 0.0
        self.seedMeasure = None
        if self.down + self.odown == 0:
            self.QUEUESTOP = 4
        self._error((INFO, NSLocalizedString("Download completed.", "download finished")))
        NSNotificationCenter.defaultCenter().postNotificationName_object_("TorrentStatusChanged", self)
        
    def started(self, torrent):
        self.performSelectorOnMainThread_withObject_waitUntilDone_(self._started, None, 0)

    def _started(self):
        self._error((INFO, NSLocalizedString("Download started.", "download started")))
        #self.startRendezvous()
        
    def failed(self, torrent, what):
        self.performSelectorOnMainThread_withObject_waitUntilDone_(self._failed, None, 0)

    def _failed(self):
        self.done = 1
        self.flag = None
        self._state ='failed'
        self.clearDisplay()
        self.displayStopped()
        
        if self.sdel:
            self.sdel.stop()
            self.sdel = None

        NSNotificationCenter.defaultCenter().postNotificationName_object_("TorrentStatusChanged", self)

    def gotCriticalError(self):
        return self._state == 'failed' or len(self.errors) > 0 and (self.errors[-1][0] == CRITICAL or self.errors[-1][0] == ERROR)
    
    def displayStopped(self):
        self.remainingfield.setHidden_(True)
        self.progressbar.setHidden_(True)
        if self.gotCriticalError():
            self.statusfield.setStringValue_(NSLocalizedString("See log for error detail.", "error status"))
            self.statefield.setStringValue_(NSLocalizedString("Error", "error stopped status"))
            self.timefield.setStringValue_("")
        elif defaults.objectForKey_(DOQUEUE) and self.checkAutostart():
            self.statefield.setStringValue_(NSLocalizedString("Waiting", "queued status"))
            self.statusfield.setStringValue_(utils.formSize(self.metainfo.total_bytes))
            self.timefield.setStringValue_("")
        elif defaults.objectForKey_(DOQUEUE):
            self.statefield.setStringValue_(NSLocalizedString("Complete", "complete"))
            self.statusfield.setStringValue_(utils.formSize(self.metainfo.total_bytes))
            self.timefield.setStringValue_("")
        else:
            if self.completed:
                self.statefield.setStringValue_(NSLocalizedString("Complete", "complete"))
            else:
                self.statefield.setStringValue_(NSLocalizedString("Stopped", "stopped"))
            self.statusfield.setStringValue_(utils.formSize(self.metainfo.total_bytes))
            self.timefield.setStringValue_("")

    def dlExited(self, dummy=None):
        self.done = 1
        self.flag = None
        self._state ='stopped'
        self.clearDisplay()
        self.displayStopped()
        
        if self.sdel:
            self.sdel.stop()
            self.sdel = None

        NSNotificationCenter.defaultCenter().postNotificationName_object_("TorrentStatusChanged", self)

    def doChoose(self, ask=0):
        if ask or int(defaults.objectForKey_(DIRASK)) == 1:
            self.choose()
            return
        elif int(defaults.objectForKey_(DIRASK)) == 2:
            self.savepath = defaults.objectForKey_(DLDIR)
        else:
            self.savepath = self.app.ic.downloadDir()
        self.savepath = os.path.join(self.savepath, unicode(self.metainfo.name_fs, 'utf8'))
        self.displayStopped()
        NSNotificationCenter.defaultCenter().postNotificationName_object_("DoneChoosingTorrent", self)

    def startDLThread(self):
        if not self.metainfo:
            return
        self.done = 0
        self._state = 'launching'
        self.starttime = time()
        self.timefield.setStringValue_('--')
        self.statefield.setStringValue_(NSLocalizedString("Launching", "task launching status"))
        NSNotificationCenter.defaultCenter().postNotificationName_object_("TorrentStatusChanged", self)
        self.upArrow.setHidden_(False)
        self.downArrow.setHidden_(False)
        app = self.app

        app.reloadConfig()
        config = BTPreferences(app.config)
        config['max_uploads'] = self.max_uploads
        #config['min_uploads'] = self.min_uploads
        config['max_initiate'] = self.max_initiate
        config['max_allow_in'] = self.max_allow_in
        config['max_upload_rate'] = self.max_upload_rate
        self.config = config
        app.rawserver.external_add_task(0, self._startDLThread)
        
    def _startDLThread(self):
        if not self.app.mt.torrents.has_key(self.metainfo.infohash):
            self.app.mt.create_torrent(self.metainfo, self.savepath.encode('utf8'),self.savepath.encode('utf8'))
        self.app.mt.start_torrent(self.metainfo.infohash)
        self.torrent = self.app.mt.torrents[self.metainfo.infohash]
        self.app.mt.set_option('max_upload_rate', self.max_upload_rate * 1024, self.metainfo.infohash)
        
        ## make sure the event loop wakes up
        def f():
            pass
        self.app.mt.rawserver.add_task(0, f)

        if not self.torrent:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(self.dlExited(), None, 0)
        
        else:
            self._state = 'running'
            NSNotificationCenter.defaultCenter().postNotificationName_object_("TorrentLaunched", self)
            NSNotificationCenter.defaultCenter().postNotificationName_object_("TorrentStatusChanged", self)
        
    def closeTorrent_(self, sender):
        self.app.performSelector_withObject_afterDelay_('removeTorrent', self, 0)
        return self
        
    def cycleTorrent_(self, sender):
        # start torrent if stopped
        # stop torrent if started
        if self.isRunning():
            self.cancelDL(self)
            # make sure log and such get updated to reflect our new status
            NSNotificationCenter.defaultCenter().postNotificationName_object_("TorrentSelectionChanged", None)
            
        else:
            if self.savepath:
                self.startDLThread()            
            else:
                self.startDL()
        return self
            
    def revealTorrent_(self, sender):
        # show torrent in finder
        x = self.savepath
        if self.metainfo.is_batch:
            os.path.join(x, unicode(self.metainfo.name_fs, 'utf8'))
        NSWorkspace.sharedWorkspace().selectFile_inFileViewerRootedAtPath_(x, "")
        return self
            
    def inspectTorrent_(self, sender):
        if self.torrent_path:
            TorrentInspector.alloc().initWithTorrentPath_(self.torrent_path).retain()
        else:
            TorrentInspector.alloc().initWithTorrentData_(self.torrent_data).retain()            

    def autostartTorrent(self, sender):
        self.startDLThread()

    def setStopRatio(self, newRatio):
        if newRatio != self.STOPRATIO:
            self.STOPRATIO = newRatio
            self.resetSeedMeasure()
            
    def resetSeedMeasure(self):
        self.seedMeasure = RateMeasure((((self.odown + self.down) * self.STOPRATIO) - (self.up + self.oup)))

    def inColumnReorder(self):
        self.ICR = True
        map(lambda a: a.retain().removeFromSuperviewWithoutNeedingDisplay(),
            [self.getFileView(), self.getTimeView(), self.getXFerView()])

    def notInColumnReorder(self):
        self.ICR = False
        
    def isInColumnReorder(self):
        return self.ICR

    def getUpDownSinceLast(self):
        u, d = self.up - self.gup, self.down - self.gdown
        self.gup = self.up
        self.gdown = self.down
        return u, d
