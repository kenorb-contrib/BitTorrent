#!/usr/bin/env python

# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Matt Chisholm

from __future__ import division

import os
import sys

assert sys.version_info >= (2, 3), "Install Python 2.3 or greater"

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

defaults = get_defaults('btmaketorrentgui')
defconfig = dict([(name, value) for (name, value, doc) in defaults])
del name, value, doc


class MainWindow(Window):

    def __init__(self, config):
        Window.__init__(self)
        self.mainwindow = self # temp hack to make modal win32 file choosers work
        self.connect('destroy', self.quit)
        self.set_title('%s metafile creator %s'%(app_name, version))
        self.set_border_width(SPACING)

        self.config = config

        right_column_width=276
        self.box = gtk.VBox(spacing=SPACING)

        self.table = gtk.Table(rows=3,columns=2,homogeneous=False)
        self.table.set_col_spacings(SPACING)
        self.table.set_row_spacings(SPACING)
        y = 0

        # file list
        self.table.attach(lalign(gtk.Label('Make .torrent metafiles for these files:')),
                          0,2,y,y+1, xoptions=gtk.FILL, yoptions=gtk.FILL, )
        y+=1

        self.file_store = gtk.ListStore(gobject.TYPE_STRING)

        for i in range(8): self.file_store.append(('foo',))

        self.file_scroll = gtk.ScrolledWindow()
        self.file_scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self.file_scroll.set_shadow_type(gtk.SHADOW_OUT)

        self.file_list = gtk.TreeView(self.file_store)
        r = gtk.CellRendererText()
        column = gtk.TreeViewColumn('_Files', r, text=0)
        self.file_list.append_column(column)
        self.file_list.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

        file_list_height = self.file_list.size_request()[1] + SCROLLBAR_WIDTH
        self.file_store.clear()

        self.file_scroll.set_size_request(-1, file_list_height)
        self.file_scroll.add(self.file_list)
        self.table.attach(self.file_scroll,0,2,y,y+1,yoptions=gtk.EXPAND|gtk.FILL)
        y+=1

        self.file_list_button_box = gtk.HBox(homogeneous=True,spacing=SPACING)

        self.add_button = gtk.Button(stock=gtk.STOCK_ADD)
        self.add_button.connect('clicked', self.choose_files)
        self.file_list_button_box.pack_start(self.add_button)
        self.remove_button = gtk.Button(stock=gtk.STOCK_REMOVE)
        self.remove_button.connect('clicked', self.remove_selection)
        self.remove_button.set_sensitive(False)
        self.file_list_button_box.pack_start(self.remove_button)
        self.clear_button = gtk.Button(stock=gtk.STOCK_CLEAR)
        self.clear_button.connect('clicked', self.clear_file_list)
        self.clear_button.set_sensitive(False)
        self.file_list_button_box.pack_start(self.clear_button)
        self.table.attach(self.file_list_button_box,0,2,y,y+1,
                          xoptions=gtk.FILL, yoptions=0)
        y+=1

        # Announce
        self.table.attach(ralign(gtk.Label('Announce URL:')),0,1,y,y+1,
                          xoptions=gtk.FILL, yoptions=0)
        self.announce_entry = gtk.Entry()
        self.announce_entry.set_text(self.config['tracker_name'])
        self.announce_entry.set_size_request(right_column_width,-1)
        self.table.attach(self.announce_entry,1,2,y,y+1, xoptions=gtk.FILL|gtk.EXPAND, yoptions=0)
        y+=1

        # Piece size
        self.table.attach(ralign(gtk.Label('Piece size:')),0,1,y,y+1,
                          xoptions=gtk.FILL, yoptions=0)
        self.piece_size = gtk.combo_box_new_text()
        self.piece_size.offset = 15
        for i in range(7):
            self.piece_size.append_text(str(Size(2**(i+self.piece_size.offset))))
        self.piece_size.set_active(self.config['piece_size_pow2'] -
                                   self.piece_size.offset)
        self.piece_size_box = gtk.HBox(spacing=SPACING)
        self.piece_size_box.pack_start(self.piece_size, expand=False, fill=False)
        self.table.attach(self.piece_size_box,1,2,y,y+1, xoptions=gtk.FILL|gtk.EXPAND, yoptions=0)
        y+=1


        self.box.pack_start(self.table, expand=True, fill=True)

        self.buttonbox = gtk.HBox(homogeneous=True, spacing=SPACING)

        self.quitbutton = gtk.Button(stock=gtk.STOCK_QUIT)
        self.quitbutton.connect('clicked', self.quit)
        self.buttonbox.pack_start(self.quitbutton, expand=True, fill=True)

        self.buttonbox.pack_start(gtk.Label(''), expand=True, fill=True)

        self.makebutton = IconButton('Make', stock=gtk.STOCK_EXECUTE)
        self.makebutton.connect('clicked', self.make)
        self.makebutton.set_sensitive(False)
        self.buttonbox.pack_end(self.makebutton, expand=True, fill=True)

        self.box.pack_end(self.buttonbox, expand=False, fill=False)

        self.announce_entry.connect('changed', self.check_buttons)
        self.file_store.connect('row-changed', self.check_buttons)
        sel = self.file_list.get_selection()
        sel.connect('changed', self.check_buttons)

        self.add(self.box)

