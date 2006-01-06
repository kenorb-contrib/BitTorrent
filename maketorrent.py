#!/usr/bin/env python

# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Matt Chisholm

from __future__ import division

from BitTorrent.platform import install_translation
install_translation()

import os
import sys

assert sys.version_info >= (2, 3), _("Install Python %s or greater") % '2.3'

from threading import Event

import gtk
import gobject

from BitTorrent.GUI import *
from BitTorrent import Desktop
from BitTorrent import version
from BitTorrent import configfile
from BitTorrent.defaultargs import get_defaults
from BitTorrent.makemetafile import make_meta_files
from BitTorrent.parseargs import makeHelp
from BitTorrent.platform import btspawn
from BitTorrent.ConvertedMetainfo import set_filesystem_encoding

defaults = get_defaults('maketorrent')
defconfig = dict([(name, value) for (name, value, doc) in defaults])
del name, value, doc
ui_options = ('torrent_dir','piece_size_pow2','tracker_list','use_tracker')

def sfe_ef(e,s):
    print s
set_filesystem_encoding(defconfig['filesystem_encoding'], sfe_ef)

EXTENSION = '.torrent'

MAXIMUM_NODES = 8

class MainWindow(Window):

    def __init__(self, config):
        Window.__init__(self)
        self.mainwindow = self # temp hack to make modal win32 file choosers work
        self.tooltips = gtk.Tooltips()
        self.connect('destroy', self.quit)
        self.set_title(_("%s torrent file creator %s")%(app_name, version))
        self.set_border_width(SPACING)

        self.config = config
        self.tracker_list = []
        if self.config['tracker_list']:
            self.tracker_list = self.config['tracker_list'].split(',')

        right_column_width=276
        self.box = gtk.VBox(spacing=SPACING)

        self.box.pack_start(lalign(gtk.Label(
            _("Make torrent file for this file/directory:"))),
                            expand=False, fill=False)

        self.filebox = gtk.Entry()
        self.filebox.set_editable(False)
        self.change_button = gtk.Button(_("Choose..."))
        self.change_button.connect('clicked', self.choose_files)

        hb = gtk.HBox(spacing=SPACING)
        hb.pack_start(self.filebox, expand=True, fill=True)
        hb.pack_end(self.change_button, expand=False, fill=False)

        self.box.pack_start(hb, expand=False, fill=False, padding=0)

        self.box.pack_start(lalign(gtk.Label(
            _("(Directories will become batch torrents)"))),
                            expand=False, fill=False, padding=0)

        self.box.pack_start(gtk.HSeparator(), expand=False, fill=False, padding=0)

        self.table = gtk.Table(rows=3,columns=2,homogeneous=False)
        self.table.set_col_spacings(SPACING)
        self.table.set_row_spacings(SPACING)
        y = 0

        # Piece size
        self.table.attach(ralign(gtk.Label(_("Piece size:"))),0,1,y,y+1,
                          xoptions=gtk.FILL, yoptions=0)

        self.piece_size = gtk.combo_box_new_text()
        self.piece_size.offset = 15
        for i in range(7):
            self.piece_size.append_text(str(Size(2**(i+self.piece_size.offset))))
        self.piece_size.set_active(self.config['piece_size_pow2'] -
                                   self.piece_size.offset)

        self.piece_size_box = gtk.HBox(spacing=SPACING)
        self.piece_size_box.pack_start(self.piece_size,
                                       expand=False, fill=False)
        self.table.attach(self.piece_size_box,1,2,y,y+1,
                          xoptions=gtk.FILL|gtk.EXPAND, yoptions=0)
        y+=1


        # Announce URL / Tracker
        self.tracker_radio = gtk.RadioButton(group=None, label=_("Use _tracker:"))
        self.tracker_radio.value = True
        
        self.table.attach(self.tracker_radio,0,1,y,y+1,
                          xoptions=gtk.FILL, yoptions=0)
        self.announce_entry = gtk.Entry()
        self.announce_completion = gtk.EntryCompletion()
        self.announce_entry.set_completion(self.announce_completion)
        self.announce_completion.set_text_column(0)
        self.build_completion()

        self.tracker_radio.entry = self.announce_entry
        if self.config['use_tracker'] == self.tracker_radio.value:
            self.announce_entry.set_sensitive(True)
        else:
            self.announce_entry.set_sensitive(False)

        if self.config['tracker_name']:
            self.announce_entry.set_text(self.config['tracker_name'])
        elif len(self.tracker_list):
            self.announce_entry.set_text(self.tracker_list[0])
        else:
            self.announce_entry.set_text('http://my.tracker:6969/announce')
            
        self.announce_entry.set_size_request(right_column_width,-1)
        self.table.attach(self.announce_entry,1,2,y,y+1, xoptions=gtk.FILL|gtk.EXPAND, yoptions=0)
        y+=1

        # DHT / Trackerless
        self.dht_radio = gtk.RadioButton(group=self.tracker_radio,
                                         label=_("Use _DHT:"))
        self.dht_radio.value = False
        
        self.table.attach(align(self.dht_radio,0,0), 0,1,y,y+1,
                          xoptions=gtk.FILL|gtk.EXPAND, yoptions=0)

        self.dht_nodes_expander = gtk.Expander(_("Nodes (optional):"))
        self.dht_nodes_expander.connect('size-allocate', self.resize_to_fit)
        
        self.dht_nodes = NodeList(self, 'router.bittorrent.com:6881')
        self.dht_frame = gtk.Frame()
        self.dht_frame.add(self.dht_nodes)
        self.dht_frame.set_shadow_type(gtk.SHADOW_IN)
        self.dht_nodes_expander.add(self.dht_frame)

        self.table.attach(self.dht_nodes_expander,1,2,y,y+1, xoptions=gtk.FILL|gtk.EXPAND, yoptions=0)
        self.dht_radio.entry = self.dht_nodes

        if self.config['use_tracker'] == self.dht_radio.value:
            self.dht_nodes.set_sensitive(True)
        else:
            self.dht_nodes.set_sensitive(False)

        y+=1

        for w in self.tracker_radio.get_group():
            w.connect('toggled', self.toggle_tracker_dht)

        for w in self.tracker_radio.get_group():
            if w.value == bool(self.config['use_tracker']):
                w.set_active(True)
            else:
                w.set_active(False)

        # Hsep
        self.table.attach(gtk.HSeparator(),0,2,y,y+1,yoptions=0)
        y+=1

        # Comment
        self.comment_expander = gtk.Expander(_("Comments:"))
        self.comment_expander.connect('size-allocate', self.resize_to_fit)
        
        self.comment_buffer = gtk.TextBuffer()
        self.comment_text = gtk.TextView()
        self.comment_text.set_buffer(self.comment_buffer)
        self.comment_text.set_wrap_mode(gtk.WRAP_WORD)
        self.comment_scroll = gtk.ScrolledWindow()
        self.comment_scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self.comment_scroll.set_shadow_type(gtk.SHADOW_IN)
        self.comment_scroll.add(self.comment_text)

        self.comment_expander.add(self.comment_scroll)
        self.table.attach(self.comment_expander,0,2,y,y+1,
                          xoptions=gtk.FILL, yoptions=0)
        y+=1

        # add table
        self.box.pack_start(self.table, expand=True, fill=True, padding=0)

        # buttons

        self.buttonbox = gtk.HBox(homogeneous=True, spacing=SPACING)

        self.quitbutton = gtk.Button(stock=gtk.STOCK_CLOSE)
