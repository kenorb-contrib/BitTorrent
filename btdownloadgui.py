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

# Written by Uoti Urpala and Matt Chisholm

from __future__ import division

import sys

assert sys.version_info >= (2, 3), "Install Python 2.3 or greater"

import itertools
import math
import os
import threading
import datetime
import random
import gtk
import pango
import gobject
import webbrowser
from urllib import quote, url2pathname

from BitTorrent import configfile
from BitTorrent import HELP_URL, DONATE_URL
from BitTorrent import is_frozen_exe
from BitTorrent.parseargs import parseargs, makeHelp
from BitTorrent import version, doc_root
from BitTorrent.defaultargs import get_defaults
from BitTorrent import TorrentQueue
from BitTorrent.TorrentQueue import RUNNING, QUEUED, KNOWN, ASKING_LOCATION
from BitTorrent.controlsocket import ControlSocket
from BitTorrent import BTFailure, INFO, WARNING, ERROR, CRITICAL
from BitTorrent import OpenPath
from BitTorrent import Desktop
from BitTorrent import ClientIdentifier
from BitTorrent import path_wrap
from BitTorrent.GUI import * 

defaults = get_defaults('btdownloadgui')
defaults.extend((('donated' , '', ''), # the version that the user last donated for
                 ('notified', '', ''), # the version that the user was last notified of
                 ))

NAG_FREQUENCY = 3
PORT_RANGE = 5

defconfig = dict([(name, value) for (name, value, doc) in defaults])
del name, value, doc

ui_options = [
    'max_upload_rate'       ,
    'minport'               ,
    'maxport'               ,
    'next_torrent_time'     ,
    'next_torrent_ratio'    ,
    'last_torrent_ratio'    ,
    'ask_for_save'          ,
    'save_in'               ,
    'ip'                    ,
    'start_torrent_behavior',
    'chop_max_allow_in'     ,
    ]
advanced_ui_options_index = len(ui_options)
ui_options.extend([
    'min_uploads'     ,
    'max_uploads'     ,
    'max_initiate'    ,
    'max_allow_in'    ,
    'max_files_open'  ,
    'display_interval',
    'pause'           ,
    'donated'         ,
    'notified'        ,
    ])


if is_frozen_exe:
    ui_options.append('progressbar_hack')
    defproghack = 0
    wv = sys.getwindowsversion()
    if (wv[3], wv[0], wv[1]) == (2, 5, 1):
        # turn on progress bar hack by default for Win XP 
        defproghack = 1
    defaults.extend((('progressbar_hack' , defproghack, ''),)) 
                     
main_torrent_dnd_tip = 'drag to reorder'
torrent_menu_tip = 'right-click for menu'
torrent_tip_format = '%s:\n %s\n %s'

rate_label = ' rate: %s'

speed_classes = {
    (   4,    5): 'dialup'           ,
    (   6,   14): 'DSL/cable 128k up',
    (  15,   29): 'DSL/cable 256k up',
    (  30,   91): 'DSL 768k up'      ,
    (  92,  137): 'T1'               ,
    ( 138,  182): 'T1/E1'            ,
    ( 183,  249): 'E1'               ,
    ( 250, 5446): 'T3'               ,
    (5447,18871): 'OC3'              ,
    }


def find_dir(path):
    if os.path.isdir(path):
        return path
    directory, garbage = os.path.split(path)
    while directory:
        if os.access(directory, os.F_OK) and os.access(directory, os.W_OK):
            return directory
        directory, garbage = os.path.split(directory)
        if garbage == '':
            break        
    return None

def smart_dir(path):
    path = find_dir(path)
    if path is None:
        path = Desktop.desktop
    return path

def build_menu(menu_items, accel_group=None):
    menu = gtk.Menu()
    for label,func in menu_items:
        if label == '----':
            s = gtk.SeparatorMenuItem()
            s.show()
            menu.add(s)
        else:
            item = gtk.MenuItem(label)
            if func is not None:
                item.connect("activate", func)
            else:
                item.set_sensitive(False)
            if accel_group is not None:
                accel_index = label.find('_')
                if accel_index > -1:
                    accel_key = label[accel_index+1]
                    item.add_accelerator("activate", accel_group,
                                         ord(accel_key),
                                         gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)

            item.show()
            menu.add(item)
    return menu

class Validator(gtk.Entry):
    valid_chars = '1234567890'
    minimum = None
    maximum = None
    cast = int
    
    def __init__(self, option_name, config, setfunc):
        gtk.Entry.__init__(self)
        self.option_name = option_name
        self.config      = config
        self.setfunc     = setfunc

        self.set_text(str(config[option_name]))
            
        self.set_size_request(self.width,-1)
        
        self.connect('insert-text', self.text_inserted)
        self.connect('focus-out-event', self.focus_out)

    def get_value(self):
        value = None
        try:
            value = self.cast(self.get_text())
        except ValueError:
            pass
        return value

    def set_value(self, value):
        self.set_text(str(value))
        self.setfunc(self.option_name, value)        
        
    def focus_out(self, entry, widget):
        value = self.get_value()

        if value is None:
            return

        if (self.minimum is not None) and (value < self.minimum):
            value = self.minimum
        if (self.maximum is not None) and (value > self.maximum):
            value = self.maximum

        self.set_value(value)

    def text_inserted(self, entry, input, position, user_data):
        for i in input:
            if (self.valid_chars is not None) and (i not in self.valid_chars):
                self.emit_stop_by_name('insert-text')
                return True


class IPValidator(Validator):
    valid_chars = '1234567890.'
    width = 128
    cast = str

class PortValidator(Validator):
    width = 64
    minimum = 0
    maximum = 65535

    def add_end(self, end_name):
        self.end_option_name = end_name

    def set_value(self, value):
        self.set_text(str(value))
        self.setfunc(self.option_name, value)
        self.setfunc(self.end_option_name, value+PORT_RANGE)


class PercentValidator(Validator):
    width = 48
    minimum = 0

class MinutesValidator(Validator):
    width = 48
    minimum = 1


class RateSliderBox(gtk.VBox):
    base = 10
    multiplier = 4
    max_exponent = 3.3
    
    def __init__(self, config, torrentqueue):
        gtk.VBox.__init__(self, homogeneous=False)
        self.config = config
        self.torrentqueue = torrentqueue

        if self.config['max_upload_rate'] < self.slider_to_rate(0):
            self.config['max_upload_rate'] = self.slider_to_rate(0)

        self.rate_slider_label = gtk.Label(
            self.value_to_label(self.config['max_upload_rate']))

        self.rate_slider_adj = gtk.Adjustment(
            self.rate_to_slider(self.config['max_upload_rate']), 0,
            self.max_exponent, 0.01, 0.1)
        
        self.rate_slider = gtk.HScale(self.rate_slider_adj)
        self.rate_slider.set_draw_value(False)
        self.rate_slider_adj.connect('value_changed', self.set_max_upload_rate)

        self.pack_start(self.rate_slider_label , expand=False, fill=False)
        self.pack_start(self.rate_slider       , expand=False, fill=False)

        if False: # this shows the legend for the slider
            self.rate_slider_legend = gtk.HBox(homogeneous=True)
            for i in range(int(self.max_exponent+1)):
                label = gtk.Label(str(self.slider_to_rate(i)))
                alabel = halign(label, i/self.max_exponent)
                self.rate_slider_legend.pack_start(alabel,
                                                   expand=True, fill=True)
            self.pack_start(self.rate_slider_legend, expand=False, fill=False)


    def start(self):
        self.set_max_upload_rate(self.rate_slider_adj)

    def rate_to_slider(self, value):
        return math.log(value/self.multiplier, self.base)

    def slider_to_rate(self, value):
        return int(round(self.base**value * self.multiplier))

    def value_to_label(self, value):
        conn_type = ''
        for key, conn in speed_classes.items():
            min_v, max_v = key
            if min_v <= value <= max_v:
                conn_type = ' (%s)'%conn
                break
        label = 'Maximum upload'+(rate_label % Rate(value*1024)) + \
                conn_type
        return label

    def set_max_upload_rate(self, adj):
        option = 'max_upload_rate'
        value = self.slider_to_rate(adj.get_value())
        self.config[option] = value
        self.torrentqueue.set_config(option, value)
        self.rate_slider_label.set_text(self.value_to_label(int(value)))


class StopStartButton(gtk.Button):
    stop_tip  = 'Temporarily stop all running torrents'
    start_tip = 'Resume downloading'

    def __init__(self, main):
        gtk.Button.__init__(self)
        self.main = main
        self.connect('clicked', self.toggle)

        self.stop_image = gtk.Image()
        self.stop_image.set_from_stock('bt-pause', gtk.ICON_SIZE_BUTTON)
        self.stop_image.show()

        self.start_image = gtk.Image()
        self.start_image.set_from_stock('bt-play', gtk.ICON_SIZE_BUTTON)
        self.start_image.show()

        self.has_image = False

    def toggle(self, widget):
        self.set_paused(not self.main.config['pause'])

    def set_paused(self, paused):
        if paused:
            if self.has_image:
                self.remove(self.stop_image)
            self.add(self.start_image)
            self.main.tooltips.set_tip(self, self.start_tip)
            self.main.stop_queue()
        else:
            if self.has_image:
                self.remove(self.start_image)
            self.add(self.stop_image)
            self.main.tooltips.set_tip(self, self.stop_tip )
            self.main.restart_queue()
        self.has_image = True


class VersionWindow(Window):
    def __init__(self, main, newversion, download_url):
        Window.__init__(self)
        self.set_title('New %s version available'%app_name)
        self.set_border_width(SPACING)
        self.set_resizable(gtk.FALSE)
        self.main = main
        self.newversion = newversion
        self.download_url = download_url
        self.connect('destroy', lambda w: self.main.window_closed('version'))
        self.vbox = gtk.VBox(spacing=SPACING)
        self.hbox = gtk.HBox(spacing=SPACING)
        self.image = gtk.Image()
        self.image.set_from_stock(gtk.STOCK_DIALOG_INFO, gtk.ICON_SIZE_DIALOG)
        self.hbox.pack_start(self.image)
        
        self.label = gtk.Label()
        self.label.set_markup(
            ("A newer version of %s is available.\n" % app_name) +
            ("You are using %s, and the new version is %s.\n" % (version, newversion)) +
            ("You can always get the latest version from \n%s" % self.download_url)
            ) 
        self.label.set_selectable(True)
        self.hbox.pack_start(self.label)
        self.vbox.pack_start(self.hbox)
        self.bbox = gtk.HBox(spacing=SPACING)

        self.closebutton = gtk.Button('Download _later')
        self.closebutton.connect('clicked', self.close)

        self.newversionbutton = gtk.Button('Download _now')
        self.newversionbutton.connect('clicked', self.get_newversion)

        self.bbox.pack_end(self.newversionbutton, expand=gtk.FALSE, fill=gtk.FALSE)
        self.bbox.pack_end(self.closebutton     , expand=gtk.FALSE, fill=gtk.FALSE)

        self.checkbox = gtk.CheckButton('_Remind me later')
        self.checkbox.set_active(True)
        self.checkbox.connect('toggled', self.remind_toggle)
        
        self.bbox.pack_start(self.checkbox, expand=gtk.FALSE, fill=gtk.FALSE)

        self.vbox.pack_start(self.bbox)
        
        self.add(self.vbox)
        self.show_all()

    def remind_toggle(self, widget):
        v = self.checkbox.get_active()
        notified = ''
        if v:
            notified = ''
        else:
            notified = self.newversion
        self.main.set_config('notified', notified)

    def close(self, widget):
        self.destroy()

    def get_newversion(self, widget):
        self.main.visit_url(self.download_url)
        self.destroy()


class AboutWindow(object):

    def __init__(self, main, donatefunc):
        self.win = Window()
        self.win.set_title('About %s'%app_name)
        self.win.set_size_request(300,400)
        self.win.set_border_width(SPACING)
        self.win.set_resizable(False)
        self.win.connect('destroy', lambda w: main.window_closed('about'))
        self.scroll = gtk.ScrolledWindow()
        self.scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self.scroll.set_shadow_type(gtk.SHADOW_IN)

        self.outervbox = gtk.VBox()

        self.outervbox.pack_start(get_logo(96), expand=False, fill=False)

        self.outervbox.pack_start(gtk.Label('Version %s'%version), expand=False, fill=False)

        self.vbox = gtk.VBox()
        self.vbox.set_size_request(250, -1)

        credits_f = file(os.path.join(doc_root, 'credits.txt'))
        l = credits_f.read()
        credits_f.close()
        label = gtk.Label(l.strip())
        label.set_line_wrap(gtk.TRUE)
        label.set_selectable(True)
        label.set_justify(gtk.JUSTIFY_CENTER)
        label.set_size_request(250,-1)
        self.vbox.pack_start(label, expand=False, fill=False)

        self.scroll.add_with_viewport(self.vbox)

        self.outervbox.pack_start(self.scroll, padding=SPACING)

        self.donatebutton = gtk.Button("Donate")
        self.donatebutton.connect('clicked', donatefunc)
        self.donatebuttonbox = gtk.HButtonBox()
        self.donatebuttonbox.pack_start(self.donatebutton,
                                        expand=False, fill=False)
        self.outervbox.pack_end(self.donatebuttonbox, expand=False, fill=False)

        self.win.add(self.outervbox)

        self.win.show_all()

    def close(self, widget):
        self.win.destroy()    