#        HelpWindow(None, makeHelp('btmaketorrentgui', defaults))
        
        self.show_all()

    def remove_selection(self,widget):
        sel = self.file_list.get_selection()
        list_store, rows = sel.get_selected_rows()
        rows.reverse()
        for row in rows:
            list_store.remove(list_store.get_iter(row))

    def clear_file_list(self,widget):
        self.file_store.clear()
        self.check_buttons()

    def choose_files(self,widget):
        fn = None
        if self.config['torrent_dir']:
            fn = self.config['torrent_dir']
        else:
            fn = Desktop.desktop 

        selector = FileOrFolderSelection(self, fullname=fn, 
                       got_multiple_location_func=self.add_files)
    
    def add_files(self, names):
        for name in names:
            self.file_store.append((name,))
        torrent_dir = os.path.split(name)[0]
        if torrent_dir[-1] != os.sep:
            torrent_dir += os.sep
        self.config['torrent_dir'] = torrent_dir

    def get_piece_size_exponent(self):
        i = self.piece_size.get_active()
        exp = i+self.piece_size.offset
        self.config['piece_size_pow2'] = exp
        return exp

    def get_file_list(self):
        it = self.file_store.get_iter_first()
        files = []
        while it is not None:
            files.append(self.file_store.get_value(it, 0))
            it = self.file_store.iter_next(it)
        return files

    def get_announce_url(self):
        announce_url = self.announce_entry.get_text()
        self.config['tracker_name'] = announce_url
        return announce_url

    def make(self, widget):
        file_list = self.get_file_list()
        piece_size_exponent = self.get_piece_size_exponent()
        announce_url = self.get_announce_url()
        errored = False
        if not errored:
            d = ProgressDialog(self, file_list, announce_url, piece_size_exponent)
            d.main()

    def check_buttons(self, *widgets):
        file_list = self.get_file_list()
        announce_url = self.get_announce_url()

        if len(file_list) >= 1:
            self.clear_button.set_sensitive(True)
            sel = self.file_list.get_selection()
            list_store, rows = sel.get_selected_rows()
            if len(rows):
                self.remove_button.set_sensitive(True)
            else:
                self.remove_button.set_sensitive(False)
            if len(announce_url) >= len('http://x.cc'):
                self.makebutton.set_sensitive(True)
            else:
                self.makebutton.set_sensitive(False)
        else:
            self.clear_button.set_sensitive(False)
            self.remove_button.set_sensitive(False)
            self.makebutton.set_sensitive(False)

    def quit(self, widget):
        gtk.main_quit()


class ProgressDialog(gtk.Dialog):

    def __init__(self, parent, file_list, announce_url, piece_length):
        gtk.Dialog.__init__(self, parent=parent, flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT)
        self.set_size_request(400,-1)
        self.set_border_width(SPACING)
        self.set_title('Building torrents...')
        self.file_list = file_list
        self.announce_url = announce_url
        self.piece_length = piece_length
        self.flag = Event() # ???

        self.label = gtk.Label('Checking file sizes...')
        self.label.set_line_wrap(gtk.TRUE)

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

    def main(self):
        self.complete()

    def cancel(self, widget=None):
        self.flag.set()
        self.destroy()

    def set_progress_value(self, value):
        self.progressbar.set_fraction(value)
        self._update_gui()

    def set_file(self, filename):
        self.label.set_text('building ' + filename + '.torrent')
        self._update_gui()

    def _update_gui(self):
        while gtk.events_pending():
            gtk.main_iteration(block=False)

    def complete(self):
        try:
            make_meta_files(self.announce_url,
                        self.file_list,
                        self.flag,
                        self.set_progress_value,
                        self.set_file,
                        self.piece_length)
            if not self.flag.isSet():
                self.set_title('Done.')
                self.label.set_text('Done building torrents.')
                self.set_progress_value(1)
                self.action_area.remove(self.cancelbutton)
                self.action_area.pack_start(self.done_button)
                self.done_button.show()
        except (OSError, IOError), e:
            self.set_title('Error!')
            self.label.set_text('Error building torrents: ' + str(e))


if __name__ == '__main__':

    config, args = configfile.parse_configuration_and_args(defaults,
                                    'btmaketorrentgui', sys.argv[1:], 0, None)
    w = MainWindow(config)
    try:
        gtk.main()
    except KeyboardInterrupt:
        # gtk.mainloop not running
        # exit and don't save config options
        sys.exit(1)

    save_options = ('torrent_dir','piece_size_pow2','tracker_name')
    def error_callback(error, string): print string
    configfile.save_ui_config(w.config, 'btmaketorrentgui', save_options, error_callback)
