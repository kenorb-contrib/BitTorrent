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
from Preferences import *

NibClassBuilder.extractClasses("ChoosePort")

class PortChanger(NibClassBuilder.AutoBaseClass):
    def initWithErr(self, err):
        self = super(PortChanger, self).init()
        self.err = err
        NSBundle.loadNibNamed_owner_("ChoosePort", self)

    def awakeFromNib(self):
        defaults = NSUserDefaults.standardUserDefaults()
        self.errField.setStringValue_(self.err)
        self.portField.setIntValue_(defaults.integerForKey_(MINPORT))
        NSApp().runModalForWindow_(self.window)

    def save_(self, sender):
        defaults = NSUserDefaults.standardUserDefaults()        
        defaults.setObject_forKey_(self.portField.intValue(), MINPORT)
        NSApp().stopModal()
        NSApp().terminate_(self)
