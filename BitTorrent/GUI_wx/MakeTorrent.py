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

# Written by Matt Chisholm, Greg Hazel, and Steven Hazel

from __future__ import division

from BTL.translation import _

import os
import sys

from threading import Event

from BitTorrent import version
from BitTorrent import configfile
from BitTorrent.GUI_wx import SPACING, BTApp, BTFrameWithSizer, BTDialog, BTPanel, Grid, VSizer, HSizer, ChooseFileOrDirectorySizer
from BitTorrent.UI import Size
from BitTorrent.defaultargs import get_defaults
from BitTorrent.makemetafile import make_meta_files
from BitTorrent.parseargs import makeHelp
from BitTorrent.platform import app_name, btspawn

from BTL.yielddefer import launch_coroutine

import wx
import wx.grid

defaults = get_defaults('maketorrent')
defconfig = dict([(name, value) for (name, value, doc) in defaults])
del name, value, doc
ui_options = ('torrent_dir','piece_size_pow2','tracker_list','use_tracker')

EXTENSION = '.torrent'

MAXIMUM_NODES = 8


class MakeTorrentPanel(BTPanel):
    sizer_class = VSizer
    sizer_args = ()



class MakeTorrentWindow(BTFrameWithSizer):
    panel_class = MakeTorrentPanel

    def __init__(self, parent, config):
        BTFrameWithSizer.__init__(self, parent,
                         style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.SYSTEM_MENU|wx.CAPTION|wx.CLOSE_BOX|wx.CLIP_CHILDREN |wx.RESIZE_BORDER)  # HERE HACK.  I added RESIZE_BORDER because the window doesn't resize properly when Advanced button is pressed. --Dave
	self.parent = parent
        self.SetTitle(_("%s Publisher")%(app_name))
        self.config = config
        self.tracker_list = []
        if self.config['tracker_list']:
            self.tracker_list = self.config['tracker_list'].split(',')

        ## widgets

        # file widgets
        self.top_text = wx.StaticText(self.panel,
                                      label=_("Publish this file/directory:"))

        self.dir_text = wx.StaticText(self.panel,
                                      label= _("(Directories will become batch torrents)"))

        # title widgets
        self.title_label = wx.StaticText(self.panel, label=_("Title"))
        self.title = wx.TextCtrl(self.panel)
        self.title.SetValue(self.config['title'])

        # Comment widgets
        self.comment_label = wx.StaticText(self.panel, label=_("Comments:"))
        self.comment_text = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE, size=(-1,50))
        self.comment_text.SetValue(self.config['comment'])

        # horizontal line
        self.simple_advanced_line = wx.StaticLine(self.panel, style=wx.LI_HORIZONTAL)

        # piece size widgets
        self.piece_size_label = wx.StaticText(self.panel, label=_("Piece size:"))
        self.piece_size = wx.Choice(self.panel)
        self.piece_size.Append(_("Auto"))
        self.piece_size.offset = 15
        for i in range(7):
            self.piece_size.Append(str(Size(2**(i+self.piece_size.offset))))
        self.piece_size.SetSelection(0)

        # Announce URL / Tracker widgets
        self.tracker_radio = wx.RadioButton(self.panel, label=_("Use &tracker:"), style=wx.RB_GROUP)
        self.tracker_radio.group = [self.tracker_radio, ]
        self.tracker_radio.value = True

        self.announce_entry = wx.ComboBox(self.panel, style=wx.CB_DROPDOWN,
                                          choices=self.tracker_list)

        self.tracker_radio.entry = self.announce_entry
        if self.tracker_radio.GetValue():
            self.announce_entry.Enable(True)
        else:
            self.announce_entry.Enable(False)

        if self.config['tracker_name']:
            self.announce_entry.SetValue(self.config['tracker_name'])
        elif len(self.tracker_list):
            self.announce_entry.SetValue(self.tracker_list[0])
        else:
            self.announce_entry.SetValue('http://my.tracker:6969/announce')

        # DHT / Trackerless widgets
        self.dht_radio = wx.RadioButton(self.panel, label=_("Use &DHT:"))
        self.tracker_radio.group.append(self.dht_radio)
        self.dht_radio.value = False

        self.dht_nodes_box = wx.StaticBox(self.panel, label=_("Nodes (optional):"))
        self.dht_nodes = NodeList(self.panel, 'router.bittorrent.com:6881')

        self.dht_radio.entry = self.dht_nodes

        for w in self.tracker_radio.group:
            w.Bind(wx.EVT_RADIOBUTTON, self.toggle_tracker_dht)

        for w in self.tracker_radio.group:
            if w.value == bool(self.config['use_tracker']):
                w.SetValue(True)
            else:
                w.SetValue(False)

        if self.config['use_tracker']:
            self.dht_nodes.Disable()
        else:
            self.announce_entry.Disable()

        # Button widgets
        self.quitbutton = wx.Button(self.panel, label=_("&Close"))
        self.quitbutton.Bind(wx.EVT_BUTTON, self.quit)
        self.makebutton = wx.Button(self.panel, label=_("&Publish"))
        self.makebutton.Bind(wx.EVT_BUTTON, self.make)
        self.makebutton.Enable(False)

        self.advancedbutton = wx.Button(self.panel, label=_("&Advanced"))
        self.advancedbutton.Bind(wx.EVT_BUTTON, self.toggle_advanced)
        self.simplebutton = wx.Button(self.panel, label=_("&Simple"))
        self.simplebutton.Bind(wx.EVT_BUTTON, self.toggle_advanced)

        ## sizers
        # file sizers
        def setfunc(path):
            self.config['torrent_dir'] = path
        path = ''
        if self.config.has_key('torrent_dir') and self.config['torrent_dir']:
            path = self.config['torrent_dir']
        elif self.config.has_key('open_from') and self.config['open_from']:
            path = self.config['open_from']
        elif self.config.has_key('save_in') and self.config['save_in']:
            path = self.config['save_in']
        self.choose_file_sizer = ChooseFileOrDirectorySizer(self.panel, path,
                                                            setfunc=setfunc)

        self.choose_file_sizer.pathbox.Bind(wx.EVT_TEXT, self.check_buttons)

        self.box = self.panel.sizer
        self.box.AddFirst(self.top_text, flag=wx.ALIGN_LEFT)
        self.box.Add(self.choose_file_sizer, flag=wx.GROW)
        self.box.Add(self.dir_text, flag=wx.ALIGN_LEFT)
        self.box.Add(wx.StaticLine(self.panel, style=wx.LI_HORIZONTAL), flag=wx.GROW)

        # Ye Olde Flexe Gryde Syzer
        self.table = wx.FlexGridSizer(5,2,SPACING,SPACING)

        # Title
        self.table.Add(self.title_label, flag=wx.ALIGN_CENTER_VERTICAL)
        self.table.Add(self.title, flag=wx.GROW)

        # Comments
        self.table.Add(self.comment_label, flag=wx.ALIGN_CENTER_VERTICAL)
        self.table.Add(self.comment_text, flag=wx.GROW)

        # separator
        self.table.Add((0,0),0)
        self.table.Add(self.simple_advanced_line, flag=wx.GROW)

        # Piece size sizers
        self.table.Add(self.piece_size_label, flag=wx.ALIGN_CENTER_VERTICAL)
        self.table.Add(self.piece_size, flag=wx.GROW)

        # Announce URL / Tracker sizers
        self.table.Add(self.tracker_radio, flag=wx.ALIGN_CENTER_VERTICAL)
        self.table.Add(self.announce_entry,flag=wx.GROW)

        # DHT / Trackerless sizers
        self.table.Add(self.dht_radio, flag=wx.ALIGN_CENTER_VERTICAL)

        self.dht_nodes_sizer = wx.StaticBoxSizer(self.dht_nodes_box, wx.VERTICAL)
        self.dht_nodes_sizer.Add(self.dht_nodes, flag=wx.ALL, border=SPACING)

        self.table.Add(self.dht_nodes_sizer, flag=wx.GROW)

        # add table
        self.table.AddGrowableCol(1)
        self.box.Add(self.table, flag=wx.GROW)

        self.box.Add(wx.StaticLine(self.panel, style=wx.LI_HORIZONTAL), flag=wx.GROW)

        # Button sizers
        self.buttonbox = HSizer()

        self.buttonbox.AddFirst(self.advancedbutton)
        self.buttonbox.Add(self.simplebutton)
        self.buttonbox.Add(self.quitbutton)
        self.buttonbox.Add(self.makebutton)

        self.box.Add(self.buttonbox, flag=wx.ALIGN_RIGHT, border=0)

        # bind a bunch of things to check_buttons
        self.announce_entry.Bind(wx.EVT_TEXT, self.check_buttons)
        self.choose_file_sizer.pathbox.Bind(wx.EVT_TEXT, self.check_buttons)
        # radio buttons are checked in toggle_tracker_dht

        minwidth = self.GetBestSize()[0]
        self.SetMinSize(wx.Size(minwidth, -1))

        # Flip advanced once because toggle_advanced flips it back
        self.advanced = True
        self.toggle_advanced(None)
        if self.config['verbose']:
            self.toggle_advanced(None)

        self.check_buttons()

        self.Show()

        self.Bind(wx.EVT_CLOSE, self.quit)


    def Fit(self):
        self.panel.Fit()
        self.SetClientSize(self.panel.GetSize())


    def quit(self, event=None):
        self.save_config()
	if self.parent:
	    self.Show(False)
	else:
	    self.Destroy()


    def toggle_advanced(self, event):
        show = not self.advanced
        if show:
            # reinstate the StaticBoxSizer before Show()
            self.table.Add(self.dht_nodes_sizer, flag=wx.GROW)
        else:
            # detach the StaticBoxSizer before Show(False)
            self.table.Detach(self.dht_nodes_sizer)

        for w in (
            self.simple_advanced_line,
            self.piece_size, self.piece_size_label,
            self.tracker_radio, self.announce_entry,
            self.dht_radio,  self.dht_nodes, self.dht_nodes_box,
            self.simplebutton,
            ):
            w.Show(show)
        self.advancedbutton.Show(self.advanced)

        if show:
            self.dht_nodes_sizer.Layout()
            self.dht_nodes_sizer.Fit(self)
        self.table.Layout()
        self.table.Fit(self)
        self.sizer.RecalcSizes()
        self.sizer.Fit(self)
        self.advanced = show



    def toggle_tracker_dht(self, event):
        widget = event.GetEventObject()
        self.config['use_tracker'] = widget.value

        for e in [self.announce_entry, self.dht_nodes]:
            if widget.entry is e:
                e.Enable(True)
            else:
                e.Enable(False)
        self.check_buttons()


    def get_piece_size_exponent(self):
        i = self.piece_size.GetSelection()
        if i == 0:
            # Auto
            exp = 0
        else:
            exp = i-1 + self.piece_size.offset
        self.config['piece_size_pow2'] = exp
        return exp


    def get_file(self):
        return self.choose_file_sizer.get_choice()


    def get_announce(self):
        if self.config['use_tracker']:
            announce = self.announce_entry.GetValue()
            self.config['tracker_name'] = announce
        else:
            announce = self.dht_nodes.GetValue()
        return announce


    def make(self, widget):
        file_name = self.get_file()
        piece_size_exponent = self.get_piece_size_exponent()
        announce = self.get_announce()
        title = self.title.GetValue()
        comment = self.comment_text.GetValue()

        if self.config['use_tracker']:
            self.add_tracker(announce)
        errored = False
        if not errored:
            d = ProgressDialog(self, [file_name,], announce,
                               piece_size_exponent, title, comment,
                               self.config)
            d.main()


    def check_buttons(self, *widgets):
        file_name = self.get_file()
        tracker = self.announce_entry.GetValue()
        if file_name not in (None, '') and os.path.exists(file_name):
            if self.config['use_tracker']:
                if len(tracker) >= len('http://x.cc'):
                    self.makebutton.Enable(True)
                else:
                    self.makebutton.Enable(False)
            else:
                self.makebutton.Enable(True)
        else:
            self.makebutton.Enable(False)


    def save_config(self):
        def error_callback(error, string): print string
        configfile.save_global_config(self.config, 'maketorrent', error_callback, ui_options)


    def add_tracker(self, tracker_name):
        try:
            self.tracker_list.pop(self.tracker_list.index(tracker_name))
        except ValueError:
            pass
        self.tracker_list[0:0] = [tracker_name,]

        self.config['tracker_list'] = ','.join(self.tracker_list)

        if not self.announce_entry.IsEmpty():
            self.announce_entry.Clear()
        for t in self.tracker_list:
            self.announce_entry.Append(t)