class LogWindow(object):
    def __init__(self, main, logbuffer, config):
        self.config = config
        self.main = main
        self.win = Window()
        self.win.set_title('%s Activity Log'%app_name)
        self.win.set_default_size(600, 200)
        self.win.set_border_width(SPACING)
            
        self.buffer = logbuffer
        self.text = gtk.TextView(self.buffer)
        self.text.set_editable(False)
        self.text.set_cursor_visible(False)
        self.text.set_wrap_mode(gtk.WRAP_WORD)

        self.scroll = gtk.ScrolledWindow()
        self.scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self.scroll.set_shadow_type(gtk.SHADOW_IN)
        self.scroll.add(self.text)

        self.vbox = gtk.VBox(spacing=SPACING)
        self.vbox.pack_start(self.scroll)

        self.buttonbox = gtk.HButtonBox()
        self.buttonbox.set_spacing(SPACING)
        
        self.closebutton = gtk.Button(stock='gtk-close')
        self.closebutton.connect('clicked', self.close)
        
        self.savebutton = gtk.Button(stock='gtk-save')
        self.savebutton.connect('clicked', self.save_log_file_selection)

        self.clearbutton = gtk.Button(stock='gtk-clear')
        self.clearbutton.connect('clicked', self.clear_log)

        self.buttonbox.pack_start(self.savebutton)
        self.buttonbox.pack_start(self.closebutton)

        self.hbox2 = gtk.HBox(homogeneous=False)

        self.hbox2.pack_end(self.buttonbox, expand=False, fill=False)

        bb = gtk.HButtonBox()
        bb.pack_start(self.clearbutton)
        self.hbox2.pack_start(bb, expand=False, fill=True)

        self.vbox.pack_end(self.hbox2, expand=False, fill=True)

        self.win.add(self.vbox)        
        self.win.connect("destroy", lambda w: self.main.window_closed('log'))
        self.scroll_to_end()
        self.win.show_all()

    def scroll_to_end(self):
        mark = self.buffer.create_mark(None, self.buffer.get_end_iter())
        self.text.scroll_mark_onscreen(mark)

    def save_log_file_selection(self, *args):
        name = 'bittorrent.log'
        path = smart_dir(self.config['save_in'])
        fullname = os.path.join(path, name)
        self.main.open_window('savefile',
                              title="Save log in:",
                              fullname=fullname,
                              got_location_func=self.save_log,
                              no_location_func=lambda: self.main.window_closed('savefile'))


    def save_log(self, saveas):
        self.main.window_closed('savefile')
        f = file(saveas, 'w')
        f.write(self.buffer.get_text(self.buffer.get_start_iter(),
                                     self.buffer.get_end_iter()))
        save_message = self.buffer.log_text('log saved', None)
        f.write(save_message)
        f.close()

    def clear_log(self, *args):
        self.buffer.clear_log()

    def close(self, widget):
        self.win.destroy()


class LogBuffer(gtk.TextBuffer):
    h = { CRITICAL:'critical',
          ERROR   :'error'   ,
          WARNING :'warning' ,
          INFO    :'info'    , } 

    def __init__(self):
        gtk.TextBuffer.__init__(self)        

        tt = self.get_tag_table()

        size_tag = gtk.TextTag('small')
        size_tag.set_property('size-points', 10)
        tt.add(size_tag)

        info_tag = gtk.TextTag('info')
        info_tag.set_property('foreground', '#00a040')
        tt.add(info_tag)

        warning_tag = gtk.TextTag('warning')
        warning_tag.set_property('foreground', '#a09000')
        tt.add(warning_tag)

        error_tag = gtk.TextTag('error')
        error_tag.set_property('foreground', '#b00000')
        tt.add(error_tag)

        critical_tag = gtk.TextTag('critical')
        critical_tag.set_property('foreground', '#b00000')
        critical_tag.set_property('weight', pango.WEIGHT_BOLD)
        tt.add(critical_tag)


    def log_text(self, text, severity=CRITICAL):
        now_str = datetime.datetime.strftime(datetime.datetime.now(),
                                             '[%Y-%m-%d %H:%M:%S] ')
        self.insert_with_tags_by_name(self.get_end_iter(), now_str, 'small')
        if severity is not None:
            self.insert_with_tags_by_name(self.get_end_iter(), '%s\n'%text,
                                          'small', self.h[severity])
        else:
            self.insert_with_tags_by_name(self.get_end_iter(),
                                          ' -- %s -- \n'%text, 'small')
            
        return now_str+text+'\n'

    def clear_log(self):
        self.set_text('')
        self.log_text('log cleared', None)



class SettingsWindow(object):

    def __init__(self, main, config, setfunc):
        self.main = main
        self.setfunc = setfunc
        self.config = config
        self.win = Window()
        self.win.connect("destroy", lambda w: main.window_closed('settings'))
        self.win.set_title('%s Settings'%app_name)
        self.win.set_border_width(SPACING)

        self.notebook = gtk.Notebook()

        self.vbox = gtk.VBox(spacing=SPACING)
        self.vbox.pack_start(self.notebook, expand=False, fill=False)

        # Saving tab
        self.saving_box = gtk.VBox(spacing=SPACING)
        self.saving_box.set_border_width(SPACING)
        self.notebook.append_page(self.saving_box, gtk.Label("Saving"))

        self.dl_frame = gtk.Frame("Download folder:")
        self.saving_box.pack_start(self.dl_frame, expand=False, fill=False)

        self.dl_box = gtk.VBox(spacing=SPACING)
        self.dl_box.set_border_width(SPACING)
        self.dl_frame.add(self.dl_box)
        self.save_in_box = gtk.HBox(spacing=SPACING)
        self.save_in_box.pack_start(gtk.Label("Default:"), expand=False, fill=False)

        self.dl_save_in = gtk.Entry()
        self.dl_save_in.set_editable(False)
        self.set_save_in(self.config['save_in'])
        self.save_in_box.pack_start(self.dl_save_in, expand=True, fill=True)

        self.dl_save_in_button = gtk.Button('Change...')
        self.dl_save_in_button.connect('clicked', self.get_save_in)
        self.save_in_box.pack_start(self.dl_save_in_button, expand=False, fill=False)
        self.dl_box.pack_start(self.save_in_box, expand=False, fill=False)
        self.dl_ask_checkbutton = gtk.CheckButton("Ask where to save each download")
        self.dl_ask_checkbutton.set_active( bool(self.config['ask_for_save']) )

        def toggle_save(w):
            self.config['ask_for_save'] = int(not self.config['ask_for_save'])
            self.setfunc('ask_for_save', self.config['ask_for_save'])

        self.dl_ask_checkbutton.connect('toggled', toggle_save) 
        self.dl_box.pack_start(self.dl_ask_checkbutton, expand=False, fill=False)
        # end Saving tab

        # Downloading tab
        self.downloading_box = gtk.VBox(spacing=SPACING)
        self.downloading_box.set_border_width(SPACING)
        self.notebook.append_page(self.downloading_box, gtk.Label("Downloading"))

        self.dnd_frame = gtk.Frame('Starting additional torrents manually:')
        self.dnd_box = gtk.VBox(spacing=SPACING, homogeneous=True)
        self.dnd_box.set_border_width(SPACING)

        self.dnd_states = ['replace','add','ask']
        self.dnd_original_state = self.config['start_torrent_behavior']
        
        self.always_replace_radio = gtk.RadioButton(
            group=None,
            label="Always stops the _last running torrent")
        self.dnd_box.pack_start(self.always_replace_radio)
        self.always_replace_radio.state_name = self.dnd_states[0]
        
        self.always_add_radio = gtk.RadioButton(
            group=self.always_replace_radio,
            label="Always starts the torrent in _parallel")
        self.dnd_box.pack_start(self.always_add_radio)
        self.always_add_radio.state_name = self.dnd_states[1]

        self.always_ask_radio = gtk.RadioButton(
            group=self.always_replace_radio,
            label="_Asks each time"
            )
        self.dnd_box.pack_start(self.always_ask_radio)
        self.always_ask_radio.state_name = self.dnd_states[2]

        self.dnd_group = self.always_replace_radio.get_group()
        for r in self.dnd_group:
            r.connect('toggled', self.start_torrent_behavior_changed)

        self.set_start_torrent_behavior(self.config['start_torrent_behavior'])
        
        self.dnd_frame.add(self.dnd_box)
        self.downloading_box.pack_start(self.dnd_frame, expand=False, fill=False)

        self.next_torrent_frame = gtk.Frame('Seed completed torrents:')
        self.next_torrent_box   = gtk.VBox(spacing=SPACING, homogeneous=True)
        self.next_torrent_box.set_border_width(SPACING) 
        
        self.next_torrent_frame.add(self.next_torrent_box)


        self.next_torrent_ratio_box = gtk.HBox()
        self.next_torrent_ratio_box.pack_start(gtk.Label('until share ratio reaches '),
                                               fill=False, expand=False)
        self.next_torrent_ratio_field = PercentValidator('next_torrent_ratio',
                                                         self.config, self.setfunc)
        self.next_torrent_ratio_box.pack_start(self.next_torrent_ratio_field,
                                               fill=False, expand=False)
        self.next_torrent_ratio_box.pack_start(gtk.Label(' percent, or'),
                                               fill=False, expand=False)
        self.next_torrent_box.pack_start(self.next_torrent_ratio_box)


        self.next_torrent_time_box = gtk.HBox()
        self.next_torrent_time_box.pack_start(gtk.Label('for '),
                                              fill=False, expand=False)
        self.next_torrent_time_field = MinutesValidator('next_torrent_time',
                                                        self.config, self.setfunc)
        self.next_torrent_time_box.pack_start(self.next_torrent_time_field,
                                              fill=False, expand=False)
        self.next_torrent_time_box.pack_start(gtk.Label(' minutes, whichever comes first.'),
                                              fill=False, expand=False)
        self.next_torrent_box.pack_start(self.next_torrent_time_box)

        
        self.downloading_box.pack_start(self.next_torrent_frame, expand=False, fill=False)

        self.last_torrent_frame = gtk.Frame('Seed last completed torrent:')
        self.last_torrent_vbox = gtk.VBox(spacing=SPACING)
        self.last_torrent_vbox.set_border_width(SPACING)
        self.last_torrent_box = gtk.HBox()
        self.last_torrent_box.pack_start(gtk.Label('until share ratio reaches '),
                                         expand=False, fill=False)
        self.last_torrent_ratio_field = PercentValidator('last_torrent_ratio',
                                                         self.config, self.setfunc)
        self.last_torrent_box.pack_start(self.last_torrent_ratio_field,
                                         fill=False, expand=False)
        self.last_torrent_box.pack_start(gtk.Label(' percent.'),
                                         fill=False, expand=False)
        self.last_torrent_vbox.pack_start(self.last_torrent_box)
        
        self.last_torrent_frame.add(self.last_torrent_vbox)
        self.downloading_box.pack_start(self.last_torrent_frame, expand=False, fill=False)
        self.downloading_box.pack_start(lalign(gtk.Label('"0 percent" means seed forever.')))

        # end Downloading tab
        

        # Network tab
        self.network_box = gtk.VBox(spacing=SPACING)
        self.network_box.set_border_width(SPACING)
        self.notebook.append_page(self.network_box, gtk.Label('Network'))

        self.port_range_frame = gtk.Frame('Look for available port:')        
        self.port_range = gtk.HBox()
        self.port_range.set_border_width(SPACING)
        self.port_range.pack_start(gtk.Label('starting at port: '),
                                   expand=False, fill=False)
        self.minport_field = PortValidator('minport', self.config, self.setfunc)
        self.minport_field.add_end('maxport')
        self.port_range.pack_start(self.minport_field, expand=False, fill=False)
        self.minport_field.settingswindow = self
        self.port_range.pack_start(gtk.Label(' (0-65535)'),
                                   expand=False, fill=False)

        self.port_range_frame.add(self.port_range)
        self.network_box.pack_start(self.port_range_frame, expand=False, fill=False)


        self.ip_frame = gtk.Frame('IP to report to the tracker:')
        self.ip_box = gtk.VBox()
        self.ip_box.set_border_width(SPACING)
        self.ip_field = IPValidator('ip', self.config, self.setfunc)
        self.ip_box.pack_start(self.ip_field, expand=False, fill=False)
        self.ip_box.pack_start(lalign(gtk.Label('(Has no effect unless you are on the\nsame local network as the tracker)')), expand=False, fill=False)
        self.ip_frame.add(self.ip_box)
        self.network_box.pack_start(self.ip_frame, expand=False, fill=False)


        if is_frozen_exe: 
            self.reset_checkbox = gtk.CheckButton("Potential Windows TCP stack fix")
            self.reset_checkbox.set_active( bool(self.config['chop_max_allow_in']) )
            self.network_box.pack_start(self.reset_checkbox, expand=False, fill=False)

            def toggle_reset(w):
                self.config['chop_max_allow_in'] = int(not self.config['chop_max_allow_in'])
                self.setfunc('chop_max_allow_in', self.config['chop_max_allow_in'])
            self.reset_checkbox.connect('toggled', toggle_reset)
        
        # end Network tab        

        # Misc tab
        if is_frozen_exe:
            # allow the user to set the progress bar text to all black
            self.progressbar_hack = gtk.CheckButton('Progress bar text is always black\n(requires restart)')
            if self.config['progressbar_hack'] :
                self.progressbar_hack.set_active(True)
            else:
                self.progressbar_hack.set_active(False)
            def progressbar_callback(w):
                self.config['progressbar_hack'] = int(not self.config['progressbar_hack'])
                self.setfunc('progressbar_hack', self.config['progressbar_hack'])
            self.progressbar_hack.connect('toggled', progressbar_callback)

            self.misc_box = gtk.VBox(spacing=SPACING)
            self.misc_box.set_border_width(SPACING)
            self.misc_box.pack_start(self.progressbar_hack, expand=False, fill=False)
            self.notebook.append_page(self.misc_box, gtk.Label("Misc"))
        # end Misc tab

        # Advanced tab
        if advanced_ui:
            self.advanced_box = gtk.VBox(spacing=SPACING)
            self.advanced_box.set_border_width(SPACING)
            hint = gtk.Label("WARNING: Changing these settings can\nprevent %s from functioning correctly."%app_name)
            self.advanced_box.pack_start(lalign(hint), expand=False, fill=False)
            self.store = gtk.ListStore(*[gobject.TYPE_STRING] * 2)
            for option in ui_options[advanced_ui_options_index:]:
                self.store.append((option, str(self.config[option])))

            self.treeview = gtk.TreeView(self.store)
            r = gtk.CellRendererText()
            column = gtk.TreeViewColumn('Option', r, text=0)
            self.treeview.append_column(column)
            r = gtk.CellRendererText()
            r.set_property('editable', True)
            r.connect('edited', self.store_value_edited)
            column = gtk.TreeViewColumn('Value', r, text=1)
            self.treeview.append_column(column)

            self.advanced_box.pack_start(self.treeview, expand=False, fill=False)
            self.notebook.append_page(self.advanced_box, gtk.Label("Advanced"))
        

        self.win.add(self.vbox)
        self.win.show_all()


    def get_save_in(self, widget=None):
        self.file_selection = self.main.open_window('choosefolder',
                                                    title='Choose default download directory',
                                                    fullname=self.config['save_in'],
                                                    got_location_func=self.set_save_in,
                                                    no_location_func=lambda: self.main.window_closed('choosefolder'))

    def set_save_in(self, save_location):
        self.main.window_closed('choosefolder')
        if os.path.isdir(save_location):
            if save_location[-1] != os.sep:
                save_location += os.sep
            self.config['save_in'] = save_location
            save_in = path_wrap(self.config['save_in'])
            self.dl_save_in.set_text(save_in)
            self.setfunc('save_in', self.config['save_in'])

    def set_start_torrent_behavior(self, state_name):
        if state_name in self.dnd_states:
            for r in self.dnd_group:
                if r.state_name == state_name:
                    r.set_active(True)
                else:
                    r.set_active(False)
        else:
            self.always_replace_radio.set_active(True)        

    def start_torrent_behavior_changed(self, radiobutton):
        if radiobutton.get_active():
            self.setfunc('start_torrent_behavior', radiobutton.state_name)

    def store_value_edited(self, cell, row, new_text):
        it = self.store.get_iter_from_string(row)
        option = ui_options[int(row)+advanced_ui_options_index]
        t = type(defconfig[option])
        try:
            if t is type(None) or t is str:
                value = new_text
            elif t is int or t is long:
                value = int(new_text)
            elif t is float:
                value = float(new_text)
            else:
                raise TypeError, str(t)
        except ValueError:
            return
        self.setfunc(option, value)
        self.store.set(it, 1, str(value))

    def close(self, widget):
        self.win.destroy()


