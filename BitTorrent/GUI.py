# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
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
import os
import threading

assert gtk.gtk_version   >= (2, 6), _(  "GTK %s or newer required") % '2.6'
assert gtk.pygtk_version >= (2, 6), _("PyGTK %s or newer required") % '2.6'

from BitTorrent import app_name, FAQ_URL, languages, language_names
from BitTorrent.platform import image_root, read_language_file, write_language_file

def lock_wrap(function, *args):
    gtk.threads_enter()
    function(*args)
    gtk.threads_leave()

def gtk_wrap(function, *args):
    gobject.idle_add(lock_wrap, function, *args)

SPACING = 8
WINDOW_TITLE_LENGTH = 128 # do we need this?
WINDOW_WIDTH = 600

# get screen size from GTK
d = gtk.gdk.display_get_default()
s = d.get_default_screen()
MAX_WINDOW_HEIGHT = s.get_height()
MAX_WINDOW_WIDTH  = s.get_width()
if os.name == 'nt':
    MAX_WINDOW_HEIGHT -= 32 # leave room for start bar (exact)
    MAX_WINDOW_HEIGHT -= 32 # and window decorations (depends on windows theme)
else:
    MAX_WINDOW_HEIGHT -= 32 # leave room for window decorations (could be any size)
    

MIN_MULTI_PANE_HEIGHT = 107

BT_TARGET_TYPE = 0
EXTERNAL_FILE_TYPE = 1
EXTERNAL_STRING_TYPE = 2

BT_TARGET              = ("application/x-bittorrent" , gtk.TARGET_SAME_APP, BT_TARGET_TYPE      )
EXTERNAL_FILE          = ("text/uri-list"            , 0                  , EXTERNAL_FILE_TYPE  )

#gtk(gdk actually) is totally unable to receive text drags
#of any sort in windows because they're too lazy to use OLE.
#this list is all the atoms I could possibly find so that
#url dnd works on linux from any browser.
EXTERNAL_TEXTPLAIN     = ("text/plain"               , 0                  , EXTERNAL_STRING_TYPE)
EXTERNAL_TEXT          = ("TEXT"                     , 0                  , EXTERNAL_STRING_TYPE)
EXTERNAL_COMPOUND_TEXT = ("COMPOUND_TEXT"            , 0                  , EXTERNAL_STRING_TYPE)
EXTERNAL_MOZILLA       = ("text/x-moz-url"           , 0                  , EXTERNAL_STRING_TYPE)
EXTERNAL_NETSCAPE      = ("_NETSCAPE_URL"            , 0                  , EXTERNAL_STRING_TYPE)
EXTERNAL_HTML          = ("text/html"                , 0                  , EXTERNAL_STRING_TYPE)
EXTERNAL_UNICODE       = ("text/unicode"             , 0                  , EXTERNAL_STRING_TYPE)
EXTERNAL_UTF8          = ("text/plain;charset=utf-8" , 0                  , EXTERNAL_STRING_TYPE)
EXTERNAL_UTF8_STRING   = ("UTF8_STRING"              , 0                  , EXTERNAL_STRING_TYPE)
EXTERNAL_STRING        = ("STRING"                   , 0                  , EXTERNAL_STRING_TYPE)
EXTERNAL_OLE2_DND      = ("OLE2_DND"                 , 0                  , EXTERNAL_STRING_TYPE)
EXTERNAL_RTF           = ("Rich Text Format"         , 0                  , EXTERNAL_STRING_TYPE)
#there should alse be text/plain;charset={current charset}

TARGET_EXTERNAL = [EXTERNAL_FILE,
                   EXTERNAL_TEXTPLAIN,
                   EXTERNAL_TEXT,
                   EXTERNAL_COMPOUND_TEXT,
                   EXTERNAL_MOZILLA,
                   EXTERNAL_NETSCAPE,
                   EXTERNAL_HTML,
                   EXTERNAL_UNICODE,
                   EXTERNAL_UTF8,
                   EXTERNAL_UTF8_STRING,
                   EXTERNAL_STRING,
                   EXTERNAL_OLE2_DND,
                   EXTERNAL_RTF]