class NodeList(Grid):
    def __init__(self, parent, nodelist):
        Grid.__init__(self, parent, style=wx.WANTS_CHARS)

        self.CreateGrid( 0, 2, wx.grid.Grid.SelectRows)
        self.SetColLabelValue(0, _("Host"))
        self.SetColLabelValue(1, _("Port"))

        self.SetColRenderer(1, wx.grid.GridCellNumberRenderer())
        self.SetColEditor(1, wx.grid.GridCellNumberEditor(0, 65535))

        self.SetColLabelSize(self.GetTextExtent("l")[1]+4)
        self.SetRowLabelSize(1)
        self.SetSize((1000,1000))

        self.storing = False
        self.Bind(wx.grid.EVT_GRID_CMD_CELL_CHANGE, self.store_value)

        self.append_node(('router.bittorrent.com', '65536'))

        for i, e in enumerate(nodelist.split(',')):
            host, port = e.split(':')
            self.append_node((host,port))

        self.append_node(('',''))

    def append_node(self, (host, port)):
        self.InsertRows(self.GetNumberRows(), 1)
        self.SetCellValue(self.GetNumberRows()-1, 0, host)
        self.SetCellValue(self.GetNumberRows()-1, 1, port)
        self.AutoSizeColumn(0)
        self.SetColSize(1, self.GetTextExtent('65536')[0] * 2)
        ###self.AutoSize()

    def store_value(self, event):
        if self.storing:
            return
        self.storing = True
        table = self.GetTable()
        row = event.GetRow()
        col = event.GetCol()
        value = table.GetValue(row, col)
        if col == 0:
            self.store_host_value(row, value)
        elif col == 1:
            self.store_port_value(row, value)
        self.storing = False

    def store_host_value(self, row, value):
        parts = value.split('.')
        if value != '':
            for p in parts:
                if not p.isalnum():
                    return
                try:
                    value = value.encode('idna')
                except UnicodeError:
                    return
        self.check_row(row)

    def store_port_value(self, row, value):
        if value != '':
            try:
                v = int(value)
                if v > 65535:
                    value = 65535
                if v < 0:
                    value = 0
            except ValueError:
                return # return on non-integer values
        self.check_row(row)

    def check_row(self, row):
        # called after editing to see whether we should add a new
        # blank row, or remove the now blank currently edited row.
        table = self.GetTable()
        host_value = table.GetValue(row, 0)
        port_value = table.GetValue(row, 1)
        if (host_value and
            port_value and
            int(row) == self.GetNumberRows()-1):
            self.append_node(('',''))
        elif (host_value == '' and
              (not port_value or int(port_value) == 0) and
              int(row) != self.GetNumberRows()-1):
            self.DeleteRows(row, 1)

    def get_nodes(self):
        retlist = []
        id = -1
        table = self.GetTable()
        for row in xrange(self.GetNumberRows()):
            host = table.GetValue(row, 0)
            port = table.GetValue(row, 1)
            if host != '' and port != '' and port != 0:
                retlist.append((host,port))
        return retlist

    def GetValue(self):
        nodelist = self.get_nodes()
        return ','.join(['%s:%s'%node for node in nodelist])