class FileListWindow(object):

    def __init__(self, metainfo, closefunc):
        self.metainfo = metainfo
        self.setfunc = None
        self.allocfunc = None
        priorities = [0, 0]
        self.win = Window()
        self.win.set_title('Files in "%s"' % self.metainfo.name)
        self.win.connect("destroy", closefunc)

        self.box1 = gtk.VBox()

        size_request = [0,0]
        
        if advanced_ui and False:
            self.toolbar = gtk.Toolbar()
            for label, stockicon, method, arg in (("Apply"         , gtk.STOCK_APPLY  , self.set_priorities, None ),
                                                  ("Allocate"      , gtk.STOCK_SAVE   , self.dosomething, 'alloc',),
                                                  ("Never download", gtk.STOCK_DELETE , self.dosomething, 'never',),
                                                  ("Decrease"      , gtk.STOCK_GO_DOWN, self.dosomething, -1     ,),
                                                  ("Increase"      , gtk.STOCK_GO_UP  , self.dosomething, +1     ,),):
                self.make_tool_item(label, stockicon, method, arg)
            self.box1.pack_start(self.toolbar, False)
            size_request = [450,54]
            
        self.sw = gtk.ScrolledWindow()
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.box1.pack_start(self.sw)
        self.win.add(self.box1)

        columns = ['Filename','Length','%']
        pre_size_list = ['MMMMMMMMMMMMMMMMMMMMMMMM', '6666 MB', '100.0']
        if advanced_ui:
            columns += ['A','Order']
            pre_size_list += ['*','None','black']
        num_columns = len(pre_size_list)

        self.store = gtk.ListStore(*[gobject.TYPE_STRING] * num_columns)
        self.store.append(pre_size_list)
        self.treeview = gtk.TreeView(self.store)
        cs = []
        for i, name in enumerate(columns):
            r = gtk.CellRendererText()
            r.set_property('xalign', (0, 1, 1, .5, 1)[i])
            if i != 4:
                column = gtk.TreeViewColumn(name, r, text = i)
            else:
                column = gtk.TreeViewColumn(name, r, text = i, foreground = i + 1)
            column.set_resizable(True)
            self.treeview.append_column(column)
            cs.append(column)

        self.sw.add(self.treeview)
        self.treeview.set_headers_visible(False)
        self.treeview.columns_autosize()
        self.box1.show_all()
        self.treeview.realize()

        for column in cs:
            column.set_fixed_width(max(5,column.get_width()))
            column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        self.treeview.set_headers_visible(True)
        self.store.clear()
        self.treeview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.piecelen = self.metainfo.piece_length
        self.lengths = self.metainfo.sizes
        self.initialize_file_priorities(priorities)
        for name, size, priority in itertools.izip(self.metainfo.orig_files,
                                        self.metainfo.sizes, self.priorities):
            row = [name, Size(size), '?',]
            if advanced_ui:
                row += ['', priority == 255 and 'None' or str(priority), 'black']
            self.store.append(row)

        tvsr = self.treeview.size_request()
        vertical_padding = 18 
        size_request = [max(size_request[0],tvsr[0]),
                        (size_request[1] + tvsr[1] ) + vertical_padding]
        maximum_height = 300
        if size_request[1] > maximum_height - SCROLLBAR_WIDTH:
            size_request[1] = maximum_height
            size_request[0] = size_request[0] + SCROLLBAR_WIDTH
        self.win.set_default_size(*size_request)
                                  
        self.win.show_all()

    def make_tool_item_24(self, label, stockicon, method, arg): # for pygtk 2.4
        icon = gtk.Image()
        icon.set_from_stock(stockicon, gtk.ICON_SIZE_SMALL_TOOLBAR)
        item = gtk.ToolButton(icon_widget=icon, label=label)
        item.set_homogeneous(True)
        if arg is not None:
            item.connect('clicked', method, arg)
        else:
            item.connect('clicked', method)
        self.toolbar.insert(item, 0)

    def make_tool_item_22(self, label, stockicon, method, arg): # for pygtk 2.2
        icon = gtk.Image()
        icon.set_from_stock(stockicon, gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.toolbar.prepend_item(label, None, None, icon, method, user_data=arg)

    if gtk.pygtk_version >= (2, 4):
        make_tool_item = make_tool_item_24
    else:
        make_tool_item = make_tool_item_22
        
    def set_priorities(self, widget):
        r = []
        piece = 0
        pos = 0
        curprio = prevprio = 1000
        for priority, length in itertools.izip(self.priorities, self.lengths):
            pos += length
            curprio = min(priority, curprio)
            while pos >= (piece + 1) * self.piecelen:
                if curprio != prevprio:
                    r.extend((piece, curprio))
                prevprio = curprio
                if curprio == priority:
                    piece = pos // self.piecelen
                else:
                    piece += 1
                if pos == piece * self.piecelen:
                    curprio = 1000
                else:
                    curprio = priority
        if curprio != prevprio:
            r.extend((piece, curprio))
        self.setfunc(r)
        it = self.store.get_iter_first()
        for i in xrange(len(self.priorities)):
            self.store.set_value(it, 5, "black")
            it = self.store.iter_next(it)
        self.origpriorities = list(self.priorities)

    def initialize_file_priorities(self, piecepriorities):
        self.priorities = []
        piecepriorities = piecepriorities + [999999999]
        it = iter(piecepriorities)
        assert it.next() == 0
        pos = piece = curprio = 0
        for length in self.lengths:
            pos += length
            priority = curprio
            while pos >= piece * self.piecelen:
                curprio = it.next()
                if pos > piece * self.piecelen:
                    priority = max(priority, curprio)
                piece = it.next()
            self.priorities.append(priority)
        self.origpriorities = list(self.priorities)

    def dosomething(self, widget, dowhat):
        self.treeview.get_selection().selected_foreach(self.adjustfile, dowhat)

    def adjustfile(self, treemodel, path, it, dowhat):
        row = path[0]
        if dowhat == "alloc":
            self.allocfunc(row)
            return
        if self.priorities[row] == 255:
            return
        if dowhat == 'never':
            self.priorities[row] = 255
        else:
            if self.priorities[row] == 0 and dowhat < 0:
                return
            self.priorities[row] += dowhat
        treemodel.set_value(it, 4, self.priorities[row] == 255 and 'None' or str(self.priorities[row]))
        treemodel.set_value(it, 5, self.priorities[row] == self.origpriorities[row] and 'black' or 'red')

    def update(self, left, allocated):
        it = self.store.get_iter_first()
        for left, total, alloc in itertools.izip(left, self.lengths,
                                                 allocated):
            if total == 0:
                p = 1
            else:
                p = (total - left) / total
            self.store.set_value(it, 2, "%.1f" % (int(p * 1000)/10))
            if advanced_ui:
                self.store.set_value(it, 3, '*' * alloc)
            it = self.store.iter_next(it)

    def close(self):
        self.win.destroy()


class PeerListWindow(object):

    def __init__(self, torrent_name, closefunc):
        self.win = Window()
        self.win.connect("destroy", closefunc)
        self.win.set_title( 'Peers for "%s"'%torrent_name)
        self.sw = gtk.ScrolledWindow()
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self.sw.set_shadow_type(gtk.SHADOW_IN)
        self.win.add(self.sw)

        column_header = ['IP address', 'Client', 'Connection', 'KB/s down', 'KB/s up', 'MB downloaded', 'MB uploaded', '% complete', 'KB/s est. peer download']
        pre_size_list = ['666.666.666.666', 'TorrentStorm 1.3', 'bad peer', 66666, 66666, '1666.66', '1666.66', '100.0', 6666]
        numeric_cols = [3,4,5,6,7,8]
        store_types = [gobject.TYPE_STRING]*3  + [gobject.TYPE_INT]*2 + [gobject.TYPE_STRING]*3 + [gobject.TYPE_INT]
        
        if advanced_ui:
            column_header[2:2] = ['Peer ID']
            pre_size_list[2:2] = ['-AZ2104-']
            store_types[2:2]   = [gobject.TYPE_STRING]
            column_header[5:5] = ['Interested','Choked','Snubbed']
            pre_size_list[5:5] = ['*','*','*']
            store_types[5:5]   = [gobject.TYPE_STRING]*3
            column_header[9:9] = ['Interested','Choked','Optimistic upload']
            pre_size_list[9:9] = ['*','*','*']
            store_types[9:9]   = [gobject.TYPE_STRING]*3
            numeric_cols = [4,8,12,13,14,15]

        num_columns = len(column_header)
        self.store = gtk.ListStore(*store_types)
        self.store.append(pre_size_list)

        def makesortfunc(sort_func):
            def sortfunc(treemodel, iter1, iter2, column):
                a_str = treemodel.get_value(iter1, column)
                b_str = treemodel.get_value(iter2, column)
                if a_str is not None and b_str is not None:
                    return sort_func(a_str,b_str)
                else:
                    return 0
            return sortfunc

        def ip_sort(a_str,b_str):
            a = map(int, a_str.split('.'))
            b = map(int, b_str.split('.'))
            return cmp(a,b)

        def float_sort(a_str,b_str):
            a,b = 0,0
            try: a = float(a_str)
            except ValueError: pass
            try: b = float(b_str)
            except ValueError: pass
            return cmp(a,b)

        self.store.set_sort_func(0, makesortfunc(ip_sort), 0)
        for i in range(2,5):
            self.store.set_sort_func(num_columns-i, makesortfunc(float_sort), num_columns-i)
        
        self.treeview = gtk.TreeView(self.store)
        cs = []
        for i, name in enumerate(column_header):
            r = gtk.CellRendererText()
            if i in numeric_cols:
                r.set_property('xalign', 1)
            column = gtk.TreeViewColumn(name, r, text = i)
            column.set_resizable(True)
            column.set_min_width(5)
            column.set_sort_column_id(i)
            self.treeview.append_column(column)
            cs.append(column)
        self.treeview.set_rules_hint(True)
        self.sw.add(self.treeview)
        self.treeview.set_headers_visible(False)
        self.treeview.columns_autosize()
        self.sw.show_all()
        self.treeview.realize()
        for column in cs:
            column.set_fixed_width(column.get_width())
            column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        self.treeview.set_headers_visible(True)
        self.store.clear()
        self.treeview.get_selection().set_mode(gtk.SELECTION_NONE)
        width = self.treeview.size_request()[0]
        self.win.set_default_size(width+SCROLLBAR_WIDTH, 300)
        self.win.show_all()
        self.prev = []


    def update(self, peers, bad_peers):
        fields = []

        def p_bool(value): return value and '*' or ''

        for peer in peers:
            field = []
            field.append(peer['ip']) 

            client, version = ClientIdentifier.identify_client(peer['id']) 
            field.append(client + ' ' + version)

            if advanced_ui:
                field.append(quote(peer['id'])) 

            field.append(peer['initiation'] == 'R' and 'remote' or 'local')
            dl = peer['download']
            ul = peer['upload']

            for l in (dl, ul):
                rate = l[1]
                if rate > 100:
                    field.append(int(round(rate/(2**10)))) 
                else:
                    field.append(0)
                if advanced_ui:
                    field.append(p_bool(l[2]))
                    field.append(p_bool(l[3]))
                    if len(l) > 4:
                        field.append(p_bool(l[4]))
                    else:
                        field.append(p_bool(peer['is_optimistic_unchoke']))

            field.append('%.2f'%round(dl[0] / 2**20, 2))
            field.append('%.2f'%round(ul[0] / 2**20, 2))
            field.append('%.1f'%round(int(peer['completed']*1000)/10, 1))

            field.append(int(peer['speed']//(2**10)))

            fields.append(field)

        for (ip, (is_banned, stats)) in bad_peers.iteritems():
            field = []
            field.append(ip)

            client, version = ClientIdentifier.identify_client(stats.peerid)
            field.append(client + ' ' + version)

            if advanced_ui:
                field.append(quote(stats.peerid))

            field.append('bad peer')

            # the sortable peer list won't take strings in these fields
            field.append(0) 

            if advanced_ui:
                field.extend([0] * 7) # upRate, * fields
            else:
                field.extend([0] * 1) # upRate
                
            field.append("%d ok" % stats.numgood)
            field.append("%d bad" % len(stats.bad))
            if is_banned: # completion
                field.append('banned')
            else:
                field.append('ok')
            field.append(0) # peer dl rate
            fields.append(field)

        if self.store.get_sort_column_id() < 0:
            # ListStore is unsorted, it might be faster to set only modified fields
            it = self.store.get_iter_first()
            for old, new in itertools.izip(self.prev, fields):
                if old != new:
                    for i, value in enumerate(new):
                        if value != old[i]:
                            self.store.set_value(it, i, value)
                it = self.store.iter_next(it)
            for i in range(len(fields), len(self.prev)):
                self.store.remove(it)
            for i in range(len(self.prev), len(fields)):
                self.store.append(fields[i])
            self.prev = fields
        else:
            # ListStore is sorted, no reason not to to reset all fields
            self.store.clear()
            for field in fields:
                self.store.append(field)
            
        

    def close(self):
        self.win.destroy()


class TorrentInfoWindow(object):

    def __init__(self, torrent_box, closefunc):
        self.win = Window()
        self.torrent_box = torrent_box
        name = self.torrent_box.metainfo.name
        self.win.set_title('Info for "%s"'%name)
        self.win.set_size_request(-1,-1)
        self.win.set_border_width(SPACING)
        self.win.set_resizable(False)
        self.win.connect('destroy', closefunc)
        self.vbox = gtk.VBox(spacing=SPACING)

        self.table = gtk.Table(rows=4, columns=3, homogeneous=False)
        self.table.set_row_spacings(SPACING)
        self.table.set_col_spacings(SPACING)
        y = 0

        def add_item(key, val, y):
            self.table.attach(ralign(gtk.Label(key)), 0, 1, y, y+1)
            v = gtk.Label(val)
            v.set_selectable(True)
            self.table.attach(lalign(v), 1, 2, y, y+1)

        add_item('Torrent name:', name, y)
        y+=1

        add_item('Announce url:', self.torrent_box.metainfo.announce, y)
        y+=1

        size = Size(self.torrent_box.metainfo.total_bytes)
        num_files = ', in one file'
        if self.torrent_box.is_batch:
            num_files = ', in %d files' % len(self.torrent_box.metainfo.sizes)
        add_item('Total size:',  str(size)+num_files, y)
        y+=1

        if advanced_ui:
            pl = self.torrent_box.metainfo.piece_length
            count, lastlen = divmod(size, pl)
            sizedetail = '%d x %d + %d = %d' % (count, pl, lastlen, int(size))
            add_item('Pieces:', sizedetail, y)
            y+=1
            add_item('Info hash:', self.torrent_box.infohash.encode('hex'), y)
            y+=1

        path = self.torrent_box.dlpath 
        filename = ''
        if not self.torrent_box.is_batch:
            path,filename = os.path.split(self.torrent_box.dlpath)
        if path[-1] != os.sep:
            path += os.sep
        path = path_wrap(path)
        add_item('Save in:', path, y)
        y+=1

        if not self.torrent_box.is_batch:
            add_item('File name:', filename, y)
            y+=1
        
        self.vbox.pack_start(self.table)

        self.vbox.pack_start(gtk.HSeparator(), expand=False, fill=False)

        self.hbox = gtk.HBox(spacing=SPACING)
        lbbox = gtk.HButtonBox()
        rbbox = gtk.HButtonBox()
        lbbox.set_spacing(SPACING)

        if OpenPath.can_open_files:
            opendirbutton = IconButton("Open directory", stock=gtk.STOCK_OPEN)
            opendirbutton.connect('clicked', self.torrent_box.open_dir)
            lbbox.pack_start(opendirbutton, expand=False, fill=False)

        opendirbutton.set_sensitive(self.torrent_box.can_open_dir())

        filelistbutton = IconButton("Show file list", stock='gtk-index')
        if self.torrent_box.is_batch:
            filelistbutton.connect('clicked', self.torrent_box.open_filelist)
        else:
            filelistbutton.set_sensitive(False)
        lbbox.pack_start(filelistbutton, expand=False, fill=False)

        closebutton = gtk.Button(stock='gtk-close')
        closebutton.connect('clicked', lambda w: self.close())
        rbbox.pack_end(closebutton, expand=False, fill=False)

        self.hbox.pack_start(lbbox, expand=False, fill=False)
        self.hbox.pack_end(  rbbox, expand=False, fill=False)

        self.vbox.pack_end(self.hbox, expand=False, fill=False)

        self.win.add(self.vbox)
        
        self.win.show_all()

    def close(self):
        self.win.destroy()


class TorrentBox(gtk.EventBox):
    
    def __init__(self, infohash, metainfo, dlpath, completion, main):
        gtk.EventBox.__init__(self)
        self.infohash = infohash
        self.metainfo = metainfo
        self.dlpath = dlpath
        self.completion = completion
        self.main = main

        self.uptotal   = self.main.torrents[self.infohash].uptotal
        self.downtotal = self.main.torrents[self.infohash].downtotal
        if self.downtotal > 0:
            self.up_down_ratio = self.uptotal / self.downtotal
        else:
            self.up_down_ratio = None

        self.infowindow = None
        self.filelistwindow = None
        self.is_batch = metainfo.is_batch
        self.menu = None
        self.menu_handler = None

        self.vbox = gtk.VBox(homogeneous=False, spacing=SPACING)
        self.label = gtk.Label()
        self.set_name()
        
        self.vbox.pack_start(lalign(self.label), expand=False, fill=False)

        self.hbox = gtk.HBox(homogeneous=False, spacing=SPACING)

        self.icon = gtk.Image()
        self.icon.set_size_request(-1, 29)

        self.iconbox = gtk.VBox()
        self.iconevbox = gtk.EventBox()        
        self.iconevbox.add(self.icon)
        self.iconbox.pack_start(self.iconevbox, expand=False, fill=False)
        self.hbox.pack_start(self.iconbox, expand=False, fill=False)
        
        self.vbox.pack_start(self.hbox)
        
        self.infobox = gtk.VBox(homogeneous=False)

        self.progressbarbox = gtk.HBox(homogeneous=False, spacing=SPACING)
        self.progressbar = gtk.ProgressBar()

        self.reset_progressbar_color()
        
        if self.completion is not None:
            self.progressbar.set_fraction(self.completion)
            if self.completion >= 1:
                done_label = self.make_done_label()
                self.progressbar.set_text(done_label)
            else:
                self.progressbar.set_text('%.1f%%'%(self.completion*100))
        else:
            self.progressbar.set_text('?')
            
        self.progressbarbox.pack_start(self.progressbar,
                                       expand=True, fill=True)

        self.buttonevbox = gtk.EventBox()
        self.buttonbox = gtk.HBox(homogeneous=True, spacing=SPACING)

        self.infobutton = gtk.Button()
        self.infoimage = gtk.Image()
        self.infoimage.set_from_stock('bt-info', gtk.ICON_SIZE_BUTTON)
        self.infobutton.add(self.infoimage)
        self.infobutton.connect('clicked', self.open_info)
        self.main.tooltips.set_tip(self.infobutton,
                                   'Torrent info')

        self.buttonbox.pack_start(self.infobutton, expand=True)

        self.cancelbutton = gtk.Button()
        self.cancelimage = gtk.Image()
        if self.completion is not None and self.completion >= 1:
            self.cancelimage.set_from_stock('bt-remove', gtk.ICON_SIZE_BUTTON)
            self.main.tooltips.set_tip(self.cancelbutton,
                                       'Remove torrent')
        else:
            self.cancelimage.set_from_stock(gtk.STOCK_CANCEL, gtk.ICON_SIZE_BUTTON)
            self.main.tooltips.set_tip(self.cancelbutton,
                                       'Abort torrent')
            
        self.cancelbutton.add(self.cancelimage)
        self.cancelbutton.connect('clicked', self.confirm_remove)
        
        self.buttonbox.pack_start(self.cancelbutton, expand=True, fill=False)
        self.buttonevbox.add(self.buttonbox)

        vbuttonbox = gtk.VBox(homogeneous=False)
        vbuttonbox.pack_start(self.buttonevbox, expand=False, fill=False)
        self.hbox.pack_end(vbuttonbox, expand=False, fill=False)

        self.infobox.pack_start(self.progressbarbox, expand=False, fill=False)

        self.hbox.pack_start(self.infobox, expand=True, fill=True)
        self.add( self.vbox )

        self.drag_source_set(gtk.gdk.BUTTON1_MASK,
                             [BT_TARGET],
                             gtk.gdk.ACTION_MOVE)
        self.connect('drag_data_get', self.drag_data_get)

        self.connect('drag_begin' , self.drag_begin )
        self.connect('drag_end'   , self.drag_end   )
        self.cursor_handler_id = self.connect('enter_notify_event', self.change_cursors)


    def reset_progressbar_color(self):
        # Hack around broken GTK-Wimp theme:
        # make progress bar text always black
        # see task #694
        if is_frozen_exe and self.main.config['progressbar_hack']:
            style = self.progressbar.get_style().copy()
            black = style.black
            self.progressbar.modify_fg(gtk.STATE_PRELIGHT, black)
        

    def change_cursors(self, *args):
        # BUG: this is in a handler that is disconnected because the
        # window attributes are None until after show_all() is called
        self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND2))
        self.buttonevbox.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.LEFT_PTR))
        self.disconnect(self.cursor_handler_id)
        

    def drag_data_get(self, widget, context, selection, targetType, eventTime):
        selection.set(selection.target, 8, self.infohash)

    def drag_begin(self, *args):
        pass

    def drag_end(self, *args):
        self.main.drag_end()

    def make_done_label(self, statistics=None):
        s = ''
        if statistics and statistics['timeEst'] is not None:
            s = ', will seed for %s' % Duration(statistics['timeEst'])
        elif statistics:
            s = ', will seed indefinitely.'

        if self.up_down_ratio is not None:
            done_label = 'Done, share ratio: %d%%' % \
                         (self.up_down_ratio*100) + s
        elif statistics is not None:
            done_label = 'Done, %s uploaded' % \
                         Size(statistics['upTotal']) + s
        else:
            done_label = 'Done'

        return done_label
        

    def set_name(self):
        max_title_width = 560
        self.label.set_text(self.metainfo.name)
        if self.label.size_request()[0] > max_title_width:
            self.label.set_size_request(max_title_width, -1)

    def make_menu(self):
        filelistfunc = None
        if self.is_batch:
            filelistfunc = self.open_filelist

        menu_items = [("Torrent _info", self.open_info),]

        if OpenPath.can_open_files:
            func = None
            if self.can_open_dir():
                func = self.open_dir
            menu_items += [('_Open directory', func), ]

        menu_items += [('----', None),
                       ("_File list"  , filelistfunc),]

        self.menu = build_menu(menu_items+self.menu_items)
                
        self.menu_handler = self.connect_object("event", self.show_menu, self.menu)
        

    def open_info(self, widget=None):
        if self.infowindow is None:
            self.infowindow = TorrentInfoWindow(self, self.infoclosed)
    
    def infoclosed(self, widget=None):
        self.infowindow = None

    def close_info(self):
        if self.infowindow is not None:
            self.infowindow.close()

    def open_filelist(self, widget):
        if not self.is_batch:
            return
        if self.filelistwindow is None:
            self.filelistwindow = FileListWindow(self.metainfo,
                                                 self.filelistclosed)
            self.main.torrentqueue.check_completion(self.infohash, True)

    def filelistclosed(self, widget):
        self.filelistwindow = None

    def close_filelist(self):
        if self.filelistwindow is not None:
            self.filelistwindow.close()

    def close_child_windows(self):
        self.close_info()
        self.close_filelist()

    def destroy(self):
        if self.menu is not None:
            self.menu.destroy()
        self.menu = None
        gtk.EventBox.destroy(self)

    def show_menu(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            widget.popup(None, None, None, event.button, event.time)
            return gtk.TRUE
        return gtk.FALSE

    def _short_path(self, dlpath):
        path_length = 40
        sep = '...'
        ret = os.path.split(dlpath)[0]
        if len(ret) > path_length+len(sep):
            return ret[:int(path_length/2)]+sep+ret[-int(path_length/2):]
        else:
            return ret

    def get_path_to_open(self):
        path = self.dlpath
        if not self.is_batch:
            path = os.path.split(self.dlpath)[0]
        return path

    def can_open_dir(self):
        return os.access(self.get_path_to_open(), os.F_OK|os.R_OK)
        
    def open_dir(self, widget):
        OpenPath.opendir(self.get_path_to_open())


    def confirm_remove(self, widget):
        message = 'Are you sure you want to remove "%s"?' % self.metainfo.name
        if self.completion >= 1:
            if self.up_down_ratio is not None:
                message = 'Your share ratio for this torrent is %d%%. '%(self.up_down_ratio*100) + message
            else:
                message = 'You have uploaded %s to this torrent. '%(Size(self.uptotal)) + message
            
        d = MessageDialog(self.main.mainwindow,
                          'Remove this torrent?',
                          message, 
                          type=gtk.MESSAGE_QUESTION,
                          buttons=gtk.BUTTONS_OK_CANCEL,
                          yesfunc=self.remove,
                          )

    def remove(self):
        self.main.torrentqueue.remove_torrent(self.infohash)


class KnownTorrentBox(TorrentBox):

    def __init__(self, infohash, metainfo, dlpath, completion, main):
        TorrentBox.__init__(self, infohash, metainfo, dlpath, completion, main)

        status_tip = ''
        if completion >= 1:
            self.icon.set_from_stock('bt-finished', gtk.ICON_SIZE_LARGE_TOOLBAR)
            status_tip = 'Finished'
            known_torrent_dnd_tip = 'drag into list to seed'
        else:
            self.icon.set_from_stock('bt-broken', gtk.ICON_SIZE_LARGE_TOOLBAR)
            status_tip = 'Failed'
            known_torrent_dnd_tip = 'drag into list to resume'

        self.main.tooltips.set_tip(self.iconevbox,
                                   torrent_tip_format % (status_tip,
                                                         known_torrent_dnd_tip,
                                                         torrent_menu_tip))

        self.menu_items = [('----', None),
                           #('Move to _start', self.move_to_start),
                           ('Re_start'  , self.move_to_end  ),
                           ('_Remove' , self.confirm_remove),
                           ]


        self.make_menu()

        self.show_all()

    def move_to_end(self, widget):
        self.main.change_torrent_state(self.infohash, QUEUED)
        

class DroppableTorrentBox(TorrentBox):

    def __init__(self, infohash, metainfo, dlpath, completion, main):
        TorrentBox.__init__(self, infohash, metainfo, dlpath, completion, main)
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP,
                           [BT_TARGET,],
                           gtk.gdk.ACTION_MOVE)

        self.connect('drag_data_received', self.drag_data_received)
        self.connect('drag_motion', self.drag_motion)
        self.index = None

    def drag_data_received(self, widget, context, x, y, selection, targetType, time):
        half_height = self.size_request()[1] // 2
        where = cmp(y, half_height)
        if where == 0: where = 1
        self.parent.put_infohash_at_child(selection.data, self, where)

    def drag_motion(self, widget, context, x, y, time):
        self.get_current_index()
        half_height = self.size_request()[1] // 2
        if y < half_height: 
            self.parent.highlight_before_index(self.index)
        else:
            self.parent.highlight_after_index(self.index)
        return gtk.FALSE

    def drag_end(self, *args):
        self.parent.highlight_child()
        TorrentBox.drag_end(self, *args)

    def get_current_index(self):
        self.index = self.parent.get_index_from_child(self)


