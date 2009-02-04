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

from AppKit import *
from Foundation import *
from sha import sha
from PyObjCTools import NibClassBuilder

NibClassBuilder.extractClasses("TorrentInspector")

from BitTorrent.ConvertedMetainfo import ConvertedMetainfo
from BitTorrent.bencode import bencode as encode
from BitTorrent.bencode import bdecode as decode
from khashmir.util import unpackPeers, compact_peer_info

from utils import formSize
import traceback
import os, sys

POINT = (0,0)

class TorrentInspector(NibClassBuilder.AutoBaseClass):
    path = None
    def initWithTorrentPath_(self, path):
        self.path = path
        try:
            data = open(path, 'rb').read()
        except IOError, e:
            NSRunAlertPanel(NSLocalizedString("Error Opening Torrent", "torrent open error"),
                            NSLocalizedString("Unable to read torrent file: %s" % str(e)),
                            NSLocalizedString("OK", "OK"), None, none)
        return self.initWithTorrentData_(data)
    
    def initWithTorrentData_(self, data):
        self = super(TorrentInspector, self).init()
        self.dict = decode(data)
        self.metainfo = ConvertedMetainfo(self.dict)
        try:
            NSBundle.loadNibNamed_owner_("TorrentInspector", self)
        except UnicodeError:
            NSRunAlertPanel(NSLocalizedString("Decode Error: %s", "unicode decode error window title") % "", 
                            NSLocalizedString("This torrent was made with a broken tool and has an incorrectly encoded filename. Sorry!  Error message: %s", "unicode decode detail") % sys.exc_info()[1], 
                            NSLocalizedString("OK", "OK"), None, None)

        return self
    
    def awakeFromNib(self):
        global POINT
        POINT = self.win.cascadeTopLeftFromPoint_(POINT)
        self.display()
        if self.path:
            self.win.setTitleWithRepresentedFilename_(self.path)
        else:
            self.win.setTitleWithRepresentedFilename_(self.metainfo.name_fs)
        self.win.makeKeyAndOrderFront_(self)
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, self.windowWillClose_, "NSWindowWillCloseNotification", self.win)

    def display(self):
        self.name.setStringValue_(unicode(self.metainfo.name_fs, 'utf8'))
        self.size.setStringValue_(NSLocalizedString("%s (%s bytes)", "torrent inspector size string") % (formSize(self.metainfo.total_bytes), self.metainfo.total_bytes))

        self.infohash.setStringValue_(self.metainfo.infohash.encode('hex'))
        try:
            self.announce.setStringValue_(self.metainfo.announce)
        except AttributeError: 
            # trackerless torrent
            self.announceTitle.setTitle_(NSLocalizedString("Nodes", "Nodes"))
            try:
                self.announce.setStringValue_(''.join(["%s:%s, " % (h,p) for h,p in self.metainfo.nodes])[:-2])
            except:
                self.announce.setStringValue_(NSLocalizedString("Failed to decode nodes properly.", "nodes decode failure"))
        try:
            comment = self.dict['comment'].decode('utf8', 'replace')
        except KeyError:
            comment = ''
        except UnicodeDecodeError:
            comment = "<comment failed to decode correctly>"
        storage = self.comment.textStorage()
        storage.replaceCharactersInRange_withString_((0, storage.length()), comment)



            
        
    def save_(self, sender):
        if hasattr(self.metainfo, 'announce'):
            self.dict['announce'] = self.announce.stringValue().encode('utf8')
        else:
            self.dict['nodes'] = [(str(a[0]), int(a[1])) for a in [node.strip().split(":") for node in self.announce.stringValue().split(",")]]
        self.dict['comment'] = self.comment.textStorage().string().encode('utf8')
        s = encode(self.dict)
        f = open(self.path, 'wb')
        f.write(s)
        f.close()
        
    def revert_(self, sender):
        self.display()
    

    def numberOfRowsInTableView_(self,tv):
        if self.metainfo.is_batch:
            return(len(self.metainfo.files_fs))
        else:
            return 1

    def tableView_objectValueForTableColumn_row_(self, tv, col, row):
        if self.metainfo.is_batch:
            return unicode(self.metainfo.files_fs[row], 'utf8')
        else:
            return unicode(self.metainfo.name_fs, 'utf8')
        
            
    def windowWillClose_(self, note):
        self.autorelease()