def deunicode(s):
    try:
        s = s.decode('utf8', 'replace').encode('utf8')
    except:
        pass
    return s



class ProgressDialog(BTDialog):

    def __init__(self, parent, file_list, announce, piece_length, title,
                 comment, config):
        BTDialog.__init__(self, parent=parent, size=(400,-1))
	self.parent = parent
        self.SetTitle(_("Building torrents..."))
        self.file_list = file_list
        self.announce = deunicode(announce)
        self.piece_length = piece_length
        self.title = deunicode(title)
        self.comment = deunicode(comment)
        self.config = config

        self.flag = Event() # ???

        self.vbox = VSizer()
        self.label = wx.StaticText(self, label=_("Checking file sizes..."))
        #self.label.set_line_wrap(True)

        self.vbox.AddFirst(self.label, flag=wx.ALIGN_LEFT)

        self.progressbar = wx.Gauge(self, range = 1000, size=(400, 25), style = wx.GA_SMOOTH)
        self.vbox.Add(self.progressbar, flag=wx.GROW)

        self.vbox.Add(wx.StaticLine(self, style=wx.LI_HORIZONTAL), flag=wx.GROW)

        self.action_area = wx.BoxSizer(wx.HORIZONTAL)

        self.cancelbutton = wx.Button(self, label=_("&Abort"))
        self.cancelbutton.Bind(wx.EVT_BUTTON, self.cancel)
        self.action_area.Add(self.cancelbutton,
                             flag=wx.LEFT|wx.RIGHT|wx.BOTTOM, border=SPACING)

        self.done_button = wx.Button(self, label=_("&Ok"))
        self.done_button.Bind(wx.EVT_BUTTON, self.cancel)
        self.action_area.Add(self.done_button,
                             flag=wx.LEFT|wx.RIGHT|wx.BOTTOM, border=SPACING)

        self.action_area.Show(self.done_button, False)

        self.seed_button = wx.Button(self, label=_("&Start seeding"))
        self.seed_button.Bind(wx.EVT_BUTTON, self.seed)
        self.action_area.Add(self.seed_button,
                             flag=wx.RIGHT|wx.BOTTOM, border=SPACING)

        self.action_area.Show(self.seed_button, False)

        self.Bind(wx.EVT_CLOSE, self.cancel)

        self.vbox.Add(self.action_area, flag=wx.ALIGN_RIGHT,
                      border=0)

        self.SetSizerAndFit(self.vbox)
        self.Show()


    def main(self):
        self.complete()


    def seed(self, widget=None):
        for f in self.file_list:
	    if self.parent.parent:
		launch_coroutine(wx.the_app.gui_wrap, wx.the_app.publish_torrent, f+EXTENSION, f)
	    else:
		btspawn('bittorrent', f+EXTENSION, '--publish', f)
        self.cancel()


    def cancel(self, widget=None):
        self.flag.set()
        self.Destroy()


    def set_progress_value(self, value):
        self.progressbar.SetValue(value * 1000)
        self._update_gui()


    def set_file(self, filename):
        self.label.SetLabel(_("building: ") + filename + EXTENSION)
        self.vbox.Layout()
        self.Fit()
        self._update_gui()


    def _update_gui(self):
        wx.GetApp().Yield(True)


    def complete(self):
        try:
            make_meta_files(self.announce.encode('utf8'),
                            self.file_list,
                            flag=self.flag,
                            progressfunc=self.set_progress_value,
                            filefunc=self.set_file,
                            piece_len_pow2=self.piece_length,
                            title=self.title,
                            comment=self.comment,
                            use_tracker=self.config['use_tracker'],
                            data_dir=self.config['data_dir'],
                            )
            if not self.flag.isSet():
                self.SetTitle(_("Done."))
                self.label.SetLabel(_("Done building torrents."))
                self.set_progress_value(1)
                self.action_area.Show(self.cancelbutton, False)
                self.action_area.Show(self.seed_button, True)
                self.action_area.Show(self.done_button, True)
                self.vbox.Layout()
        except (OSError, IOError), e:
            self.SetTitle(_("Error!"))
            self.label.SetLabel(_("Error building torrents: ") + unicode(e.args[0]))




