# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# written by Matt Chisholm

from __future__ import division

import gtk
import pango
import gobject
import os.path

from __init__ import image_root, app_name

SPACING = 8
WINDOW_TITLE_LENGTH = 128 # do we need this?
WINDOW_WIDTH = 600
MAX_WINDOW_HEIGHT = 600 # BUG: can we get this from the user's screen size?
MAX_WINDOW_WIDTH  = 600 # BUG: can we get this from the user's screen size?
MIN_MULTI_PANE_HEIGHT = 160

# a slightly hackish but very reliable way to get OS scrollbar width
sw = gtk.ScrolledWindow()
SCROLLBAR_WIDTH = sw.size_request()[0] - 48
del sw

def align(obj,x,y):
    a = gtk.Alignment(x,y,0,0)
    a.add(obj)
    return a
    
def halign(obj, amt):
    return align(obj,amt,0.5)

def lalign(obj):
    return halign(obj,0)

def ralign(obj):
    return halign(obj,1)

def valign(obj, amt):
    return align(obj,0.5,amt)


factory = gtk.IconFactory()

# these don't seem to be documented anywhere:
# ICON_SIZE_BUTTON        = 20x20
# ICON_SIZE_LARGE_TOOLBAR = 24x24

for n in 'broken finished info pause play queued running remove'.split():
    fn = os.path.join(image_root, ("%s.png"%n))

    pixbuf = gtk.gdk.pixbuf_new_from_file(fn)
    
    set = gtk.IconSet(pixbuf)

    factory.add('bt-%s'%n, set)

factory.add_default()

def get_logo(size=32):
    fn = os.path.join(image_root, 'logo', 'bittorrent_%d.png'%size)
    logo = gtk.Image()
    logo.set_from_file(fn)
    return logo

class Size(long):
    """displays size in human-readable format"""
    size_labels = ['','K','M','G','T','P','E','Z','Y']    
    radix = 2**10

    def __new__(cls, value, precision=None):
        self = long.__new__(cls, value)
        return self

    def __init__(self, value, precision=0):
        long.__init__(self, value)
        self.precision = precision

    def __str__(self, precision=None):
        if precision is None:
            precision = self.precision
        value = self
        for unitname in self.size_labels:
            if value < self.radix and precision < self.radix:
                break
            value /= self.radix
            precision /= self.radix
        if unitname and value < 10 and precision < 1:
            return '%.1f %sB' % (value, unitname)
        else:
            return '%.0f %sB' % (value, unitname)


class Rate(Size):
    """displays rate in human-readable format"""
    def __init__(self, value, precision=2**10):
        Size.__init__(self, value, precision)

    def __str__(self, precision=None):
        return '%s/s'% Size.__str__(self, precision=None)


class Duration(long):
    """displays duration in human-readable format"""
    def __str__(value):
        if value >= 172800:
            return '%d days' % (value//86400) # 2 days or longer
        elif value >= 86400:
            return '1 day %d hours' % ((value-86400)//3600) # 1-2 days
        elif value >= 3600:
            return '%d:%02d hours' % (value//3600, (value%3600)//60) # 1 h - 1 day
        elif value >= 60:
            return '%d:%02d minutes' % (value//60, value%60) # 1 minute to 1 hour
        else:
            return '%d seconds' % int(value)


class IconButton(gtk.Button):
    def __init__(self, label, iconpath=None, stock=None):
        gtk.Button.__init__(self)

        self.hbox = gtk.HBox(spacing=5)
        
        self.icon = gtk.Image()
        if stock is not None:
            self.icon.set_from_stock(stock, gtk.ICON_SIZE_BUTTON)
        elif iconpath is not None:
            self.icon.set_from_file(iconpath)
        else:
            raise TypeError, "IconButton needs iconpath or stock"
        self.hbox.pack_start(self.icon)

        self.label = gtk.Label(label)
        self.hbox.pack_start(self.label)

        self.add(halign(self.hbox, 0.5))


class Window(gtk.Window):
    def __init__(self, *args):
        apply(gtk.Window.__init__, (self,)+args)
        self.set_icon_from_file(os.path.join(image_root,'bittorrent.ico'))


class ScrolledWindow(gtk.ScrolledWindow):
    def scroll_to_bottom(self):
        child_height = self.child.child.size_request()[1]
        new_adj = gtk.Adjustment(child_height, 0, child_height)
        self.set_vadjustment(new_adj)


class MessageDialog(gtk.MessageDialog):
    def __init__(self, parent, title, message,
                 type=gtk.MESSAGE_ERROR,
                 buttons=gtk.BUTTONS_OK,
                 yesfunc=None, nofunc=None ):
        gtk.MessageDialog.__init__(self, parent,
                                   gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                                   type, buttons, message)

        self.set_size_request(-1, -1)
        self.set_resizable(gtk.FALSE)
        self.set_title(title)
        
        self.label.set_line_wrap(gtk.TRUE)

        self.connect('response', self.callback)

        self.yesfunc = yesfunc
        self.nofunc = nofunc
        self.show_all()

    def callback(self, widget, response_id, *args):
        if ((response_id == gtk.RESPONSE_OK or
             response_id == gtk.RESPONSE_YES) and
            self.yesfunc):
            self.yesfunc()
        if ((response_id == gtk.RESPONSE_CANCEL or
             response_id == gtk.RESPONSE_NO )
            and self.nofunc):
            self.nofunc()
        self.destroy()


class HSeparatedBox(gtk.VBox):

    def pack_start(self, widget, *args, **kwargs):
        if len(self.get_children()):
            s = gtk.HSeparator()
            gtk.VBox.pack_start(self, s, *args, **kwargs)
            s.show()
        gtk.VBox.pack_start(self, widget, *args, **kwargs)

    def pack_end(self, widget, *args, **kwargs):
        if len(self.get_children()):
            s = gtk.HSeparator()
            gtk.VBox.pack_start(self, s, *args, **kwargs)
            s.show()
        gtk.VBox.pack_end(self, widget, *args, **kwargs)

    def remove(self, widget):
        children = self.get_children()
        if len(children) > 1:
            index = children.index(widget)
            if index == 0:
                sep = children[index+1]
            else:
                sep = children[index-1]
            gtk.VBox.remove(self, sep)
        gtk.VBox.remove(self, widget)
