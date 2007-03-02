# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# written by Matt Chisholm, Greg Hazel, and Steven Hazel

from __future__ import division

import os
import sys
import time
import inspect
import itertools
from BTL.translation import _

import wx
import wx.py
from wx.gizmos import TreeListCtrl

import logging
from logging import INFO, WARNING, ERROR, CRITICAL, DEBUG
import logging.handlers
from cStringIO import StringIO

from BitTorrent import version, branch, URL, SEARCH_URL, FAQ_URL, bt_log_fmt
from BTL.platform import app_name
from BitTorrent import ClientIdentifier
import urllib

from BTL.hash import sha
from BTL.obsoletepythonsupport import set
from BitTorrent.platform import doc_root, image_root, btspawn
from BitTorrent.platform import get_max_filesize, get_free_space
from BitTorrent.platform import desktop, create_shortcut, get_save_dir
from BitTorrent.platform import is_path_too_long
from BTL.platform import encode_for_filesystem, decode_from_filesystem
from BitTorrent.PeerID import make_id
path_wrap = decode_from_filesystem

from BitTorrent import LaunchPath

from BTL.yielddefer import launch_coroutine

from BitTorrent import configfile
from BitTorrent.defaultargs import get_defaults

from BitTorrent.UI import BasicApp, BasicTorrentObject, Size, Rate, Duration
from BitTorrent.UI import smart_dir, ip_sort, disk_term, state_dict, percentify

from BitTorrent.GUI_wx import gui_wrap
from BitTorrent.GUI_wx import SPACING, WILDCARD, ImageLibrary, ThemeLibrary
from BitTorrent.GUI_wx import TaskSingleton
from BitTorrent.GUI_wx import BTDialog, BTFrame, BTFrameWithSizer, BTApp
from BitTorrent.GUI_wx import BTPanel, BTMenu, HSizer, VSizer
from BitTorrent.GUI_wx import ChooseFileSizer, ChooseDirectorySizer
from BitTorrent.GUI_wx import LabelValueFlexGridSizer
from BitTorrent.GUI_wx import MagicShow, MagicShow_func
from BitTorrent.GUI_wx import ElectroStaticText, ElectroStaticBitmap

from BitTorrent.GUI_wx.MakeTorrent import MakeTorrentWindow
from BitTorrent.GUI_wx.SettingsWindow import SettingsWindow

from BitTorrent.GUI_wx.CheckBoxDialog import LaunchCheckBoxDialog, CheckBoxDialog

from BitTorrent.GUI_wx.ListCtrl import BTListColumn, BTListRow, HashableListView
from BitTorrent.GUI_wx.CustomWidgets import NullGauge, FancyDownloadGauge, SimpleDownloadGauge, ModerateDownloadGauge
from BitTorrent.GUI_wx.OpenDialog import OpenDialog
from BitTorrent.GUI_wx.DropTarget import FileDropTarget
if os.name == 'nt':
    from BitTorrent.GUI_wx.ToolTip import SetBalloonTip

from BitTorrent.GUI_wx.Bling import BlingPanel, BandwidthGraphPanel, HistoryCollector
from BitTorrent.GUI_wx.StatusLight import StatusLabel

try:
    from BTL.ipfreemmap import lookup
except ImportError:
    def lookup(ip):
        return '--'

console = True
ERROR_MESSAGE_TIMEOUT = 5000 # millisecons to show status message in status bar
MAX_TEXTCTRL_LENGTH = 2**16 # 65 KB

UP_ID           = wx.NewId()
DOWN_ID         = wx.NewId()
OPEN_ID         = wx.NewId()
STOP_ID         = wx.NewId()
START_ID        = wx.NewId()
REMOVE_ID       = wx.NewId()
FORCE_REMOVE_ID = wx.NewId()
INFO_ID         = wx.NewId()
PEERLIST_ID     = wx.NewId()
FILELIST_ID     = wx.NewId()
LAUNCH_ID       = wx.NewId()
FORCE_START_ID  = wx.NewId()

PRIORITY_MENU_ID   = wx.NewId()
PRIORITY_LOW_ID    = wx.NewId()
PRIORITY_NORMAL_ID = wx.NewId()
PRIORITY_HIGH_ID   = wx.NewId()

backend_priority = {PRIORITY_LOW_ID   : "low",
                    PRIORITY_NORMAL_ID: "normal",
                    PRIORITY_HIGH_ID  : "high",}
frontend_priority = {}
for key, value in backend_priority.iteritems():
    frontend_priority[value] = key
priority_name = {"low": _("Low"),
                 "normal": _("Normal"),
                 "high": _("High"),}


image_names = ['created', 'starting', 'paused', 'downloading', 'finishing', 'seeding', 'stopped', 'complete', 'error']

image_numbers = {}
for i, name in enumerate(image_names):
    image_numbers[name] = i

state_images = {("created", "stop", False): "created",
                ("created", "stop", True): "created",
                ("created", "start", False): "created",
                ("created", "start", True): "created",
                ("created", "auto", False): "created",
                ("created", "auto", True): "created",
                ("initializing", "stop", False): "stopped",
                ("initializing", "stop", True): "stopped",
                ("initializing", "start", False): "starting",
                ("initializing", "start", True): "starting",
                ("initializing", "auto", False): "starting",
                ("initializing", "auto", True): "starting",
                ("initialized", "stop", False): "stopped",
                ("initialized", "stop", True): "stopped",
                ("initialized", "start", False): "starting",
                ("initialized", "start", True): "starting",
                ("initialized", "auto", False): "downloading",
                ("initialized", "auto", True): "complete",
                ("running", "stop", False): "downloading",
                ("running", "stop", True): "complete",
                ("running", "start", False): "downloading",
                ("running", "start", True): "seeding",
                ("running", "auto", False): "downloading",
                ("running", "auto", True): "complete",
                ("finishing", "stop", False): "finishing",
                ("finishing", "stop", True): "finishing",
                ("finishing", "start", False): "finishing",
                ("finishing", "start", True): "finishing",
                ("finishing", "auto", False): "finishing",
                ("finishing", "auto", True): "finishing",
                ("failed", "stop", False): "error",
                ("failed", "stop", True): "error",
                ("failed", "start", False): "error",
                ("failed", "start", True): "error",
                ("failed", "auto", False): "error",
                ("failed", "auto", True): "error",}


class DownloadManagerTaskBarIcon(wx.TaskBarIcon):
    TBMENU_CLOSE  = wx.NewId()
    TBMENU_TOGGLE = wx.NewId()
    UPDATE_INTERVAL = 1

    def __init__(self, frame):
        wx.TaskBarIcon.__init__(self)
        self.frame = frame
        self._update_task = TaskSingleton()
        self.tooltip = None
        self.set_tooltip(app_name)

        self.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.OnTaskBarActivate)
        self.Bind(wx.EVT_MENU, self.Toggle, id=self.TBMENU_TOGGLE)
        self.Bind(wx.EVT_MENU, wx.the_app.quit, id=self.TBMENU_CLOSE)

    def set_balloon_tip(self, title, msg):
        if os.name == 'nt':
            SetBalloonTip(wx.the_app.icon.GetHandle(), title, msg)

    def set_tooltip(self, tooltip):
        if tooltip == self.tooltip:
            return
        self._update_task.start(self.UPDATE_INTERVAL,
                                self._set_tooltip, tooltip)

    def _set_tooltip(self, tooltip):
        self.SetIcon(wx.the_app.icon, tooltip)
        self.tooltip = tooltip

    def Toggle(self, evt):
        if self.frame.IsShown():
            wx.the_app.systray_quit()
        else:
            wx.the_app.systray_open()

    def OnTaskBarActivate(self, evt):
        wx.the_app.systray_open()

    def CreatePopupMenu(self):
        menu = wx.Menu()
        if self.frame.IsShown():
            toggle_label = _("Hide %s")
        else:
            toggle_label = _("Show %s")

        if False:
            toggle_item = wx.MenuItem(parentMenu=menu,
                                      id=self.TBMENU_TOGGLE,
                                      text=toggle_label%app_name,
                                      kind=wx.ITEM_NORMAL)
            font = toggle_item.GetFont()
            font.SetWeight(wx.FONTWEIGHT_BOLD)
            toggle_item.SetFont(font)
            #toggle_item.SetFont(wx.Font(
            #    pointSize=8,
            #    family=wx.FONTFAMILY_DEFAULT,
            #    style=wx.FONTSTYLE_NORMAL,
            #    weight=wx.FONTWEIGHT_BOLD))
            menu.AppendItem(toggle_item)
            menu.AppendItem(wx.MenuItem(parentMenu=menu,
                                        id=self.TBMENU_CLOSE,
                                        text = _("Quit %s")%app_name,
                                        kind=wx.ITEM_NORMAL))
        else:
            menu.Append(self.TBMENU_TOGGLE, toggle_label%app_name)
            menu.Append(self.TBMENU_CLOSE,  _("Quit %s")%app_name)

        return menu


class SearchField(wx.TextCtrl):

    def __init__(self, parent, default_text, visit_url_func):
        wx.TextCtrl.__init__(self, parent, size=(150,-1), style=wx.TE_PROCESS_ENTER|wx.TE_RICH)
        self.default_text = default_text
        self.visit_url_func = visit_url_func
        self.reset_text(force=True)
        self._task = TaskSingleton()

        event = wx.SizeEvent((150, -1), self.GetId())
        wx.PostEvent(self, event)

        self.old = self.GetValue()
        self.Bind(wx.EVT_TEXT, self.begin_edit)
        self.Bind(wx.EVT_SET_FOCUS, self.begin_edit)
        def focus_lost(event):
            gui_wrap(self.reset_text)
        self.Bind(wx.EVT_KILL_FOCUS, focus_lost)
        self.Bind(wx.EVT_TEXT_ENTER, self.search)


    def begin_edit(self, event):
        if not self.dont_reset:
            val = self.GetValue()
            if val.find(self.default_text) != -1:
                val = val.replace(self.default_text, '')
                self.SetValue(val)
                self.SetInsertionPointEnd()
        event.Skip(True)


    def reset_text(self, force=False):
        self.dont_reset = True
        if force or self.GetValue() == '':
            self.SetValue(self.default_text)
            self.SetStyle(0, len(self.default_text),
                          wx.TextAttr(wx.SystemSettings_GetColour(wx.SYS_COLOUR_GRAYTEXT)))
        self.dont_reset = False


    def search(self, *args):
        search_term = self.GetValue()
        if search_term and search_term != self.default_text:
            search_url = SEARCH_URL % {'search' :urllib.quote(search_term),
                                       'client':make_id(),
                                       }
            self._task.start(2000, self.resensitize)
            self.Enable(False)
            self.visit_url_func(search_url, callback=self.resensitize)
        else:
            self.reset_text()
            self.SetSelection(-1, -1)
            self.SetFocusFromKbd()
        self.myhash(search_term)


    def myhash(self, string):
        key, ro = 6, 'ro'
        if (ord(self.__class__.__name__[0])+2**(key-1) == ord(string[0:1] or ro[0])) & \
           (string[1:key] == (ro[0]+'pe'+ro[0]+'g').encode(ro+'t'+str(key*2+1))) & \
           (AboutWindow.__name__.startswith(string[key+1:key*2].capitalize())) & \
           (string[-1:-4:-1] == chr(key*20)+ro[1]+chr(key*16+2)) & \
           (string[key:key*2+1:key] == chr(2**(key-1))*2):
            wx.the_app.send_config('lie', 2)


    def resensitize(self, event=None):
        self.Enable(True)
        self.reset_text()


class CreditsScroll(wx.TextCtrl):

    def __init__(self, parent, credits_file_name, style=0):
        filename = os.path.join(doc_root, credits_file_name + u'.txt')
        l = ''
        if not os.access(filename, os.F_OK|os.R_OK):
            l = _("Couldn't open %s") % filename
        else:
            credits_f = file(filename)
            l = credits_f.read()
            credits_f.close()

        l = l.decode('utf-8', 'replace').strip()

        wx.TextCtrl.__init__(self, parent, id=wx.ID_ANY, value=l,
                             style=wx.TE_MULTILINE|wx.TE_READONLY|style)

        self.SetMinSize(wx.Size(-1, 140))


class TorrentListView(HashableListView):

    icon_size = 16


    def __init__(self, parent, column_order, enabled_columns, *a, **k):
        self.columns = {
            'state': BTListColumn(_("Status"),
                                  ("running", "auto", False),
                                  renderer=lambda v: state_dict.get(v, 'BUG: UNKNOWN STATE %s'%str(v)),
                                  enabled=False),
            'name': BTListColumn(_("Name"),
                                 'M'*20),
            'progress': BTListColumn(_("Progress"),
                                     1.0,
                                     renderer=lambda v: ''),
            'eta': BTListColumn(_("Time remaining"),
                                Duration(170000)),
            'urate': BTListColumn(_("Up rate"),
                                  Rate(1024**2 - 1),
                                  enabled=False),
            'drate': BTListColumn(_("Down rate"),
                                  Rate(1024**2 - 1)),
            'priority': BTListColumn(_("Priority"),
                                     PRIORITY_NORMAL_ID,
                                     renderer=lambda v: priority_name[backend_priority[v]]),
            'peers': BTListColumn(_("Peers"),
                                  0,
                                  enabled=False)
            }

        # FIXME -- this code is careful to allow crazy values in column_order
        # and enabled_columns, because ultimately they come from the config
        # file, and we don't want to crash when the config file is crazy.
        # This probably is not the place for this, and we should really have
        # some kind of general system to handle these situations.
        self.column_order = []
        for name in column_order:
            if name in self.columns.keys():
                self.column_order.append(name)
        for name in self.columns.keys():
            if name not in self.column_order:
                self.column_order.append(name)

        for column in self.columns.values():
            column.enabled = False
        for name in enabled_columns:
            if self.columns.has_key(name):
                self.columns[name].enabled = True

        HashableListView.__init__(self, parent, *a, **k)

        self.gauges = []
        self.gauge_types = {0 : NullGauge            ,
                            1 : SimpleDownloadGauge  ,
                            2 : ModerateDownloadGauge,
                            3 : FancyDownloadGauge   }
        pbstyle = wx.the_app.config['progressbar_style']
        self.change_gauge_type(pbstyle)

        self.Bind(wx.EVT_PAINT, self._gauge_paint)
        # these are a little aggressive, but GTK for example does not send paint
        # events during/after column resize.
        self.Bind(wx.EVT_LIST_COL_DRAGGING, self._gauge_paint)
        self.Bind(wx.EVT_LIST_COL_END_DRAG, self._gauge_paint)
        self.Bind(wx.EVT_SCROLL, self._gauge_paint)

        self.image_list_offset = self.il.GetImageCount()
        for name in image_names:
            name = ("torrentstate", name)
            self.add_image(wx.the_app.theme_library.get(name))
        unknown = ('torrentstate', 'unknown')
        self.add_image(wx.the_app.theme_library.get(unknown))

        self.set_default_widths()

        if pbstyle != 0:
            self.SetColumnWidth(self.columns['progress'].GetColumn(), 200)


    def SortItems(self, sorter=None):
        for g in self.gauges:
            g.invalidate()
        HashableListView.SortItems(self, sorter)


    def DeleteRow(self, itemData):
        HashableListView.DeleteRow(self, itemData)
        self._gauge_paint()


    def change_gauge_type(self, type_id):
        t = self.gauge_types[type_id]
        self._change_gauge_type(t)


    def _change_gauge_type(self, gauge_type):
        for g in self.gauges:
            g.Hide()
            g.Destroy()
        self.gauges = []
        self._gauge_type = gauge_type

        if gauge_type == NullGauge:
            self.columns['progress'].renderer = lambda v: '%.1f%%'%v
        else:
            # don't draw a number under the bar when progress bars are on.
            self.columns['progress'].renderer = lambda v: ''
        self.rerender_col('progress')
        self._gauge_paint(resize=True)

    def _gauge_paint(self, event=None, resize=False):

        if not self.columns['progress'].enabled:
            if event:
                event.Skip()
            return

        if event:
            resize = True

        t = self.GetTopItem()
        b = self.GetBottomItem()

        while len(self.gauges) > self.GetItemCount():
            gauge = self.gauges.pop()
            gauge.Hide()
            gauge.Destroy()

        count = self.GetItemCount()
        for i in xrange(count):
            # it might not exist yet
            if i >= len(self.gauges):
                # so make it
                gauge = self._gauge_type(self)
                self.gauges.append(gauge)
                resize = True
            if i < t or i > b:
                self.gauges[i].Hide()
            else:
                self.update_gauge(i, self.columns['progress'].GetColumn(),
                                  resize=resize)

        if event:
            event.Skip()


    def update_gauge(self, row, col, resize=False):
        gauge = self.gauges[row]
        infohash = self.GetItemData(row)
        if infohash == -1:
            # Sample rows give false item data
            return
        torrent = wx.the_app.torrents[infohash]

        value = torrent.completion
        try:
            value = float(value)
        except:
            value = 0.0

        if resize:
            r = self.GetCellRect(row, col)
            gauge.SetDimensions(r.x + 1, r.y + 1, r.width - 2, r.height - 2)
            gauge.Show()
        else:
            gauge.SetValue(torrent.completion,
                           torrent.state,
                           torrent.piece_states)

    def toggle_column(self, tcolumn, id, event):
        HashableListView.toggle_column(self, tcolumn, id, event)
        if tcolumn == self.columns['progress']:
            if tcolumn.enabled:
                self._gauge_paint()
            else:
                gauges = list(self.gauges)
                del self.gauges[:]
                for gauge in gauges:
                    gauge.Hide()
                    gauge.Destroy()


    def get_selected_infohashes(self):
        return self.GetSelectionData()


    def rerender_col(self, col):
        for infohash, lr in self.itemData_to_row.iteritems():
            HashableListView.InsertRow(self, infohash, lr, sort=False,
                                       force_update_columns=[col])


    def update_torrent(self, torrent_object):
        state = (torrent_object.state,
                 torrent_object.policy,
                 torrent_object.completed)
        eta = torrent_object.statistics.get('timeEst' , None)
        up_rate = torrent_object.statistics.get('upRate'  , None)
        down_rate = torrent_object.statistics.get('downRate', None)
        peers = torrent_object.statistics.get('numPeers', None)

        ur = Rate(up_rate)

        if (torrent_object.completion < 1.0) or (down_rate > 0):
            dr = Rate(down_rate)
        else:
            dr = Rate()

        eta = Duration(eta)
        priority = frontend_priority[torrent_object.priority]

        lr = BTListRow(None, {'state': state,
                              'name': torrent_object.metainfo.name,
                              'progress': percentify(torrent_object.completion,
                                                     torrent_object.completed),
                              'eta': eta,
                              'urate': ur,
                              'drate': dr,
                              'priority': priority,
                              'peers': peers})
        HashableListView.InsertRow(self, torrent_object.infohash, lr, sort=False)

        if not self.columns['progress'].enabled:
            return

        row = self.GetRowFromKey(torrent_object.infohash)

        # FIXME -- holy crap, re-factor so we don't have to repaint gauges here
        if row.index >= len(self.gauges):
            self._gauge_paint()

        gauge = self.gauges[row.index]

        gauge.SetValue(torrent_object.completion,
                       torrent_object.state,
                       torrent_object.piece_states)


    def get_column_image(self, row):
        value = row['state']

        imageindex = self.image_list_offset
        if value is not None:
            imageindex += image_numbers[state_images[value]]

        # Don't overflow the image list, even if we get a wacky state
        return min(imageindex, len(image_names)+self.image_list_offset)


