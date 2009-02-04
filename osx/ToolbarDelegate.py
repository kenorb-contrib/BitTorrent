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

## Copyright 2004, Andrew Loewenstern.  All Rights Reserved

from Foundation import *
from AppKit import *

from PyObjCTools import NibClassBuilder

NibClassBuilder.extractClasses("TorrentWindow")

from BTAppController import NoTorrentSelected
from Preferences import *

DEFAULT_RATE = 0
DEFAULT_SLOTS = 0
MIN_SLOTS = 1

class MyItem(NSToolbarItem):
    def validate(self):
        self.setEnabled_(self.target().enabled())
    
class QueueItem(NSToolbarItem):
    def validate(self):
        if defaults.integerForKey_(DOQUEUE) == 1:
            self.setEnabled_(True)
        else:
            self.setEnabled_(False)

class PopItem(NSToolbarItem):
    def validate(self):
        if defaults.integerForKey_(DOQUEUE) == 1 and self.target().enabled():
            self.setEnabled_(True)
        else:
            self.setEnabled_(False)

class MaxUploadsItem(MyItem):
    pass
class MinUploadsItem(MyItem):
    pass
class MaxAcceptItem(MyItem):
    pass
class MaxInitiateItem(MyItem):
    pass
class MaxUploadRateItem(MyItem):
    pass

class StopPopItem(PopItem):
    pass
class RatioItem(QueueItem):
    pass
class TimeItem(QueueItem):
    pass

class TransportItem(NSToolbarItem):
    def validate(self):
        try:
            c = NSApp().delegate().selectedController()
        except NoTorrentSelected:
            self.setEnabled_(False)
        else:
            self.setEnabled_(True)

class EnabledItem(NSToolbarItem):
    def validate(self):
        self.setEnabled_(True)
        
class CloseItem(TransportItem):
    def validate(self):
        try:
            c = NSApp().delegate().selectedController()
        except NoTorrentSelected:
            self.setEnabled_(False)
        else:
            if c.isRunning():
                self.setEnabled_(False)
            else:
                self.setEnabled_(True)

class StopItem(TransportItem):
    def validate(self):
        try:
            c = NSApp().delegate().selectedController()
        except NoTorrentSelected:
            self.setEnabled_(False)
        else:
            if c.isRunning():
                self.setEnabled_(True)
            else:
                self.setEnabled_(False)

class StartItem(TransportItem):
    def validate(self):
        try:
            c = NSApp().delegate().selectedController()
        except NoTorrentSelected:
            self.setEnabled_(False)
        else:
            if c.isRunning():
                self.setEnabled_(False)
            else:
                self.setEnabled_(True)

class StopTimeItem(NSToolbarItem):
    def validate(self):
        try:
            c = NSApp().delegate().selectedController()
        except NoTorrentSelected:
            self.setEnabled_(False)
        else:
            if defaults.integerForKey_(DOQUEUE) == 1:
                if c.QUEUESTOP == 4:
                    self.setEnabled_(False)
                else:
                    self.setEnabled_(True)
            else:
                self.setEnabled_(False)
    
defaults = NSUserDefaults.standardUserDefaults()

