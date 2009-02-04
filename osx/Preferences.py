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
#
#  Preferences.py
#  BitTorrent
#
#  Created by Drue Loewenstern on Sat Feb 14 2004.
#  Copyright (c) 2004 __MyCompanyName__. All rights reserved.
#
from AppKit import *
from Foundation import *

MINPORT ="minport"
MAXPORT ="maxport" # obsolete
IP ="ip"
DIRASK = "dirask" # 0 = use internet folder, 1 = ask, 2 = use dldir
DLDIR = "dldir"

MAXULS = "max_uploads"
MINULS = "min_uploads"
MAXULRATE = "max_upload_rate"

MAXINITIATE = 'max_initiate'
MAXACCEPT = 'max_allow_in'

DOQUEUE = 'doqueue'
QUEUESTOP = 'queuestop' # 0 = ratio, 1 = time, 2 = first, 3 = last
STOPRATIO = 'stopratio'
STOPTIME = 'stoptime'

ULBYTES = 'ulbytes' #bytes uploaded, bencoded string
DLBYTES = 'dlbytes' #bytes downloaded, bencoded string

## colors
SEEDINGCOLOR = 'seedingcolor'
COMPLETECOLOR = 'completecolor'
STALLEDCOLOR = 'stalledcolor'
ERRORCOLOR = 'errorcolor'

#ULSCHED = 'upload_schedule'

QRATIO = 0
QTIME = 1
#QFIRST = 2
#QLAST = 3

QUEUESTART = 'queuestart' # 0 = start once all non-seeds are finished, 1 = as soon as any starts

QSSINGLE = 0
QSMULTI = 1

NAG = "nag"

VERSIONCHECK = 'versioncheck'

# factory settings
MINPORT_DEFAULT = 6881
MAXPORT_DEFAULT = 6889
IP_DEFAULT =""
DIRASK_DEFAULT = 0
DLDIR_DEFAULT = ""

MINULS_DEFAULT = 2
MAXULS_DEFAULT = 4
MAXULRATE_DEFAULT = 0
MAXINITIATE_DEFAULT = 40
MAXACCEPT_DEFAULT = 80

#ULSCHED_DEFAULT = 1

DOQUEUE_DEFAULT = 1
QUEUESTOP_DEFAULT = QRATIO
QUEUESTART_DEFAULT = QSSINGLE
STOPRATIO_DEFAULT = 0.8
STOPTIME_DEFAULT = 1
NAG_DEFAULT = 0

SEEDINGCOLOR_DEFAULT= NSArchiver.archivedDataWithRootObject_(NSColor.colorWithCalibratedHue_saturation_brightness_alpha_(.666, .10, 1.0, 1.0))
COMPLETECOLOR_DEFAULT = NSArchiver.archivedDataWithRootObject_(NSColor.colorWithCalibratedHue_saturation_brightness_alpha_(.333, .15, 1.0, 1.0))
STALLEDCOLOR_DEFAULT = NSArchiver.archivedDataWithRootObject_(NSColor.colorWithCalibratedHue_saturation_brightness_alpha_(.166, .3, 1.0, 1.0))
ERRORCOLOR_DEFAULT = NSArchiver.archivedDataWithRootObject_(NSColor.colorWithCalibratedHue_saturation_brightness_alpha_(1.0, .10, 1.0, 1.0))

VERSIONCHECK_DEFAULT = 1
from Foundation import *
from AppKit import *
from PyObjCTools import NibClassBuilder

import objc
import os

NibClassBuilder.extractClasses("Preferences")
appDefaults = {
                IP:IP_DEFAULT,
                MINPORT:MINPORT_DEFAULT, 
                MAXULS:MAXULS_DEFAULT, MINULS: MINULS_DEFAULT,
                MAXULRATE:MAXULRATE_DEFAULT,
                DIRASK:DIRASK_DEFAULT, DLDIR:DLDIR_DEFAULT,
                MAXINITIATE : MAXINITIATE_DEFAULT, MAXACCEPT : MAXACCEPT_DEFAULT,
                DOQUEUE : DOQUEUE_DEFAULT,
                QUEUESTOP : QUEUESTOP_DEFAULT,
                STOPRATIO : STOPRATIO_DEFAULT, STOPTIME:STOPTIME_DEFAULT,
                QUEUESTART : QUEUESTART_DEFAULT,
                NAG:NAG_DEFAULT,
                ULBYTES : 'i0e', DLBYTES : 'i0e',
                SEEDINGCOLOR:SEEDINGCOLOR_DEFAULT, COMPLETECOLOR:COMPLETECOLOR_DEFAULT,
                STALLEDCOLOR:STALLEDCOLOR_DEFAULT, ERRORCOLOR:ERRORCOLOR_DEFAULT,
                VERSIONCHECK:VERSIONCHECK_DEFAULT
                }