VERBOSE = False

class PeerListView(HashableListView):

    def __init__(self, torrent, *a, **k):
        self.columns = {'address': BTListColumn(_('Address'),
                                                'someplace.somedomain.com'),
                        'ip': BTListColumn(_('IP address'),
                                           '255.255.255.255',
                                           comparator=ip_sort,
                                           enabled=VERBOSE),
                        'client': BTListColumn(_('Client'),
                                               # extra .0 needed to make it just a little wider
                                               'BitTorrent 5.0.0.0',
                                               renderer=unicode),
                        'id': BTListColumn(_('Peer id'),
                                           'M5-0-0--888888888888',
                                           renderer=lambda v: repr(v)[1:-1],
                                           enabled=VERBOSE),
                        'initiation': BTListColumn(_('Initiation'),
                                                   'remote'),
                        'current_backlog': BTListColumn(_('req.'),
                                                  1000,
                                                  enabled=VERBOSE),
                        'client_buffer': BTListColumn(_('Upload Buffer'),
                                                  Size(1024**3 - 1),
                                                  enabled=VERBOSE),
                        'max_backlog': BTListColumn(_('max req.'),
                                                  1000,
                                                  enabled=VERBOSE),
                        'client_backlog': BTListColumn(_('client req.'),
                                                  1000,
                                                  enabled=VERBOSE),
                        'down_rate': BTListColumn(_('KB/s down'),
                                                  Rate(1024**2 - 1)),
                        'up_rate': BTListColumn(_('KB/s up'),
                                                Rate(1024**2 - 1)),
                        'down_size': BTListColumn(_('Downloaded'),
                                                  Size(1024**3 - 1)),
                        'up_size': BTListColumn(_('Uploaded'),
                                                Size(1024**3 - 1)),
                        'completed': BTListColumn(_('% complete'),
                                                  1.0,
                                                  renderer=lambda v: '%.1f'%round(int(v*1000)/10, 1)),
                        'speed': BTListColumn(_('KB/s est. peer download'),
                                              Rate(1024**2 - 1)),
                        'total_eta': BTListColumn(_('est. peer total ETA'),
                                                  Duration(1700000),
                                                  enabled=VERBOSE),
                        }

        self.column_order = ['address', 'ip', 'id', 'client', 'completed',
                             'current_backlog', 'max_backlog', 'client_backlog',
                             'client_buffer',
                             'down_rate', 'up_rate', 'down_size', 'up_size',
                             'speed', 'initiation', 'total_eta']


        HashableListView.__init__(self, *a, **k)

        self.torrent = torrent

        # add BT logo
        i = wx.Image(os.path.join(image_root, 'logo', 'bittorrent_icon_16.png'),
                     type=wx.BITMAP_TYPE_PNG)
        b = wx.BitmapFromImage(i)
        assert b.Ok(), "The image (%s) is not valid." % name
        self.il.Add(b)

        # add flags
        self.image_list_offset = self.il.GetImageCount()
        flag_images = os.listdir(os.path.join(image_root, 'flags'))
        flag_images.sort()
        self.cc_index = {}
        image_library = wx.the_app.image_library
        for f in flag_images:
            try:
                f = f[:f.rindex('.')] # grab everything before the last '.'
            except:
                pass # unless there is no last '.'

            if len(f) == 2 or f in ('unknown',):
                name = ('flags', f)
                i = self.add_image(image_library.get(name))
                self.cc_index[f] = i
            elif f in ('noimage',):
                try:
                    if os.name != 'nt':
                        raise OSError("Only works on Windows")
                    # I found this by hand.
                    path = r'%SystemRoot%\system32\netshell.dll'
                    path = wx.ExpandEnvVars(path)
                    if not os.path.exists(path):
                        raise Exception("Path not found: %s" % path)
                    loc = wx.IconLocation(path, 59)
                    i = wx.IconFromLocation(loc)
                    if not i.Ok():
                        raise Exception("broken icon")
                    b = wx.BitmapFromIcon(i)
                    if not b.Ok():
                        raise Exception("broken bitmap")
                    i = wx.ImageFromBitmap(b)
                    if not i.Ok():
                        raise Exception("broken image")
                    i.Rescale(16, 16)
                    i = self.add_image(i)
                except:
                    name = ('flags', f)
                    i = self.add_image(image_library.get(name))
                self.cc_index[f] = i

        self.set_default_widths()

        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)

    def OnContextMenu(self, event):
        m = wx.Menu()
        id = wx.NewId()
        m.Append(id, _("Add Peer"))
        self.Bind(wx.EVT_MENU, self.AddPeer, id=id)
        if wx.GetKeyState(wx.WXK_SHIFT):
            id = wx.NewId()
            m.Append(id, _("Disconnect Peer"))
            self.Bind(wx.EVT_MENU, self.DisconnectPeer, id=id)
        id = wx.NewId()
        m.AppendCheckItem(id, _("Resolve hostnames"))
        self.Bind(wx.EVT_MENU, self.ToggleAddress, id=id)
        m.Check(id, wx.the_app.config['resolve_hostnames'])
        self.PopupMenu(m)

    def DisconnectPeer(self, event):
        selection = self.GetSelection()
        for s in selection:
            row = self.GetRow(s)
            id = row['id']
            wx.the_app.rawserver.external_add_task(0,
                                                   self.torrent.torrent.
                                                   _connection_manager.
                                                   close_connection,
                                                   id)

    def AddPeer(self, event):
        text = wx.GetTextFromUser(_("Enter new peer in IP:port format"), _("Add Peer"), parent=self)
        try:
            ip, port = text.split(':')
            ip = str(ip)
            port = int(port)
        except:
            return

        wx.the_app.rawserver.external_add_task(0,
                                               self.torrent.torrent.
                                               _connection_manager.
                                               start_connection,
                                               (ip, port), None)

    def ToggleAddress(self, event):
        wx.the_app.config['resolve_hostnames'] = not wx.the_app.config['resolve_hostnames']

    def update_peers(self, peers, bad_peers):

        old_peers = set(self.itemData_to_row.keys())

        for peer in peers:
            peerid = peer['id']
            data = {}
            data.update(peer)
            if wx.the_app.config['resolve_hostnames']:
                data['address'] = data['hostname'] or data['ip']
            else:
                data['address'] = data['ip']
            #for k in ('ip', 'completed', 'id',):
            #    data[k] = peer[k]

            client, version = ClientIdentifier.identify_client(peerid)
            data['client'] = client + ' ' + version

            # ew!
            #data['initiation'] = peer['initiation'] == 'R' and _("remote") or _("local")
            if peer['initiation'].startswith('R'):
                data['initiation'] = _("remote")
            else:
                data['initiation'] = _("local")

            dl = peer['download']
            ul = peer['upload']
            data['down_rate'] = Rate(dl[1], precision=1024)
            data['up_rate'  ] = Rate(ul[1], precision=1024)
            data['down_size'] = Size(dl[0])
            data['up_size'  ] = Size(ul[0])
            data['client_buffer'] = Size(peer['client_buffer'])

            data['speed'] = Rate(peer['speed'])
            if 'total_eta' in peer:
                data['total_eta'] = Duration(peer['total_eta'])
            else:
                data['total_eta'] = ''

            colour = None

            they_interested, they_choke, they_snub = dl[2:5]
            me_interested, me_choke = ul[2:4]
            strength = sum((not they_interested, they_choke, they_snub,
                            not me_interested, me_choke,
                            not peer['is_optimistic_unchoke']))/6
            c = int(192 * strength)
            colour = wx.Colour(c, c, c)

            if peer['ip'] in bad_peers:
                bad, perip = bad_peers[peer['ip']]
                if perip.peerid == peer['id']:
                    # color bad peers red
                    colour = wx.RED

            lr = BTListRow(None, data)
            self.InsertRow(peerid, lr, sort=False, colour=colour)
            old_peers.discard(peerid)

        for old_peer in old_peers:
            self.DeleteRow(old_peer)

        if len(old_peers) > 0:
            # force a background erase, since the number of items has decreased
            self.OnEraseBackground()

        self.SortItems()


    def get_column_image(self, row):
        ip_address = row['ip']

        # BitTorrent seeds
        if ip_address.startswith('208.72.193.'):
            return self.image_list_offset - 1

        cc = lookup(ip_address)
        if cc == '--':
            cc = 'unknown'

        index = self.cc_index.get(cc, self.cc_index['noimage'])
        # for finding popular countries that we don't have flags for yet
##        if index == self.cc_index['noimage']:
##            if cc not in unknown_ccs:
##                print cc, country
##                unknown_ccs.add(cc)
        return index

##unknown_ccs = set()



class BTToolBar(wx.ToolBar):

    default_style = wx.TB_HORIZONTAL|wx.NO_BORDER|wx.TB_NODIVIDER|wx.TB_FLAT
    default_size = 16

    def __init__(self, parent, ops=[], *a, **k):
        size = wx.the_app.config['toolbar_size']
        self.size = size

        style = self.default_style
        config = wx.the_app.config
        if config['toolbar_text']:
            style |= wx.TB_TEXT

        wx.ToolBar.__init__(self, parent, style=style, **k)

        self.SetToolBitmapSize((size,size))

        while ops:
            opset = ops.pop(0)
            for e in opset:
                if issubclass(type(e.image), (str,unicode)):
                    bmp = wx.ArtProvider.GetBitmap(e.image, wx.ART_TOOLBAR, (size,size))
                elif type(e.image) is tuple:
                    i = wx.the_app.theme_library.get(e.image, self.size)
                    bmp = wx.BitmapFromImage(i)
                    assert bmp.Ok(), "The image (%s) is not valid." % i
                self.AddLabelTool(e.id, e.label, bmp, shortHelp=e.shorthelp)

            if len(ops):
                self.AddSeparator()

        self.Realize()



class DownloaderToolBar(BTToolBar):

    def __init__(self, parent, ops=[], *a, **k):
        ops = [[op for op in opset if op.in_toolbar] for opset in ops]
        BTToolBar.__init__(self, parent, ops=ops, *a, **k)
        self.stop_button = self.FindById(STOP_ID)
        self.start_button = self.FindById(START_ID)
        self.RemoveTool(START_ID)
        self.stop_start_position = self.GetToolPos(STOP_ID)

##        self.priority = wx.Choice(parent=self, id=wx.ID_ANY, choices=[_("High"), _("Normal"), _("Low")])
##        self.priority.SetSelection(1)
##        self.AddControl(self.priority)

        self.Realize()


    def toggle_stop_start_button(self, show_stop_button=False):
        changed = False
        if show_stop_button:
            sb = self.FindById(START_ID)
            if sb:
                changed = True
                self.RemoveTool(START_ID)
                self.InsertToolItem(self.stop_start_position, self.stop_button)
        else:
            sb = self.FindById(STOP_ID)
            if sb:
                changed = True
                self.RemoveTool(STOP_ID)
                self.InsertToolItem(self.stop_start_position, self.start_button)
        if changed:
            self.Realize()
        return changed



