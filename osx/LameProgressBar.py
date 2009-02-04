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

# my progress bar
# lame, but fast

from AppKit import *
from PyObjCTools import NibClassBuilder
from objc import *

NibClassBuilder.extractClasses("DLView")

class LameProgressBar(NibClassBuilder.AutoBaseClass):
    _val = 0
    def initWithFrame(self, frame):
        self = super(LameProgressBar, self).init()
        
    def drawRect_(self, rect):
        origin, size  = rect
        x, y = origin
        w, h = size
        nrect = ((x+1, y+1), (int((w-2) * self._val), h-2))
        NSColor.blackColor().set()
        NSBezierPath.strokeRect_(rect)
        NSColor.colorForControlTint_(NSColor.currentControlTint()).set()
        NSRectFill(nrect)

    def setDoubleValue_(self, new):
        self._val = new
        self.setNeedsDisplay_(True)
        