class QueuedTorrentBox(DroppableTorrentBox):

    icon_name = 'bt-queued'
    state_name = 'Waiting'

    def __init__(self, infohash, metainfo, dlpath, completion, main):
        DroppableTorrentBox.__init__(self, infohash, metainfo, dlpath, completion, main)

        self.main.tooltips.set_tip(self.iconevbox,
                                   torrent_tip_format % (self.state_name,
                                                         main_torrent_dnd_tip,
                                                         torrent_menu_tip))

        self.icon.set_from_stock(self.icon_name, gtk.ICON_SIZE_LARGE_TOOLBAR)
        self.menu_items = [#('----', None),
                           #("Change _location" , None),
                           #("Start hash check", None),
                           ("----"            , None),
                           ('Download _now', self.start),
                           ]


        if self.completion is not None and self.completion >= 1:
            self.menu_items += [('_Finish', self.finish),]
            self.menu_items += [('_Remove', self.confirm_remove),]
        else:
            self.menu_items += [('_Abort', self.confirm_remove),]
            
        self.make_menu()

        self.show_all()

    def start(self, widget):
        self.main.runbox.put_infohash_last(self.infohash)

    def finish(self, widget):
        self.main.change_torrent_state(self.infohash, KNOWN)


class PausedTorrentBox(DroppableTorrentBox):
    icon_name = 'bt-paused'
    state_name = 'Paused'

    def __init__(self, infohash, metainfo, dlpath, completion, main):
        DroppableTorrentBox.__init__(self, infohash, metainfo, dlpath, completion, main)

        self.main.tooltips.set_tip(self.iconevbox,
                                   torrent_tip_format % (self.state_name,
                                                         main_torrent_dnd_tip,
                                                         torrent_menu_tip))

        self.icon.set_from_stock(self.icon_name, gtk.ICON_SIZE_LARGE_TOOLBAR)

        
        menu_items = [("Download _later", self.move_to_end   ),
                      ("_Abort"        , self.confirm_remove),
                      ]

        if self.completion >= 1:
            menu_items = [("_Finish", self.finish),
                          ("_Remove", self.confirm_remove),
                          ]

        self.menu_items = [("----", None), ] + menu_items

        self.make_menu()

        self.show_all()

    def move_to_end(self, widget):
        self.main.change_torrent_state(self.infohash, QUEUED)

    def finish(self, widget):
        self.main.change_torrent_state(self.infohash, KNOWN)