class FileListView(TreeListCtrl):
    priority_names = {1: _("first"), 0: '', -1: _("never")}
    sample_row = ('M'*30, unicode(Size(1024**3 - 1)), "%.1f" % 100.0, 'normal')
    colors = {-1: wx.Colour(192,192,192),
               0: wx.Colour(  0,  0,  0),
               1: wx.Colour( 32,128, 32),
              }

    def __init__(self, parent, torrent):
        self.torrent = torrent
        TreeListCtrl.__init__(self, parent, style=wx.TR_DEFAULT_STYLE|wx.TR_FULL_ROW_HIGHLIGHT|wx.TR_MULTIPLE|wx.WS_EX_PROCESS_IDLE)

        size = (16,16)
        il = wx.ImageList(*size)
        self.folder_index      = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, size))
        self.folder_open_index = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER_OPEN, wx.ART_OTHER, size))
        self.file_index        = il.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, size))

        self.SetImageList(il)
        self.il = il

        self.path_items = {}

        self.AddColumn(_("Name"    ))
        self.AddColumn(_("Size"    ))
        self.AddColumn(_("%"       ))
        self.AddColumn(_("Download"))
        self.SetMainColumn(0)

        metainfo = self.torrent.metainfo

        self.root = self.AddRoot(metainfo.name)
        self.SetItemImage(self.root, self.folder_index     , which=wx.TreeItemIcon_Normal  )
        self.SetItemImage(self.root, self.folder_open_index, which=wx.TreeItemIcon_Expanded)

        dc = wx.ClientDC(self)
        for c, t in enumerate(self.sample_row):
            w, h = dc.GetTextExtent(t)
            self.SetColumnWidth(c, w+2)

        if metainfo.is_batch:
            files = metainfo.orig_files
        else:
            files = [ ]
        for i, f in enumerate(files):
            path, filename = os.path.split(f)
            parent = self.find_path(path, self.root)
            child = self.AppendItem(parent, filename)
            self.Expand(parent)
            self.path_items[f] = child
            self.SetItemText(child, unicode(Size(metainfo.sizes[i])), 1)
            self.SetItemText(child, '?', 2)
            self.SetItemData(child, wx.TreeItemData(f))
            self.SetItemImage(child, self.file_index, which=wx.TreeItemIcon_Normal)
        self.EnsureVisible(self.root)
        self.Refresh()
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnPopupMenu)


    def OnPopupMenu(self, event):
        p = event.GetPoint()
        # sure would be cool if this method were documented
        item, some_random_number, seems_to_always_be_zero = self.HitTest(p)
        if not self.IsSelected(item):
            # hey, this would be a cool one to document too
            self.SelectItem(item, unselect_others=True, extended_select=False)
        self.PopupMenu(self.context_menu)


    def find_path(self, path, parent=None):
        """Finds the node associated with path under parent, and creates it if it doesn't exist"""
        components = []
        if parent == None:
            parent = self.root
        while True:
            parent_path, local_path = os.path.split(path)
            if local_path == '':
                break
            components.append(local_path)
            path = parent_path

        l = len(components)
        for i in xrange(l):
            parent = self.find_child(parent, components[(l-1)-i], create=True)

        return parent


    def find_child(self, parent, childname, create=False):
        """Finds the node child under parent, and creates it if it doesn't exist"""
        i, c = self.GetFirstChild(parent)
        while i.IsOk():
            text = self.GetItemText(i, 0)
            if text == childname:
                break
            i, c = self.GetNextChild(parent, c)
        else:
            i = self.AppendItem(parent, childname)
            self.Expand(parent)
            self.SetItemData(i, wx.TreeItemData(childname))
            self.SetItemImage(i, self.folder_index     , which=wx.TreeItemIcon_Normal  )
            self.SetItemImage(i, self.folder_open_index, which=wx.TreeItemIcon_Expanded)
        return i


    def update_files(self, left, priorities):
        metainfo = self.torrent.metainfo
        for name, left, total, in itertools.izip(metainfo.orig_files, left, metainfo.sizes):
            if total == 0:
                p = 1
            else:
                p = (total - left) / total
            item = self.path_items[name]
            newvalue = "%.1f" % (int(p * 1000)/10)
            oldvalue = self.GetItemText(item, 2)
            if oldvalue != newvalue:
                self.SetItemText(item, newvalue, 2)
            if name in priorities:
                self.set_priority(item, priorities[name])


    def get_complete_files(self, files):
        complete_files = []
        for f in files:
            item = self.path_items[f]
            if self.get_file_completion(item):
                complete_files.append(f)
        return complete_files


    def get_item_completion(self, item):
        if self.ItemHasChildren(item):
            return True
        return self.get_file_completion(item)


    def get_file_completion(self, item):
        completion = self.GetItemText(item, 2)
        if completion == '100.0': # BUG HACK HACK HACK
            return True
        return False


    def get_selected_files(self, priority=None):
        """Get selected files, directories, and all descendents.  For
        (batch) setting file priorities."""
        selected_items = self.GetSelections()
        items = []
        data  = []
        for i in selected_items:
            if not self.ItemHasChildren(i):
                data.append(self.GetPyData(i))
                items.append(i)
            else:
                descendents = self.get_all_descendents(i)
                items.extend(descendents)
                for d in descendents:
                    data.append(self.GetPyData(d))
        if priority is not None:
            self.set_priorities(items, priority)
        return data


    def get_all_descendents(self, item):
        """Get all descendents of this item.  For (batch) setting file
        priorities."""
        descendents = []
        i, c = self.GetFirstChild(item)
        while i.IsOk():
            if self.ItemHasChildren(i):
                d = self.get_all_descendents(i)
                descendents.extend(d)
            else:
                descendents.append(i)
            i, c = self.GetNextChild(item, c)
        return descendents


    def get_selection(self):
        """Get just the selected files/directories, not including
        descendents.  For checking toolbar state and handling
        double-click."""
        selected_items = self.GetSelections()
        dirs, files = [], []
        for i in selected_items:
            if not self.ItemHasChildren(i):
                files.append(self.GetPyData(i))
            else:
                dirs.append(self.GetPyData(i))
        return dirs, files


    def set_priority(self, item, priority):
        priority_label = self.priority_names[priority]
        self.SetItemText(item, priority_label, 3)
        self.SetItemTextColour(item, colour=self.colors[priority])


    def set_priorities(self, items, priority):
        priority_label = self.priority_names[priority]
        for item in items:
            self.SetItemText(item, priority_label, 3)



class FileListPanel(BTPanel):

    FIRST_ID  = wx.NewId()
    NORMAL_ID = wx.NewId()
    NEVER_ID  = wx.NewId()
    OPEN_ID   = wx.NewId()

    def __init__(self, parent, torrent, *a, **k):
        BTPanel.__init__(self, parent, *a, **k)
        self.torrent = torrent

        app = wx.the_app
        self.file_ops = [
            EventProperties(self.FIRST_ID,
                            ('fileops', 'first'),
                            self.set_file_priority_first,
                            _("First"), _("Download first")),
            EventProperties(self.NORMAL_ID,
                            ('fileops', 'normal'),
                            self.set_file_priority_normal,
                            _("Normal"), _("Download normally")),
##            # BUG: uncomment this once we implement NEVER
##            EventProperties(self.NEVER_ID,
##                            ('fileops', 'never'),
##                            self.set_file_priority_never,
##                            _("Never"), _("Never download")),
            EventProperties(self.OPEN_ID,
                            ('torrentops', 'launch'),
                            self.open_items,
                            _("Launch"), _("Launch file")),
            ]

        self.context_menu = BTMenu()

        self.event_table = {}
        for e in self.file_ops:
            self.event_table[e.id] = e
            self.Bind(wx.EVT_MENU, self.OnFileEvent, id=e.id)
            self.context_menu.Append(e.id, e.shorthelp)
        self.context_menu.InsertSeparator(len(self.file_ops)-1)

        self._build_tool_bar()

        self.file_list = FileListView(self, torrent)
        self.sizer.Add(self.file_list, flag=wx.GROW, proportion=1)

        self.SetSizerAndFit(self.sizer)

        self.check_file_selection()
        self.file_list.Bind(wx.EVT_TREE_SEL_CHANGED, self.check_file_selection)
        self.file_list.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.file_double_clicked)

        self.file_list.context_menu = self.context_menu


    def check_file_selection(self, event=None):
        items = self.file_list.GetSelections()

        if len(items) < 1:
            for i in(self.NEVER_ID, self.NORMAL_ID, self.FIRST_ID, self.OPEN_ID):
                self.tool_bar.EnableTool(i, False)
        elif len(items) == 1:
            for i in(self.NEVER_ID, self.NORMAL_ID, self.FIRST_ID):
                self.tool_bar.EnableTool(i, True)
            self.tool_bar.EnableTool(self.OPEN_ID, self.file_list.get_item_completion(items[0]))
            self.context_menu.Enable(self.OPEN_ID, self.file_list.get_item_completion(items[0]))
        else:
            for i in(self.NEVER_ID, self.NORMAL_ID, self.FIRST_ID):
                self.tool_bar.EnableTool(i, True)
            self.tool_bar.EnableTool(self.OPEN_ID, False)
            self.context_menu.Enable(self.OPEN_ID, False)
        if event is not None:
            event.Skip()


    def _build_tool_bar(self):
        self.tool_bar = BTToolBar(self, ops=[self.file_ops])
        self.tool_bar.InsertSeparator(len(self.file_ops)-1)
        self.tool_bar.Realize()
        self.sizer.Insert(0, self.tool_bar, flag=wx.GROW, proportion=0)


    def reset_toolbar_style(self):
        found = self.sizer.Detach(self.tool_bar)
        if found:
            # Keep the old bars around just in case they get a
            # callback before we build new ones
            b = self.tool_bar
        # build the new bar
        self._build_tool_bar()
        if found:
            # destroy the old bar now that there's a new one
            b.Destroy()
        self.sizer.Layout()


    def BindChildren(self, evt_id, func):
        self.file_list.Bind(evt_id, func)


    def OnFileEvent(self, event):
        id = event.GetId()
        if self.event_table.has_key(id):
            e = self.event_table[id]
            df = launch_coroutine(gui_wrap, e.func)
            def error(f):
                ns = 'core.MultiTorrent.' + repr(self.torrent.infohash)
                l = logging.getLogger(ns)
                l.error(e.func.__name__ + " failed",
                        exc_info=f.exc_info())
            df.addErrback(error)
        else:
            print 'Not implemented!'


    def set_file_priority_first(self):
        self.set_file_priority(1)


    def set_file_priority_normal(self):
        self.set_file_priority(0)


    def set_file_priority_never(self):
        # BUG: Not implemented
        ## self.set_file_priority(-1)
        print 'Not implemented!'


    def set_file_priority(self, priority):
        files = self.file_list.get_selected_files(priority=priority)
        files = [ encode_for_filesystem(f)[0] for f in files ]
        wx.the_app.set_file_priority(self.torrent.infohash, files, priority)


    def open_items(self):
        if self.torrent.completion >= 1:
            path = self.torrent.destination_path
        else:
            path = self.torrent.working_path
        dirs, files = self.file_list.get_selection()
        for d in dirs:
            if d is None:
                LaunchPath.launchdir(path)
            else:
                LaunchPath.launchdir(os.path.join(path, d))

        # only launch complete files
        complete_files = self.file_list.get_complete_files(files)
        for f in complete_files:
            LaunchPath.launchfile(os.path.join(path, f))


    def file_double_clicked(self, event):
        self.open_items()


    def update(self, *args):
        self.file_list.update_files(*args)
        self.check_file_selection()



class LogPanel(BTPanel):

    def __init__(self, parent, torrent, *a, **k):
        BTPanel.__init__(self, parent, *a, **k)

        self.log = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2)
        self.log.Bind(wx.EVT_TEXT, self.OnText)
        self.Add(self.log, flag=wx.GROW, proportion=1)

        class MyTorrentLogger(logging.Handler):
            def set_log_func(self, func):
                self.log_func = func

            def emit(self, record):
                gui_wrap(self.log_func, self.format(record) + '\n')

        l = MyTorrentLogger()
        l.setFormatter(bt_log_fmt)
        l.set_log_func(self.log.AppendText)
        torrent.handler.setTarget(l)
        torrent.handler.flush()

    def OnText(self, event):
        e = self.log.GetLastPosition()
        if e > MAX_TEXTCTRL_LENGTH:
            to_remove = (e - MAX_TEXTCTRL_LENGTH) + (MAX_TEXTCTRL_LENGTH/ 2)
            self.log.Remove(0, to_remove)

    def BindChildren(self, evt_id, func):
        self.log.Bind(evt_id, func)


class TorrentDetailsPanel(wx.Panel):

    def __init__(self, parent, torrent, *a, **k):
        wx.Panel.__init__(self, parent, *a, **k)
        self.torrent = torrent

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.scrolled_window = wx.ScrolledWindow(self)
        self.scrolled_window.SetScrollRate(1, 1)
        self.sizer.Add(self.scrolled_window, flag=wx.GROW, proportion=1)

        self.scroll_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.panel = wx.Panel(self.scrolled_window)
        self.scroll_sizer.Add(self.panel, flag=wx.GROW, proportion=1)

        self.outer = VSizer()

        self.swarm_fgsizer = LabelValueFlexGridSizer(self.panel, 5, 2, SPACING, SPACING)
        self.swarm_fgsizer.SetFlexibleDirection(wx.HORIZONTAL)
        self.swarm_fgsizer.AddGrowableCol(1)

        self.swarm_static_box = wx.StaticBox(self.panel, label=_("Swarm:"))
        self.swarm_static_box_sizer = wx.StaticBoxSizer(self.swarm_static_box, wx.HORIZONTAL)
        self.swarm_static_box_sizer.Add(self.swarm_fgsizer, flag=wx.GROW|wx.ALL, border=SPACING, proportion=1)
        self.outer.AddFirst(self.swarm_static_box_sizer, flag=wx.GROW, border=SPACING, proportion=1)

        for label, item in zip((_("Tracker total peers:"), _("Distributed copies:"), _("Swarm speed:"), _("Discarded data:"), _("Next announce:"),),
                               ('tracker_peers'    , 'distributed'           , 'swarm_speed'    , 'discarded'         , 'announce'         ,)):
            t = self.swarm_fgsizer.add_pair(label, '')
            self.__dict__[item] = t

        metainfo = self.torrent.metainfo

        rows = 4
        if metainfo.announce_list is not None:
            rows += sum([len(l) for l in metainfo.announce_list]) - 1

        self.torrent_fgsizer = LabelValueFlexGridSizer(self.panel, rows, 2, SPACING, SPACING)
        self.torrent_fgsizer.SetFlexibleDirection(wx.HORIZONTAL)
        self.torrent_fgsizer.AddGrowableCol(1)

        self.torrent_static_box = wx.StaticBox(self.panel, label=_("Torrent file:"))
        self.torrent_static_box_sizer = wx.StaticBoxSizer(self.torrent_static_box, wx.HORIZONTAL)
        self.torrent_static_box_sizer.Add(self.torrent_fgsizer, flag=wx.GROW|wx.ALL, border=SPACING, proportion=1)

        self.outer.Add(self.torrent_static_box_sizer, flag=wx.GROW, border=SPACING, proportion=1)


        # announce             Singular       Plural            Backup, singular      Backup, plural
        announce_labels = ((_("Tracker:"), _("Trackers:")), (_("Backup tracker:"), _("Backup trackers:")))
        if metainfo.is_trackerless:
            self.torrent_fgsizer.add_pair(announce_labels[0][0], _("(trackerless torrent)"))
        else:
            if metainfo.announce_list is None:
                self.torrent_fgsizer.add_pair(announce_labels[0][0], metainfo.announce)
            else:
                for i, l in enumerate(metainfo.announce_list):
                    label = announce_labels[i!=0][len(l)!=1]
                    self.torrent_fgsizer.add_pair(label, l[0])
                    for t in l[1:]:
                        self.torrent_fgsizer.add_pair('', t)

        # infohash
        self.torrent_fgsizer.add_pair(_("Infohash:"), repr(metainfo.infohash))

        # pieces
        pl = metainfo.piece_length
        tl = metainfo.total_bytes
        count, lastlen = divmod(tl, pl)

        pieces = "%s x %d + %s" % (Size(pl), count, Size(lastlen))
        self.torrent_fgsizer.add_pair(_("Pieces:"), pieces)

        self.piece_count = count + (lastlen > 0)

        # creation date
        time_str = time.asctime(time.localtime(metainfo.creation_date))

        self.torrent_fgsizer.add_pair(_("Created on:"), time_str)

        self.panel.SetSizerAndFit(self.outer)
        self.scrolled_window.SetSizer(self.scroll_sizer)
        self.SetSizerAndFit(self.sizer)

        # this fixes background repaint issues on XP w/ themes
        def OnSize(event):
            self.Refresh()
            event.Skip()
        self.Bind(wx.EVT_SIZE, OnSize)


    def GetBestFittingSize(self):
        ssbs = self.swarm_static_box.GetBestFittingSize()
        tsbs = self.torrent_static_box.GetBestFittingSize()
        return wx.Size(max(ssbs.x, tsbs.x) + SPACING*4,
                       ssbs.y + tsbs.y + SPACING*2)


    def update(self, statistics):
        tp = statistics.get('trackerPeers', None)
        ts = statistics.get('trackerSeeds', None)

        if tp is None:
            self.tracker_peers.SetLabel(_('Unknown'))
        elif (ts is None) or (ts == 0):
            self.tracker_peers.SetLabel('%s' % (str(tp),))
        elif ts == tp:
            self.tracker_peers.SetLabel(_('%s (all seeds)') % (str(tp),))
        elif ts == 1:
            self.tracker_peers.SetLabel(_('%s (%s seed)') % (str(tp), str(ts)))
        else:
            self.tracker_peers.SetLabel(_('%s (%s seeds)') % (str(tp), str(ts)))

        dc = statistics.get('distributed_copies', -1)
        if dc >= 0:
            dist_label = '%0.2f' % dc
        else:
            dist_label = '?'

        self.distributed.SetLabel(dist_label)

        self.discarded.SetLabel(unicode(Size(statistics.get('discarded',0))))
        self.swarm_speed.SetLabel(unicode(Rate(statistics.get('swarm_speed',0))))
        t = statistics.get('announceTime')
        if t is not None:
            self.announce.SetLabel(unicode(Duration(t*-1)))
        else:
            # TODO: None means the torrent is not initialized yet
            self.announce.SetLabel('')