class Preferences (NibClassBuilder.AutoBaseClass):
    def init(self):
        self = super(Preferences, self).init()
        self.fname = None
        self.defaults = NSUserDefaults.standardUserDefaults()
        self.defaults.registerDefaults_(appDefaults)
        ## convert strings to int
        strings = [MINPORT, MAXULS, MINULS, MAXULRATE, MINULS, MAXULS]
        for key in strings:
            val = self.defaults.objectForKey_(key)
            if type(val) == type(''):
                self.defaults.setObject_forKey_(int(val), key)

        self.globalPrefs = GlobalPrefs.alloc().init()
        self.torrentPrefs = TorrentPrefs.alloc().init()
        self.queuePrefs = QueuePrefs.alloc().init()
        self.colorPrefs = ColorPrefs.alloc().init()

        return self

    def awakeFromNib(self):
        self.sharedDefaults.setInitialValues_(appDefaults)
        globalTab = self.tabView.tabViewItemAtIndex_(0)
        globalTab.setView_(self.globalView)

        torrentTab = self.tabView.tabViewItemAtIndex_(1)
        torrentTab.setView_(self.torrentView)

        queueTab = self.tabView.tabViewItemAtIndex_(2)
        queueTab.setView_(self.queueView)
        window = self.tabView.window()
        window.registerForDraggedTypes_([NSFilenamesPboardType])

        colorTab = self.tabView.tabViewItemAtIndex_(3)
        colorTab.setView_(self.colorView)

        self.sharedDefaults.addObserver_forKeyPath_options_context_(NSApp().delegate(), "defaults.max_upload_rate", NSKeyValueObservingOptionNew & NSKeyValueObservingOptionOld, 0)

        self.tabView.selectTabViewItemAtIndex_(0)

    def windowDidBecomeKey_(self, aNotification):
        pass

    def draggingEntered_(self, sender):
        board = sender.draggingPasteboard()
        names = board.propertyListForType_('NSFilenamesPboardType')
        if len(names) > 0:
            f = names[0]
            if os.path.isdir(f):
                self.fname = self.dldir.stringValue()
                self.dldir.setStringValue_(f)
                return NSDragOperationGeneric
        return NSDragOperationNone
        
    def draggingExited_(self, sender):
        if self.fname:
            self.dldir.setStringValue_(self.fname)
        else:
            self.dldir.setStringValue_(self.defaults.objectForKey_(DLDIR))
        
    def performDragOperation_(self, sender):
        self.fname = self.dldir.stringValue()
        self.defaults.setObject_forKey_(self.fname, DLDIR)
        return 1

class GlobalPrefs(NSObject):
    pass
class TorrentPrefs(NSObject):
    pass

class QueuePrefs(NSObject):
    pass
colors = {}

class ColorPrefs(NSObject):
    def init(self):
        self.cacheColors()
        return self
    
    def cacheColors(self):
        defaults = NSUserDefaults.standardUserDefaults()
        colors[SEEDINGCOLOR] = self.decodeColor(defaults.objectForKey_(SEEDINGCOLOR))
        colors[COMPLETECOLOR] = self.decodeColor(defaults.objectForKey_(COMPLETECOLOR))
        colors[STALLEDCOLOR] = self.decodeColor(defaults.objectForKey_(STALLEDCOLOR))
        colors[ERRORCOLOR] = self.decodeColor(defaults.objectForKey_(ERRORCOLOR))
        
    def decodeColor(self, c):
        return NSUnarchiver.unarchiveObjectWithData_(c)
