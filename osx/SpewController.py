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
from BTAppController import NoTorrentSelected
from BitTorrent.ClientIdentifier import identify_client as client
from utils import *

NibClassBuilder.extractClasses("DetailView")

f = open('/tmp/unknown_clients', 'wb')
def spewval(d, v):
    if v == 'ip':
        return d['ip']
    elif v == 'cl':
        return "%s %s" % client(d['id'], f)
    elif v == 'lr':
        return d['initiation'][0]
    elif v == 'ui':
        if d['completed'] == 1.0:
            return '-'
        elif d['upload'][2]:
            if d['is_optimistic_unchoke']:
                return '*'
            else:
                return 'i'
    elif v == 'ur':
        return formRate(d['upload'][1])
    elif v == 'uc':
        if d['upload'][3]:
            return 'c'
    elif v == 'di':
        if d['download'][2]:
            if d['download'][4] and not d['download'][3]:
                return "s"
            return 'i'
    elif v == 'dr':
        return formRate(d['download'][1])
    elif v == 'dc':
        if d['download'][3]:
            return 'c'
    elif v == 'ds':
        if d['download'][4]:
            return 's'
    return ''

gray = NSColor.grayColor()
black = NSColor.blackColor()

def cmp_spew(a, b):
    def r(x, y):
        if x[0] > y[0]:
            return 1
        elif x[0] < y[0]:
            return -1
        else:
            if len(x) == 1:
                return 0
            else:
                return r(x[1:], y[1:])

    a = a['ip'].split('.'); b = b['ip'].split('.')
    a = map(lambda x: int(x), a); b = map(lambda x: int(x), b)
    return r(a, b)

class SpewController (NibClassBuilder.AutoBaseClass):
    def init(self):
        self = super(SpewController, self).init()
        self.spew = None
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, self.selectionChanged, "TorrentSelectionChanged", None)
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, self.display, "TorrentDisplayed", None)
        self.count = 0
        return self
        
    def awakeFromNib(self):
        if self.table.window().isVisible():
            self.selectionChanged(None)
            
    def selectionChanged(self, note):
        try:
            c = self.delegate.selectedController()
            if c.torrent:
                try:
                    self.spew = c.torrent.get_status(spew=1)['spew']
                    self.spew.sort(cmp_spew)
                except KeyError:
                    self.spew = None
            else:
                self.spew = None
            self.table.window().setTitle_(NSLocalizedString("%s peer details", "peer detail title string") % c.metainfo.name.decode('utf-8'))
        except NoTorrentSelected:
            self.spew = None
            self.table.window().setTitle_(NSLocalizedString("No torrent selected", "empty detail title string"))

        self.table.reloadData()
    
    def display(self, note):
        if self.table.window().isVisible():
            try:
                c = self.delegate.selectedController()
                if not note or note.object() == c:
                    self.count = (self.count + 1) % 2
                    if self.count == 0:
                        if not c.torrent:
                            self.spew = None
                        else:
                            try:
                                self.spew = c.torrent.get_status(spew=1)['spew']
                                self.spew.sort(cmp_spew)
                            except KeyError:
                                self.spew = None
                        self.table.reloadData()
            except NoTorrentSelected:
                self.spew = None
    
    def showWindow(self):
        self.selectionChanged(None)
        self.table.reloadData()
        self.table.window().makeKeyAndOrderFront_(self)

    def toggleWindow(self):
        w = self.table.window()
        if w.isVisible():
            w.close()
        else:
            self.showWindow()
        
    ### tv datasource methods
    def numberOfRowsInTableView_(self, tv):
        if self.spew:
            n = len(self.spew)
        else:
            n = 0
        return n
    
    def tableView_objectValueForTableColumn_row_(self, tv, col, row):
        try:
            v = spewval(self.spew[row], col.identifier())
        except NoTorrentSelected:
            v = ""
            
        return v

    def tableView_willDisplayCell_forTableColumn_row_(self, tv, cell, col, row):
        if col.identifier() == "dr":
            if self.spew[row]["download"][3] or not self.spew[row]['download'][2]:
                cell.setTextColor_(gray)
                return
        if col.identifier() == "ur" :
            if self.spew[row]["upload"][3] or not self.spew[row]['upload'][2]:
                cell.setTextColor_(gray)
                return
        cell.setTextColor_(black)