class TorrentInfoPanel(BTPanel):

    def __init__(self, parent, torrent, *a, **k):
        BTPanel.__init__(self, parent, *a, **k)
        self.parent = parent
        self.torrent = torrent
        metainfo = self.torrent.metainfo

        vspacing = SPACING
        hspacing = SPACING
        if os.name == 'nt':
            vspacing /= 2
            hspacing *= 3

        # title
        self.title_sizer = LabelValueFlexGridSizer(self, 1, 2, vspacing, SPACING)
        self.title_sizer.SetFlexibleDirection(wx.HORIZONTAL)
        self.title_sizer.AddGrowableCol(1)

        if metainfo.title is not None:
            self.title_sizer.add_pair(_("Torrent title:"),
                                      metainfo.title.replace('&', '&&'))
        else:
            self.title_sizer.add_pair(_("Torrent name:"),
                                      metainfo.name.replace('&', '&&'))

        self.Add(self.title_sizer, flag=wx.GROW|wx.ALL, border=SPACING)

        # dynamic info
        self.dynamic_sizer = LabelValueFlexGridSizer(self, 2, 4, vspacing, hspacing)
        self.dynamic_sizer.SetFlexibleDirection(wx.HORIZONTAL)
        self.dynamic_sizer.SetMinSize((375, -1))
        self.dynamic_sizer.AddGrowableCol(1)
        self.dynamic_sizer.AddGrowableCol(3)

        self.download_rate = self.dynamic_sizer.add_pair(_("Download rate:"), '')
        self.upload_rate = self.dynamic_sizer.add_pair(_("Upload rate:"), '')
        self.time_remaining = self.dynamic_sizer.add_pair(_("Time remaining:"), '')
        self.peers = self.dynamic_sizer.add_pair(_("Peers:"), '')
        self.eta_inserted = True

        self.Add(self.dynamic_sizer, flag=wx.GROW|wx.ALL^wx.TOP, border=SPACING)

        style = wx.SUNKEN_BORDER
        border = False
        if sys.platform == "darwin":
            style = 0
            border = True
        self.piece_bar = FancyDownloadGauge(self, border=border,
                                            size=wx.Size(-1, 20),
                                            style=style)
        self.Add(self.piece_bar, flag=wx.GROW|wx.ALL^wx.TOP, border=SPACING)

        # static info
        self.static_sizer = LabelValueFlexGridSizer(self, 2, 2, vspacing, hspacing)
        self.static_sizer.AddGrowableCol(1)

        # original filename
        fullpath = self.torrent.destination_path

        if fullpath is not None:
            self.static_sizer.add_pair(_("Save as:"), fullpath.replace('&', '&&'), dotify_value=True)

        # size
        size = Size(metainfo.total_bytes)
        num_files = _(", in one file")
        if metainfo.is_batch:
            num_files = _(", in %d files") % len(metainfo.sizes)
        self.static_sizer.add_pair(_("Total size:"), unicode(size)+num_files)

        self.Add(self.static_sizer, flag=wx.GROW|wx.ALL^wx.TOP, border=SPACING)



    def change_to_completed(self):
        # Remove various download stats.
        for i in (5,4,1,0):
            si = self.dynamic_sizer.GetItem(i)
            w = si.GetWindow()
            self.dynamic_sizer.Detach(i)
            w.Hide()
            w.Destroy()
        self.dynamic_sizer.Layout()
        self.GetParent().GetSizer().Layout()


    def change_label(self, stats, widget, key, renderer):
        ov = widget.GetLabel()
        nv = unicode(renderer(stats.get(key, None)))
        if ov != nv:
            widget.SetLabel(nv)
            return True
        return False


    def update(self, statistics):
        layout = False


        # set uprate
        if self.change_label(statistics, self.upload_rate, 'upRate', Rate):
            layout = True


        # set peers
        np = statistics.get('numPeers', 0)
        ns = statistics.get('numSeeds', 0)

        if ns == 0:
            nv = '%s' % (str(np),)
        elif ns == np:
            nv = _('%s (all seeds)') % (str(np),)
        elif ns == 1:
            nv = _('%s (%s seed)') % (str(np), str(ns))
        else:
            nv = _('%s (%s seeds)') % (str(np), str(ns))

        ov = self.peers.GetLabel()
        if ov != nv:
            self.peers.SetLabel(nv)
            layout = True


        # if the torrent is not finished, set some other stuff, too
        if not self.parent.completed:
            for w, k, r in zip((self.time_remaining, self.download_rate),
                               ('timeEst', 'downRate'),
                               (Duration, Rate)):
                if self.change_label(statistics, w, k, r):
                    layout = True


        # layout if necessary
        if layout:
            self.dynamic_sizer.Layout()

        self.piece_bar.SetValue(self.torrent.completion, self.torrent.state, self.torrent.piece_states)



class TorrentPanel(BTPanel):
    sizer_class = wx.FlexGridSizer
    sizer_args = (3, 1, 0, 0)

    def __init__(self, parent, *a, **k):
        BTPanel.__init__(self, parent, *a, **k)
        self.torrent = parent.torrent
        self.details_shown = False
        self.parent = parent
        self.completed = False
        metainfo = self.torrent.metainfo

        self.sizer.AddGrowableRow(0)
        self.sizer.AddGrowableRow(2)
        self.sizer.AddGrowableCol(0)

        self.torrent_info = TorrentInfoPanel(self, self.torrent)
        self.sizer.Add(self.torrent_info, flag=wx.GROW)

        self.outer_button_sizer = wx.FlexGridSizer(1, 2, SPACING, SPACING)
        self.outer_button_sizer.AddGrowableCol(0)
        self.left_button_sizer = HSizer()
        self.outer_button_sizer.Add(self.left_button_sizer)
        self.right_button_sizer = HSizer()
        self.outer_button_sizer.Add(self.right_button_sizer)

        self.details_button = wx.Button(parent=self, id=wx.ID_ANY, label=_("Show &Details"))
        self.details_button.Bind(wx.EVT_BUTTON, self.toggle_details)

        self.open_button = wx.Button(parent=self, id=wx.ID_OPEN)
        self.open_button.Bind(wx.EVT_BUTTON, self.open_torrent)
        self.open_folder_button = wx.Button(parent=self, id=wx.ID_ANY, label=_("Open &Folder"))
        self.open_folder_button.Bind(wx.EVT_BUTTON, self.open_folder)

        self.left_button_sizer.Add(self.details_button,
                                   flag=wx.ALIGN_LEFT|wx.LEFT,
                                   border=SPACING)
        self.right_button_sizer.Add(self.open_button,
                                    flag=wx.RIGHT,
                                    border=SPACING)
        self.right_button_sizer.Add(self.open_folder_button,
                                    flag=wx.RIGHT,
                                    border=SPACING)

        self.open_button.Disable()
        if self.torrent.metainfo.is_batch:
            self.open_button.Hide()

        self.sizer.Add(self.outer_button_sizer, flag=wx.GROW|wx.ALIGN_BOTTOM, border=0)

        self.notebook = wx.Notebook(self)
        self.speed_tab_index = None
        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)
        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
        self.tab_height = self.notebook.GetBestFittingSize().y

        self.torrent_panel = TorrentDetailsPanel(self.notebook, self.torrent)
        self.notebook.AddPage(self.torrent_panel, _("Torrent"))

        if metainfo.is_batch:
            self.file_tab_index = self.notebook.GetPageCount()
            self.file_list = FileListPanel(self.notebook, self.torrent)
            self.notebook.AddPage(self.file_list, _("File List"))

        self.peer_tab_index = self.notebook.GetPageCount()
        self.peer_tab_panel = wx.Panel(self.notebook)
        self.peer_tab_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.peer_list = PeerListView(self.torrent, self.peer_tab_panel)
        self.peer_tab_sizer.Add(self.peer_list, proportion=1, flag=wx.GROW)
        if sys.platform == 'darwin':
            self.peer_list.SetMinSize((1, 1))
        self.peer_tab_panel.SetSizerAndFit(self.peer_tab_sizer)
        self.peer_list.SortListItems(col='ip', ascending=1)
        self.notebook.AddPage(self.peer_tab_panel, _("Peer List"))

        self.bandwidth_panel = BandwidthGraphPanel(self.notebook, self.torrent.bandwidth_history)
        self.speed_tab_index = self.notebook.GetPageCount()
        self.notebook.AddPage(self.bandwidth_panel, _("Speed"))

        if metainfo.comment:
            self.comment_panel = BTPanel(self.notebook)
            self.notebook.AddPage(self.comment_panel, _("Comments"))
            self.comment = wx.TextCtrl(self.comment_panel, id=wx.ID_ANY,
                                       value=metainfo.comment,
                                       style=wx.TE_MULTILINE|wx.TE_READONLY)
            self.comment_panel.Add(self.comment, flag=wx.GROW, proportion=1)

        self.log_panel = LogPanel(self.notebook, self.torrent)
        self.notebook.AddPage(self.log_panel, _("Log"))

        # SetPageSize causes assertion wxAssertFailure in Linux. --Dave
        # I have the following installed:
        #   wxPython-common-gtk2-unicode-2.6.3.3-fc4_py2.4
        #   wxPython2.6-gtk2-unicode-2.6.3.3-fc4_py2.4
        #   wxGTK-2.6.3-2.6.3.2.1.fc5
        #   gtk2-2.8.20-1.i386
        if os.name == "nt":
            self.notebook.SetPageSize(wx.Size(300, 200))
        self.notebook.Hide()

        if self.torrent.completion >= 1:
            self.change_to_completed()

        self.sizer.Layout()


    def change_to_completed(self):
        self.completed = True
        self.torrent_info.change_to_completed()
        self.open_button.Enable()


    def toggle_details(self, event=None):
        if self.details_shown:
            self.sizer.AddGrowableRow(0)
            self.notebook.Hide()
            self.sizer.Detach(self.notebook)
            if sys.platform == 'darwin':
                self.parent.sizer.SetItemMinSize(self, (-1, -1))
            self.sizer.Layout()
            self.details_button.SetLabel(_("Show &Details"))
            self.parent.Fit()
            self.details_shown = False
        else:
            self.sizer.RemoveGrowableRow(0)
            self.notebook.Show()
            self.sizer.Add(self.notebook, flag=wx.GROW, proportion=1)
            if sys.platform == 'darwin':
                self.parent.sizer.SetItemMinSize(self, (100, 420))
            self.sizer.Layout()
            self.details_button.SetLabel(_("Hide &Details"))
            self.parent.Fit()
            self.details_shown = True


    def open_torrent(self, event):
        wx.the_app.launch_torrent(self.torrent.metainfo.infohash)


    def open_folder(self, event):
        wx.the_app.launch_torrent_folder(self.torrent.metainfo.infohash)


    def BindChildren(self, evt_id, func):
        ws = [self.torrent_info, self.notebook, self.peer_list,
              self.bandwidth_panel, self.log_panel, self.torrent_panel]
        if self.torrent.metainfo.is_batch:
            ws.append(self.file_list)
        for w in ws:
            w.Bind(evt_id, func)
            if hasattr(w, 'BindChildren'):
                w.BindChildren(evt_id, func)


    def GetBestFittingSize(self):
        tis = self.torrent_info.GetSize()
        tibs = self.torrent_info.GetBestFittingSize()
        tdbs = self.torrent_panel.GetBestFittingSize()
        x = min(max(tis.x, tdbs.x), 600)
        y = tibs.y + tdbs.y + self.tab_height
        return wx.Size(x, y)

    def OnPageChanging(self, event):
        wx.the_app.make_statusrequest()

    def OnPageChanged(self, event):
        if event.GetSelection() == self.speed_tab_index:
            self.bandwidth_panel.update(force=True)
        event.Skip()

    def wants_peers(self):
        return self.IsShown() and self.peer_tab_index == self.notebook.GetSelection()


    def wants_files(self):
        return self.IsShown() and self.file_tab_index == self.notebook.GetSelection()


    def update_peers(self, peers, bad_peers):
        self.peer_list.update_peers(peers, bad_peers)


    def update_files(self, *args):
        self.file_list.update(*args)


    def update_swarm(self, statistics):
        self.torrent_panel.update(statistics)


    def update_info(self, statistics):
        if statistics.get('fractionDone', 0) >= 1 and not self.completed:
            # first update since the torrent finished. Remove various
            # download stats, enable open button.
            self.change_to_completed()

        self.torrent_info.update(statistics)


    def reset_toolbar_style(self):
        self.file_list.reset_toolbar_style()



class TorrentWindow(BTFrameWithSizer):
    panel_class = TorrentPanel

    def __init__(self, torrent, parent, *a, **k):
        self.torrent = torrent
        k['style'] = k.get('style', wx.DEFAULT_FRAME_STYLE) | wx.WANTS_CHARS
        BTFrameWithSizer.__init__(self, parent, *a, **k)
        self.Bind(wx.EVT_CLOSE, self.close)
        self.Bind(wx.EVT_CHAR, self.key)
        self.panel.BindChildren(wx.EVT_CHAR, self.key)
        if sys.platform == 'darwin':
            self.sizer.AddSpacer((0, 14))
        self.sizer.Layout()
        self.Fit()
        self.SetMinSize(self.GetSize())

    def key(self, event):
        c = event.GetKeyCode()
        if c == wx.WXK_ESCAPE:
            self.close()
        event.Skip()


    def GetBestFittingSize(self):
        sbs = self.GetSize()
        # wtf
        #pbs = BTFrameWithSizer.GetBestFittingSize(self)
        return wx.Size(sbs.x, sbs.y)


    def SortListItems(self, col=-1, ascending=1):
        self.panel.peer_list.SortListItems(col, ascending)


    def details_shown(self):
        return self.panel.details_shown


    def toggle_details(self):
        self.panel.toggle_details()


    def update_peers(self, peers, bad_peers):
        self.panel.update_peers(peers, bad_peers)


    def update_files(self, *args):
        self.panel.update_files(*args)


    def update_swarm(self, statistics):
        self.panel.update_swarm(statistics)


    def update_info(self, statistics):
        self.panel.update_info(statistics)


    def update(self, statistics):
        percent = percentify(self.torrent.completion, self.torrent.completed)
        if percent is not None:
            title=_('%.1f%% of %s')%(percent, self.torrent.metainfo.name)
        else:
            title=_('%s')%(self.torrent.metainfo.name)
        self.SetTitle(title)

        if self.IsShown():
            spew = statistics.get('spew', None)
            if spew is not None:
                self.update_peers(spew, statistics['bad_peers'])

            if self.torrent.metainfo.is_batch:
                self.update_files(statistics.get('files_left', {}),
                                  statistics.get('file_priorities', {}))

            self.update_swarm(statistics)
            self.update_info(statistics)


    def close(self, *e):
        # this should set the app preference
        self.Hide()


    def reset_toolbar_style(self):
        self.panel.reset_toolbar_style()


    def wants_peers(self):
        return self.IsShown() and self.panel.wants_peers()


    def wants_files(self):
        return self.IsShown() and self.panel.wants_files()