##=======
##        # Piece size
##        self.table.attach(ralign(gtk.Label('Piece size:')),0,1,y,y+1,
##                          xoptions=gtk.FILL, yoptions=0)


##        self.piece_size_box = gtk.HBox(spacing=SPACING)
##        self.piece_size_box.pack_start(self.piece_size, expand=False, fill=False)
##        self.table.attach(self.piece_size_box,1,2,y,y+1, xoptions=gtk.FILL|gtk.EXPAND, yoptions=0)
##        y+=1


##        self.box.pack_start(self.table, expand=True, fill=True)

##        self.buttonbox = gtk.HBox(homogeneous=True, spacing=SPACING)

##        self.quitbutton = gtk.Button(stock=gtk.STOCK_QUIT)
##>>>>>>> remote
        self.quitbutton.connect('clicked', self.quit)
        self.buttonbox.pack_start(self.quitbutton, expand=True, fill=True)

        self.buttonbox.pack_start(gtk.Label(''), expand=True, fill=True)

        self.makebutton = IconButton(_("_Make"), stock=gtk.STOCK_EXECUTE)
        self.makebutton.connect('clicked', self.make)
        self.makebutton.set_sensitive(False)
        self.buttonbox.pack_end(self.makebutton, expand=True, fill=True)

        self.box.pack_end(self.buttonbox, expand=False, fill=False)

        self.announce_entry.connect('changed', self.check_buttons)
        self.filebox.connect('changed', self.check_buttons)
        for w in self.tracker_radio.get_group():
            w.connect('clicked', self.check_buttons)

        self.box.pack_end(gtk.HSeparator(), expand=False, fill=False)

        self.add(self.box)

#        HelpWindow(None, makeHelp('maketorrent', defaults))
        
        self.box.show_all()