### Toolbar actions
class ToolbarDelegate(NibClassBuilder.AutoBaseClass):

    def init(self):
        self = super(ToolbarDelegate, self).init()
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, self.selectionChanged, "TorrentSelectionChanged", None)
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, self.selectionChanged, "TorrentStatusChanged", None)
        self.items = {}
        return self
        
    def selectionChanged(self, note):
        try:
            c = self.appDelegate.selectedController()
        except NoTorrentSelected:
            pass
        else:
            torrent = c.torrent
            if torrent:
                self.max_upload_rate.setIntValue_(torrent.config['max_upload_rate'])
                self.min_uploads.setIntValue_(torrent.config['min_uploads'])
                self.max_uploads.setIntValue_(torrent.config['max_uploads'])                
                self.max_initiate.setIntValue_(torrent.config['max_initiate'])
                self.max_accept.setIntValue_(torrent.config['max_allow_in'])
                self.stopPop.selectItemAtIndex_(self.stopPop.indexOfItemWithTag_(c.QUEUESTOP))
                
            else:
                self.appDelegate.reloadConfig()
                self.max_uploads.setIntValue_(c.max_uploads)
                #self.min_uploads.setIntValue_(c.min_uploads) 
                self.max_upload_rate.setIntValue_(c.max_upload_rate)
                self.max_initiate.setIntValue_(c.max_initiate)
                self.max_accept.setIntValue_(c.max_allow_in) 
                self.stopPop.selectItemAtIndex_(self.stopPop.indexOfItemWithTag_(c.QUEUESTOP))
                self.ratio.setFloatValue_(c.STOPRATIO)
                self.time.setIntValue_(c.STOPTIME)

            def f(id):
                def z(a, id=id):
                    x = False
                    try:
                        x = a.itemIdentifier() == id
                    except AttributeError:
                        pass
                    return x
                return z

            self.updateAutostop(c)
            # the docs say not to call this
            self.tbar.validateVisibleItems()

    def updateAutostop(self, c):
        def f(id):
            def z(a, id=id):
                x = False
                try:
                    x = a.itemIdentifier() == id
                except AttributeError:
                    pass
                return x
            return z
        # do swappable ratio/time thing here
        if c.QUEUESTOP == 0:
            self.time.setFloatValue_(c.STOPRATIO)
            fmt = self.time.formatter()
            fmt.setFormat_(",0.0;0.0")
            fmt.setMinimum_(0)
            fmt.setLocalizesFormat_(True)
            time = filter(f('STOPTIME'), self.tbar.items())
            if time:
                time[0].setLabel_(NSLocalizedString("Stop Ratio", "stop ratio toolbar label"))
        elif c.QUEUESTOP == 1:
            self.time.setIntValue_(c.STOPTIME)
            fmt = self.time.formatter()
            fmt.setFormat_(",0;0")
            fmt.setMinimum_(1)
            fmt.setLocalizesFormat_(True)
            time = filter(f('STOPTIME'), self.tbar.items())
            if time:
                time[0].setLabel_(NSLocalizedString("Stop Mins.", "stop time toolbar label"))

    def enabled(self):
        try:
            c = self.appDelegate.selectedController()
        except NoTorrentSelected:
            return 0
        return 1
    
    def takeMaxUploadsFrom_(self, sender):
        sender.setIntValue_(sender.intValue())
        try:
            c = self.appDelegate.selectedController()
        except NoTorrentSelected:
            return 0
        if c.torrent:
            c.torrent.set_option('max_uploads', sender.intValue())
        c.max_uploads = sender.intValue()

    def takeMinUploadsFrom_(self, sender):
        sender.setIntValue_(sender.intValue())
        val = sender.intValue()
        if val < MIN_SLOTS:
            val = MIN_SLOTS
        sender.setIntValue_(val)
        try:
            c = self.appDelegate.selectedController()
        except NoTorrentSelected:
            return 0
        if c.torrent:
            c.torrent.set_option('min_uploads', sender.intValue())
        c.min_uploads = sender.intValue()
        
    def takeMaxUploadRateFrom_(self, sender):
        sender.setIntValue_(sender.intValue())
        try:
            c = self.appDelegate.selectedController()
        except NoTorrentSelected:
            return 0
        if c.torrent:
            c.torrent.set_option('max_upload_rate', sender.intValue() * 1024)
        c.max_upload_rate = sender.intValue()

        
    def takeMaxInitiateFrom_(self, sender):
        sender.setIntValue_(sender.intValue())
        try:
            c = self.appDelegate.selectedController()
        except NoTorrentSelected:
            return 0
        if c.torrent:
            c.torrent.set_option('max_initiate', sender.intValue())
        c.max_initiate = sender.intValue()
        
    def takeMaxAcceptFrom_(self, sender):
        sender.setIntValue_(sender.intValue())
        try:
            c = self.appDelegate.selectedController()
        except NoTorrentSelected:
            return 0
        if c.torrent:
            c.torrent.set_option('max_allow_in', sender.intValue())
        c.max_allow_in = sender.intValue()

    def takeStopQueueFrom_(self, sender):
        try:
            c = self.appDelegate.selectedController()
        except NoTorrentSelected:
            return 0
        else:
            c.QUEUESTOP = sender.selectedItem().tag()
            self.updateAutostop(c)
            
    def takeStopRatioFrom_(self, sender):
        try:
            c = self.appDelegate.selectedController()
        except NoTorrentSelected:
            return 0
        else:
            c.setStopRatio(sender.floatValue())
            
    def takeStopTimeFrom_(self, sender):
        try:
            c = self.appDelegate.selectedController()
        except NoTorrentSelected:
            return 0
        else:
            if c.QUEUESTOP == 0:
                c.setStopRatio(sender.floatValue())
                sender.setFloatValue_(c.STOPRATIO)
            elif c.QUEUESTOP == 1:
                c.STOPTIME = sender.intValue()
                sender.setIntValue_(c.STOPTIME)
    
    def awakeFromNib(self):
        t = NSToolbar.alloc().initWithIdentifier_("torrenttoolbar")
        t.setDelegate_(self)
        t.setAutosavesConfiguration_(True)
        t.setAllowsUserCustomization_(True)
        self.window.setToolbar_(t)
        t.setVisible_(True)
        self.tbar = t

    def createItemForIdentifier(self, itemIdentifier):
        if itemIdentifier == 'close':
            item = CloseItem.alloc().initWithItemIdentifier_('close')
            item.setView_(self.closeButton)
            item.setTarget_(self.appDelegate)
            item.setAction_(self.appDelegate.closeTorrent_)
            item.setLabel_(NSLocalizedString("Clear", "close button label"))
            item.setPaletteLabel_(NSLocalizedString("Clear Torrent", "close label"))
            rect = self.closeButton.frame()
            item.setMinSize_(rect.size)
            item.setEnabled_(0)
        elif itemIdentifier == 'start':
            item = StartItem.alloc().initWithItemIdentifier_('start')
            item.setView_(self.startButton)
            item.setTarget_(self.appDelegate)
            item.setAction_(self.appDelegate.cycleTorrent_)
            item.setPaletteLabel_(NSLocalizedString("Start Torrent", "start torrent pallette label"))
            rect = self.startButton.frame()
            item.setMinSize_(rect.size)
            item.setEnabled_(0)
            item.setLabel_(NSLocalizedString("Start", "start"))
        elif itemIdentifier == 'stop':
            item = StopItem.alloc().initWithItemIdentifier_('stop')
            item.setView_(self.stopButton)
            item.setTarget_(self.appDelegate)
            item.setAction_(self.appDelegate.cycleTorrent_)
            item.setPaletteLabel_(NSLocalizedString("Stop Torrent", "stop torrent pallette label"))
            rect = self.stopButton.frame()
            item.setMinSize_(rect.size)
            item.setEnabled_(0)
            item.setLabel_(NSLocalizedString("Stop", "stop"))
        elif itemIdentifier == 'info':
            item = TransportItem.alloc().initWithItemIdentifier_('info')
            item.setView_(self.infoButton)
            item.setTarget_(self.appDelegate)
            item.setAction_(self.appDelegate.inspectTorrent_)
            item.setLabel_(NSLocalizedString("Inspect", "inspect toolbar label"))
            item.setPaletteLabel_(NSLocalizedString("Inspect Torrent", "inspect toolbar palette label"))
            rect = self.infoButton.frame()
            item.setMinSize_(rect.size)
            item.setEnabled_(0)
        elif itemIdentifier == 'reveal':
            item = TransportItem.alloc().initWithItemIdentifier_('reveal')
            item.setView_(self.revealButton)
            item.setTarget_(self.appDelegate)
            item.setAction_(self.appDelegate.revealTorrent_)
            item.setLabel_(NSLocalizedString("Show", "show toolbar label"))
            item.setPaletteLabel_(NSLocalizedString("Show in Finder", "show toolbar palette label"))
            rect = self.revealButton.frame()
            item.setMinSize_(rect.size)
            item.setEnabled_(0)
        elif itemIdentifier == 'peers':
            item = EnabledItem.alloc().initWithItemIdentifier_('peers')
            item.setView_(self.peersButton)
            item.setTarget_(self.appDelegate)
            item.setAction_(self.appDelegate.toggleDetail_)
            item.setLabel_(NSLocalizedString("Peers", "peer detail toolbar label"))
            item.setPaletteLabel_(NSLocalizedString("Show Peer Detail", "peer detail toolbar palette label"))
            rect = self.peersButton.frame()
            item.setMinSize_(rect.size)
            item.setEnabled_(0)
        elif itemIdentifier == 'log':
            item = EnabledItem.alloc().initWithItemIdentifier_('log')
            item.setView_(self.logButton)
            item.setTarget_(self.appDelegate.logDrawer)
            item.setAction_(self.appDelegate.logDrawer.toggle_)
            item.setLabel_(NSLocalizedString("Log", "log toolbar label"))
            item.setPaletteLabel_(NSLocalizedString("Toggle Log Drawer", "peer detail toolbar palette label"))
            rect = self.logButton.frame()
            item.setMinSize_(rect.size)
            item.setEnabled_(0)
        elif itemIdentifier == 'min_uploads':
            item = MinUploadsItem.alloc().initWithItemIdentifier_('min_uploads')
            item.setView_(self.min_uploads)
            item.setTarget_(self)
            item.setAction_(self.takeMinUploadsFrom_)
            item.setLabel_(NSLocalizedString("Opt. Slots", "min_uploads toolbar label"))
            item.setPaletteLabel_(NSLocalizedString("Optimistic Unchoke Slots", "optimistic unchokes toolbar palette label"))
            self.min_uploads.setIntValue_(defaults.integerForKey_(MINULS))
            rect = self.min_uploads.frame()
            item.setMinSize_(rect.size)
            item.setEnabled_(0)
        elif itemIdentifier == 'max_uploads':
            item = MaxUploadsItem.alloc().initWithItemIdentifier_('max_uploads')
            item.setView_(self.max_uploads)
            item.setTarget_(self)
            item.setAction_(self.takeMaxUploadsFrom_)
            item.setLabel_(NSLocalizedString("Max Slots", "max_uploads toolbar label"))
            item.setPaletteLabel_(NSLocalizedString("Maximum Upload Slots", "max_uploads toolbar palette label"))
            self.max_uploads.setIntValue_(defaults.integerForKey_(MAXULS))
            rect = self.max_uploads.frame()
            item.setMinSize_(rect.size)
            item.setEnabled_(0)
        elif itemIdentifier == 'max_upload_rate':
            item = MaxUploadRateItem.alloc().initWithItemIdentifier_('max_upload_rate')
            item.setView_(self.max_upload_rate)
            item.setTarget_(self)
            item.setAction_(self.takeMaxUploadRateFrom_)
            item.setLabel_(NSLocalizedString("Max UL KiB/s", "max_upload_rate toolbar label"))
            item.setPaletteLabel_(NSLocalizedString("Maximum Upload Rate", "max_upload_rate toolbar palette mlabel"))
            self.max_upload_rate.setIntValue_(0)
            rect = self.max_upload_rate.frame()
            item.setMinSize_(rect.size)
            item.setEnabled_(0)
        elif itemIdentifier == 'max_initiate':
            item = MaxInitiateItem.alloc().initWithItemIdentifier_('max_initiate')
            item.setView_(self.max_initiate)
            item.setTarget_(self)
            item.setAction_(self.takeMaxInitiateFrom_)
            item.setLabel_(NSLocalizedString("Max Initiate", "max_initiate toolbar label"))
            item.setPaletteLabel_(NSLocalizedString("Maxium Peers to Initiate Connections", "max_initiate toolbar palette label"))
            self.max_initiate.setIntValue_(defaults.integerForKey_(MAXINITIATE))
            rect = self.max_initiate.frame()
            item.setMinSize_(rect.size)
            item.setEnabled_(0)
        elif itemIdentifier == 'max_accept':
            item = MaxAcceptItem.alloc().initWithItemIdentifier_('max_accept')
            item.setView_(self.max_accept)
            item.setTarget_(self)
            item.setAction_(self.takeMaxAcceptFrom_)
            item.setLabel_(NSLocalizedString("Max Accept", "max_accept toolbar label"))
            item.setPaletteLabel_(NSLocalizedString("Maximum Peers to Accept Connections", "max_accept toolbar palette label"))
            self.max_accept.setIntValue_(defaults.integerForKey_(MAXACCEPT))
            rect = self.max_accept.frame()
            item.setMinSize_(rect.size)
            item.setEnabled_(0)
        elif itemIdentifier == 'QUEUESTOP':
            item = StopPopItem.alloc().initWithItemIdentifier_('QUEUESTOP')
            item.setView_(self.stopPop)
            item.setTarget_(self)
            item.setAction_(self.takeStopQueueFrom_)
            item.setLabel_(NSLocalizedString("Autostop", "autostop toolbar label"))
            item.setPaletteLabel_(NSLocalizedString("Autostop Method", "autostop toolbar palette label"))
            #self.stopPop.selectItemAtIndex_(self.stopPop.indexOfItemWithTag_(defaults.integerForKey_(QUEUESTOP)))
            rect = self.stopPop.frame()
            item.setMinSize_(rect.size)
            item.setEnabled_(0)
        elif itemIdentifier == 'STOPTIME':
            item = StopTimeItem.alloc().initWithItemIdentifier_('STOPTIME')
            item.setView_(self.time)
            item.setTarget_(self)
            item.setAction_(self.takeStopTimeFrom_)
            item.setLabel_(NSLocalizedString("Stop Mins.", "stop time toolbar label"))
            item.setPaletteLabel_(NSLocalizedString("Autostop in minutes", "stop timetoolbar palette label"))
            self.time.setIntValue_(defaults.integerForKey_(STOPTIME))
            rect = self.time.frame()
            item.setMinSize_(rect.size)
            item.setEnabled_(0)
        elif itemIdentifier == 'STOPRATIO':
            item = MaxAcceptItem.alloc().initWithItemIdentifier_('STOPRATIO')
            item.setView_(self.ratio)
            item.setTarget_(self)
            item.setAction_(self.takeStopRatioFrom_)
            item.setLabel_(NSLocalizedString("Stop Ratio", "stop ratio toolbar label"))
            item.setPaletteLabel_(NSLocalizedString("Autostop Ratio", "stop ratio toolbar palette label"))
            self.ratio.setFloatValue_(defaults.floatForKey_(STOPRATIO))
            rect = self.ratio.frame()
            item.setMinSize_(rect.size)
            item.setEnabled_(0)
        elif itemIdentifier == 'cycle':
            item = None
        return item

    ### Toolbar delegate methods
    apple = [NSToolbarCustomizeToolbarItemIdentifier, NSToolbarFlexibleSpaceItemIdentifier, NSToolbarSpaceItemIdentifier, NSToolbarSeparatorItemIdentifier]
    uls = ["max_uploads", 'max_upload_rate']
    que = ['QUEUESTOP', 'STOPTIME']
    std = ['close', 'stop', 'start', 'info', 'reveal', 'log', 'peers']

    def toolbarAllowedItemIdentifiers_(self, toolbar):
        return self.apple + self.std + self.que + self.uls
        
    def toolbarDefaultItemIdentifiers_(self, toolbar):
        l = ['close', 'stop', 'start', NSToolbarSpaceItemIdentifier, 'info', 'reveal']
        l += [NSToolbarFlexibleSpaceItemIdentifier, 'log']
        return l

    def toolbar_itemForItemIdentifier_willBeInsertedIntoToolbar_(self, toolbar, itemIdentifier, flag):
        try:
            item = self.items[itemIdentifier]
        except KeyError:
            item = self.createItemForIdentifier(itemIdentifier)
            self.items[itemIdentifier] = item
        return item