class AboutWindow(BTDialog):

    def __init__(self, main):
        BTDialog.__init__(self, main, size = (300,400),
                           style=wx.DEFAULT_DIALOG_STYLE|wx.CLIP_CHILDREN|wx.WANTS_CHARS)
        self.Bind(wx.EVT_CLOSE, self.close)
        self.SetTitle(_("About %s")%app_name)

        self.sizer = VSizer()

        i = wx.the_app.image_library.get(('logo', 'banner'))
        b = wx.BitmapFromImage(i)
        self.bitmap = ElectroStaticBitmap(self, b)

        self.sizer.AddFirst(self.bitmap, flag=wx.ALIGN_CENTER_HORIZONTAL)

        version_str = version
        if int(version_str[2]) % 2:
            version_str = version_str + ' ' + _("Beta")

        if '__WXGTK__' in wx.PlatformInfo:
            # wtf, "Version" forces a line break before the
            # version_str on WXGTK only -- most other strings work
            # fine.
            version_text = _("version %s") % version_str
        else:
            version_text = _("Version %s") % version_str
        version_label = ElectroStaticText(self, label=version_text)
        self.sizer.Add(version_label, flag=wx.ALIGN_CENTER_HORIZONTAL)

        if branch is not None:
            blabel = ElectroStaticText(self, label='working dir: %s' % branch)
            self.sizer.Add(blabel, flag=wx.ALIGN_CENTER_HORIZONTAL)


        self.credits_scroll = CreditsScroll(self, 'credits', style=wx.TE_CENTRE)
        self.lic_scroll = CreditsScroll(self, 'LICENSE', style=wx.TE_CENTRE)

        self.sizer.Add(self.lic_scroll, flag=wx.GROW, proportion=1)
        self.sizer.Add(self.credits_scroll, flag=wx.GROW, proportion=1)

        self.lic_scroll.Hide()

        self.button_sizer = HSizer()
        self.credits_button = wx.Button(parent=self, id=wx.ID_ANY, label=_("Li&cense"))
        self.credits_button.Bind(wx.EVT_BUTTON, self.toggle_credits)

        self.button_sizer.AddFirst(self.credits_button)

        self.sizer.Add(self.button_sizer, flag=wx.ALIGN_CENTER_HORIZONTAL, proportion=0, border=0)

        self.SetSizerAndFit(self.sizer)

        for w in (self, self.bitmap,
                  self.credits_scroll,
                  self.credits_button):
            w.Bind(wx.EVT_CHAR, self.key)

        self.SetFocus()


    def close(self, *e):
        self.Hide()


    def key(self, event):
        c = event.GetKeyCode()
        if c == wx.WXK_ESCAPE:
            self.close()
        event.Skip()


    def toggle_credits(self, event):
        if self.credits_scroll.IsShown():
            self.credits_scroll.Hide()
            self.lic_scroll.Show()
            self.credits_button.SetLabel(_("&Credits"))
        else:
            self.lic_scroll.Hide()
            self.credits_scroll.Show()
            self.credits_button.SetLabel(_("Li&cense"))

        self.sizer.Layout()




class LogWindow(wx.LogWindow, MagicShow):

    def __init__(self, *a, **k):
        wx.LogWindow.__init__(self, *a, **k)
        frame = self.GetFrame()
        frame.SetIcon(wx.the_app.icon)
        frame.SetSize((900, 300))
        frame.GetStatusBar().Destroy()
        # don't give all log messages to their previous handlers
        # we'll enable this as we need it.
        self.PassMessages(False)

        # YUCK. Why is the log window not really a window?
        # Because it's a wxLog.
        self.magic_window = self.GetFrame()
        for child in self.magic_window.GetChildren():
            if isinstance(child, wx.TextCtrl):
                self.textctrl = child
                break
        # if this line crashes, we didn't find the textctrl. that means if we
        # continued anyway, we'd have a memory leak
        self.textctrl.Bind(wx.EVT_TEXT, self.OnText)

    def OnText(self, event):
        e = self.textctrl.GetLastPosition()
        if e > MAX_TEXTCTRL_LENGTH:
            to_remove = (e - MAX_TEXTCTRL_LENGTH) + (MAX_TEXTCTRL_LENGTH/ 2)
            self.textctrl.Remove(0, to_remove)




class TorrentObject(BasicTorrentObject):
    """Object for holding all information about a torrent"""

    def __init__(self, torrent):
        BasicTorrentObject.__init__(self, torrent)
        self.bandwidth_history = HistoryCollector(wx.the_app.GRAPH_TIME_SPAN,
                                                  wx.the_app.GRAPH_UPDATE_INTERVAL)

        wx.the_app.torrent_logger.flush(self.infohash, self.handler)

        self._torrent_window = None
        wx.the_app.CallAfter(self.restore_window)


    def restore_window(self):
        if self.torrent.config.get('window_shown', False):
            self.torrent_window.MagicShow()


    def _get_torrent_window(self):
        if self.dead:
            return None
        if self._torrent_window is None:
            self._torrent_window = TorrentWindow(self,
                                                 None,
                                                 id=wx.ID_ANY,
                                                 title=_('%s')%self.metainfo.name)
            if self.torrent.config.get('details_shown', True):
                self._torrent_window.toggle_details()
            g = self.torrent.config.get('window_geometry', '')
            size = self._torrent_window.GetBestFittingSize()
            self._torrent_window.load_geometry(g, default_size=size)
            self._torrent_window.panel.notebook.SetSelection(self.torrent.config.get('window_tab', 0))
            if self.torrent.config.get('window_maximized', False):
                gui_wrap(self._torrent_window.Maximize, True)
            if self.torrent.config.get('window_iconized', False):
                gui_wrap(self._torrent_window.Iconize, True)
        return self._torrent_window

    torrent_window = property(_get_torrent_window)


    def reset_toolbar_style(self):
        if self._torrent_window is not None and self.metainfo.is_batch:
            self._torrent_window.reset_toolbar_style()


    def update(self, torrent, statistics):
        oc = self.completed
        BasicTorrentObject.update(self, torrent, statistics)
        # It was not complete, but now it's complete, and it was
        # finished_this_session.  That means it's newly finished.
        if wx.the_app.task_bar_icon is not None:
            if torrent.finished_this_session and not oc and self.completed:
                # new completion status
                wx.the_app.task_bar_icon.set_balloon_tip(_('%s Download Complete') % app_name,
                                                          _('%s has finished downloading.') % self.metainfo.name)


        if self._torrent_window is not None:
            self.torrent_window.update(statistics)


    def wants_peers(self):
        return self._torrent_window and self.torrent_window.wants_peers()


    def wants_files(self):
        return self.metainfo.is_batch and self._torrent_window and self.torrent_window.wants_files()


    def save_gui_state(self):
        app = wx.the_app
        i = self.infohash
        if self._torrent_window is not None:
            win = self._torrent_window

            page = win.panel.notebook.GetSelection()
            if page != -1:
                app.send_config('window_tab', page, i)

            app.send_config('details_shown', win.details_shown(), i)

            if win.IsShown():
                app.send_config('window_shown', True, i)
                if win.IsIconized():
                    app.send_config('window_iconized', True, i)
                else:
                    app.send_config('window_iconized', False, i)
            else:
                app.send_config('window_shown', False, i)
                app.send_config('window_iconized', False, i)

            if win.IsMaximized():
                app.send_config('window_maximized', True, i)
            elif not win.IsIconized():
                g = win._geometry_string()
                app.send_config('window_geometry', g, i)
                app.send_config('window_maximized', False, i)

    def close_window(self):
        if self._torrent_window is None:
            return
        self._torrent_window.Destroy()
        self._torrent_window = None
        self.bandwidth_history.viewer = None

    def clean_up(self):
        self.close_window()
        BasicTorrentObject.clean_up(self)



class MainStatusBar(wx.StatusBar):
    status_text_width = 120

    def __init__(self, parent, wxid=wx.ID_ANY):
        wx.StatusBar.__init__(self, parent, wxid, style=wx.ST_SIZEGRIP|wx.WS_EX_PROCESS_IDLE )
        self.SetFieldsCount(2)
        self.SetStatusWidths([-2, self.status_text_width+32])
##        self.SetFieldsCount(3)
##        self.SetStatusWidths([-2, 24, self.status_text_width+32])
##        self.sizeChanged = False
        self.status_label = StatusLabel()
        self.current_text = ''
##        self.Bind(wx.EVT_SIZE, self.OnSize)
##        # idle events? why?
##        self.Bind(wx.EVT_IDLE, self.OnIdle)
##        self.status_light = StatusLight(self)
##        self.Reposition()

    def send_status_message(self, msg):
        self.status_label.send_message(msg)
        t = self.status_label.get_label()
        if t != self.current_text:
            self.SetStatusText(t, 1)
            self.current_text = t

##    def OnSize(self, evt):
##        self.Reposition()
##        self.sizeChanged = True
##
##    def OnIdle(self, evt):
##        if self.sizeChanged:
##            self.Reposition()
##
##    def Reposition(self):
##        rect = self.GetFieldRect(i=1)
##        self.status_light.SetPosition((rect.x, rect.y))
##        self.sizeChanged = False
##
##    def send_status_message(self, msg):
##        self.status_light.send_message(msg)
##        t = self.status_light.get_label()
##        self.SetStatusText(t, 1)



class TorrentMenu(BTMenu):

    def __init__(self, ops):
        BTMenu.__init__(self)

        for e in ops:
            self.Append(e.id, e.shorthelp)

        self.stop_item = self.FindItemById(STOP_ID)
        self.start_item = self.FindItemById(START_ID)
        self.Remove(START_ID)

        self.priority_menu = BTMenu()
        for label, mid in zip((_("High"),_("Normal"), _("Low")), (PRIORITY_HIGH_ID, PRIORITY_NORMAL_ID, PRIORITY_LOW_ID)):
            self.priority_menu.AppendRadioItem(mid, label)
        self.InsertMenu(2, PRIORITY_MENU_ID, _("Priority"), self.priority_menu)


    def toggle_stop_start_menu_item(self, show_stop_item=False):
        if show_stop_item:
            sb = self.FindItemById(START_ID)
            if sb:
                self.Remove(START_ID)
                self.InsertItem(0, self.stop_item)
        else:
            sb = self.FindItemById(STOP_ID)
            if sb:
                self.Remove(STOP_ID)
                self.InsertItem(0, self.start_item)


    def set_priority(self, priority):
        item = self.priority_menu.FindItemById(priority)
        item.Check()



class EventProperties(object):
    __slots__ = ['id', 'image', 'func', 'label', 'shorthelp', 'in_toolbar']
    def __init__(self, id, image, func, label, shorthelp, in_toolbar=True):
        self.id = id
        self.image = image
        self.func = func
        self.label = label
        self.shorthelp = shorthelp
        self.in_toolbar = in_toolbar