TARGET_ALL = [BT_TARGET,
              EXTERNAL_FILE,
              EXTERNAL_TEXTPLAIN,
              EXTERNAL_TEXT,
              EXTERNAL_COMPOUND_TEXT,
              EXTERNAL_MOZILLA,
              EXTERNAL_NETSCAPE,
              EXTERNAL_HTML,
              EXTERNAL_UNICODE,
              EXTERNAL_UTF8,
              EXTERNAL_UTF8_STRING,
              EXTERNAL_STRING,
              EXTERNAL_OLE2_DND,
              EXTERNAL_RTF]

# a slightly hackish but very reliable way to get OS scrollbar width
sw = gtk.ScrolledWindow()
SCROLLBAR_WIDTH = sw.size_request()[0] - 48
del sw

def align(obj,x,y):
    if type(obj) is gtk.Label:
        obj.set_alignment(x,y)
        return obj
    else:
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

def malign(obj):
    return valign(obj, 0.5)

factory = gtk.IconFactory()

# these don't seem to be documented anywhere:
# ICON_SIZE_BUTTON        = 20x20
# ICON_SIZE_LARGE_TOOLBAR = 24x24

for n in 'abort broken finished info pause paused play queued running remove status-running status-starting status-pre-natted status-natted status-stopped status-broken'.split():
    fn = os.path.join(image_root, 'icons', 'default', ('%s.png'%n))
    if os.access(fn, os.F_OK):
        pixbuf = gtk.gdk.pixbuf_new_from_file(fn)
        set = gtk.IconSet(pixbuf)
        factory.add('bt-%s'%n, set)
    # maybe we should load a default icon if none exists 
    
factory.add_default()

def get_logo(size=32):
    fn = os.path.join(image_root, 'logo', 'bittorrent_%d.png'%size)
    logo = gtk.Image()
    logo.set_from_file(fn)
    return logo

class Size(long):
    """displays size in human-readable format"""
    __slots__ = []
    size_labels = ['','K','M','G','T','P','E','Z','Y']    
    radix = 2**10
    def __new__(cls, value):
        self = long.__new__(cls, value)
        return self

    def __init__(self, value):
        long.__init__(self, value)

    def __str__(self, precision=None):
        if precision is None:
            precision = 0
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
    __slots__ = []
    def __init__(self, value):
        Size.__init__(self, value)

    def __str__(self, precision=2**10):
        return '%s/s'% Size.__str__(self, precision=precision)