class RunningTorrentBox(DroppableTorrentBox):

    def __init__(self, infohash, metainfo, dlpath, completion, main):
        DroppableTorrentBox.__init__(self, infohash, metainfo, dlpath, completion, main)

        self.main.tooltips.set_tip(self.iconevbox,
                                   torrent_tip_format % ('Running',
                                                         main_torrent_dnd_tip,
                                                         torrent_menu_tip))

        self.seed = False
        self.peerlistwindow = None

        self.icon.set_from_stock('bt-running', gtk.ICON_SIZE_LARGE_TOOLBAR)

        self.rate_label_box = gtk.HBox(homogeneous=True)

        self.up_rate   = gtk.Label()
        self.down_rate = gtk.Label()
        self.rate_label_box.pack_start(lalign(self.up_rate  ),
                                       expand=True, fill=True)
        self.rate_label_box.pack_start(lalign(self.down_rate),
                                       expand=True, fill=True)

        self.infobox.pack_start(self.rate_label_box)        

        if advanced_ui:
            self.extrabox = gtk.VBox(homogeneous=False)

            self.table = gtk.Table(2, 7, False)
            self.labels = []
            lnames = ('peers','seeds','distr','up curr.','down curr.','up prev.','down prev.')
            
            for i, name in enumerate(lnames):
                label = gtk.Label(name)
                self.table.attach(label, i, i+1, 0, 1, xpadding = SPACING)
                label = gtk.Label('-')
                self.labels.append(label)
                self.table.attach(label, i, i+1, 1, 2, xpadding = SPACING)
            self.extrabox.pack_start(self.table)

            # extra info
            self.elabels = []
            for i in range(4):
                label = gtk.Label('-')
                self.extrabox.pack_start(lalign(label))
                self.elabels.append(label)

            pl = self.metainfo.piece_length
            tl = self.metainfo.total_bytes
            count, lastlen = divmod(tl, pl)
            self.piece_count = count + (lastlen > 0)

            self.elabels[0].set_text("Share ratio: -")

            self.infobox.pack_end(self.extrabox, expand=False, fill=False)


        self.make_menu()
        self.show_all()


    def change_to_completed(self):
        self.completion = 1.0
        self.cancelimage.set_from_stock('bt-remove', gtk.ICON_SIZE_BUTTON)
        self.main.tooltips.set_tip(self.cancelbutton,
                                   'Remove torrent')
        self.make_menu()

    def make_menu(self):
        menu_items = [("Download _later", self.move_to_end),
                      ("_Abort"  , self.confirm_remove),
                      ]

        if self.completion >= 1:
            menu_items = [("_Finish", self.finish),
                          ("_Remove", self.confirm_remove),
                          ]

        self.menu_items = [("_Peer list"  , self.open_peerlist),
                           ('----'        , None),
                           ] + menu_items

        if self.menu_handler:
            self.disconnect(self.menu_handler)
            
        TorrentBox.make_menu(self)

    def move_to_end(self, widget):
        self.main.change_torrent_state(self.infohash, QUEUED)

    def finish(self, widget):
        self.main.change_torrent_state(self.infohash, KNOWN)

    def close_child_windows(self):
        TorrentBox.close_child_windows(self)
        self.close_peerlist()

    def open_filelist(self, widget):
        if not self.is_batch:
            return
        if self.filelistwindow is None:
            self.filelistwindow = FileListWindow(self.metainfo,
                                                 self.filelistclosed)
            self.main.make_statusrequest()

    def open_peerlist(self, widget):
        if self.peerlistwindow is None:
            self.peerlistwindow = PeerListWindow(self.metainfo.name,
                                                 self.peerlistclosed)
            self.main.make_statusrequest()

    def peerlistclosed(self, widget):
        self.peerlistwindow = None

    def close_peerlist(self):
        if self.peerlistwindow is not None:
            self.peerlistwindow.close()

    def update_status(self, statistics):
        fractionDone = statistics.get('fractionDone')
        activity = statistics.get('activity')

        self.main.set_title(torrentName=self.metainfo.name,
                            fractionDone=fractionDone)

        dt = self.downtotal
        if statistics.has_key('downTotal'):
            dt += statistics['downTotal']

        ut = self.uptotal
        if statistics.has_key('upTotal'):
            ut += statistics['upTotal']

        if dt > 0:
            self.up_down_ratio = ut / dt
        
        eta_label = '?'
        done_label = 'Done' 
        if 'numPeers' in statistics:
            eta = statistics.get('timeEst')
            if eta is not None:
                eta_label = Duration(eta)
            if fractionDone == 1:
                done_label = self.make_done_label(statistics)

        if fractionDone == 1:
            self.progressbar.set_fraction(1)
            self.progressbar.set_text(done_label)
            if not self.completion >= 1:
                self.change_to_completed()
        else:
            self.progressbar.set_fraction(fractionDone)
            progress_bar_label = '%.1f%% done, %s remaining' % \
                                 (int(fractionDone*1000)/10, eta_label) 
            self.progressbar.set_text(progress_bar_label)
            

        if 'numPeers' not in statistics:
            return

        self.down_rate.set_text('Download'+rate_label %
                                Rate(statistics['downRate']))
        self.up_rate.set_text  ('Upload'  +rate_label %
                                Rate(statistics['upRate']))

        if advanced_ui:
            self.labels[0].set_text(str(statistics['numPeers']))
            if self.seed:
                statistics['numOldSeeds'] = 0 # !@# XXX
                self.labels[1].set_text('(%d)' % statistics['numOldSeeds'])
            else:
                self.labels[1].set_text(str(statistics['numSeeds']))
            self.labels[2].set_text(str(statistics['numCopies']))
            self.labels[3].set_text(str(Size(statistics['upTotal'])))
            self.labels[4].set_text(str(Size(statistics['downTotal'])))
            self.labels[5].set_text(str(Size(self.uptotal)))
            self.labels[6].set_text(str(Size(self.downtotal)))

        if advanced_ui:
            # refresh extra info
            if self.up_down_ratio is not None:
                self.elabels[0].set_text('Share ratio: %.2f%%' % (self.up_down_ratio*100))
            self.elabels[1].set_text('Pieces: %d total, %d complete, %d partial, %d active (%d empty)'
                                     % (self.piece_count                 ,
                                        statistics['storage_numcomplete'],
                                        statistics['storage_dirty'],
                                        statistics['storage_active'],
                                        statistics['storage_new']))
            self.elabels[2].set_text('Next distributed copies: ' + ', '.join(["%d:%.1f%%" % (a, int(b*1000)/10) for a, b in zip(itertools.count(int(statistics['numCopies']+1)), statistics['numCopyList'])]))
            self.elabels[3].set_text('%d bad pieces + %s in discarded requests' % (statistics['storage_numflunked'], Size(statistics['discarded'])))

        if self.peerlistwindow is not None:
            spew = statistics.get('spew')
            if spew is not None:
                self.peerlistwindow.update(spew, statistics['bad_peers'])
        if self.filelistwindow is not None:
            if 'files_left' in statistics:
                self.filelistwindow.update(statistics['files_left'],
                                           statistics['files_allocated'])


