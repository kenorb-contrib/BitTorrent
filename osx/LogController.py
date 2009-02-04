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

from time import asctime, localtime

NibClassBuilder.extractClasses("MainMenu")

class LogController (NibClassBuilder.AutoBaseClass):

    def awakeFromNib(self):
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, self.incomingError, "DLControllerError", None)
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, self.selectionChanged, "TorrentSelectionChanged", None)

    def selectionChanged(self, note):
        self.logView.reloadData()
        self.logView.sizeToFit()
        self.logView.scrollRowToVisible_(self.logView.numberOfRows() - 1)

    def incomingError(self, note):
        c, l, t, e = note.object()
        try:
            if c == self.delegate.selectedController():
                self.logView.noteNumberOfRowsChanged()
                self.logView.sizeToFit()
                self.logView.scrollRowToVisible_(self.logView.numberOfRows() - 1)
        except NoTorrentSelected:
            pass
        
    ### tv datasource methods
    def numberOfRowsInTableView_(self, tv):
        n = 0
        try:
            n = len(self.delegate.selectedController().errorList())
        except NoTorrentSelected:
            pass
        return n
    
    def tableView_objectValueForTableColumn_row_(self, tv, col, row):
        val = ""
        if col.identifier() == 'time':
            i = 1
            try:
                val = self.delegate.selectedController().errorList()[row][i]
                val = asctime(localtime(val))
            except NoTorrentSelected:
                pass
            except IndexError:
                print ">>> invalid row in errlist"
        else:
            i = 2
            try:
                val = self.delegate.selectedController().errorList()[row][i]
            except NoTorrentSelected:
                pass
            except IndexError:
                print ">>> invalid row in errlist"
            
        return val

    ## drawer delegate methods
    def drawerWillOpen_(self, drawer):
        self.logView.sizeToFit()
        
    def drawerDidOpen_(self, drawer):
        self.menu.setState_(NSOnState)
        self.logView.reloadData()
        self.logView.sizeToFit()
        
    def drawerDidClose_(self, drawer):
        self.menu.setState_(NSOffState)
        