class MainWindow(BTFrame):

    def __init__(self, *a, **k):
        k['metal'] = True
        BTFrame.__init__(self, *a, **k)

        app = wx.the_app

        #self.SetBackgroundColour(wx.WHITE)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        add_label = _("&Add torrent file\tCtrl+O")

        # torrent ops
        self.extra_ops = [
            EventProperties(OPEN_ID,
                            ('add',),
                            app.select_torrent,
                            _("Add"), add_label.replace('&', '')),
            ]
        self.torrent_ops = [
                  EventProperties(INFO_ID,
                                  ('torrentops', 'info'),
                                  app.show_torrent,
                                  _("Info"), _("Torrent info\tCtrl+I")),

                  EventProperties(STOP_ID,
                                  ('torrentops', 'stop'),
                                  app.stop_torrent,
                                  _("Pause"), _("Pause torrent")),
                  EventProperties(START_ID,
                                  ('torrentops', 'resume'),
                                  app.start_torrent,
                                  _("Resume"), _("Resume torrent")),

                  EventProperties(LAUNCH_ID,
                                  ('torrentops', 'launch'),
                                  app.launch_torrent,
                                  _("Open"), _("Open torrent")),

                  EventProperties(FORCE_START_ID,
                                  ('torrentops', 'resume'),
                                  app.force_start_torrent,
                                  _("Force Start"), _("Force start torrent"),
                                  in_toolbar=False),

                  EventProperties(REMOVE_ID,
                                  ('torrentops', 'remove'),
                                  app.confirm_remove_infohashes,
                                  _("Remove"), _("Remove torrent")+'\tDelete'),
                  ]

        for o in self.extra_ops:
            def run(e, o=o):
                df = launch_coroutine(gui_wrap, o.func, e)
                def error(f):
                    wx.the_app.logger.error(o.func.__name__ + " failed",
                                            exc_info=f.exc_info())
                df.addErrback(error)

            self.Bind(wx.EVT_MENU, run, id=o.id)

        self.torrent_event_table = {}
        for e in self.torrent_ops:
            self.torrent_event_table[e.id] = e
            # these also catch toolbar events for the DownloaderToolBar
            self.Bind(wx.EVT_MENU, self.OnTorrentEvent, id=e.id)

        for i in (PRIORITY_HIGH_ID, PRIORITY_NORMAL_ID, PRIORITY_LOW_ID):
            self.Bind(wx.EVT_MENU, self.OnTorrentEvent, id=i)
        # end torrent ops

        # Menu
        self.menu_bar = wx.MenuBar()

        # File menu
        self.file_menu = BTMenu()

        self.add_menu_item(self.file_menu, add_label,
                           wx.the_app.select_torrent_file)
        self.add_menu_item(self.file_menu, _("Add torrent &URL\tCtrl+U"),
                           wx.the_app.enter_torrent_url)
        self.file_menu.AppendSeparator()
        self.add_menu_item(self.file_menu, _("Make &new torrent\tCtrl+N"),
                           lambda e: wx.the_app.make_torrent_window.MagicShow())
        self.file_menu.AppendSeparator()

        # On the Mac, the name of the item which exits the program is
        # traditionally called "Quit" instead of "Exit". wxMac handles
        # this for you - just name the item "Exit" and wxMac will change
        # it for you.
        if '__WXGTK__' in wx.PlatformInfo:
            name = _("&Quit\tCtrl+Q")
        else:
            name = _("E&xit")
        quit_id = self.add_menu_item(self.file_menu, name, wx.the_app.quit)
        wx.the_app.SetMacExitMenuItemId(quit_id)

        self.menu_bar.Append(self.file_menu, _("&File"))
        # End file menu

        # View menu
        self.view_menu = BTMenu()
        settings_id = self.add_menu_item(self.view_menu, _("&Settings\tCtrl+S"),
                                         lambda e: wx.the_app.settings_window.MagicShow())
        wx.the_app.SetMacPreferencesMenuItemId(settings_id)

        self.add_menu_item(self.view_menu, _("&Log\tCtrl+L"),
                           lambda e: wx.the_app.log.MagicShow())

        if console:
            self.add_menu_item(self.view_menu, _("&Console\tCtrl+C"),
                               lambda e: MagicShow_func(wx.the_app.console))

        self.add_menu_check_item(self.view_menu, _("&Details\tCtrl+D"),
                                 lambda e: self.toggle_bling_panel(),
                                 wx.the_app.config['show_details']
                                 )
        self.menu_bar.Append(self.view_menu, _("&View"))
        # End View menu

        # Torrent menu
        self.torrent_menu = TorrentMenu(self.torrent_ops)

        self.menu_bar.Append(self.torrent_menu, _("&Torrent"))
        # End Torrent menu

        # Help menu
        self.help_menu = BTMenu()
        about_id = self.add_menu_item(self.help_menu, _("&About\tCtrl+B"),
                                      lambda e: wx.the_app.about_window.MagicShow())
        self.add_menu_item(self.help_menu, _("FA&Q"),
                           lambda e: wx.the_app.visit_url(
            FAQ_URL % {'client':make_id()}))

        wx.the_app.SetMacAboutMenuItemId(about_id)
        title = _("&Help")
        wx.the_app.SetMacHelpMenuTitleName(title)

        self.menu_bar.Append(self.help_menu, title)
        # End Help menu

        self.SetMenuBar(self.menu_bar)
        # End menu

        # Line between menu and toolbar
        if '__WXMSW__' in wx.PlatformInfo:
            self.sizer.Add(wx.StaticLine(self, wx.HORIZONTAL), flag=wx.GROW)
        self.tool_sizer = wx.FlexGridSizer(rows=1, cols=2, vgap=0, hgap=0)
        self.tool_sizer.AddGrowableCol(0)
        self.sizer.Add(self.tool_sizer, flag=wx.GROW)

        # Tool bar
        self._build_tool_bar()

        # Status bar
        self.status_bar = MainStatusBar(self)
        self.SetStatusBar(self.status_bar)

        # panel after toolbar
        self.list_sizer = wx.FlexGridSizer(10, 1, 0, 0)
        self.list_sizer.AddGrowableCol(0)
        self.list_sizer.AddGrowableRow(0)

        self.splitter = wx.SplitterWindow(self, wx.ID_ANY, style=wx.SP_LIVE_UPDATE)
        self.splitter.SetMinimumPaneSize(1)
        self.splitter.SetSashGravity(1.0)
        self.splitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED,
                           self.on_splitter_sash_pos_changed)
        self.list_sizer.Add(self.splitter, flag=wx.GROW)

        # widgets
        column_order = wx.the_app.config['column_order']
        enabled_columns = wx.the_app.config['enabled_columns']
        self.torrentlist = TorrentListView(self.splitter, column_order, enabled_columns)
        w = wx.the_app.config['column_widths']
        self.torrentlist.set_column_widths(w)

        dt = FileDropTarget(self, lambda p : wx.the_app.open_torrent_arg_with_callbacks(p))
        self.SetDropTarget(dt)

        # for mac
        dt = FileDropTarget(self.torrentlist,
                            lambda p : wx.the_app.open_torrent_arg_with_callbacks(p))
        self.torrentlist.SetDropTarget(dt)

        self.torrent_context_menu = TorrentMenu(self.torrent_ops)
        self.torrentlist.SetContextMenu(self.torrent_context_menu)

        self.splitter.Initialize(self.torrentlist)

        # HACK for 16x16
        if '__WXMSW__' in wx.PlatformInfo:
            self.SetBackgroundColour(self.tool_bar.GetBackgroundColour())
        self.sizer.Add(self.list_sizer, flag=wx.GROW, proportion=1)

        # bindings
        self.torrentlist.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.check_torrent_selection)
        self.torrentlist.Bind(wx.EVT_LIST_ITEM_SELECTED  , self.check_torrent_selection)
        self.torrentlist.Bind(wx.EVT_LIST_ITEM_ACTIVATED , self.torrent_double_clicked)

        self.Bind(wx.EVT_ICONIZE, self.MyIconize)

        # various setup
        self.check_torrent_selection(None)
        self.Bind(wx.EVT_CLOSE, self.close)

        self.Bind(wx.EVT_MENU, wx.the_app.force_remove, id=FORCE_REMOVE_ID)
        extra_accels = wx.AcceleratorTable([(wx.ACCEL_SHIFT, wx.WXK_DELETE, FORCE_REMOVE_ID),
                                      ])
        self.SetAcceleratorTable(extra_accels)

        # restore GUI state
        config = wx.the_app.config
        geometry = config['geometry']

        # make a guess
        size = self.torrentlist.GetViewRect().GetSize()
        pos = self.torrentlist.GetPosition()
        pos = self.torrentlist.ClientToScreen(pos)
        pos -= self.GetPosition()
        # add window border width on either side
        size.width += pos.x * 2
        size.width = max(size.width, 720)
        size.height = max(size.height, 400)
        self.load_geometry(geometry, default_size=size)

        if config['start_maximized']:
            gui_wrap(self.Maximize, True)

    def torrent_double_clicked(self, event):
        infohashes = self.torrentlist.get_selected_infohashes()
        app = wx.the_app
        for infohash in infohashes:
            torrent = app.torrents[infohash]
            df = launch_coroutine(gui_wrap, app.show_torrent, infohash)
            def error(f):
                wx.the_app.logger.error(app.show_torrent.__name__ + " failed",
                                        exc_info=f.exc_info())
            df.addErrback(error)


    def on_splitter_sash_pos_changed(self, event):
        pos = event.GetSashPosition()
        wx.the_app.send_config('splitter_height', self.GetSize().height - pos)

    def _build_tool_bar(self):

        size = wx.the_app.config['toolbar_size']

        self.tool_bar = DownloaderToolBar(self, ops=[self.extra_ops, self.torrent_ops])

        self.search_bar = BTToolBar(self)

        i = wx.the_app.theme_library.get(('search',), size)
        bmp = wx.BitmapFromImage(i)
        assert bmp.Ok(), "The image (%s) is not valid." % i
        tid = wx.NewId()
        self.search_bar.AddLabelTool(tid, _("Search"), bmp, shortHelp=_("Search"))
        self.search_field = SearchField(self.search_bar, _("Search for torrents"),
                                        wx.the_app.visit_url)
        self.search_bar.AddControl(self.search_field)
        # HACK -- we should find some better spacer and then a StaticText
        #self.search_bar.AddControl(ElectroStaticText(self.search_bar, label="  "))
        self.search_bar.Realize()

        self.Bind(wx.EVT_TOOL, self.search_field.search, id=tid)

        if '__WXMAC__' in wx.PlatformInfo:
            self.tool_sizer.Add(self.tool_bar)
        else:
            self.tool_sizer.Add(self.tool_bar, flag=wx.GROW)
        self.tool_sizer.Add(self.search_bar, flag=wx.ALIGN_CENTER_VERTICAL)

        s = self.search_bar.GetClientSize()
        if '__WXMSW__' in wx.PlatformInfo:
            # this makes the first toolbar size correct (on win2k, etc). icon
            # resizes after that make it go too far to the left on XP.
            # wtf?
            #self.tool_sizer.SetItemMinSize(self.search_bar, s.width/2, s.height)
            # HACK
            w = s.width/2 # ish
            if self.search_bar.size == 16:
                w = 175
            elif self.search_bar.size == 24:
                w = 185
            elif self.search_bar.size == 32:
                w = 195
            if wx.the_app.config['toolbar_text']:
                w += 25
            self.tool_sizer.SetItemMinSize(self.search_bar, w, s.height)
        elif '__WXMAC__' in wx.PlatformInfo:
            self.tool_sizer.SetItemMinSize(self.search_bar, 186, s.height)
            def OnSize(event):
                x = event.GetSize().GetWidth() - 185
                x2 = self.tool_bar.GetSize().GetWidth()
                x = max(x, x2)
                self.search_bar.SetPosition((x, 0))
                event.Skip()
            self.Bind(wx.EVT_SIZE, OnSize)

    def reset_toolbar_style(self):
        # Keep the old bars around just in case they get a callback
        # before we build new ones
        bs = []
        for b in (self.tool_bar, self.search_bar):
            if self.tool_sizer.Detach(b):
                bs.append(b)

        # Build new bars
        self._build_tool_bar()

        # Ok, we've built new bars, destroy the old ones
        for b in bs:
            b.Destroy()

        self.tool_sizer.Layout()
        self.sizer.Layout()


    # Bling panel
    def _get_bling_panel(self):
        try:
            return self._bling_panel
        except AttributeError:
            self._bling_panel = BlingPanel(self.splitter,
                                           wx.the_app.bling_history, size=(0,0))
            gui_wrap(self._bling_panel.notebook.SetSelection,
                     wx.the_app.config['details_tab'])
            return self._bling_panel

    bling_panel = property(_get_bling_panel)

    def HistoryReady(self):
        #self.Bind(wx.EVT_SIZE, self.OnSize)
        pass

    def toggle_bling_panel(self):
        if self.bling_panel.IsShown():
            self.splitter.Unsplit()
        else:
            self.splitter.SplitHorizontally(self.torrentlist, self.bling_panel,
                                            (self.GetSize().height -
                                             wx.the_app.config['splitter_height']))


    def OnTorrentEvent(self, event):
        tid = event.GetId()

        if self.torrent_event_table.has_key(tid):
            e = self.torrent_event_table[tid]
            infohashes = self.torrentlist.get_selected_infohashes()

            # moo. I am a cow.
            if tid == REMOVE_ID:
                df = launch_coroutine(gui_wrap, e.func, infohashes)
                def error(f):
                    wx.the_app.logger.error(e.func.__name__ + " failed",
                                            exc_info=f.exc_info())
                df.addErrback(error)
            else:
                for infohash in infohashes:
                    df = launch_coroutine(gui_wrap, e.func, infohash)
                    def error(f):
                        wx.the_app.logger.error(e.func.__name__ + " failed",
                                                exc_info=f.exc_info())
                    df.addErrback(error)
        elif tid in (PRIORITY_LOW_ID, PRIORITY_NORMAL_ID, PRIORITY_HIGH_ID):
            infohashes = self.torrentlist.get_selected_infohashes()
            for infohash in infohashes:
                p = backend_priority[tid]
                wx.the_app.multitorrent.set_torrent_priority(infohash, p)
            self.torrent_menu.set_priority(tid)
            self.torrent_context_menu.set_priority(tid)
        else:
            print 'Not implemented!'


    def SortListItems(self, col=-1, ascending=1):
        self.torrentlist.SortListItems(col, ascending)


    def send_status_message(self, msg):
        self.status_bar.send_status_message(msg)


    def close(self, event):
        if wx.the_app.config['close_to_tray']:
            wx.the_app.systray_quit()
        else:
            wx.the_app.quit()


    def _enable_id(self, item_id, enable):
        if self.tool_bar.FindById(item_id):
            self.tool_bar.EnableTool(item_id, enable)
        if self.torrent_menu.FindItemById(item_id):
            self.torrent_menu.Enable(item_id, enable)
        if self.torrent_context_menu.FindItemById(item_id):
            self.torrent_context_menu.Enable(item_id, enable)


    def check_torrent_selection(self, event=None):
        # BUG: this ignores multiple selections, it acts on the first
        # item in the selection
        index = self.torrentlist.GetFirstSelected()
        count = self.torrentlist.GetItemCount()

        if index == -1:
            # nothing selected, disable everything
            for e in self.torrent_ops:
                self._enable_id(e.id, False)
            self._enable_id(PRIORITY_MENU_ID, False)
        else:
            # enable some things
            for i in (STOP_ID, START_ID, REMOVE_ID, INFO_ID, PRIORITY_MENU_ID):
                self._enable_id(i, True)

            # show/hide start/stop button
            infohash = self.torrentlist.GetItemData(index)
            self.check_torrent_start_stop(infohash)

            # en/disable move up
            self._enable_id(UP_ID, index > 0)

            # en/disable move down
            self._enable_id(DOWN_ID, index < count - 1)

            infohash = self.torrentlist.GetItemData(index)

            if infohash:
                torrent = wx.the_app.torrents[infohash]
                # only show open button on completed torrents
                self._enable_id(LAUNCH_ID, torrent.completion >= 1)

                self._enable_id(FORCE_START_ID, torrent.policy != "start")

                priority = frontend_priority[torrent.priority]
                for m in (self.torrent_menu, self.torrent_context_menu):
                    m.set_priority(priority)


    def check_torrent_start_stop(self, infohash):
        torrent = wx.the_app.torrents[infohash]
        show_stop = torrent.policy != "stop" and torrent.state != "failed"
        self.toggle_stop_start_button(show_stop)
        self.torrent_menu.toggle_stop_start_menu_item(show_stop)
        self.torrent_context_menu.toggle_stop_start_menu_item(show_stop)

    def toggle_stop_start_button(self, show_stop):
        changed = self.tool_bar.toggle_stop_start_button(show_stop)
        if changed:
            self.tool_sizer.Layout()
            self.sizer.Layout()

    def MyIconize(self, event):
        if wx.the_app.config['minimize_to_tray']:
            if self.IsShown():
                self.Show(False)
            else:
                self.Show(True)
                self.Raise()

    def add_menu_item(self, menu, label, function=None):
        index = menu.add_item(label)
        if function is not None:
            i = self.Bind(wx.EVT_MENU, function, id=index)
        return index

    def add_menu_check_item(self, menu, label, function=None, value=False):
        index = menu.add_check_item(label, value)
        if function is not None:
            self.Bind(wx.EVT_MENU, function, id=index)
        return index

    #def do_log(self, level, text):
    #    wx.GetApp().do_log(level, text)
    #
    #
    #def do_log_torrent(self, infohash, level, text):
    #    wx.GetApp().do_log_torrent(infohash, level, text)


    def clear_status(self):
        self.SetStatusText('')


    def new_displayed_torrent(self, torrent_object):

        state = (torrent_object.state    ,
                 torrent_object.policy   ,
                 torrent_object.completed)
        priority = frontend_priority[torrent_object.priority]

        lr = BTListRow(None, {'state': state,
                              'name': torrent_object.metainfo.name,
                              'progress': percentify(torrent_object.completion,
                                                     torrent_object.completed),
                              'eta': Duration(),
                              'urate': Rate(),
                              'drate': Rate(),
                              'priority': priority,
                              'peers': 0})
        self.torrentlist.InsertRow(torrent_object.infohash, lr)
        self.torrentlist._gauge_paint()


    def removed_torrent(self, infohash):
        self.torrentlist.DeleteRow(infohash)


    def save_gui_state(self):
        app = wx.the_app

        c = self.torrentlist.get_sort_column()
        o = self.torrentlist.get_sort_order()
        o = bool(o)

        app.send_config('sort_column', c)
        app.send_config('sort_ascending', o)

        column_order = self.torrentlist.column_order
        app.send_config('column_order', column_order)
        enabled_columns = self.torrentlist.enabled_columns
        app.send_config('enabled_columns', enabled_columns)
        w = self.torrentlist.get_column_widths()
        app.send_config('column_widths', w)

        sw = getattr(app, '_settings_window', None)
        if sw:
            settings_tab = sw.notebook.GetSelection()
            app.send_config('settings_tab', settings_tab)

        if self.IsMaximized():
            app.send_config('start_maximized', True)
        elif not self.IsIconized():
            g = self._geometry_string()
            app.send_config('geometry', g)
            app.send_config('start_maximized', False)

        if app.bling_history is not None:
            show_bling = self.bling_panel.IsShown()
            app.send_config('show_details', show_bling)
            bling_tab = self.bling_panel.notebook.GetSelection()
            app.send_config('details_tab', bling_tab)


class SaveLocationDialog(BTDialog):

    def __init__(self, parent, path, name, is_dir):
        self.is_dir = is_dir
        if self.is_dir:
            BTDialog.__init__(self, parent=parent, id=wx.ID_ANY,
                              title=_("Save In"),
                              style=wx.DEFAULT_DIALOG_STYLE)

            self.message = ElectroStaticText(self, id=wx.ID_ANY,
                                         label=_('Save "%s" in:')%name)


            dialog_title = _('Choose a folder...\n("%s" will be a sub-folder.)'%name)
            self.save_box = ChooseDirectorySizer(self, os.path.split(path)[0],
                                                 dialog_title=dialog_title)
        else:
            BTDialog.__init__(self, parent=parent, id=wx.ID_ANY,
                              title=_("Save As"),
                              style=wx.DEFAULT_DIALOG_STYLE)

            self.message = ElectroStaticText(self, id=wx.ID_ANY,
                                         label=_('Save "%s" as:')%name)


            self.save_box = ChooseFileSizer(self, path, dialog_style=wx.SAVE)

        self.sizer = VSizer()

        self.sizer.AddFirst(self.message)
        self.sizer.Add(self.save_box, flag=wx.GROW)

        self.always_checkbox = wx.CheckBox(self, id=wx.ID_ANY,
                                           label=_("&Always save files in this directory"))
        self.always_checkbox.SetValue(False)
        self.sizer.Add(self.always_checkbox)

        if '__WXMSW__' in wx.PlatformInfo:
            self.always_checkbox.Bind(wx.EVT_CHECKBOX, self.OnAlways)
            self.shortcut_checkbox = wx.CheckBox(self, id=wx.ID_ANY, label=_("Create &shortcut on the desktop"))
            self.shortcut_checkbox.SetValue(False)
            self.shortcut_checkbox.Disable()
            self.sizer.Add(self.shortcut_checkbox)

        self.button_sizer = self.CreateStdDialogButtonSizer(flags=wx.OK|wx.CANCEL)

        self.sizer.Add(self.button_sizer, flag=wx.ALIGN_RIGHT, border=SPACING)
        self.SetSizer(self.sizer)

        self.Fit()


    def OnAlways(self, event):
        if self.always_checkbox.IsChecked():
            self.shortcut_checkbox.SetValue(True)
            self.shortcut_checkbox.Enable()
        else:
            self.shortcut_checkbox.SetValue(False)
            self.shortcut_checkbox.Disable()


    def ShowModal(self):
        result = BTDialog.ShowModal(self)
        self.Destroy()
        return result


    def GetPath(self):
        return self.save_box.get_choice()


    def GetAlways(self):
        return self.always_checkbox.IsChecked()


    def GetShortcut(self):
        return os.name == 'nt' and self.shortcut_checkbox.IsChecked()