class DroppableHSeparator(PaddedHSeparator):

    def __init__(self, main, spacing=SPACING):
        PaddedHSeparator.__init__(self, spacing)
        self.main = main
        self.drag_dest_set(#gtk.DEST_DEFAULT_MOTION| # uncommenting this breaks downward scrolling
            gtk.DEST_DEFAULT_DROP,
            [BT_TARGET],
            gtk.gdk.ACTION_MOVE )

        self.connect('drag_data_received', self.drag_data_received)
        self.connect('drag_motion'       , self.drag_motion       )

    def drag_highlight(self):
        self.sep.drag_highlight()
        self.main.main.add_unhighlight_handle()

    def drag_unhighlight(self):
        self.sep.drag_unhighlight()

    def drag_data_received(self, widget, context, x, y, selection, targetType, time):
        self.main.drop_on_separator(self, selection.data)

    def drag_motion(self, *args):
        self.drag_highlight()
        return gtk.FALSE


class DroppableBox(HSeparatedBox):
    def __init__(self, main, spacing=0):
        HSeparatedBox.__init__(self, spacing=spacing)
        self.main = main
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP,
                           [BT_TARGET],
                           gtk.gdk.ACTION_MOVE)
        self.connect('drag_data_received', self.drag_data_received)
        self.connect('drag_motion', self.drag_motion)

    def drag_motion(self, *args):
        return gtk.FALSE

    def drag_data_received(self, *args):
        pass


class KnownBox(DroppableBox):

    def __init__(self, main, spacing=0):
        DroppableBox.__init__(self, main, spacing=spacing)
        self.drag_dest_set(gtk.DEST_DEFAULT_MOTION |
                           gtk.DEST_DEFAULT_DROP,
                           [BT_TARGET],
                           gtk.gdk.ACTION_MOVE)

    def pack_start(self, widget, *args, **kwargs):
        old_len = len(self.get_children())
        DroppableBox.pack_start(self, widget, *args, **kwargs)
        if old_len <= 0:
            self.main.maximize_known_pane()
        self.main.knownscroll.scroll_to_bottom()

    def remove(self, widget, *args, **kwargs):
        DroppableBox.remove(self, widget, *args, **kwargs)
        new_len = len(self.get_children())
        if new_len == 0:
            self.main.maximize_known_pane()

    def drag_data_received(self, widget, context, x, y, selection, targetType, time):
        infohash = selection.data
        self.main.finish(infohash)

    def drag_motion(self, *args):
        self.main.drag_highlight(widget=self)
    
    def drag_highlight(self):
        self.main.knownscroll.drag_highlight()
        self.main.add_unhighlight_handle()

    def drag_unhighlight(self):
        self.main.knownscroll.drag_unhighlight()


class RunningAndQueueBox(gtk.VBox):

    def __init__(self, main, **kwargs):
        gtk.VBox.__init__(self, **kwargs)
        self.main = main

    def drop_on_separator(self, sep, infohash):
        self.main.change_torrent_state(infohash, QUEUED, 0)

    def highlight_between(self):
        self.drag_highlight()

    def drag_highlight(self):
        self.get_children()[1].drag_highlight()

    def drag_unhighlight(self):
        self.get_children()[1].drag_unhighlight()
        

class SpacerBox(DroppableBox):
    
    def drag_data_received(self, widget, context, x, y, selection, targetType, time):
        infohash = selection.data
        self.main.queuebox.put_infohash_last(infohash)

BEFORE = -1
AFTER  =  1

class ReorderableBox(DroppableBox):

    def new_separator(self):
        return DroppableHSeparator(self)

    def __init__(self, main):
        DroppableBox.__init__(self, main)
        self.main = main
        self.drag_dest_set(#gtk.DEST_DEFAULT_MOTION | # connecting this breaks downward scrolling
                           gtk.DEST_DEFAULT_DROP |
                           0,
                           [BT_TARGET],
                           gtk.gdk.ACTION_MOVE)

        self.connect('drag_data_received', self.drag_data_received)
        self.connect('drag_motion'       , self.drag_motion)


    def drag_data_received(self, widget, context, x, y, selection, targetType, time):
        if targetType == BT_TARGET_TYPE:
            half_height = self.size_request()[1] // 2
            if y < half_height:
                self.put_infohash_first(selection.data)
            else:
                self.put_infohash_last(selection.data)
            return gtk.TRUE
        else:
            print 'got external type'
            return gtk.FALSE

    def drag_motion(self, *args):
        return gtk.FALSE

    def drag_highlight(self):
        final = self.get_children()[-1]
        final.drag_highlight()
        self.main.add_unhighlight_handle()

    def drag_unhighlight(self): 
        self.highlight_child(index=None)
        self.parent.drag_unhighlight()

    def highlight_before_index(self, index):
        self.drag_unhighlight()
        children = self._get_children()
        if index > 0:
            children[index*2 - 1].drag_highlight()
        else:
            self.highlight_at_top()

    def highlight_after_index(self, index):
        self.drag_unhighlight()
        children = self._get_children()
        if index*2 < len(children)-1:
            children[index*2 + 1].drag_highlight()
        else:
            self.highlight_at_bottom()

    def highlight_child(self, index=None):
        for i, child in enumerate(self._get_children()):
            if index is not None and i == index*2:
                child.drag_highlight()
            else:
                child.drag_unhighlight()


    def drop_on_separator(self, sep, infohash):
        children = self._get_children()
        for i, child in enumerate(children):
            if child == sep:
                reference_child = children[i-1]
                self.put_infohash_at_child(infohash, reference_child, AFTER)
                break


    def get_queue(self):
        queue = []
        c = self.get_children()
        for t in c:
            queue.append(t.infohash)
        return queue

    def put_infohash_first(self, infohash):
        self.highlight_child()
        children = self.get_children()
        if len(children) > 1 and infohash == children[0].infohash:
            return
        
        self.put_infohash_at_index(infohash, 0)

    def put_infohash_last(self, infohash):
        self.highlight_child()
        children = self.get_children()
        end = len(children)
        if len(children) > 1 and infohash == children[end-1].infohash:
            return

        self.put_infohash_at_index(infohash, end)

    def put_infohash_at_child(self, infohash, reference_child, where):
        self.highlight_child()
        if infohash == reference_child.infohash:
            return
        
        target_index = self.get_index_from_child(reference_child)
        if where == AFTER:
            target_index += 1
        self.put_infohash_at_index(infohash, target_index)

    def get_index_from_child(self, child):
        c = self.get_children()
        ret = -1
        try:
            ret = c.index(child)
        except ValueError:
            pass
        return ret


class RunningBox(ReorderableBox):

    def put_infohash_at_index(self, infohash, target_index):
        #print 'RunningBox.put_infohash_at_index', infohash.encode('hex')[:8], target_index

        l = self.get_queue()
        replaced = None
        if l:
            replaced = l[-1]
        self.main.confirm_replace_running_torrent(infohash, replaced,
                                                  target_index)

    def highlight_at_top(self):
        pass
        # BUG: Don't know how I will indicate in the UI that the top of the list is highlighted

    def highlight_at_bottom(self):
        self.parent.highlight_between()


class QueuedBox(ReorderableBox):

    def put_infohash_at_index(self, infohash, target_index):
        #print 'want to put', infohash.encode('hex'), 'at', target_index
        self.main.change_torrent_state(infohash, QUEUED, target_index)

    def highlight_at_top(self):
        self.parent.highlight_between()

    def highlight_at_bottom(self):
        pass
        # BUG: Don't know how I will indicate in the UI that the bottom of the list is highlighted



class Struct(object):
    pass


