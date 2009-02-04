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


from Foundation import *
from AppKit import *
from PyObjCTools import NibClassBuilder
from objc import *
from random import randint
import os, sys
from time import sleep, time

# don't use twisted on Panther
if int(os.uname()[2][0]) >= 8:
    from twisted.internet import kqreactor
    kqreactor.install()
    


from PortChanger import PortChanger

from DLController import MalformedTorrentFile, DLController
import LameProgressBar

import utils

from BitTorrent.MultiTorrent import MultiTorrent
from BitTorrent.RawServer_twisted import RawServer
from BitTorrent.prefs import Preferences as BTPreferences
from BitTorrent.defaultargs import common_options, rare_options
from BitTorrent import BTFailure, INFO, WARNING, ERROR, CRITICAL
from BitTorrent.bencode import bencode, bdecode

from BitTorrent import NewVersion

from threading import Event
import thread
from hotshot import Profile

from PyInterpreter import PyInterpreter


PREFDIR = os.path.expanduser("~/Library/Application Support/BitTorrent")
RESDIR = os.path.join(PREFDIR, "resume")
STORED_TORRENTS = os.path.join(PREFDIR, "OpenTorrents")

import DLCell
from DLCell import *
TimeCell = lookUpClass("TimeCell")
FileCell = lookUpClass("FileCell")
XFerCell = lookUpClass("XFerCell")
ICHelper = lookUpClass("ICHelper")

class NoTorrentSelected(Exception):
    pass

class TorrentAlreadyOpened(Exception):
    pass
    
from Preferences import *
from Generate import *
from SpewController import *
from TorrentInspector import TorrentInspector

import BitTorrent
 
NibClassBuilder.extractClasses("MainMenu")
NibClassBuilder.extractClasses("TorrentWindow")
NibClassBuilder.extractClasses("DetailView")

URL=NSLocalizedString("http://www.bittorrent.com/donate_mac.html", "donate url")

gray = NSColor.colorWithCalibratedHue_saturation_brightness_alpha_(0, 0, .94, 1)

class TorrentTableView (NibClassBuilder.AutoBaseClass):
    ICR = False  # in column reorder
    IRR = False  # in row reorder
    def dragImageForRows_event_dragImageOffset_(self, rows, event, offset):
        c = self.backgroundColor()
        self.setBackgroundColor_(NSColor.colorWithDeviceWhite_alpha_(.66, .66))
        self.IRR = True
        d = self.dataWithPDFInsideRect_(self.rectOfRow_(rows[0]))
        self.IRR = False
        self.setBackgroundColor_(c)
        i =  NSImage.alloc().initWithData_(d)
        return i

    def draggingSourceOperationMaskForLocal_(self, isLocal):
        if isLocal:
            return NSDragOperationMove
        else:
            return NSDragOperationCopy

    def drawRow_clipRect_(self, row, rect):
        global colors
        app = NSApp().delegate()
        try:
            c = app.torrents[row]
        except IndexError:
            pass
        else:
            try:
                sc = app.selectedController()
            except:
                sc = None
            if not self.IRR:
                if c != sc:
                    fill = False
                    if not c.isRunning():
                        if c.gotCriticalError():
                            colors[ERRORCOLOR].setFill()
                            fill = True
                        elif c.completed:
                            colors[COMPLETECOLOR].setFill()
                            fill = True                        
                    else:
                        if c.isSeed():
                            colors[SEEDINGCOLOR].setFill()
                            fill = True                        
                        elif not c.isActive():
                            colors[STALLEDCOLOR].setFill()
                            fill = True                        
                        elif c.done:
                            colors[SEEDINGCOLOR].setFill()
                            fill = True
                    rrect = self.rectOfRow_(row)
                    if fill and self.needsToDrawRect_(rrect):
                        NSRectFill(rrect)
                super(TorrentTableView, self).drawRow_clipRect_(row, rect)

        