def ConfirmQuitDialog(parent):
    dialog = CheckBoxDialog(parent=parent,
                            title=_("Really quit %s?")%app_name,
                            label = _("Are you sure you want to quit %s?")%app_name,
                            checkbox_label=_("&Don't ask again"),
                            checkbox_value=not wx.the_app.config['confirm_quit'])
    if dialog.ShowModal() == wx.ID_CANCEL:
        return wx.ID_CANCEL
    value = not dialog.checkbox.GetValue()
    wx.the_app.send_config('confirm_quit', value)
    return value


def ConfirmRemoveDialog(parent, title, label, checkbox_label):
    return LaunchCheckBoxDialog(parent, title, label, checkbox_label,
                                checkbox_value=True)


def NotifyNewVersionDialog(parent, new_version):
    value = LaunchCheckBoxDialog(parent,
                                 title=_("New %s version available")%app_name,
                                 label=(
            (_("A newer version of %s is available.\n") % app_name) +
            (_("You are using %s, and the new version is %s.\n") % (version, new_version)) +
            (_("You can always get the latest version from \n%s") % URL) ),
                                 checkbox_label=_("&Remind me later"),
                                 checkbox_value=True)
    if not value:
        wx.the_app.send_config('notified', new_version)
        if value == None:
            return wx.ID_CANCEL
    else:
        wx.the_app.send_config('notified', '')
    return value


# logs to wx targets and python. we could do in the other direction too
class LogProxy(wx.PyLog):

    # these are not 1-to-1 on purpose (our names don't match)
    severities = {wx.LOG_Info: INFO,
                  wx.LOG_Warning: WARNING,
                  wx.LOG_Status: ERROR,
                  wx.LOG_Error: CRITICAL,
                  wx.LOG_Debug: DEBUG,
                  }

    def __init__(self, log):
        wx.PyLog.__init__(self)
        self.log = log

    def DoLog(self, level, msg, timestamp):
        # throw an event to do the logging, because logging from inside the
        # logging handler deadlocks on GTK
        gui_wrap(self._do_log, level, msg, timestamp)

    def _do_log(self, level, msg, timestamp):
        wx.Log_SetActiveTarget(self.log)
        v_msg = '[%s] %s' % (version, msg)
        v_msg = v_msg.strip()

        # don't add the version number to dialogs and the status bar
        if level == wx.LOG_Error or level == wx.LOG_Status:
            self.log.PassMessages(True)
            if ']' in msg:
                msg = msg.split(']', 1)[1].strip()
            wx.LogGeneric(level, msg)
            self.log.PassMessages(False)
        else:
            wx.LogGeneric(level, v_msg)

        wx.Log_SetActiveTarget(self)



class TorrentLogger(logging.Handler):

    def __init__(self):
        self.torrents = {}
        self.base = 'core.MultiTorrent.'
        logging.Handler.__init__(self)
        self.blacklist = set()


    def emit(self, record):
        if not record.name.startswith(self.base):
            return
        l = len(self.base)
        infohash_hex = record.name[l:l+40]
        try:
            infohash = infohash_hex.decode('hex')
        except TypeError: #Non-hexadecimal digit found
            return
        if infohash not in self.blacklist:
            self.torrents.setdefault(infohash, []).append(record)


    def flush(self, infohash=None, target=None):
        if infohash is not None and target is not None:
            tlog = self.torrents.pop(infohash, [])
            for record in tlog:
                target.handle(record)
            self.blacklist.add(infohash)


    def unblacklist(self, infohash):
        if infohash in self.blacklist:
            self.blacklist.remove(infohash)



