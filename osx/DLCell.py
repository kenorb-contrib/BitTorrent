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
from objc import *

from PyObjCTools import NibClassBuilder

from DLController import DLController
from Preferences import SEEDINGCOLOR,COMPLETECOLOR,STALLEDCOLOR,ERRORCOLOR, colors
#NibClassBuilder.extractClasses("DLView")

CCell = lookUpClass("CCell")

white = NSColor.whiteColor()

class DLCell (CCell):        
    def drawWithFrame_inView_(self, frame, view):
        bview = self.getCView()
        sview = bview.superview()
        if view.ICR:
            if view.isEqual_(sview):
                bview.removeFromSuperviewWithoutNeedingDisplay()
        else:
            if not view.isEqual_(sview):
                view.addSubview_(bview)
            bview.setFrame_(frame)

class PyTimeCell(DLCell):
    def getCView(self):
        return self.getController().getTimeView()
    
class PyFileCell(DLCell):
    def getCView(self):
        return self.getController().getFileView()

class PyXFerCell(DLCell):
    def getCView(self):
        return self.getController().getXFerView()