class Duration(float):
    """displays duration in human-readable format"""
    __slots__ = []
    def __str__(self):
        if self > 365 * 24 * 60 * 60:
            return '?'
        elif self >= 172800:
            return _("%d days") % (self//86400) # 2 days or longer
        elif self >= 86400:
            return _("1 day %d hours") % ((self-86400)//3600) # 1-2 days
        elif self >= 3600:
            return _("%d:%02d hours") % (self//3600, (self%3600)//60) # 1 h - 1 day
        elif self >= 60:
            return _("%d:%02d minutes") % (self//60, self%60) # 1 minute to 1 hour
        elif self >= 0:
            return _("%d seconds") % int(self)
        else:
            return _("0 seconds")


class FancyLabel(gtk.Label):
    def __init__(self, label_string, *values):
        self.label_string = label_string
        gtk.Label.__init__(self, label_string%values)

    def set_value(self, *values):
        self.set_text(self.label_string%values)


class IconButton(gtk.Button):
    def __init__(self, label, iconpath=None, stock=None):
        gtk.Button.__init__(self, label)
        
        self.icon = gtk.Image()
        if stock is not None:
            self.icon.set_from_stock(stock, gtk.ICON_SIZE_BUTTON)
        elif iconpath is not None:
            self.icon.set_from_file(iconpath)
        else:
            raise TypeError, 'IconButton needs iconpath or stock'
        self.set_image(self.icon)


class LanguageChooser(gtk.Frame):
    def __init__(self):
        gtk.Frame.__init__(self, "Translate %s into:" % app_name)
        self.set_border_width(SPACING)
        
        model = gtk.ListStore(*[gobject.TYPE_STRING] * 2)
        default = model.append(("System default", ''))

        lang = read_language_file()
        for l in languages:
            it = model.append((language_names[l].encode('utf8'), l))
            if l == lang:
                default = it

        self.combo = gtk.ComboBox(model)
        cell = gtk.CellRendererText()
        self.combo.pack_start(cell, True)
        self.combo.add_attribute(cell, 'text', 0)

        if default is not None:
            self.combo.set_active_iter(default)

        self.combo.connect('changed', self.changed)
        box = gtk.VBox(spacing=SPACING)
        box.set_border_width(SPACING)
        box.pack_start(self.combo, expand=False, fill=False)
        l = gtk.Label("You must restart %s for the\nlanguage "
                      "setting to take effect." % app_name)
        l.set_alignment(0,1)
        l.set_line_wrap(True)
        box.pack_start(l, expand=False, fill=False)
        self.add(box)

    def changed(self, *a):
        it = self.combo.get_active_iter()
        model = self.combo.get_model()
        code = model.get(it, 1)[0]
        write_language_file(code)

class IconMixin(object):
    def __init__(self):
        iconname = os.path.join(image_root,'bittorrent.ico')
        icon16 = gtk.gdk.pixbuf_new_from_file_at_size(iconname, 16, 16)
        icon32 = gtk.gdk.pixbuf_new_from_file_at_size(iconname, 32, 32)
        self.set_icon_list(icon16, icon32)
        
class Window(IconMixin, gtk.Window):
    def __init__(self, *args):
        gtk.Window.__init__(self, *args)
        IconMixin.__init__(self)

class HelpWindow(Window):
    def __init__(self, main, helptext):
        Window.__init__(self)
        self.set_title(_("%s Help")%app_name)
        self.main = main
        self.set_border_width(SPACING)

        self.vbox = gtk.VBox(spacing=SPACING)
        
        self.faq_box = gtk.HBox(spacing=SPACING)
        self.faq_box.pack_start(gtk.Label(_("Frequently Asked Questions:")), expand=False, fill=False)
        self.faq_url = gtk.Entry()
        self.faq_url.set_text(FAQ_URL)
        self.faq_url.set_editable(False)
        self.faq_box.pack_start(self.faq_url, expand=True, fill=True)
        self.faq_button = gtk.Button(_("Go"))
        self.faq_button.connect('clicked', lambda w: self.main.visit_url(FAQ_URL) )
        self.faq_box.pack_start(self.faq_button, expand=False, fill=False)
        self.vbox.pack_start(self.faq_box, expand=False, fill=False)

        self.cmdline_args = gtk.Label(helptext)

        self.cmdline_sw = ScrolledWindow()
        self.cmdline_sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self.cmdline_sw.add_with_viewport(self.cmdline_args)

        self.cmdline_sw.set_size_request(self.cmdline_args.size_request()[0]+SCROLLBAR_WIDTH, 200)

        self.vbox.pack_start(self.cmdline_sw)
        
        self.add(self.vbox)

        self.show_all()
        
        if self.main is not None:
            self.connect('destroy', lambda w: self.main.window_closed('help'))
        else:
            self.connect('destroy', lambda w: gtk.main_quit())
            gtk.main()
                        


    def close(self, widget=None):
        self.destroy()    


class ScrolledWindow(gtk.ScrolledWindow):
    def scroll_to_bottom(self):
        child_height = self.child.child.size_request()[1]
        self.scroll_to(0, child_height)
        
    def scroll_by(self, dx=0, dy=0):
        v = self.get_vadjustment()
        new_y = min(v.upper, v.value + dy)
        self.scroll_to(0, new_y)

    def scroll_to(self, x=0, y=0):
        v = self.get_vadjustment()
        child_height = self.child.child.size_request()[1]
        new_adj = gtk.Adjustment(y, 0, child_height)
        self.set_vadjustment(new_adj)


class AutoScrollingWindow(ScrolledWindow):
    def __init__(self):
        ScrolledWindow.__init__(self)
        self.drag_dest_set(gtk.DEST_DEFAULT_MOTION |
                           gtk.DEST_DEFAULT_DROP,
                           TARGET_ALL,
                           gtk.gdk.ACTION_MOVE|gtk.gdk.ACTION_COPY)
        self.connect('drag_motion'       , self.drag_motion       )
#        self.connect('drag_data_received', self.drag_data_received)
        self.vscrolltimeout = None

#    def drag_data_received(self, widget, context, x, y, selection, targetType, time):
#        print _("AutoScrollingWindow.drag_data_received("), widget

    def drag_motion(self, widget, context, x, y, time):
        v = self.get_vadjustment()
        if v.page_size - y <= 10:
            amount = (10 - int(v.page_size - y)) * 2
            self.start_scrolling(amount)
        elif y <= 10:
            amount = (y - 10) * 2
            self.start_scrolling(amount)
        else:
            self.stop_scrolling()
        return True

    def scroll_and_wait(self, amount, lock_held):
        if not lock_held:
            gtk.threads_enter()
        self.scroll_by(0, amount)
        if not lock_held:
            gtk.threads_leave()
        if self.vscrolltimeout is not None:
            gobject.source_remove(self.vscrolltimeout)
        self.vscrolltimeout = gobject.timeout_add(100, self.scroll_and_wait, amount, False)
        #print "adding timeout", self.vscrolltimeout, amount

    def start_scrolling(self, amount):
        if self.vscrolltimeout is not None:
            gobject.source_remove(self.vscrolltimeout)            
        self.scroll_and_wait(amount, True)
        
    def stop_scrolling(self):
        if self.vscrolltimeout is not None:
            #print "removing timeout", self.vscrolltimeout
            gobject.source_remove(self.vscrolltimeout)
            self.vscrolltimeout = None

class MessageDialog(IconMixin, gtk.MessageDialog):
    flags = gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT
    
    def __init__(self, parent, title, message,
                 type=gtk.MESSAGE_ERROR,
                 buttons=gtk.BUTTONS_OK,
                 yesfunc=None, nofunc=None,
                 default=gtk.RESPONSE_OK
                 ):
        gtk.MessageDialog.__init__(self, parent,
                                   self.flags,
                                   type, buttons, message)
        IconMixin.__init__(self)

        self.set_size_request(-1, -1)
        self.set_resizable(False)
        self.set_title(title)
        if default is not None:
            self.set_default_response(default)
        
        self.label.set_line_wrap(True)

        self.connect('response', self.callback)

        self.yesfunc = yesfunc
        self.nofunc = nofunc
        if os.name == 'nt':
            parent.present()
        self.show_all()

    def callback(self, widget, response_id, *args):
        if ((response_id == gtk.RESPONSE_OK or
             response_id == gtk.RESPONSE_YES) and
            self.yesfunc is not None):
            self.yesfunc()
        if ((response_id == gtk.RESPONSE_CANCEL or
             response_id == gtk.RESPONSE_NO )
            and self.nofunc is not None):
            self.nofunc()
        self.destroy()

class ErrorMessageDialog(MessageDialog):
    flags = gtk.DIALOG_DESTROY_WITH_PARENT


class FileSelection(IconMixin, gtk.FileChooserDialog):

    def __init__(self, action, main, title='', fullname='',
                 got_location_func=None, no_location_func=None,
                 got_multiple_location_func=None, show=True):
        gtk.FileChooserDialog.__init__(self, action=action, title=title,
                     buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                              gtk.STOCK_OK, gtk.RESPONSE_OK))
        IconMixin.__init__(self)
        from BitTorrent.ConvertedMetainfo import filesystem_encoding
        self.fsenc = filesystem_encoding
        try:
            fullname.decode('utf8')
        except:
            fullname = fullname.decode(self.fsenc)
        self.set_default_response(gtk.RESPONSE_OK)
        if action == gtk.FILE_CHOOSER_ACTION_CREATE_FOLDER:
            self.convert_button_box = gtk.HBox()
            self.convert_button = gtk.Button(_("Choose an existing folder..."))
            self.convert_button.connect('clicked', self.change_action)
            self.convert_button_box.pack_end(self.convert_button,
                                             expand=False,
                                             fill=False)
            self.convert_button_box.show_all()
            self.set_extra_widget(self.convert_button_box)
        elif action == gtk.FILE_CHOOSER_ACTION_OPEN:
            self.all_filter = gtk.FileFilter()
            self.all_filter.add_pattern('*')
            self.all_filter.set_name(_("All Files"))
            self.add_filter(self.all_filter)
            self.torrent_filter = gtk.FileFilter()
            self.torrent_filter.add_pattern('*.torrent')
            self.torrent_filter.add_mime_type('application/x-bittorrent')
            self.torrent_filter.set_name(_("Torrents"))
            self.add_filter(self.torrent_filter)
            self.set_filter(self.torrent_filter)

        self.main = main
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        if fullname:
            if action == gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER:
                self.set_filename(fullname)
            elif action == gtk.FILE_CHOOSER_ACTION_OPEN:
                if fullname[-1] != os.sep:
                    fullname = fullname + os.sep
                path, filename = os.path.split(fullname)
                self.set_current_folder(path)
            else:
                if fullname[-1] == os.sep:
                    fullname = fullname[:-1]
                path, filename = os.path.split(fullname)
                if gtk.gtk_version < (2,8):
                    path = path.encode(self.fsenc)
                self.set_current_folder(path)
                self.set_current_name(filename)
        if got_multiple_location_func is not None:
            self.got_multiple_location_func = got_multiple_location_func
            self.set_select_multiple(True)
        self.got_location_func = got_location_func
        self.no_location_func = no_location_func
        self.connect('response', self.got_response)
        self.d_handle = self.connect('destroy', self.got_response,
                                     gtk.RESPONSE_CANCEL)
        if show:
            self.show()

    def change_action(self, widget):
        if self.get_action() == gtk.FILE_CHOOSER_ACTION_CREATE_FOLDER:
            self.convert_button.set_label(_("Create a new folder..."))
            self.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
        elif self.get_action() == gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER:
            self.convert_button.set_label(_("Choose an existing folder..."))
            self.set_action(gtk.FILE_CHOOSER_ACTION_CREATE_FOLDER)

    def got_response(self, widget, response):
        if response == gtk.RESPONSE_OK:
            if self.get_select_multiple():
                if self.got_multiple_location_func is not None:
                    self.got_multiple_location_func(self.get_filenames())
            elif self.got_location_func is not None:
                fn = self.get_filename()
                if fn:
                    self.got_location_func(fn)
                else:
                    self.no_location_func()
        else:
            if self.no_location_func is not None:
                self.no_location_func()
        self.disconnect(self.d_handle)
        self.destroy()

    def done(self, widget=None):
        if self.get_select_multiple():
            self.got_multiple_location()
        else:
            self.got_location()
        self.disconnect(self.d_handle)
        self.destroy()

    def close_child_windows(self):
        self.destroy()

    def close(self, widget=None):
        self.destroy()


class OpenFileSelection(FileSelection):

    def __init__(self, *args, **kwargs):
        FileSelection.__init__(self, gtk.FILE_CHOOSER_ACTION_OPEN, *args,
                               **kwargs)


class SaveFileSelection(FileSelection):

    def __init__(self, *args, **kwargs):
        FileSelection.__init__(self, gtk.FILE_CHOOSER_ACTION_SAVE, *args,
                               **kwargs)


class ChooseFolderSelection(FileSelection):

    def __init__(self, *args, **kwargs):
        FileSelection.__init__(self, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                               *args, **kwargs)

class CreateFolderSelection(FileSelection):

    def __init__(self, *args, **kwargs):
        FileSelection.__init__(self, gtk.FILE_CHOOSER_ACTION_CREATE_FOLDER,
                               *args, **kwargs)


class FileOrFolderSelection(FileSelection):
    def __init__(self, *args, **kwargs):
        FileSelection.__init__(self, gtk.FILE_CHOOSER_ACTION_OPEN, *args,
                               **kwargs)
        self.select_file   = _("Select a file"  )
        self.select_folder = _("Select a folder")
        self.convert_button_box = gtk.HBox()
        self.convert_button = gtk.Button(self.select_folder)
        self.convert_button.connect('clicked', self.change_action)
        self.convert_button_box.pack_end(self.convert_button,
                                         expand=False,
                                         fill=False)
        self.convert_button_box.show_all()
        self.set_extra_widget(self.convert_button_box)
        self.reset_by_action()
        self.set_filter(self.all_filter)


    def change_action(self, widget):
        if self.get_action() == gtk.FILE_CHOOSER_ACTION_OPEN:
            self.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
        elif self.get_action() == gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER:
            self.set_action(gtk.FILE_CHOOSER_ACTION_OPEN)
        self.reset_by_action()

    def reset_by_action(self):
        if self.get_action() == gtk.FILE_CHOOSER_ACTION_OPEN:
            self.convert_button.set_label(self.select_folder)
            self.set_title(self.select_file)
        elif self.get_action() == gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER:
            self.convert_button.set_label(self.select_file)
            self.set_title(self.select_folder)

    def set_title(self, title):
        mytitle = title + ':'
        FileSelection.set_title(self, mytitle)


class PaddedHSeparator(gtk.VBox):
    def __init__(self, spacing=SPACING):
        gtk.VBox.__init__(self)
        self.sep = gtk.HSeparator()
        self.pack_start(self.sep, expand=False, fill=False, padding=spacing)
        self.show_all()
        

class HSeparatedBox(gtk.VBox):

    def new_separator(self):
        return PaddedHSeparator()

    def _get_children(self):
        return gtk.VBox.get_children(self)

    def get_children(self):
        return self._get_children()[0::2]

    def _reorder_child(self, child, index):
        gtk.VBox.reorder_child(self, child, index)

    def reorder_child(self, child, index):
        children = self._get_children()
        oldindex = children.index(child)
        sep = None
        if oldindex == len(children) - 1:
            sep = children[oldindex-1]
        else:
            sep = children[oldindex+1]

        newindex = index*2
        if newindex == len(children) -1:
            self._reorder_child(sep, newindex-1)
            self._reorder_child(child, newindex)
        else:
            self._reorder_child(child, newindex)
            self._reorder_child(sep, newindex+1)

    def pack_start(self, widget, *args, **kwargs):
        if len(self._get_children()):
            s = self.new_separator()
            gtk.VBox.pack_start(self, s, *args, **kwargs)
            s.show()
        gtk.VBox.pack_start(self, widget, *args, **kwargs)

    def pack_end(self, widget, *args, **kwargs):
        if len(self._get_children()):
            s = self.new_separator()
            gtk.VBox.pack_start(self, s, *args, **kwargs)
            s.show()
        gtk.VBox.pack_end(self, widget, *args, **kwargs)

    def remove(self, widget):
        children = self._get_children()
        if len(children) > 1:
            index = children.index(widget)
            if index == 0:
                sep = children[index+1]
            else:
                sep = children[index-1]
            sep.destroy()
        gtk.VBox.remove(self, widget)