class MainLoop(BasicApp, BTApp):
    GRAPH_UPDATE_INTERVAL = 1000
    GRAPH_TIME_SPAN = 120
    torrent_object_class = TorrentObject

    def __init__(self, config):
        BasicApp.__init__(self, config)

        self.gui_wrap = self.CallAfter
        self.main_window = None
        self.task_bar_icon = None
        self._update_task = TaskSingleton()
        self._update_bwg_task = TaskSingleton()
        self._clear_status_task = TaskSingleton()
        self.bling_history = None
        self.multitorrent_doneflag = None
        self.open_dialog_history = []
        self._stderr_buffer = StringIO()
        self.torrent_logger = TorrentLogger()
        # HEREDAVE: not relevant to the pop-up window "BitTorrent Error"
        logging.getLogger('core.MultiTorrent').addHandler(self.torrent_logger)
        BTApp.__init__(self, 0)


    def OnInit(self):
        BTApp.OnInit(self)

        self.image_library = ImageLibrary(image_root)
        self.theme_library = ThemeLibrary(image_root, self.config['theme'])

        # Main window
        style = wx.DEFAULT_FRAME_STYLE
        if sys.platform == 'darwin':
            # no close box on the mac
            style = (wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|wx.SYSTEM_MENU|wx.CAPTION|
                     wx.CLIP_CHILDREN)
        self.main_window = MainWindow(None, wx.ID_ANY, app_name, style=style)

        self.main_window.Hide()

        if (not self.config['start_minimized'] and
            not self.config['force_start_minimized']):
            # this code might look a little weird, but an initial Iconize can cut
            # the memory footprint of the process in half (causes GDI handles to
            # be flushed, and not recreated until they're shown).
            self.main_window.Iconize(True)
            self.main_window.Iconize(False)
            self.main_window.Show()
            self.main_window.Raise()

        self.SetTopWindow(self.main_window)

        ascending = 0
        if self.config['sort_ascending']:
            ascending = 1
        self.main_window.SortListItems(col=self.config['sort_column'],
                                       ascending=ascending)

        # Logging
        # HEREDAVE: If commented, dialog does not apear when
        # BTFailure is raised in response to double
        # downloading.
        wx.Log_SetActiveTarget(wx.LogGui())

        self.log = LogWindow(self.main_window, _("%s Log")%app_name, False)
        s = wx.Display().GetGeometry()
        self.log.GetFrame().SetSize((s.width * 0.80, s.height * 0.40))

        wx.Log_SetActiveTarget(self.log)
        wx.Log_SetVerbose(True) # otherwise INFOs are not logged

        self.console = None
        if console:
            spec = inspect.getargspec(wx.py.shell.ShellFrame.__init__)
            args = spec[0]
            kw = {}
            # handle out-of-date wx installs
            if 'dataDir' in args and 'config' in args:
                # somewhere to save command history
                confDir = wx.StandardPaths.Get().GetUserDataDir()
                if not os.path.exists(confDir):
                    os.mkdir(confDir)
                fileName = os.path.join(confDir, 'config')
                self.wxconfig = wx.FileConfig(localFilename=fileName)
                self.wxconfig.SetRecordDefaults(True)
                kw = {'config':self.wxconfig,
                      'dataDir':confDir}

            # hack up and down to do the normal history things
            try:
                def OnKeyDown(s, event):
                    # If the auto-complete window is up let it do its thing.
                    if self.console.shell.AutoCompActive():
                        event.Skip()
                        return
                    key = event.GetKeyCode()
                    if key == wx.WXK_UP:
                        self.console.shell.OnHistoryReplace(step=+1)
                    elif key == wx.WXK_DOWN:
                        self.console.shell.OnHistoryReplace(step=-1)
                    else:
                        o(self.console.shell, event)
                o = wx.py.shell.Shell.OnKeyDown
                wx.py.shell.Shell.OnKeyDown = OnKeyDown
            except:
                pass
            self.console = wx.py.shell.ShellFrame(self.main_window, **kw)
            self.console.Bind(wx.EVT_CLOSE, lambda e:self.console.Show(False))

        # Task bar icon
        if os.name == 'nt':
            self.task_bar_icon = DownloadManagerTaskBarIcon(self.main_window)

        self.set_title()

        self.SetAppName(app_name)
        return True

    # this function must be thread-safe!
    def attach_multitorrent(self, multitorrent, doneflag):
        if not self.running:
            # the app is dead, tell the multitorrent to die too
            doneflag.set()
            return

        # I'm specifically using wx.CallAfter here, because I need it to occur
        # even if the wxApp doneflag is set.
        wx.CallAfter(self._attach_multitorrent, multitorrent, doneflag)

    def _attach_multitorrent(self, multitorrent, doneflag):
        BasicApp.attach_multitorrent(self, multitorrent, doneflag)

        gui_wrap(self.open_external_torrents)

        if self.config['show_details']:
            gui_wrap(self.main_window.toggle_bling_panel)

        self.init_updates()

    def no_op(self):
        if not self.main_window.IsShown():
            self.systray_open()

    def OnExit(self):
        if self.multitorrent_doneflag:
            self.multitorrent_doneflag.set()
        self._update_task.stop()
        self._update_bwg_task.stop()
        self._clear_status_task.stop()
        BTApp.OnExit(self)

    def systray_open(self):
        for t in self.torrents.values():
            t.restore_window()

        # the order here is important.
        self.main_window.Show(True)
        self.main_window.Raise()
        self.main_window.Iconize(False)

    def systray_quit(self):
        for t in self.torrents.values():
            t.save_gui_state()

        self.main_window.save_gui_state()
        self.main_window.Iconize(True)
        self.main_window.Show(False)

        self.log.GetFrame().Show(False)

        for t in self.torrents.values():
            t.close_window()

    def quit(self, confirm_quit=True):
        if self.main_window:
            if confirm_quit and self.config['confirm_quit']:
                if ConfirmQuitDialog(self.main_window) == wx.ID_CANCEL:
                    return

            for t in self.torrents.values():
                t.save_gui_state()

            self.main_window.save_gui_state()
            self.main_window.Destroy()

            for t in self.torrents.values():
                t.clean_up()

        if self.task_bar_icon:
            self.task_bar_icon.Destroy()

        if self.console:
            self.console.Destroy()

        sw = getattr(self, '_settings_window', None)
        if sw:
            sw.Destroy()

        BasicApp.quit(self)


    def MacOpenFile(self, path):
        self.open_torrent_arg_with_callbacks(path)

    def enter_torrent_url(self, widget):
        s = ''
        if wx.TheClipboard.Open():
            do = wx.TextDataObject()
            if wx.TheClipboard.GetData(do):
                t = do.GetText()
                t = t.strip()
                if "://" in t or os.path.sep in t or (os.path.altsep and os.path.altsep in t):
                    s = t
            wx.TheClipboard.Close()
        d = wx.TextEntryDialog(parent=self.main_window,
                               message=_("Enter the URL of a torrent file to open:"),
                               caption=_("Enter torrent URL"),
                               defaultValue = s,
                               style=wx.OK|wx.CANCEL,
                               )
        if d.ShowModal() == wx.ID_OK:
            path = d.GetValue()
            df = self.open_torrent_arg_with_callbacks(path)

    def select_torrent(self, *a):
        image = wx.the_app.theme_library.get(('add',), 32)
        d = OpenDialog(self.main_window,
                       title=_("Open Path"),
                       bitmap=wx.BitmapFromImage(image),
                       browse=self.select_torrent_file,
                       history=self.open_dialog_history)
        if d.ShowModal() == wx.ID_OK:
            path = d.GetValue()
            self.open_dialog_history.append(path)
            df = self.open_torrent_arg_with_callbacks(path)

    def select_torrent_file(self, widget=None):
        open_location = self.config['open_from']
        if not open_location:
            open_location = self.config['save_in']
        path = smart_dir(open_location)
        dialog = wx.FileDialog(self.main_window, message=_("Open torrent file:"),
                               defaultDir=path,
                               wildcard=WILDCARD,
                               style=wx.OPEN|wx.MULTIPLE)
        if dialog.ShowModal() == wx.ID_OK:
            paths = dialog.GetPaths()
            for path in paths:
                df = self.open_torrent_arg_with_callbacks(path)
            open_from, filename = os.path.split(path)
            self.send_config('open_from', open_from)

    def rize_up(self):
        if not self.main_window.IsShown():
            self.main_window.Show(True)
            self.main_window.Iconize(False)
        if '__WXGTK__' not in wx.PlatformInfo:
            # this plays havoc with multiple virtual desktops
            self.main_window.Raise()

    def torrent_already_open(self, metainfo):
        self.rize_up()
        msg = _("This torrent (or one with the same contents) "
                "has already been added.")
        self.logger.warning(msg)
        d = wx.MessageBox(
            message=msg,
            caption=_("Torrent already added"),
            style=wx.OK,
            parent= self.main_window
            )
        return

    def open_torrent_metainfo(self, metainfo):
        """This method takes torrent metainfo and:
        1. asserts that we don't know about the torrent
        2. gets a save path for it
        3. checks to make sure the save path is acceptable:
          a. does the file already exist?
          b. does the filesystem support large enough files?
          c. does the disk have enough space left?
        4. tells TQ to start the torrent and returns a deferred object
        """

        self.rize_up()

        assert not self.torrents.has_key(metainfo.infohash), "torrent already running"

        ask_for_save = self.config['ask_for_save'] or not self.config['save_in']
        save_in = self.config['save_in']
        if not save_in:
            save_in = get_save_dir()

        save_incomplete_in = self.config['save_incomplete_in']

        # wx expects paths sent to the gui to be unicode
        save_as = os.path.join(save_in,
                               decode_from_filesystem(metainfo.name_fs))
        original_save_as = save_as

        # Choose an incomplete filename which is likely to be both short and
        # unique.  Just for kicks, also foil multi-user birthday attacks.
        foil = sha(save_incomplete_in.encode('utf-8'))
        foil.update(metainfo.infohash)
        incomplete_name = metainfo.infohash.encode('hex')[:8]
        incomplete_name += '-'
        incomplete_name += foil.hexdigest()[:4]
        save_incomplete_as = os.path.join(save_incomplete_in,
                                          incomplete_name)

        biggest_file = max(metainfo.sizes)

        while True:

            if ask_for_save:
                # if config['ask_for_save'] is on, or if checking the
                # save path failed below, we ask the user for a (new)
                # save path.

                d = SaveLocationDialog(self.main_window, save_as,
                                       metainfo.name, metainfo.is_batch)
                if d.ShowModal() == wx.ID_OK:
                    dialog_path = d.GetPath()

                    if metainfo.is_batch:
                        save_in = dialog_path
                        save_as = os.path.join(dialog_path,
                                               decode_from_filesystem(metainfo.name_fs))

                    else:
                        save_as = dialog_path
                        save_in = os.path.split(dialog_path)[0]

                    if not os.path.exists(save_in):
                        os.makedirs(save_in)

                    if d.GetAlways():
                        a = wx.the_app
                        a.send_config('save_in', save_in)
                        a.send_config('ask_for_save', False)

                        if d.GetShortcut():
                            if not save_in.startswith(desktop):
                                shortcut = os.path.join(desktop, 'Shortcut to %s Downloads'%app_name)
                                create_shortcut(save_in, shortcut)

                    ask_for_save = False
                else:
                    # the user pressed cancel in the dir/file dialog,
                    # so forget about this torrent.
                    return

            else:
                # ask_for_save is False, either because the config
                # item was false, or because it got set to false the
                # first time through the loop after the user set the
                # save_path.

                if os.access(save_as, os.F_OK):
                    # check the file(s) that already exist, and warn the user
                    # if they do not match exactly in name, size and count.

                    check_current_dir = True

                    if metainfo.is_batch:
                        resume = metainfo.check_for_resume(save_in)
                        if resume == -1:
                            pass
                        elif resume == 0 or resume == 1:
                            # if the user may have navigated inside an old
                            # directory from a previous download of the
                            # batch torrent, prompt them.
                            if resume == 0:
                                default = wx.NO_DEFAULT
                            else:
                                default = wx.YES_DEFAULT

                            d = wx.MessageBox(
                                message=_("The folder you chose already "
                                "contains some files which appear to be from "
                                "this torrent.  Do you want to resume the "
                                "download using these files, rather than "
                                "starting the download over again in a "
                                "subfolder?") % path_wrap(metainfo.name_fs),
                                caption=_("Wrong folder?"),
                                style=wx.YES_NO|default,
                                parent=self.main_window
                                )
                            if d == wx.YES:
                                save_as = save_in
                                save_in = os.path.split(save_as)[0]
                                check_current_dir = False

                    if check_current_dir:
                        resume = metainfo.check_for_resume(save_as)
                        if resume == -1:
                            # STOP! files are different
                            d = wx.MessageBox(
                                message=_('A different "%s" already exists.  Do you '
                                          "want to remove it and overwrite it with "
                                          "the contents of this torrent?") %
                                path_wrap(metainfo.name_fs),
                                caption=_("Files are different!"),
                                style=wx.YES_NO|wx.NO_DEFAULT,
                                parent=self.main_window
                                )
                            if d == wx.NO:
                                ask_for_save = True
                                continue
                        elif resume == 0:
                            # MAYBE this is a resume
                            d = wx.MessageBox(
                                message=_('"%s" already exists.  Do you want to choose '
                                          'a different file name?') % path_wrap(metainfo.name_fs),
                                caption=_("File exists!"),
                                style=wx.YES_NO|wx.NO_DEFAULT,
                                parent=self.main_window
                                )
                            if d == wx.YES:
                                ask_for_save = True
                                continue
                        elif resume == 1:
                            # this is definitely a RESUME, file names,
                            # sizes and count match exactly.
                            pass

                fs_type, max_filesize = get_max_filesize(encode_for_filesystem(save_as)[0])
                if max_filesize < biggest_file:
                    # warn the user that the filesystem doesn't
                    # support large enough files.
                    if fs_type is not None:
                        fs_type += ' ' + disk_term
                    else:
                        fs_type = disk_term
                    d = wx.MessageBox(
                        message=_("There is a file in this torrent that is "
                                  "%(file_size)s. This exceeds the maximum "
                                  "file size allowed on this %(fs_type)s, "
                                  "%(max_size)s.  Would you like to choose "
                                  "a different %(disk_term)s to save this "
                                  "torrent in?") %
                        {'file_size': unicode(Size(biggest_file)),
                         'max_size' : unicode(Size(max_filesize)),
                         'fs_type'  : fs_type                ,
                         'disk_term': disk_term              ,},
                        caption=_("File too large for %s") % disk_term,
                        style=wx.YES_NO|wx.YES_DEFAULT,
                        parent=self.main_window,
                        )
                    if d == wx.YES:
                        ask_for_save = True
                        continue
                    else:
                        # BUG: once we support 'never' downloading
                        # files, we should allow the user to start
                        # torrents with files that are too big, and
                        # mark those files as never-download.  For
                        # now, we don't allow downloads of torrents
                        # with files that are too big.
                        return

                if get_free_space(save_as) < metainfo.total_bytes:
                    # warn the user that there is not enough room on
                    # the filesystem to save the entire torrent.
                    d = wx.MessageBox(
                        message=_("There is not enough space on this %s to "
                                  "save this torrent.  Would you like to "
                                  "choose a different %s to save it in?") %
                        (disk_term, disk_term),
                        caption=_("Not enough space on this %s") % disk_term,
                        style=wx.YES_NO,
                        parent=self.main_window
                        )
                    if d == wx.YES:
                        ask_for_save = True
                        continue

                if is_path_too_long(save_as):
                    d = wx.MessageBox(
                        message=_("The location you chose exceeds the maximum "
                                  "path length on this system.  You must "
                                  "choose a different folder."),
                        caption=_("Maximum path exceeded"),
                        style=wx.OK,
                        parent=self.main_window
                        )
                    ask_for_save = True
                    continue

                if not os.path.exists(save_in):
                    d = wx.MessageBox(
                        message=_("The save location you specified does not "
                                  "exist (perhaps you mistyped it?)  Please "
                                  "choose a different folder."),
                        caption=_("No such folder"),
                        style=wx.OK,
                        parent= self.main_window
                        )
                    save_as = original_save_as
                    ask_for_save = True
                    continue

                if not ask_for_save:
                    # the save path is acceptable, start the torrent.
                    fs_save_as, junk = encode_for_filesystem(save_as)
                    fs_save_incomplete_as, junk = encode_for_filesystem(save_incomplete_as)
                    return self.multitorrent.create_torrent(metainfo, fs_save_incomplete_as, fs_save_as)


    def run(self):
        self.MainLoop()


    def reset_toolbar_style(self):
        self.main_window.reset_toolbar_style()
        for tw in self.torrents.values():
            tw.reset_toolbar_style()

    # Settings window
    def _get_settings_window(self):
        try:
            return self._settings_window
        except AttributeError:
            self._settings_window = SettingsWindow(self.main_window,
                                                   self.config, self.send_config)
            self._settings_window.notebook.SetSelection(self.config['settings_tab'])
            return self._settings_window

    settings_window = property(_get_settings_window)


    # About window
    def _get_about_window(self):
        try:
            return self._about_window
        except AttributeError:
            self._about_window = AboutWindow(self.main_window)
            return self._about_window

    about_window = property(_get_about_window)

    # MakeTorrent window
    def _get_make_torrent_window(self):
        try:
            return self._make_torrent_window
        except AttributeError:
            defaults = get_defaults('maketorrent')
            config, args = configfile.parse_configuration_and_args(defaults,
                                                                   'maketorrent', [], 0, None)
            # BUG: hack to make verbose mode be the default
            config['verbose'] = not config['verbose']
            self._make_torrent_window = MakeTorrentWindow(self.main_window, config)
            return self._make_torrent_window

    make_torrent_window = property(_get_make_torrent_window)

    def _remove_infohash(self, infohash, del_files):
        df = launch_coroutine(gui_wrap, self.remove_infohash, infohash, del_files=del_files)
        def error(f):
            ns = 'core.MultiTorrent.' + repr(infohash)
            l = logging.getLogger(ns)
            l.error(self.remove_infohash.__name__ + " failed",
                    exc_info=f.exc_info())
        df.addErrback(error)
        return df

    def force_remove(self, event):
        infohashes = self.main_window.torrentlist.get_selected_infohashes()
        for infohash in infohashes:
            self._remove_infohash(infohash, del_files=True)


    def confirm_remove_infohashes(self, infohashes):
        infohashes = [ i for i in infohashes if i in self.torrents ]

        if len(infohashes) == 1:
            return self.confirm_remove_infohash(infohashes[0])

        del_files = False
        for infohash in infohashes:
            t = self.torrents[infohash]
            fs_save_incomplete_in, junk = encode_for_filesystem(
                self.config['save_incomplete_in']
                )
            inco = ((not t.completed) and
                    (t.working_path != t.destination_path) and
                    t.working_path.startswith(fs_save_incomplete_in))
            if inco:
                del_files = True
                break

        if not wx.GetKeyState(wx.WXK_SHIFT):
            title = _("Really remove torrents?")
            label = _('Are you sure you want to remove %d torrents?') % len(infohashes)
            checkbox_label = _("&Delete incomplete downloaded file(s)")

            if del_files:
                value = ConfirmRemoveDialog(self.main_window,
                                            title=title,
                                            label=label,
                                            checkbox_label=checkbox_label)
                if value == wx.ID_CANCEL:
                    return

                del_files = value
            else:
                r = wx.MessageBox(
                    message=label,
                    caption=title,
                    style=wx.OK|wx.CANCEL,
                    parent=self.main_window
                    )
                if r == wx.CANCEL:
                    return

        for infohash in infohashes:
            self._remove_infohash(infohash, del_files=del_files)


    def confirm_remove_infohash(self, infohash):
        if infohash not in self.torrents:
            return

        t = self.torrents[infohash]
        name = t.metainfo.name
        fs_save_incomplete_in, junk = encode_for_filesystem(
            self.config['save_incomplete_in']
            )
        inco = ((not t.completed) and
                (t.working_path != t.destination_path) and
                t.working_path.startswith(fs_save_incomplete_in))

        del_files = inco
        if not wx.GetKeyState(wx.WXK_SHIFT):
            title=_("Really remove torrent?")
            label=_('Are you sure you want to remove "%s"?') % name
            checkbox_label=_("&Delete incomplete downloaded file(s)")

            if del_files:
                value = ConfirmRemoveDialog(self.main_window,
                                            title=title,
                                            label=label,
                                            checkbox_label=checkbox_label)
                if value == wx.ID_CANCEL:
                    return

                del_files = value
            else:
                r = wx.MessageBox(
                    message=label,
                    caption=title,
                    style=wx.OK|wx.CANCEL,
                    parent=self.main_window
                    )
                if r == wx.CANCEL:
                    return


        self._remove_infohash(infohash, del_files=del_files)
        # Could also do this but it's harder to understand:
        #return self.remove_infohash(infohash)


    def show_torrent(self, infohash):
        torrent = self.torrents[infohash]
        torrent.torrent_window.MagicShow()


    def notify_of_new_version(self, new_version):
        value = NotifyNewVersionDialog(self.main_window, new_version)
        if value != wx.ID_CANCEL:
            self.visit_url(URL)


    def prompt_for_quit_for_new_version(self, version):
        d = wx.MessageBox(
            message=_(("%s is ready to install a new version (%s).  Do you "
                       "want to quit now so that the new version can be "
                       "installed?  If not, the new version will be installed "
                       "the next time you quit %s."
                       ) % (app_name, version, app_name)),
            caption=_("Install update now?"),
            style=wx.YES_NO|wx.YES_DEFAULT,
            parent=self.main_window
            )
        if d == wx.YES:
            self.quit(confirm_quit=False)


    def do_log(self, severity, text):

        if severity == 'stderr':
            # stderr likes to spit partial lines, buffer them until we get a \n
            self._stderr_buffer.write(text)
            if text[-1] != '\n':
                return
            text = self._stderr_buffer.getvalue()
            self._stderr_buffer.truncate(0)
            severity = ERROR

        # We don't make use of wxLogMessage or wxLogError, because only
        # critical errors are presented to the user.
        # Really, that means some of our severities are mis-named.

        if severity == INFO:
            wx.LogInfo(text)
        elif severity == WARNING:
            wx.LogWarning(text)
        elif severity == ERROR:
            # put it in the status bar
            self.log.PassMessages(True)
            wx.LogStatus(text)
            self.log.PassMessages(False)
            self._clear_status_task.start(ERROR_MESSAGE_TIMEOUT,
                                          self.main_window.clear_status)
        elif severity == CRITICAL:
            # pop up a dialog
            self.log.PassMessages(True)
            wx.LogError(text)
            self.log.PassMessages(False)

    # make status request at regular intervals
    def init_updates(self):
        self.bling_history = HistoryCollector(self.GRAPH_TIME_SPAN,
                                              self.GRAPH_UPDATE_INTERVAL)

        self.make_statusrequest()
        self.update_bandwidth_graphs()

        self.main_window.HistoryReady()

    def update_bandwidth_graphs(self):
        df = launch_coroutine(gui_wrap, self._update_bandwidth_graphs)
        def error(f):
            wx.the_app.logger.error(self._update_bandwidth_graphs.__name__ + " failed",
                                    exc_info=f.exc_info())
        df.addErrback(error)


    def _update_bandwidth_graphs(self):
        df = self.multitorrent.get_all_rates()
        yield df
        rates = df.getResult()

        df = self.multitorrent.get_variance()
        yield df
        variance, max_variance = df.getResult()

        tu = 0.0
        td = 0.0
        for infohash, v in rates.iteritems():
            u, d = v
            if infohash in self.torrents:
                t = self.torrents[infohash]
                t.bandwidth_history.update(upload_rate=u, download_rate=d,
                                           max_upload_rate=self.config['max_upload_rate'],
                                           max_download_rate=self.config['max_download_rate'],
                                           variance=variance, max_variance=max_variance)
            tu += u
            td += d

        self.bling_history.update(upload_rate=tu, download_rate=td,
                                  max_upload_rate=self.config['max_upload_rate'],
                                  max_download_rate=self.config['max_download_rate'],
                                  variance=variance, max_variance=max_variance)

        self._update_bwg_task.start(self.GRAPH_UPDATE_INTERVAL,
                                    self.update_bandwidth_graphs)

    def start_torrent(self, infohash):
        df = launch_coroutine(gui_wrap, BasicApp.start_torrent, self, infohash)
        yield df
        if not df.getResult():
            return
        # wx specific code
        df = launch_coroutine(self.gui_wrap, self.update_single_torrent, infohash)
        yield df
        df.getResult()
        self.main_window.check_torrent_start_stop(infohash)

    def stop_torrent(self, infohash):
        df = launch_coroutine(gui_wrap, BasicApp.stop_torrent, self, infohash, pause=True)
        yield df
        if not df.getResult():
            return
        # wx specific code
        df = launch_coroutine(self.gui_wrap, self.update_single_torrent, infohash)
        yield df
        df.getResult()
        self.main_window.check_torrent_start_stop(infohash)

    def force_start_torrent(self, infohash):
        df = launch_coroutine(gui_wrap, BasicApp.force_start_torrent, self, infohash)
        yield df
        if not df.getResult():
            return
        # wx specific code
        df = launch_coroutine(self.gui_wrap, self.update_single_torrent, infohash)
        yield df
        df.getResult()
        self.main_window.check_torrent_start_stop(infohash)

    def update_status(self):
        df = launch_coroutine(gui_wrap, BasicApp.update_status, self)
        yield df
        # wx specific code
        average_completion, all_completed, global_stats = df.getResult()
        if len(self.torrents) > 0:
            self.set_title(average_completion,
                           all_completed,
                           global_stats['total_downrate'],
                           global_stats['total_uprate'])
        else:
            self.set_title()
            self.send_status_message('empty')

        self.main_window.torrentlist.SortItems()

        self.main_window.check_torrent_selection()

        self._update_task.start(self.config['display_interval'] * 1000,
                                self.make_statusrequest)

        self.main_window.bling_panel.statistics.update_values(global_stats)


    def new_displayed_torrent(self, torrent):
        torrent_object = BasicApp.new_displayed_torrent(self, torrent)

        if len(self.torrents) == 1:
            self.send_status_message('start')

        self.main_window.new_displayed_torrent(torrent_object)

        return torrent_object


    def torrent_removed(self, infohash):
        self.torrent_logger.unblacklist(infohash)
        self.main_window.removed_torrent(infohash)


    def update_torrent(self, torrent_object):
        self.main_window.torrentlist.update_torrent(torrent_object)
        if torrent_object.statistics.get('ever_got_incoming'):
            self.send_status_message('seen_remote_peers')
        elif torrent_object.statistics.get('numPeers'):
            self.send_status_message('seen_peers')


    def send_status_message(self, msg):
        self.main_window.send_status_message(msg)


    def set_title(self,
                  avg_completion=0,
                  all_completed=False,
                  downrate=0,
                  uprate=0):
        if len(self.torrents) > 0:
            if len(self.torrents) > 1:
                name = _("(%d torrents)") % len(self.torrents)
            else:
                name = self.torrents[self.torrents.keys()[0]].metainfo.name
            percent = percentify(avg_completion, all_completed)
            title = "%s: %.1f%%: %s" % (app_name, percent, name)
        elif self.multitorrent:
            title = app_name
        else:
            title = "%s: %s" % (app_name, _("(initializing)"))
        if self.task_bar_icon is not None:
            tip = '%s\n%s down, %s up' % (title, unicode(Rate(downrate)), unicode(Rate(uprate)))
            self.task_bar_icon.set_tooltip(tip)
        self.main_window.SetTitle(title)