class BTAppController (NibClassBuilder.AutoBaseClass):
    def init(self):
        self = super(BTAppController, self).init()
        self.prefs = Preferences.alloc().init()
        self.prefwindow = None
        self.generator = Generate.alloc().init()
        
        self.ic =ICHelper.alloc().init()
        
        # displayed torrent controllers
        self.torrents = []
        
        # waiting to die
        self.dead_torrents = []
        
        # ready to start
        # (<open panel>, <insert row>, (<filename>|<stream>, <is_stream>))  -1 insert row means use last row
        # stream = 0 if filename, 1 if bencoded torrent file
        self.tqueue = [] 
                
        self.retain()
        self.inited = 0
        self.launched = 0
        self.in_choose = 0
        self.last_qcheck = time()
        
        self.sc = 0
        self.defaults = NSUserDefaults.standardUserDefaults()

        self.tup = bdecode(self.defaults.objectForKey_(ULBYTES))
        self.tdown = bdecode(self.defaults.objectForKey_(DLBYTES))
        
        self.config = common_options + rare_options
        self.config = BTPreferences().initWithDict(dict([(name, value) for (name, value, doc) in self.config]))

        self.config['data_dir'] = PREFDIR
                
        self.config['bind'] = ''
        self.config['bad_libc_workaround'] = True
        self.config['filesystem_encoding'] = 'utf8'
        #XXXX
        #self.config['start_trackerless_client'] = False

        self.legacyConfig()
        self.reloadConfig()
        
        self.pyi = None
        
        self.doneflag = Event()

        if not os.path.exists(PREFDIR):
            os.mkdir(PREFDIR)
        if not os.path.exists(RESDIR):
            os.mkdir(RESDIR)


        self.ticon = None

        self.stalled = []
        self.terminated = False
        
        return self

    def loadConsole_(self, sender):
        if not self.pyi:
            self.pyi = PyInterpreter.alloc().init()
            NSBundle.loadNibNamed_owner_("PyInterpreter", self.pyi)
        else:
            self.pyi.textView.window().makeKeyAndOrderFront_(self)

    def legacyConfig(self):
        n = self.defaults.integerForKey_(QUEUESTOP)
        if n > 1:
            self.defaults.setObject_forKey_(0, QUEUESTOP)
        
    def reloadConfig(self):
        self.config['minport'] = self.defaults.integerForKey_(MINPORT)
        self.config['maxport'] = self.defaults.integerForKey_(MINPORT)
        self.config['max_upload_rate'] = self.defaults.integerForKey_(MAXULRATE)
        self.config['max_allow_in'] = self.defaults.integerForKey_(MAXACCEPT)
        self.config['max_initiate'] = self.defaults.integerForKey_(MAXINITIATE)
        self.config['max_uploads'] = self.defaults.integerForKey_(MAXULS)

    def listen_forever(self):
        pool = NSAutoreleasePool.alloc().init()
        # XXX
        #self.profile = Profile("BT.prof");self.profile.start()
        self.rawserver = RawServer(self.config)
        self.mt = MultiTorrent(self.config, self.doneflag, self.rawserver, self.multi_errorfunc, self.config['data_dir'])
        self.rawserver.ident = thread.get_ident()
        self.mt.set_option("max_upload_rate", self.config['max_upload_rate'] * 1024)
        self.rawserver.listen_forever(self.doneflag)
        #self.profile.stop();self.profile.close()

    def multi_errorfunc(self, level, text ):
        if level == CRITICAL:
            self.statusField.setStringValue_(NSLocalizedString("Critical Error: %s", "critical error") % text)
            # bomb out
        elif level == ERROR:
            self.statusField.setStringValue_(NSLocalizedString("Error: %s", "normal error") % text)
        elif level == WARNING:
            print ">>>", NSLocalizedString("Warning: %s", "warning error") % text
        elif level == INFO:
            print ">>>", NSLocalizedString("Info: %s", "info error") % text
    
    def awakeFromNib(self):
        if not self.inited:
            self.inited = 1
            NSBundle.loadNibNamed_owner_("TorrentWindow", self)
            self.drawerMenu.setTarget_(self.logDrawer)
            self.drawerMenu.setAction_(self.logDrawer.toggle_)
            self.logDrawer.delegate().menu = self.drawerMenu
            self.torrentTable.registerForDraggedTypes_([NSFilenamesPboardType])

    def openPage_(self, sender):
        NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(URL))

    def openHomePage_(self, sender):
        NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_("http://www.bittorrent.com/"))

    def nag(self):
        nag = self.defaults.objectForKey_(NAG)
        if nag == 0 or (nag != BitTorrent.version and randint(0,2) == 0):
            if nag == 0:
                self.defaults.setObject_forKey_(1, NAG)
            NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(URL))
            x = NSRunAlertPanel(NSLocalizedString("Please Donate", "nag window title"), 
                                NSLocalizedString("If you like BitTorrent and want to see more cool apps from the author, you should make a donation.", "nag message"), 
                                NSLocalizedString("Later", "nag later"), NSLocalizedString("Already Donated", "nag already"), None)
            if x == NSAlertAlternateReturn:
                self.defaults.setObject_forKey_(BitTorrent.version, NAG)
                NSRunInformationalAlertPanel(NSLocalizedString("Thank You", "Thank You"), NSLocalizedString("Thank you for making a donation.  You will not be bothered with donation requests until you upgrade.", "thanks for donating"),
                                             NSLocalizedString("OK", "OK"), None, None)

    def applicationDidFinishLaunching_(self, aNotification):
        try:
            NSThread.detachNewThreadSelector_toTarget_withObject_(self.listen_forever, self, None)
        except BTFailure, e:
            err = str(e)
            if err.startswith("Could not open a listening port"):
                p = PortChanger.alloc().initWithErr(err)
            else:
                x = NSRunAlertPanel(NSLocalizedString("Fatal Error", "fatal error"), 
                                    NSLocalizedString("Failed to initialize BitTorrent core.  Error: %s", "bittorrent failure message") % str(e), 
                                None, None, None)
                NSApp().terminate_(self)

        self.launched = 1

        #self.profile = Profile("BT.prof")
        #self.profile.start()

        tcell = PyTimeCell.alloc().init()
        fcell = PyFileCell.alloc().init()
        xcell = PyXFerCell.alloc().init()

        cols = self.torrentTable.tableColumns()
        for c in cols:
            #c.setHeaderCell_(TorrentTableHeaderCell.alloc().initTextCell_(c.headerCell().stringValue()))
            if c.identifier() == 'time':
                c.setDataCell_(tcell)
            elif c.identifier() == 'file':
                c.setDataCell_(fcell)
            elif c.identifier() == 'xfer':
                c.setDataCell_(xcell)


        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, self._otorrent, "DoneChoosingTorrent", None)        
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, self.saveTorrents, "NSWorkspaceWillPowerOffNotification", None)
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, self.moveTorrent, "NSTableViewColumnDidMoveNotification", None)
        
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(1.5, self, self.updateStatus, None, 1)
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(10, self, self.checkQueue, None, 1) 
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(300, self, self.saveTorrents, None, 1)
        
        self.loadTorrents()
        
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, self.reapDead, "TorrentStatusChanged", None)
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, self.statusChanged, "TorrentStatusChanged", None)
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, self.updateCycleMenu, "TorrentStatusChanged", None)
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, self.updateCycleMenu, "TorrentSelectionChanged", None)

        if defaults.objectForKey_(VERSIONCHECK):
            self.checkVersion()

        # open any torrents waiting
        self.otorrent(None)



    ## version check stuff
    def checkVersion(self):
        test_new_version = ''
        test_current_version = ''
        if self.config.has_key('new_version'):
            test_new_version = self.config['new_version']
        if self.config.has_key('current_version'):
            test_current_version = self.config['current_version']

        try:
            self.statusField.setStringValue_("")
            self.vc = NewVersion.Updater(self.vcThreadWrap,
                                         self.alertNewVersion,
                                         lambda a: a,
                                         lambda a: a,
                                         self.versionCheckFailed, test_new_version=test_new_version, test_current_version=test_current_version)
            self.vc.check()
        except:
            import traceback
            traceback.print_exc()
        
    def vcThreadWrap(self, *args):
        self.performSelectorOnMainThread_withObject_waitUntilDone_(self._call, (args[0], args[1:]), 0)

    def _call(self, x):
        try:
            x[0](*x[1])
        except:
            import traceback
            print_exc()
        
    def versionCheckFailed(self, level, error):
        self.statusField.setStringValue_(str(error))
    
    def alertNewVersion(self, vers, url):
        if not self.vc.infohash:
            # new version available but for some reason we didn't get a valid torrent file
            return
        res = NSRunAlertPanel(NSLocalizedString("New Version Available", ''),
                              NSLocalizedString("Version %s is now available.  Would you like to download it now?", '') % vers,
                              NSLocalizedString("OK", ''),
                              NSLocalizedString("Cancel", ''),
                              NSLocalizedString("No Startup Check",''))
        if res == -1:
            self.defaults.setObject_forKey_(0, VERSIONCHECK)
        elif res == 1:
            ## download it
            try:
                self.tqueue.insert(0, (0, -1, (self.vc.torrentfile, 1)))
                if not self.in_choose:
                    self.otorrent(None)
            except:
                import traceback
                print_exc()
            
    def gotVersion(self, vers):
        old = [int(x) for x in BitTorrent.version.split('.')]
        if old[1] % 2 and len(vers.split(None, 2)) > 1:
            new = [int(x) for x in vers.split(None, 2)[1].split('.')]            
        else:
            new = [int(x) for x in vers.split(None, 2)[0].split('.')]

        for my, n in zip(old, new):
            if my < n:
                self.alertNewVersion(".".join([str(x) for x in new]))
            elif my > n:
                break
        self.vc = None
        


    def showDetail_(self, sender):
        if not self.sc:
            self.sc = SpewController.alloc().init()
            self.sc.delegate = self
            NSBundle.loadNibNamed_owner_("DetailView", self.sc)
        self.sc.showWindow()

    def toggleDetail_(self, sender):
        if not self.sc:
            return self.showDetail_(sender)
        self.sc.toggleWindow()
        
    def updateStatus(self, timer):
        up = down = 0.0
        for c in self.torrents:
            c.display()
            up += c.uprate
            down += c.downrate
            a, b = c.getUpDownSinceLast()
            self.tup += a
            self.tdown += b

        try:
            up += self.mt.dht.udp.rltransport.measure.get_rate()
        except AttributeError:
            pass
        
        self.upRateField.setStringValue_(utils.formRate(up))
        self.downRateField.setStringValue_(utils.formRate(down))
        self.defaults.setObject_forKey_(bencode(self.tup), ULBYTES)
        self.defaults.setObject_forKey_(bencode(self.tdown), DLBYTES)
        
        if self.terminated:
            if len(filter(lambda a: a.isRunning(), self.torrents)) == 0:
                self.defaults.synchronize()
                NSApp().terminate_(self)
                
    def checkQueue(self, start=0):
        redisp = False
        if not self.defaults.objectForKey_(DOQUEUE):
            return
        stopped = running = active = 0
        stopl = []
        for c in self.torrents:
            if c.isRunning():
                running += 1
                n = c.checkAutostop()
                if c.isActive() and c in self.stalled:
                    self.stalled.remove(c)
                    c.resetSeedMeasure()
                    redisp = True
                if n:
                    c.cancelDL(self)
                    stopl.append(c)
                    if c in self.stalled:
                        self.stalled.remove(c)
                        redisp = True
                    stopped += 1
                elif not c.isSeed() and c.isActive():
                    active += 1
                elif not c.isActive() and not c.isSeed() and c not in self.stalled:
                    stopped += 1
                    self.stalled.append(c)
                    redisp = True

        if redisp:
            self.torrentTable.reloadData()
                    
        if running > 1 and running == len(self.stalled):
            #all running torrents are stalled, don't start any more
            return

        if stopped or (start == 1 and (len(self.torrents) == 1 or not running)):
            canstart = 0
            if start == 1:
                canstart = 1
            elif self.defaults.objectForKey_(QUEUESTART) == 1:
                canstart = stopped
            elif active == 0:
                canstart = 1
            for c in self.torrents:
                if canstart and c not in stopl and c.checkAutostart():
                    c.autostartTorrent(self)
                    canstart -=1
                if canstart == 0:
                    break

    ## used by log and spew
    def selectedController(self):
        i = self.torrentTable.selectedRow()
        if i == -1:
            raise NoTorrentSelected
        elif len(self.torrents) <= i:
            raise NoTorrentSelected
        return self.torrents[i]
    
    ### tv datasource methods
    def numberOfRowsInTableView_(self, tv):
        return len(self.torrents)
    
    def tableView_objectValueForTableColumn_row_(self, tv, col, row):
        return self.torrents[row]
                
    ## tv delegate methods
    def tableView_mouseDownInHeaderOfTableColumn_(self, tv, col):
        self.torrentTable.ICR = True
        self.performSelector_withObject_afterDelay_(self.reorderEnded, None, 0)
        def f(a):
            if tv.isEqual_(a.superview()):
                a.removeFromSuperviewWithoutNeedingDisplay()
        for c in self.torrents:
            map(f,[c.getFileView(), c.getTimeView(), c.getXFerView()])
            c.backToPanel()
            
    def reorderEnded(self):
        self.torrentTable.ICR = False
        self.torrentTable.reloadData()
 
    def tableView_didClickTableColumn_(self, tv, col):
        self.reorderEnded()
    def tableView_didDragTableColumn_(self, tv, col):
        self.reorderEnded()
        
    def tableViewSelectionDidChange_(self, note):
        try:
            c = self.selectedController()
        except NoTorrentSelected:
            c = None

        NSNotificationCenter.defaultCenter().postNotificationName_object_("TorrentSelectionChanged", c)
        
    def moveTorrent(self, note):
        dict = note.object()
        
        
    ## responder
    def clear_(self, sender):
        try:
            c = self.selectedController()
            self.removeTorrent(c)
        except NoTorrentSelected:
            return None
        else:
            return self

    def clearAll_(self, sender):
        for c in self.torrents[:]:
            if (not c.isRunning()) and c.completed > 0:
                self.removeTorrent(c)
    
    def close_(self, sender):
        return self.clear(sender)
        
    def removeTorrent(self, c):
        if c.torrent and c.isRunning():
            self.dead_torrents.append(c)
            c.cancelDL(self)
        else:
            self.cleanupTorrent(c)

    def cleanupTorrent(self, c):
        c.backToPanel()
        c.silent = 1
        NSNotificationCenter.defaultCenter().removeObserver_( c)        
        self.torrents.remove(c)
        try:
            c = self.selectedController()
        except NoTorrentSelected:
            c = None
        self.torrentTable.reloadData()
        if not self.terminated:
            self._saveTorrents()
        NSNotificationCenter.defaultCenter().postNotificationName_object_("TorrentSelectionChanged", c)
    
    ## bt
    def loadDLWindow(self, file, ins=-1):
        controller = DLController.alloc()
        controller.window = self.torrentTable.window()
        try:
            controller.initWithTorrentFile_(file)
        except BTFailure, e:
            #XXX
            x = NSRunAlertPanel(NSLocalizedString("Fatal Error", "fatal error"), 
                                NSLocalizedString("Error: %s", "normal error") % str(e), 
                                None, None, None)
        except MalformedTorrentFile, e:
            x = NSRunAlertPanel(NSLocalizedString("Fatal Error", "fatal error"), 
                                NSLocalizedString("Error: %s", "normal error") % str(e), 
                                None, None, None)
        return self._postLoadDLWindow(controller, ins)

    def loadDLWindowData(self, data, ins=-1):
        controller = DLController.alloc()
        controller.window = self.torrentTable.window()
        try:
            controller.initWithTorrentData_(data)
        except BTFailure, e:
            #XXX
            x = NSRunAlertPanel(NSLocalizedString("Fatal Error", "fatal error"), 
                                NSLocalizedString("Error: %s", "normal error") % str(e), 
                                None, None, None)
        except MalformedTorrentFile, e:
            x = NSRunAlertPanel(NSLocalizedString("Fatal Error", "fatal error"), 
                                NSLocalizedString("Error: %s", "normal error") % str(e), 
                                None, None, None)
        return self._postLoadDLWindow(controller, ins)
        
    def _postLoadDLWindow(self, controller, ins=-1): 
        for c in self.torrents:
            if c.metainfo and c.metainfo.infohash == controller.metainfo.infohash:
                raise TorrentAlreadyOpened, c

        if ins == -1:
            ins = len(self.torrents)
            
        self.torrents.insert(ins, controller)
        self.torrentTable.noteNumberOfRowsChanged()
        def sort_controllers(a, b):
            if a.file.upper() > b.file.upper():
                return 1
            elif a.file.upper() < b.file.upper():
                return -1
            return 0
        #self.torrents.sort(sort_controllers)
        self.torrentTable.reloadData()

        try:
            c = self.selectedController()
        except NoTorrentSelected:
            c = None
        self.torrentTable.scrollRowToVisible_(self.torrentTable.selectedRow())
        self.torrentTable.display()
        NSNotificationCenter.defaultCenter().postNotificationName_object_("TorrentSelectionChanged", c)
        #self.torrentTable.selectRow_byExtendingSelection_(len(self.torrents) - 1, 0)
        return controller
        
    ## url window stuff
    def cancelUrl_(self, sender):
        self.urlWindow.orderOut_(self)
        
    def openURL_(self, sender):
        self.urlWindow.makeKeyAndOrderFront_(self)
        
    def takeUrl_(self, sender):
        self.urlWindow.orderOut_(self)
        try:
            controller = self.loadDLWindow()
        except:
            pass
        else:
            self.runWithStr__controller_("--url", self.url.stringValue(), controller)

    ## torrent file handlers
    def openTrackerResponse_(self, sender):
        panel = NSOpenPanel.openPanel()
        
        panel.beginSheetForDirectory_file_types_modalForWindow_modalDelegate_didEndSelector_contextInfo_(None, None, ['torrent'],
                                                                                 self.torrentTable.window(), self,
                                                                                                    self.openPanelDidEnd_returnCode_contextInfo_,
                                                                                                    0)
    def openPanelDidEnd_returnCode_contextInfo_(self, sheet, returnCode, contextInfo):
        if returnCode == NSOKButton:
            self.tqueue.insert(0, (1, -1, (sheet.filename(), 0)))
            self.performSelectorOnMainThread_withObject_waitUntilDone_(self.otorrent, None, 0)
    openPanelDidEnd_returnCode_contextInfo_ = selector(openPanelDidEnd_returnCode_contextInfo_, signature="v@:@ii")

    ## open a torrent from the queue
    def otorrent(self, notification):
        self.in_choose = 0
        try:
            choose, row, f = self.tqueue.pop()
            f, stream = f
        except IndexError:
            self.checkQueue(start=1)
        else:
            try:
                if not stream:
                    c = self.loadDLWindow(f, row)
                else:
                    c = self.loadDLWindowData(f, row)
            except TorrentAlreadyOpened, e:
                self.torrentTable.selectRow_byExtendingSelection_(self.torrents.index(e.args[0]), 0)
            except MalformedTorrentFile:
                pass
            else:
                self.in_choose = 1
                c.doChoose(choose)
                
            
    def _otorrent(self, note):
        self.performSelectorOnMainThread_withObject_waitUntilDone_(self.otorrent, note, 0)


    def inspectFile_(self, sender):
        panel = NSOpenPanel.openPanel()
        if (panel.runModalForDirectory_file_types_(None, None, ['torrent']) == NSOKButton):
            f = panel.filename()
            if f:
                TorrentInspector.alloc().initWithTorrentPath_(f).retain()
        
    def observeValueForKeyPath_ofObject_change_context_(self, keyPath, object, change, context):
        if keyPath == "defaults.max_upload_rate":
            self.rawserver.external_add_task(0, self.mt.set_option, 'max_upload_rate', self.defaults.integerForKey_(MAXULRATE) * 1024)
            
        
    ## open prefs and gen windows
    def openPrefs_(self, sender):
        if not self.prefwindow:
            NSBundle.loadNibNamed_owner_("Preferences", self.prefs)
            self.prefwindow = self.prefs.window()
        self.prefs.showWindow_(self)
        
    def openGenerator_(self, sender):
        self.generator.open()
        
    ## where the action is
    def runWithStr__controller_(self, method, str, controller):
        self.in_choose = 1
        controller.startDL()
        
    def openAbout_(self, sender):
        self.versField.setStringValue_(BitTorrent.version)
        self.upField.setStringValue_(utils.formSize(bdecode(self.defaults.objectForKey_(ULBYTES))))
        self.downField.setStringValue_(utils.formSize(bdecode(self.defaults.objectForKey_(DLBYTES))))
        self.aboutWindow.makeKeyAndOrderFront_(self)
        
    def application_openFile_(self, app, filename):
        self.tqueue.insert(0, (0, -1, (filename, 0)))
        if self.launched and not self.in_choose:
            self.otorrent(None)
        return 1
    
    ## what a drag
    def tableView_writeRows_toPasteboard_(self, tableView, rows, pasteBoard):
        pasteBoard.declareTypes_owner_([NSFilenamesPboardType], self)
        pasteBoard.setPropertyList_forType_([self.torrents[rows[0]].torrent_path], NSFilenamesPboardType)
        return 1

    def tableView_validateDrop_proposedRow_proposedDropOperation_(self, tableView, info, row, dropOperation):
        if dropOperation != NSTableViewDropOn:
            return NSDragOperationMove
        return NSDragOperationNone
    
    def tableView_acceptDrop_row_dropOperation_(self, tableView, info, row, dropOperation):
        pboard = info.draggingPasteboard()
        files = pboard.propertyListForType_(NSFilenamesPboardType)

        t = filter(lambda a: a.torrent_path == files[0], self.torrents)
        if len(files) == 1 and t:
            i = self.torrents.index(t[0])
            if i > row:
                t = self.torrents.pop(i)
                self.torrents.insert(row, t)
            elif i != row:
                t = self.torrents.pop(i)
                self.torrents.insert(row - 1, t)
        else:  # dragged in files
            for filename in files:
                self.tqueue.insert(0, (0, row, (filename, 0)))
            if self.launched and not self.in_choose:
                self.otorrent(None)

        tableView.setNeedsDisplay_(True)
        tableView.reloadData() 
        return 1

    ## persistance
    def saveTorrents(self, timer):
        self._saveTorrents()

    def _saveTorrents(self):
        NSKeyedArchiver.archiveRootObject_toFile_(self.torrents, STORED_TORRENTS)
    
    def reapDead(self, note):
        if self.sc:
            self.sc.display(note)
        if note.object() in self.dead_torrents:
            self.dead_torrents.remove(note.object())
            self.cleanupTorrent(note.object())
        self.performSelector_withObject_afterDelay_(self.checkQueue, None, 0)
        
    def loadTorrents(self):
        t = NSKeyedUnarchiver.unarchiveObjectWithFile_(STORED_TORRENTS)
        if t != None:
            self.torrents = list(t)
            self.torrentTable.reloadData()
        self.torrentTable.sizeToFit()
        
    def terminate_(self, sender):
        #self.profile.stop()
        NSNotificationCenter.defaultCenter().removeObserver_name_object_(self, "NSWorkspaceWillPowerOffNotification", None)
        self._saveTorrents()
        try:
            self.mt.dht.checkpoint()
        except AttributeError:
            # no trackerless
            pass
        done = 0
        for c in self.torrents:
            c.cancelDL(self)
        self.terminated = True

        self.mt.rawserver.external_add_task(0, self.doneflag.set)

        #self.profile.close()

    

    def validateMenuItem_(self, item):
        stopped = True
        try:
            c = self.selectedController()
        except NoTorrentSelected:
            c = None
        else:
            if c.isRunning():
                stopped = False
        
        if not c and item.tag() in [201, 202, 203, 204]:

            return False
        
        if item.tag() == 201:
            #201 = clear
            return stopped
        elif item.tag() == 202:
            #202 = start
            if stopped:
                item.setTitle_(NSLocalizedString("Start","start"))
            else:
                item.setTitle_(NSLocalizedString("Stop","stop"))
            self.updateCycleMenu(self)

        #203 = reveal
        #204 = inspect

        elif item.tag() == 301:
            if self.sc and self.sc.table.window().isVisible():
                item.setState_(NSOnState)
            else:
                item.setState_(NSOffState)
        return True


    def updateCycleMenu(self, note):
        try:
            c = self.selectedController()
        except NoTorrentSelected:
            pass
        else:
            if not c.isRunning():
                self.cycleMenu.setKeyEquivalent_('r')
            else:
                self.cycleMenu.setKeyEquivalent_('.')
            self.cycleMenu.setKeyEquivalentModifierMask_(NSCommandKeyMask)
            
    def closeTorrent_(self, sender):
        try:
            c = self.selectedController()
        except NoTorrentSelected:
            return 0
        else:
            c.closeTorrent_(sender)

    def cycleTorrent_(self, sender):
        try:
            c = self.selectedController()
        except NoTorrentSelected:
            return 0
        else:
            c.cycleTorrent_(sender)

    def inspectTorrent_(self, sender):
        try:
            c = self.selectedController()
        except NoTorrentSelected:
            return 0
        else:
            c.inspectTorrent_(sender)

    def revealTorrent_(self, sender):
        try:
            c = self.selectedController()
        except NoTorrentSelected:
            return 0
        else:
            c.revealTorrent_(sender)

    def updateStopped(self):
        for t in self.torrents:
            if not t.isRunning():
                t.displayStopped()
        
    def statusChanged(self, note):
        self.torrentTable.reloadData()