##        extraheight = self.dht_frame.size_request()[1] + \
##                      self.comment_scroll.size_request()[1]
##        sr = self.box.size_request()
##        self.resize(sr[0] + SPACING*2, sr[1]+extraheight + SPACING*2)
        self.resize_to_fit()
        self.show_all()

    def toggle_tracker_dht(self, widget):
        if widget.get_active():
            self.config['use_tracker'] = widget.value

        for e in [self.announce_entry, self.dht_nodes]:
            if widget.entry is e:
                e.set_sensitive(True)
            else:
                e.set_sensitive(False)

    def choose_files(self,widget):
        fn = None
        if self.config['torrent_dir']:
            fn = self.config['torrent_dir']
        else:
            fn = Desktop.desktop 

        FileOrFolderSelection(self, fullname=fn, 
                              got_multiple_location_func=self.add_files)
    
    def add_files(self, names):
        for name in names:
            self.filebox.set_text(name)
        torrent_dir = os.path.split(name)[0]
        if torrent_dir[-1] != os.sep:
            torrent_dir += os.sep
        self.config['torrent_dir'] = torrent_dir

    def get_piece_size_exponent(self):
        i = self.piece_size.get_active()
        exp = i+self.piece_size.offset
        self.config['piece_size_pow2'] = exp
        return exp

    def get_file(self):
        return self.filebox.get_text()

    def get_announce(self):
        if self.config['use_tracker']:
            announce = self.announce_entry.get_text()
            self.config['tracker_name'] = announce
        else:
            announce = self.dht_nodes.get_text()
        return announce

    def make(self, widget):
        file_name = self.get_file()
        piece_size_exponent = self.get_piece_size_exponent()
        announce = self.get_announce()
        comment = self.comment_buffer.get_text(
            *self.comment_buffer.get_bounds())
                
        if self.config['use_tracker']:
            self.add_tracker(announce) 
        errored = False
        if not errored:
            d = ProgressDialog(self, [file_name,], announce,
                               piece_size_exponent, comment)
            d.main()

    def check_buttons(self, *widgets):
        file_name = self.get_file()
        tracker = self.announce_entry.get_text()
        if file_name not in (None, ''):
            if self.config['use_tracker']:
                if len(tracker) >= len('http://x.cc'):
                    self.makebutton.set_sensitive(True)
                else:
                    self.makebutton.set_sensitive(False)
            else:
                self.makebutton.set_sensitive(True)
        else:
            self.makebutton.set_sensitive(False)

    def save_config(self):
        def error_callback(error, string): print string
        configfile.save_ui_config(self.config, 'maketorrent', ui_options, error_callback)
                
    def quit(self, widget):
        self.save_config()
        self.destroy()        

    def add_tracker(self, tracker_name):
        try:
            self.tracker_list.pop(self.tracker_list.index(tracker_name))
        except ValueError:
            pass
        self.tracker_list[0:0] = [tracker_name,]
        
        self.config['tracker_list'] = ','.join(self.tracker_list)
        self.build_completion()

    def build_completion(self):
        liststore = gtk.ListStore(gobject.TYPE_STRING)
        for t in self.tracker_list:
            liststore.append([t])
        self.announce_completion.set_model(liststore)

    def resize_to_fit(self, *args):
        garbage, y = self.size_request()
        x, garbage = self.get_size()
        gobject.idle_add(self.resize, x, y)


class AppWindow(MainWindow):
    def quit(self, widget):
        MainWindow.quit(self, widget)
        gtk.main_quit()