class DownloadInfoFrame(object):

    def __init__(self, config, torrentqueue):
        self.config = config
        if self.config['save_in'] == '':
           self.config['save_in'] = smart_dir('')
        
        self.torrentqueue = torrentqueue
        self.torrents = {}
        self.running_torrents = {}
        self.lists = {}
        self.update_handle = None
        self.unhighlight_handle = None
        gtk.threads_enter()
        self.mainwindow = Window(gtk.WINDOW_TOPLEVEL)
        self.mainwindow.set_border_width(0)

        self.mainwindow.drag_dest_set(gtk.DEST_DEFAULT_ALL,
                                      [EXTERNAL_TARGET,],
                                      gtk.gdk.ACTION_MOVE)

        self.mainwindow.connect('drag_leave'        , self.drag_leave         )
        self.mainwindow.connect('drag_data_received', self.accept_dropped_file)

        if not advanced_ui:
            self.mainwindow.set_resizable(False)

        self.mainwindow.connect('destroy', self.cancel)

        self.accel_group = gtk.AccelGroup()

        self.mainwindow.add_accel_group(self.accel_group)

        #self.accel_group.connect(ord('W'), gtk.gdk.CONTROL_MASK, gtk.ACCEL_LOCKED,
        #                         lambda *args: self.mainwindow.destroy())

        self.tooltips = gtk.Tooltips()

        self.logbuffer = LogBuffer()
        self.log_text('%s started'%app_name, severity=None)

        self.box1 = gtk.VBox(homogeneous=False, spacing=0)

        self.box2 = gtk.VBox(homogeneous=False, spacing=0)
        self.box2.set_border_width(SPACING)

        self.menubar = gtk.MenuBar()
        self.box1.pack_start(self.menubar, expand=False, fill=False)

        self.ssbutton = StopStartButton(self)

        file_menu_items = (('_Open torrent file', self.select_torrent_to_open),

                           ('----'          , None),
                           ('_Pause/Play '  , self.ssbutton.toggle),
                           ('----'          , None),
                           ('_Quit'         , lambda w: self.mainwindow.destroy()),
                           )
        view_menu_items = (('Show/Hide _finished torrents', self.toggle_known),
                           #('_Clean up finished torrents' , self.confirm_remove_finished_torrents),
                           ('----'          , None),
                           ('_Log'          , lambda w: self.open_window('log')),
                           # 'View log of all download activity',
                           #('----'          , None),
                           ('_Settings'     , lambda w: self.open_window('settings')),
                           #'Change download behavior and network settings',
                           )
        help_menu_items = (('_Help'         , self.open_help),
                           #('_Help Window'         , lambda w: self.open_window('help')),
                           ('_About'        , lambda w: self.open_window('about')),
                           ('_Donate'       , lambda w: self.donate()),
                           #('_Raise'        , lambda w: self.raiseerror()), 
                           )
        
        self.filemenu = gtk.MenuItem("_File")
        self.filemenu.set_submenu(build_menu(file_menu_items, self.accel_group))
        self.filemenu.show()

        self.viewmenu = gtk.MenuItem("_View")
        self.viewmenu.set_submenu(build_menu(view_menu_items, self.accel_group))
        self.viewmenu.show()

        self.helpmenu = gtk.MenuItem("_Help")
        self.helpmenu.set_submenu(build_menu(help_menu_items, self.accel_group))
        self.helpmenu.show()

        self.helpmenu.set_right_justified(gtk.TRUE)

        self.menubar.append(self.filemenu)
        self.menubar.append(self.viewmenu)
        self.menubar.append(self.helpmenu)
        
        self.menubar.show()

        self.header = gtk.HBox(homogeneous=False)

        self.box1.pack_start(self.box2, expand=False, fill=False)
        
        self.rate_slider_box = RateSliderBox(self.config, self.torrentqueue)

        self.ssb = gtk.VBox()
        self.ssb.pack_end(self.ssbutton, expand=False, fill=True)

        self.controlbox = gtk.HBox(homogeneous=False)
         
        self.controlbox.pack_start(self.ssb, expand=False, fill=False)
        self.controlbox.pack_start(self.rate_slider_box,
                                   expand=True, fill=True,
                                   padding=SPACING//2)
        self.controlbox.pack_start(get_logo(32), expand=False, fill=False,
                                   padding=SPACING)

        self.box2.pack_start(self.controlbox, expand=False, fill=False, padding=0)

        self.paned = gtk.VPaned()

        self.knownscroll = ScrolledWindow()
        self.knownscroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self.knownscroll.set_shadow_type(gtk.SHADOW_NONE)
        self.knownscroll.set_size_request(-1, SPACING)

        self.knownbox = KnownBox(self)
        self.knownbox.set_border_width(SPACING)

        self.knownscroll.add_with_viewport(self.knownbox)
        self.paned.pack1(self.knownscroll, resize=gtk.FALSE, shrink=gtk.TRUE)

        
        self.mainscroll = AutoScrollingWindow()
        self.mainscroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self.mainscroll.set_shadow_type(gtk.SHADOW_NONE)
        self.mainscroll.set_size_request(-1, SPACING)

        self.scrollbox = RunningAndQueueBox(self, homogeneous=False)
        self.scrollbox.set_border_width(SPACING)
        
        self.runbox = RunningBox(self)
        self.scrollbox.pack_start(self.runbox, expand=False, fill=False)

        self.scrollbox.pack_start(DroppableHSeparator(self.scrollbox), expand=False, fill=False)

        self.queuebox = QueuedBox(self)
        self.scrollbox.pack_start(self.queuebox, expand=False, fill=False)

        self.scrollbox.pack_start(SpacerBox(self), expand=True, fill=True) 

        self.mainscroll.add_with_viewport(self.scrollbox)

        self.paned.pack2(self.mainscroll, resize=gtk.TRUE, shrink=gtk.FALSE)

        self.box1.pack_start(self.paned)

        self.box1.show_all()

        self.mainwindow.add(self.box1)
        self.child_windows = {}
        self.postponed_save_windows = []

        self.helpwindow     = None
        self.errordialog    = None

        self.set_title()
        self.set_size()
        self.mainwindow.show()
        self.paned.set_position(0)
        gtk.threads_leave()


    def main(self):
        gtk.threads_enter()

        self.ssbutton.set_paused(self.config['pause'])
        self.rate_slider_box.start()
        
        self.init_updates()

        #self.log_text( 'app settings in "%s"' % config['data_dir'], INFO)
        #self.log_text( 'will download to "%s"' % config['save_in' ], INFO)

        try:
            gtk.main() 
        except KeyboardInterrupt:
            gtk.threads_leave()
            self.torrentqueue.set_done()
            raise
        gtk.threads_leave()


    def drag_leave(self, *args):
        self.drag_end()


    def accept_dropped_file(self, widget, drag_context, x, y, selection,
                            target_type, time):
        file_uris = selection.data.split('\r\n')
        for file_uri in file_uris:
            file_name = url2pathname(file_uri)
            file_name = file_name[7:]
            if os.name == 'nt':
                file_name = file_name.strip('\\')
            self.open_torrent( file_name )

    def drag_highlight(self, widget=None):
        widgets = (self.knownbox, self.runbox, self.queuebox) 
        for w in widgets:
            if w != widget:
                w.drag_unhighlight()
        for w in widgets:
            if w == widget:
                w.drag_highlight()
                self.add_unhighlight_handle()

    def drag_end(self):
        self.drag_highlight(widget=None)
        self.mainscroll.stop_scrolling()

    def set_title(self, torrentName=None, fractionDone=None):
        title = app_name
        trunc = '...'
        sep = ': '

        if self.config['pause']:
            title += sep+'(stopped)'
        elif len(self.running_torrents) == 1 and torrentName and \
               fractionDone is not None:
            maxlen = WINDOW_TITLE_LENGTH - len(app_name) - len(trunc) - len(sep)
            if len(torrentName) > maxlen:
                torrentName = torrentName[:maxlen] + trunc
            title = '%s%s%0.1f%%%s%s'% (app_name,
                                            sep,
                                            (int(fractionDone*1000)/10),
                                            sep,
                                            torrentName)
        elif len(self.running_torrents) > 1:
            title += sep+'(multiple)'

        self.mainwindow.set_title(title)

    def set_size(self):
        paned_height = self.scrollbox.size_request()[1]
        if hasattr(self.paned, 'style_get_property'):
            paned_height += self.paned.style_get_property('handle-size')
        else:
            paned_height += 5
        paned_height += self.paned.get_position()
        paned_height += 4 # fudge factor, probably from scrolled window beveling ?
        paned_height = max(paned_height, MIN_MULTI_PANE_HEIGHT)

        new_height = self.menubar.size_request()[1] + \
                     self.box2.size_request()[1] + \
                     paned_height
        new_height = min(new_height, MAX_WINDOW_HEIGHT)
        self.mainwindow.set_size_request(WINDOW_WIDTH, new_height)

    # BUG need to add handler on resize event to keep track of
    # old_position when pane is hidden manually
    def split_pane(self):
        pos = self.paned.get_position()
        if pos > 0:
            self.paned.old_position = pos
            self.paned.set_position(0)
        else:
            if hasattr(self.paned, 'old_position'):
                self.paned.set_position(self.paned.old_position)
            else:
                self.maximize_known_pane()

    def maximize_known_pane(self):
        self.set_pane_position(self.knownbox.size_request()[1])        

    def set_pane_position(self, pane_position):
            pane_position = min(MAX_WINDOW_HEIGHT//2, pane_position)
            self.paned.set_position(pane_position)

    def toggle_known(self, widget=None):
        self.split_pane()

    def open_window(self, window_name, *args, **kwargs):
        if os.name == 'nt':
            self.mainwindow.present()
        savewidget = SaveFileSelection
        if window_name == 'savedir':
            savewidget = CreateFolderSelection
            window_name = 'savefile'
        if self.child_windows.has_key(window_name):
            if window_name == 'savefile':
                kwargs['show'] = False
                self.postponed_save_windows.append(savewidget(self, **kwargs))
            return

        if window_name == 'log'       :
            self.child_windows[window_name] = LogWindow(self, self.logbuffer, self.config)
        elif window_name == 'about'   :
            self.child_windows[window_name] = AboutWindow(self, lambda w: self.donate())
        elif window_name == 'help'    :
            self.child_windows[window_name] = HelpWindow(self, makeHelp('btdownloadgui', defaults))
        elif window_name == 'settings':
            self.child_windows[window_name] = SettingsWindow(self, self.config, self.set_config)
        elif window_name == 'version' :
            self.child_windows[window_name] = VersionWindow(self, *args)
        elif window_name == 'openfile':
            self.child_windows[window_name] = OpenFileSelection(self, **kwargs)
        elif window_name == 'savefile':
            self.child_windows[window_name] = savewidget(self, **kwargs)
        elif window_name == 'choosefolder':
            self.child_windows[window_name] = ChooseFolderSelection(self, **kwargs)            

        return self.child_windows[window_name]

    def window_closed(self, window_name):
        if self.child_windows.has_key(window_name):
            del self.child_windows[window_name]
        if window_name == 'savefile' and self.postponed_save_windows:
            newwin = self.postponed_save_windows.pop(-1)
            newwin.show()
            self.child_windows['savefile'] = newwin
    
    def close_window(self, window_name):
        self.child_windows[window_name].close(None)

    def new_version(self, newversion, download_url):
        if newversion != self.config['notified']:
            self.open_window('version', newversion, download_url)


    def open_help(self,widget):
        if self.helpwindow is None:
            msg = 'BitTorrent help is at \n'\
                  '%s\n'\
                  'Would you like to go there now?'%HELP_URL
            self.helpwindow = MessageDialog(self.mainwindow,
                                            'Visit help web page?',
                                            msg,
                                            type=gtk.MESSAGE_QUESTION,
                                            buttons=gtk.BUTTONS_OK_CANCEL,
                                            yesfunc=self.visit_help,
                                            nofunc =self.help_closed,
                                            )

    def visit_help(self):
        self.visit_url(HELP_URL)
        self.help_closed()
        
    def close_help(self):
        self.helpwindow.close()

    def help_closed(self, widget=None):
        self.helpwindow = None


    def set_config(self, option, value):
        self.config[option] = value
        if option == 'display_interval':
            self.init_updates()
        self.torrentqueue.set_config(option, value)


    def confirm_remove_finished_torrents(self,widget):
        count = 0
        for infohash, t in self.torrents.iteritems():
            if t.state == KNOWN and t.completion >= 1:
                count += 1
        if count:
            if self.paned.get_position() == 0:
                self.toggle_known()
            msg = ''
            if count == 1:
                msg = 'There is one finished torrent in the list. ' +\
                      'Do you want to remove it?'
            else:
                msg = 'There are %d finished torrents in the list. '%count +\
                      'Do you want to remove all of them?'
            MessageDialog(self.mainwindow,
                          'Remove all finished torrents?',
                          msg,
                          type=gtk.MESSAGE_QUESTION,
                          buttons=gtk.BUTTONS_OK_CANCEL,
                          yesfunc=self.remove_finished_torrents)
        else:
            MessageDialog(self.mainwindow,
                          'No finished torrents',
                          'There are no finished torrents to remove.',
                          type=gtk.MESSAGE_INFO)
        

    def remove_finished_torrents(self):
        for infohash, t in self.torrents.iteritems():
            if t.state == KNOWN and t.completion >= 1:
                self.torrentqueue.remove_torrent(infohash)
        if self.paned.get_position() > 0:
            self.toggle_known()


    def cancel(self, widget):
        for window_name in self.child_windows.keys():
            self.close_window(window_name)
        
        if self.errordialog is not None:
            self.errordialog.destroy()
            self.errors_closed()

        for t in self.torrents.itervalues():
            if t.widget is not None:
                t.widget.close_child_windows()

        self.torrentqueue.set_done()
        gtk.main_quit()


    def make_statusrequest(self):
        if self.config['pause']:
            return True
        for infohash, t in self.running_torrents.iteritems():
            self.torrentqueue.request_status(infohash, t.widget.peerlistwindow
                             is not None, t.widget.filelistwindow is not None)
        return True


    def select_torrent_to_open(self, widget):
        path = smart_dir(self.config['save_in'])
        self.open_window('openfile',
                         title="Open torrent:",
                         fullname=path,
                         got_location_func=self.open_torrent,
                         no_location_func=lambda: self.window_closed('openfile'))


    def open_torrent(self, name):
        self.window_closed('openfile')
        f = None
        try:
            f = file(name, 'rb')
            data = f.read()
        except IOError: 
            pass # the user has selected a directory or other non-file object
        else:
            self.torrentqueue.start_new_torrent(data)
        if f is not None:
            f.close()  # shouldn't fail with read-only file (well hopefully)


    def save_location(self, infohash, metainfo):
        name = metainfo.name_fs

        if self.config['save_as']:
            path = self.config['save_as']
            self.got_location(infohash, path)
            self.config['save_as'] = ''
            return

        path = smart_dir(self.config['save_in'])

        fullname = os.path.join(path, name)

        if not self.config['ask_for_save']:
            if os.access(fullname, os.F_OK):
                message = MessageDialog(self.mainwindow, 'File exists!',
                                        '"%s" already exists.'\
                                        ' Do you want to choose a different file name?.'%name,
                                        buttons=gtk.BUTTONS_YES_NO,
                                        nofunc= lambda : self.got_location(infohash, fullname),
                                        yesfunc=lambda : self.get_save_location(infohash, metainfo, fullname),)

            else:
                self.got_location(infohash, fullname)
        else:
            self.get_save_location(infohash, metainfo, fullname)

    def get_save_location(self, infohash, metainfo, fullname):
        def no_location():
            self.window_closed('savefile')
            self.torrentqueue.remove_torrent(infohash)

        selector = self.open_window(metainfo.is_batch and 'savedir' or \
                                                          'savefile',
                                    title="Save location for " + metainfo.name,
                                    fullname=fullname,
                                    got_location_func = lambda fn: \
                                              self.got_location(infohash, fn),
                                    no_location_func=no_location)

        self.torrents[infohash].widget = selector

    def got_location(self, infohash, fullpath):
        self.window_closed('savefile')
        self.torrents[infohash].widget = None
        save_in = os.path.split(fullpath)[0]
        if save_in[-1] != os.sep:
            save_in += os.sep
        self.set_config('save_in', save_in)        
        self.torrents[infohash].dlpath = fullpath
        self.torrentqueue.set_save_location(infohash, fullpath)

    def add_unhighlight_handle(self):
        if self.unhighlight_handle is not None:
            gobject.source_remove(self.unhighlight_handle)
            
        self.unhighlight_handle = gobject.timeout_add(2000,
                                                      self.unhighlight_after_a_while,
                                                      priority=gobject.PRIORITY_LOW)

    def unhighlight_after_a_while(self):
        self.drag_highlight()
        gobject.source_remove(self.unhighlight_handle)
        self.unhighlight_handle = None
        return gtk.FALSE

    def init_updates(self):
        if self.update_handle is not None:
            gobject.source_remove(self.update_handle)
        self.update_handle = gobject.timeout_add(
            int(self.config['display_interval'] * 1000),
            self.make_statusrequest)

    def remove_torrent_widget(self, infohash):
        t = self.torrents[infohash]
        self.lists[t.state].remove(infohash)
        if t.state == RUNNING:
            del self.running_torrents[infohash]
            self.set_title()
        if t.state == ASKING_LOCATION:
            if t.widget is not None:
                t.widget.destroy()
            return

        if t.state in (KNOWN, RUNNING, QUEUED):
            t.widget.close_child_windows()

        if t.state == RUNNING:
            self.runbox.remove(t.widget)
        elif t.state == QUEUED:
            self.queuebox.remove(t.widget)
        elif t.state == KNOWN:
            self.knownbox.remove(t.widget)
            
        t.widget.destroy()

        self.set_size()

    def create_torrent_widget(self, infohash, queuepos=None):
        t = self.torrents[infohash]
        l = self.lists.setdefault(t.state, [])
        if queuepos is None:
            l.append(infohash)
        else:
            l.insert(queuepos, infohash)
        if t.state == ASKING_LOCATION:
            self.save_location(infohash, t.metainfo)
            self.nag()
            return
        elif t.state == RUNNING:
            self.running_torrents[infohash] = t
            if not self.config['pause']:
                t.widget = RunningTorrentBox(infohash, t.metainfo, t.dlpath,
                                             t.completion, self)
            else:
                t.widget = PausedTorrentBox(infohash, t.metainfo, t.dlpath,
                                             t.completion, self)
            box = self.runbox
        elif t.state == QUEUED:
            t.widget = QueuedTorrentBox(infohash, t.metainfo, t.dlpath,
                                        t.completion, self)
            box = self.queuebox
        elif t.state == KNOWN:
            t.widget = KnownTorrentBox(infohash, t.metainfo, t.dlpath,
                                       t.completion, self)
            box = self.knownbox
        box.pack_start(t.widget, expand=gtk.FALSE, fill=gtk.FALSE)
        if queuepos is not None:
            box.reorder_child(t.widget, queuepos)

        self.set_size()

    def log_text(self, text, severity=ERROR):
        self.logbuffer.log_text(text, severity)

    def error(self, infohash, severity, text):
        name = self.torrents[infohash].metainfo.name
        err_str = '"%s" : %s'%(name,text)
        err_str = err_str.decode('utf-8', 'replace').encode('utf-8')
        if severity >= ERROR:
            self.error_modal(err_str)
        self.log_text(err_str, severity)

    def global_error(self, severity, text):
        err_str = '(global message) : %s'%text
        err_str = err_str.decode('utf-8', 'replace').encode('utf-8')
        if severity >= ERROR:
            self.error_modal(text)
        self.log_text(err_str, severity)

    def error_modal(self, text):
        title = '%s Error' % app_name
        
        if self.errordialog is not None:
            if not self.errordialog.multi:
                self.errordialog.destroy()
                self.errordialog = MessageDialog(self.mainwindow, title, 
                                                 'Multiple errors have occurred. '
                                                 'Click OK to view the error log.',
                                                 buttons=gtk.BUTTONS_OK_CANCEL,
                                                 yesfunc=self.multiple_errors_yes,
                                                 nofunc=self.errors_closed,
                                                 )
                self.errordialog.multi = True
            else:
                # already showing the multi error dialog, so do nothing
                pass
        else:
            self.errordialog = MessageDialog(self.mainwindow, title, text,
                                             yesfunc=self.errors_closed)
            self.errordialog.multi = False


    def multiple_errors_yes(self):
        self.errors_closed()
        self.open_window('log')

    def errors_closed(self):
        self.errordialog = None

    def stop_queue(self):
        self.set_config('pause', 1)
        self.set_title()
        q = list(self.runbox.get_queue())
        for infohash in q:
            t = self.torrents[infohash]
            self.remove_torrent_widget(infohash)
            self.create_torrent_widget(infohash)

    def restart_queue(self):
        self.set_config('pause', 0)
        q = list(self.runbox.get_queue())
        for infohash in q:
            t = self.torrents[infohash]
            self.remove_torrent_widget(infohash)
            self.create_torrent_widget(infohash)

    def update_status(self, torrent, statistics):
        if self.config['pause']:
            return
        self.running_torrents[torrent].widget.update_status(statistics)

    def new_displayed_torrent(self, infohash, metainfo, dlpath, state,
                              completion=None, uptotal=0, downtotal=0):
        t = Struct()
        t.metainfo = metainfo
        t.dlpath = dlpath
        t.state = state
        t.completion = completion
        t.uptotal = uptotal
        t.downtotal = downtotal
        self.torrents[infohash] = t
        self.create_torrent_widget(infohash)

    def torrent_state_changed(self, infohash, state, completion,
                              uptotal, downtotal, queuepos=None):
        t = self.torrents[infohash]
        self.remove_torrent_widget(infohash)
        t.state = state
        t.completion = completion
        t.uptotal = uptotal
        t.downtotal = downtotal
        self.create_torrent_widget(infohash, queuepos)

    def reorder_torrent(self, infohash, queuepos):
        self.remove_torrent_widget(infohash)
        self.create_torrent_widget(infohash, queuepos)

    def update_completion(self, infohash, completion, files_left=None,
                          files_allocated=None):
        t = self.torrents[infohash]
        if files_left is not None and t.widget.filelistwindow is not None:
            t.widget.filelistwindow.update(files_left, files_allocated)

    def removed_torrent(self, infohash):
        self.remove_torrent_widget(infohash)
        del self.torrents[infohash]

    def change_torrent_state(self, infohash, newstate, index=None,
                             replaced=None, force_running=False):
        t = self.torrents[infohash]
        pred = succ = None
        if index is not None:
            l = self.lists.setdefault(newstate, [])
            if index > 0:
                pred = l[index - 1]
            if index < len(l):
                succ = l[index]
        self.torrentqueue.change_torrent_state(infohash, t.state, newstate,
                                         pred, succ, replaced, force_running)

    def finish(self, infohash):
        t = self.torrents[infohash]
        if t is None or t.state == KNOWN:
            return
        self.change_torrent_state(infohash, KNOWN)

    def confirm_replace_running_torrent(self, infohash, replaced, index):
        replace_func = lambda *args: self.change_torrent_state(infohash,
                                RUNNING, index, replaced)
        add_func     = lambda *args: self.change_torrent_state(infohash,
                                RUNNING, index, force_running=True)
        moved_torrent = self.torrents[infohash]

        if moved_torrent.state == RUNNING:
            self.change_torrent_state(infohash, RUNNING, index)
            return

        if self.config['start_torrent_behavior'] == 'replace':
            replace_func()
            return
        elif self.config['start_torrent_behavior'] == 'add':
            add_func()
            return
        
        moved_torrent_name = moved_torrent.metainfo.name
        confirm = MessageDialog(self.mainwindow,
                                'Stop running torrent?',
                                'You are about to start "%s". Do you want to stop the last running torrent as well?'%(moved_torrent_name),
                                type=gtk.MESSAGE_QUESTION,
                                buttons=gtk.BUTTONS_YES_NO,
                                yesfunc=replace_func,
                                nofunc=add_func,
                                default=gtk.RESPONSE_YES)

    def nag(self):
        if ((self.config['donated'] != version) and
            (random.random() * NAG_FREQUENCY) < 1):
            title = 'Have you donated?'
            message = 'Welcome to the new version of %s. Have you donated?'%app_name
            self.nagwindow = MessageDialog(self.mainwindow,
                                           title,
                                           message,
                                           type=gtk.MESSAGE_QUESTION,
                                           buttons=gtk.BUTTONS_YES_NO,
                                           yesfunc=self.nag_yes, nofunc=self.nag_no,)
            
    def nag_no(self):
        self.donate()

    def nag_yes(self):
        self.set_config('donated', version)
        MessageDialog(self.mainwindow,
                      'Thanks!',
                      'Thanks for donating! To donate again, '
                      'select "Donate" from the "Help" menu.')

    def donate(self):
        self.visit_url(DONATE_URL)


    def visit_url(self, url):
        t = threading.Thread(target=webbrowser.open,
                             args=(url,))
        t.start()

    def raiseerror(self, *args):
        raise ValueError('test traceback behavior')

        

if __name__ == '__main__':

    try:
        config, args = configfile.parse_configuration_and_args(defaults,
                                        'btdownloadgui', sys.argv[1:], 0, None)
    except BTFailure, e:
        print str(e)
        sys.exit(1)

    advanced_ui = config['advanced']

    if config['responsefile']:
        if args:
            raise BTFailure("Can't have both --responsefile and non-option "
                            "arguments")
        newtorrents = [config['responsefile']]
    else:
        newtorrents = args
    controlsocket = ControlSocket(config)

    got_control_socket = True
    try:
        controlsocket.create_socket()
    except BTFailure:
        got_control_socket = False
        try:
            controlsocket.send_command('no-op')
        except BTFailure:
            # XXX: this should pop up an error message for the user
            raise

    datas = []
    errors = []
    if newtorrents:
        for filename in newtorrents:
            f = None
            try:
                f = file(filename, 'rb')
                data = f.read()
                f.close()
            except Exception, e:
                if f is not None:
                    f.close()
                if "Temporary Internet Files" in filename:
                    errors.append("Could not read %s: %s. You are probably "
                                  "using a broken Internet Explorer version "
                                  "that passed BitTorrent a filename that "
                                  "doesn't exist. To work around the problem, "
                                  "try clearing your Temporary Internet Files "
                                  "or right-click the link and save the "
                                  ".torrent file to disk first." %
                                  (filename, str(e)))
                else:
                    errors.append('Could not read %s: %s' % (filename, str(e)))
                
            else:
                datas.append(data)

        # Not sure if anything really useful could be done if
        # these send_command calls fail
        if not got_control_socket:
            for data in datas:
                controlsocket.send_command('start_torrent', data)
            for error in errors:
                controlsocket.send_command('show_error', error)
            sys.exit(0)
    elif not got_control_socket:
        controlsocket.send_command('show_error', '%s already running'%app_name)
        sys.exit(1)

    gtk.threads_init()

    torrentqueue = TorrentQueue.TorrentQueue(config, ui_options, controlsocket)
    d = DownloadInfoFrame(config,TorrentQueue.ThreadWrappedQueue(torrentqueue))

    def lock_wrap(function, *args):
        gtk.threads_enter()
        function(*args)
        gtk.gdk.flush()
        gtk.threads_leave()

    def gtk_wrap(function, *args):
        gtk.threads_enter()
        gobject.idle_add(lock_wrap, function, *args)
        gtk.threads_leave()
    startflag = threading.Event()
    dlthread = threading.Thread(target = torrentqueue.run,
                                args = (d, gtk_wrap, startflag))
    dlthread.setDaemon(False)
    dlthread.start()
    startflag.wait()
    for data in datas:
        d.torrentqueue.start_new_torrent(data)
    for error in errors:
        d.global_error(ERROR, error)

    try:
        d.main()
    except KeyboardInterrupt:
        # the gtk main loop is closed in DownloadInfoFrame
        sys.exit(1)