class NodeList(gtk.TreeView):
    def __init__(self, parent, nodelist):
        self.store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        pre_size_list = ['router.bittorrent.com', '65536']
        self.store.append(pre_size_list)

        gtk.TreeView.__init__(self, self.store)
        self.set_enable_search(False)

        self.host_render = gtk.CellRendererText()
        self.host_render.set_property('editable', True)
        self.host_column = gtk.TreeViewColumn(_("_Host"), self.host_render,
                                              text=0)
        self.append_column(self.host_column)
        self.host_render.connect('edited', self.store_host_value)

        self.port_render = gtk.CellRendererText()
        self.port_render.set_property('editable', True)
        self.port_column = gtk.TreeViewColumn(_("_Port"), self.port_render,
                                              text=1)
        self.append_column(self.port_column)
        self.port_render.connect('edited', self.store_port_value)

        #self.columns_autosize()
        #self.host_column.set_fixed_width(self.host_column.get_width())
        #self.host_column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        #self.realize()
        #self.port_column.set_fixed_width(self.port_column.get_width())
        #self.port_column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)

        self.store.clear()
        
        for i, e in enumerate(nodelist.split(',')):
            host, port = e.split(':')
            self.store.append((host, port))

        if i < MAXIMUM_NODES - 1:
            self.store.append(('',''))

    def store_host_value(self, cell, row, value):
        parts = value.split('.')
        if value != '':
            for p in parts:
                if not p.isalnum():
                    return
                try:
                    value = value.encode('idna')
                except UnicodeError:
                    return
        it = self.store.get_iter_from_string(row)
        self.store.set(it, 0, str(value))
        self.check_row(row)

    def store_port_value(self, cell, row, value):
        if value != '':
            try:
                v = int(value)
                if v > 65535:
                    value = 65535
                if v < 0:
                    value = 0
            except:
                return # return on non-integer values
        it = self.store.get_iter_from_string(row)
        self.store.set(it, 1, str(value))
        #curs = self.get_cursor()
        #print curs
        #print type(curs[0][0])

        self.check_row(row)
        #newpath = ((int(row)+1,), self.port_column)
        #print newpath
        #self.set_cursor(newpath)

    def check_row(self, row):
        # called after editing to see whether we should add a new
        # blank row, or remove the now blank currently edited row.
        it = self.store.get_iter_from_string(row)
        host_value = self.store.get_value(it, 0)
        port_value = self.store.get_value(it, 1)
        if host_value and port_value         and \
               int(row) == len(self.store)-1 and \
               int(row) < MAXIMUM_NODES   -1 :
            self.store.append(('',''))
        elif host_value == '' and \
             port_value == '' and \
             int(row) != len(self.store)-1:
            self.store.remove(it)            

    def get_nodes(self):
        retlist = []
        it = self.store.get_iter_first()
        while it:
            host = self.store.get_value(it, 0)
            port = self.store.get_value(it, 1)
            if host != '' and port != '':
                retlist.append((host,port))
            it = self.store.iter_next(it)
        return retlist
        
    def get_text(self):
        nodelist = self.get_nodes()
        return ','.join(['%s:%s'%node for node in nodelist])


class ProgressDialog(gtk.Dialog):

    def __init__(self, parent, file_list, announce, piece_length, comment):
        gtk.Dialog.__init__(self, parent=parent, flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT)
        self.set_size_request(400,-1)
        self.set_border_width(SPACING)
        self.set_title(_("Building torrents..."))
        self.file_list = file_list
        self.announce = announce
        self.piece_length = piece_length
        self.comment = comment

        self.flag = Event() # ???

        self.label = gtk.Label(_("Checking file sizes..."))
        self.label.set_line_wrap(True)

        self.vbox.set_spacing(SPACING)
        self.vbox.pack_start(lalign(self.label), expand=False, fill=False)

        self.progressbar = gtk.ProgressBar()
        self.vbox.pack_start(self.progressbar, expand=False, fill=False)

        self.cancelbutton = gtk.Button(stock=gtk.STOCK_CANCEL)
        self.cancelbutton.connect('clicked', self.cancel)
        self.action_area.pack_end(self.cancelbutton)

        self.show_all()

        self.done_button = gtk.Button(stock=gtk.STOCK_OK)
        self.done_button.connect('clicked', self.cancel)

        self.seed_button = gtk.Button(_("Start seeding"))
        self.seed_button.connect('clicked', self.seed)

    def main(self):
        self.complete()

    def seed(self, widget=None):
        for f in self.file_list:
            btspawn(None, 'bittorrent', f+EXTENSION, '--save_as', f)
        self.cancel()

    def cancel(self, widget=None):
        self.flag.set()
        self.destroy()

    def set_progress_value(self, value):
        self.progressbar.set_fraction(value)
        self._update_gui()

    def set_file(self, filename):
        self.label.set_text(_("building ") + filename + EXTENSION)
        self._update_gui()

    def _update_gui(self):
        while gtk.events_pending():
            gtk.main_iteration(block=False)

    def complete(self):
        try:
            make_meta_files(self.announce, 
                            self.file_list,
                            flag=self.flag,
                            progressfunc=self.set_progress_value,
                            filefunc=self.set_file,
                            piece_len_pow2=self.piece_length,
                            comment=self.comment, 
                            use_tracker=config['use_tracker'],
                            data_dir=config['data_dir'],
                            )
            if not self.flag.isSet():
                self.set_title(_("Done."))
                self.label.set_text(_("Done building torrents."))
                self.set_progress_value(1)
                self.action_area.remove(self.cancelbutton)
                self.action_area.pack_start(self.seed_button)
                self.action_area.pack_start(self.done_button)
                self.seed_button.show()
                self.done_button.show()
        except (OSError, IOError), e:
            self.set_title(_("Error!"))
            self.label.set_text(_("Error building torrents: ") + str(e))


    

def run():
    config, args = configfile.parse_configuration_and_args(defaults,
                                    'maketorrent', [], 0, None)
    MainWindow(config)


if __name__ == '__main__':
    config, args = configfile.parse_configuration_and_args(defaults,
                                    'maketorrent', sys.argv[1:], 0, None)
    AppWindow(config)
    try:
        gtk.main()
    except KeyboardInterrupt:
        # gtk.mainloop not running
        # exit and don't save config options
        sys.exit(1)
