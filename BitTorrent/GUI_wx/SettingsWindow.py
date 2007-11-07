# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# written by Greg Hazel, based on code by Matt Chisholm

from __future__ import division

import os
import sys
import math
import random
from BTL.translation import _
from BTL.platform import app_name
from BitTorrent.platform import image_root
from BTL.sparse_set import SparseSet
from BTL.obsoletepythonsupport import set
from BitTorrent.GUI_wx import VSizer, HSizer, BTDialog, CheckButton
from BitTorrent.GUI_wx import ChooseDirectorySizer, SPACING, ElectroStaticText
from BitTorrent.GUI_wx import IPValidator, PortValidator, text_wrappable, gui_wrap
from BitTorrent.GUI_wx import list_themes
from BitTorrent.GUI_wx.CustomWidgets import FancyDownloadGauge, SimpleDownloadGauge, ModerateDownloadGauge
from BitTorrent.UI import Rate
from BitTorrent.GUI_wx.LanguageSettings import LanguageSettings

import wx

upload_speed_classes = {
        (    4,    5):_("dialup"            ),
        (    6,   14):_("DSL/cable 128Kb up"),
        (   15,   29):_("DSL/cable 256Kb up"),
        (   30,   91):_("DSL 768Kb up"      ),
        (   92,  137):_("T1"                ),
        (  138,  182):_("T1/E1"             ),
        (  183,  249):_("E1"                ),
        (  250, 5446):_("T3"                ),
        ( 5447,18871):_("OC3"               ),
        (18872,125e6):_("fast"              ),
        }

download_speed_classes = {
        (    4,    5):_("dialup"              ),
        (    6,   46):_("DSL/cable 384Kb down"),
        (   47,   93):_("DSL/cable 768Kb down"),
        (   93,  182):_("DSL/T1"              ),
        (  182,  249):_("E1"                  ),
        (  250,  729):_("DSL 6Mb down"        ),
        (  730, 5442):_("T3"                  ),
        ( 5443,18858):_("OC3"                 ),
        (18859,125e6):_("fast"                ),
        }

class RateSlider(wx.Slider):
    base = 10
    multiplier = 4
    max_exponent = 4.49
    slider_scale = 1000 # slider goes from 0 to slider_scale * max_exponent
    backend_conversion = 1024 # slider deals in KB, backend in B

    def __init__(self, parent, value, speed_classes):
        self.speed_classes = speed_classes
        value = self.bytes_to_slider(value)
        wx.Slider.__init__(self, parent, wx.ID_ANY,
                           value=value, minValue=0,
                           maxValue=self.max_exponent * self.slider_scale)

    def bytes_to_slider(self, value):
        value /= self.backend_conversion
        try:
            r = math.log(value/self.multiplier, self.base)
        except OverflowError, e:
            wx.the_app.logger.error(u'%s (%s, %s, %s)' % (unicode(e.args[0]),
                                                          value,
                                                          self.multiplier,
                                                          self.base),
                                    exc_info=sys.exc_info())
        return r * self.slider_scale

    def slider_to_bytes(self, value):
        r = self.slider_to_kbytes(value)
        return r * self.backend_conversion

    def slider_to_kbytes(self, value):
        value /= self.slider_scale
        r = int(round(self.base**value * self.multiplier))
        return r

    def slider_to_label(self, value):
        value = self.slider_to_kbytes(value)
        conn_type = ''
        for key, conn in self.speed_classes.iteritems():
            min_v, max_v = key
            if min_v <= value <= max_v:
                conn_type = ' (%s)' % conn
                break
        label = unicode(Rate(value*self.backend_conversion)) + conn_type
        return label


class RateSliderBox(wx.StaticBox):

    def __init__(self, parent, label, key, settings_window, speed_classes):
        self.key = key
        self.settings_window = settings_window
        wx.StaticBox.__init__(self, parent, label=label)
        self.sizer = wx.StaticBoxSizer(self, wx.VERTICAL)

        self.text = ElectroStaticText(parent, wx.ID_ANY, 'text')

        self.setfunc = lambda v : self.settings_window.setfunc(key, v)
        self.slider = RateSlider(parent, self.settings_window.config[key], speed_classes)
        self.slider.Bind(wx.EVT_SLIDER, self.OnSlider)
        self.LoadValue()

        self.sizer.Add(self.text, proportion=1, flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT, border=SPACING)
        self.sizer.Add(self.slider, proportion=1, flag=wx.GROW|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=SPACING)

    def LoadValue(self):
        bytes = self.settings_window.config[self.key]
        if bytes <= 0:
            wx.the_app.logger.warning(_("Impractically low rate (%s), fixing") % bytes)
            self.settings_window.config[self.key] = 4 * 1024
            bytes = self.settings_window.config[self.key]
        self.slider.SetValue(self.slider.bytes_to_slider(bytes))
        self.text.SetLabel(self.slider.slider_to_label(self.slider.GetValue()))

    def OnSlider(self, event):
        value = event.GetInt()
        bytes = self.slider.slider_to_bytes(value)
        self.setfunc(bytes)
        label = self.slider.slider_to_label(value)
        self.text.SetLabel(label)

    def Enable(self, enable):
        self.text.Enable(enable)
        self.slider.Enable(enable)


class SettingsPanel(wx.Panel):
    """Base class for settings panels"""
    label = ''

    def __init__(self, parent, *a, **k):
        style = k.get('style', 0)
        k['style'] = style | wx.CLIP_CHILDREN | wx.TAB_TRAVERSAL
        # aarrg
        self.settings_window = parent.GetParent()

        wx.Panel.__init__(self, parent, *a, **k)
        parent.AddPage(self, self.label)

        self.sizer = VSizer()
        self.SetSizerAndFit(self.sizer)


class GeneralSettingsPanel(SettingsPanel):
    label = _("General")

    def __init__(self, parent, *a, **k):
        SettingsPanel.__init__(self, parent, *a, **k)

        # widgets
        self.confirm_checkbutton = CheckButton(
            self,
            _("Confirm before quitting %s")%app_name,
            self.settings_window,
            'confirm_quit',
            self.settings_window.config['confirm_quit'])

        # sizers
        self.sizer.AddFirst(self.confirm_checkbutton)

        if os.name == 'nt':
            # widgets
            self.enforce_checkbutton = CheckButton(
                self,
                _("Enforce .torrent associations on startup"),
                self.settings_window,
                'enforce_association',
                self.settings_window.config['enforce_association'])

            self.startup_checkbutton = CheckButton(
                self,
                _("Launch BitTorrent when Windows starts"),
                self.settings_window,
                'launch_on_startup',
                self.settings_window.config['launch_on_startup'])

            self.start_minimized_checkbutton = CheckButton(
                self,
                _("Start minimized"),
                self.settings_window,
                'start_minimized',
                self.settings_window.config['start_minimized'])

            self.minimize_checkbutton = CheckButton(
                self,
                _("Minimize to the system tray"),
                self.settings_window,
                'minimize_to_tray',
                self.settings_window.config['minimize_to_tray'])

            self.quit_checkbutton = CheckButton(
                self,
                _("Close to the system tray"),
                self.settings_window,
                'close_to_tray',
                self.settings_window.config['close_to_tray'])

            # sizers
            self.sizer.Add(wx.StaticLine(self, style=wx.LI_HORIZONTAL), flag=wx.GROW)
            self.sizer.Add(self.enforce_checkbutton)
            self.sizer.Add(wx.StaticLine(self, style=wx.LI_HORIZONTAL), flag=wx.GROW)
            self.sizer.Add(self.startup_checkbutton)
            self.sizer.Add(self.start_minimized_checkbutton)
            self.sizer.Add(wx.StaticLine(self, style=wx.LI_HORIZONTAL), flag=wx.GROW)
            self.sizer.Add(self.minimize_checkbutton)
            self.sizer.Add(self.quit_checkbutton)


class SavingSettingsPanel(SettingsPanel):
    label = _("Saving")

    def __init__(self, parent, *a, **k):
        SettingsPanel.__init__(self, parent, *a, **k)
        # widgets
        self.ask_checkbutton = CheckButton(self,
            _("Ask where to save each new download"), self.settings_window,
            'ask_for_save', self.settings_window.config['ask_for_save'])

        self.save_static_box = wx.StaticBox(self, label=_("Move completed downloads to:"))

        self.save_box = ChooseDirectorySizer(self,
                                             self.settings_window.config['save_in'],
                                             setfunc = lambda v: self.settings_window.setfunc('save_in', v),
                                             editable = False,
                                             button_label = _("&Browse"))


        self.incoming_static_box = wx.StaticBox(self, label=_("Store unfinished downloads in:"))

        self.incoming_box = ChooseDirectorySizer(self,
                                                 self.settings_window.config['save_incomplete_in'],
                                                 setfunc = lambda v: self.settings_window.setfunc('save_incomplete_in', v),
                                                 editable = False,
                                                 button_label = _("B&rowse"))

        # sizers
        self.save_static_box_sizer = wx.StaticBoxSizer(self.save_static_box, wx.VERTICAL)
        self.save_static_box_sizer.Add(self.save_box,
                                    flag=wx.ALL|wx.GROW,
                                    border=SPACING)

        self.incoming_static_box_sizer = wx.StaticBoxSizer(self.incoming_static_box, wx.VERTICAL)
        self.incoming_static_box_sizer.Add(self.incoming_box,
                                           flag=wx.ALL|wx.GROW,
                                           border=SPACING)

        self.sizer.AddFirst(self.ask_checkbutton)
        self.sizer.Add(self.save_static_box_sizer, flag=wx.GROW)
        self.sizer.Add(self.incoming_static_box_sizer, flag=wx.GROW)



class NetworkSettingsPanel(SettingsPanel):
    label = _("Network")

    def __init__(self, parent, *a, **k):
        SettingsPanel.__init__(self, parent, *a, **k)

        if os.name == 'nt':
            self.autodetect = CheckButton(self,
                                          _("Autodetect available bandwidth"),
                                          self.settings_window,
                                          'bandwidth_management',
                                          self.settings_window.config['bandwidth_management'],
                                          self.bandwidth_management_callback
                                          )

            self.sizer.AddFirst(self.autodetect)
        self.up_rate_slider = RateSliderBox(self,
                                            _("Maximum upload rate"),
                                            'max_upload_rate',
                                            self.settings_window,
                                            upload_speed_classes)
        self.sizer.Add(self.up_rate_slider.sizer, flag=wx.GROW)

        self.down_rate_slider = RateSliderBox(self,
                                              _("Average maximum download rate"),
                                              'max_download_rate',
                                              self.settings_window,
                                              download_speed_classes)
        self.sizer.Add(self.down_rate_slider.sizer, flag=wx.GROW)

        if os.name == 'nt':
            self.bandwidth_management_callback()

        # Network widgets
        self.port_box = wx.StaticBox(self, label=_("Look for available port:"))
        port_text = ElectroStaticText(self, wx.ID_ANY, _("starting at port:") + ' ')
        port_range = ElectroStaticText(self, wx.ID_ANY, " (1024-65535)")
        self.port_field = PortValidator(self, 'minport',
                                        self.settings_window.config,
                                        self.settings_window.setfunc)
        self.port_field.add_end('maxport')
        self.upnp = CheckButton(self, _("Enable automatic port mapping")+" (&UPnP)",
                                self.settings_window,
                                'upnp',
                                self.settings_window.config['upnp'],
                                None)

        # Network sizers
        self.port_box_line1 = wx.BoxSizer(wx.HORIZONTAL)
        self.port_box_line1.Add(port_text , flag=wx.ALIGN_CENTER_VERTICAL, border=SPACING)
        self.port_box_line1.Add(self.port_field)
        self.port_box_line1.Add(port_range, flag=wx.ALIGN_CENTER_VERTICAL, border=SPACING)

        self.port_box_sizer = wx.StaticBoxSizer(self.port_box, wx.VERTICAL)
        self.port_box_sizer.Add(self.port_box_line1, flag=wx.TOP|wx.LEFT|wx.RIGHT, border=SPACING)
        self.port_box_sizer.Add(self.upnp, flag=wx.ALL, border=SPACING)

        self.sizer.Add(self.port_box_sizer, flag=wx.GROW)

        # debug only code
        if wx.the_app.config['debug']:
            # widgets
            self.ip_box = wx.StaticBox(self, label=_("IP to report to the tracker:"))
            self.ip_field = IPValidator(self, 'ip',
                                        self.settings_window.config,
                                        self.settings_window.setfunc)
            ip_label = ElectroStaticText(self, wx.ID_ANY,
                                     _("(Has no effect unless you are on the\nsame local network as the tracker)"))

            # sizers
            self.ip_box_sizer = wx.StaticBoxSizer(self.ip_box, wx.VERTICAL)

            self.ip_box_sizer.Add(self.ip_field, flag=wx.TOP|wx.LEFT|wx.RIGHT|wx.GROW, border=SPACING)
            self.ip_box_sizer.Add(ip_label, flag=wx.ALL, border=SPACING)

            self.sizer.Add(self.ip_box_sizer, flag=wx.GROW)

    def bandwidth_management_callback(self):
        enable = not self.autodetect.GetValue()
        if enable:
            self.up_rate_slider.LoadValue()
            self.down_rate_slider.LoadValue()
        self.up_rate_slider.Enable(enable)
        self.down_rate_slider.Enable(enable)


class AppearanceSettingsPanel(SettingsPanel):
    label = _("Appearance")
    pb_config_key = 'progressbar_style'
    # sample data
    sample_value = 0.4
    

    sample_data = {'h': SparseSet(),
                   't': SparseSet(),
                   }

    sample_data['h'].add(0, 80)
    sample_data['t'].add(80, 100)
    
    for i in range(20,0,-1):
        s = SparseSet()
        s.add(200-i*5, 200-(i-1)*5)
        sample_data[i-1] = s
    del i,s

    def __init__(self, parent, *a, **k):
        SettingsPanel.__init__(self, parent, *a, **k)

        # widgets
        self.gauge_box = wx.StaticBox(self, label=_("Progress bar style:"))

        self.gauge_sizer = wx.StaticBoxSizer(self.gauge_box, wx.VERTICAL)

        self.null_radio = wx.RadioButton(self,
                                         label=_("&None (just show percent complete)"),
                                         style=wx.RB_GROUP)
        self.null_radio.value = 0

        self.simple_radio = wx.RadioButton(self,
                                           label=_("&Ordinary progress bar"))
        self.simple_radio.value = 1
        self.simple_sample = self.new_sample(SimpleDownloadGauge, 1)

        self.moderate_radio = wx.RadioButton(self,
                                             label=_("&Detailed progress bar"))
        self.moderate_radio.value = 2
        msg = _("(shows the percentage of complete, transferring, available and missing pieces in the torrent)")
        if not text_wrappable:
            half = len(msg)//2
            for i in xrange(half):
                if msg[half+i] == ' ':
                    msg = msg[:half+i+1] + '\n' + msg[half+i+1:]
                    break
                elif msg[half-i] == ' ':
                    msg = msg[:half-i+1] + '\n' + msg[half-i+1:]
                    break
        self.moderate_text = ElectroStaticText(self, wx.ID_ANY, msg)

        if text_wrappable: self.moderate_text.Wrap(250)
        self.moderate_sample = self.new_sample(ModerateDownloadGauge, 2)

        self.fancy_radio = wx.RadioButton(self,
                                          label=_("&Piece bar"))
        self.fancy_radio.value = 3
        self.fancy_text = ElectroStaticText(self, wx.ID_ANY,
                                        _("(shows the status of each piece in the torrent)"))
        if text_wrappable: self.fancy_text.Wrap(250)

        # generate random sample data
        r = set(xrange(200)) 
        self.sample_data = {}

        for key, count in (('h',80), ('t',20)) + tuple([(i,5) for i in range(19)]):
            self.sample_data[key] = SparseSet()
            for d in random.sample(r, count):
                self.sample_data[key].add(d)
                r.remove(d)
        for d in r:
            self.sample_data[0].add(d)

        self.fancy_sample = self.new_sample(FancyDownloadGauge, 3)

        # sizers
        gauge = wx.TOP|wx.LEFT|wx.RIGHT
        extra = wx.TOP|wx.LEFT|wx.RIGHT|wx.GROW
        self.gauge_sizer.Add(self.null_radio     , flag=gauge, border=SPACING)
        self.gauge_sizer.AddSpacer((SPACING, SPACING))

        self.gauge_sizer.Add(self.simple_radio   , flag=gauge, border=SPACING)
        self.gauge_sizer.Add(self.simple_sample  , flag=extra, border=SPACING)
        self.gauge_sizer.AddSpacer((SPACING, SPACING))

        self.gauge_sizer.Add(self.moderate_radio , flag=gauge, border=SPACING)
        self.gauge_sizer.Add(self.moderate_sample, flag=extra, border=SPACING)
        self.gauge_sizer.Add(self.moderate_text  , flag=extra, border=SPACING)
        self.gauge_sizer.AddSpacer((SPACING, SPACING))

        self.gauge_sizer.Add(self.fancy_radio    , flag=gauge, border=SPACING)
        self.gauge_sizer.Add(self.fancy_sample   , flag=extra, border=SPACING)
        self.gauge_sizer.Add(self.fancy_text     , flag=extra, border=SPACING)

        self.sizer.AddFirst(self.gauge_sizer, flag=wx.GROW)

        # setup
        self.pb_group = (self.null_radio, self.simple_radio, self.moderate_radio, self.fancy_radio)

        for r in self.pb_group:
            r.Bind(wx.EVT_RADIOBUTTON, self.radio)
            if r.value == wx.the_app.config[self.pb_config_key]:
                r.SetValue(True)
            else:
                r.SetValue(False)

        # toolbar widgets
        self.toolbar_box = wx.StaticBox(self, label=_("Toolbar style:"))
        self.toolbar_text = CheckButton(self, _("Show text"),
                                        self.settings_window,
                                        'toolbar_text',
                                        self.settings_window.config['toolbar_text'],
                                        wx.the_app.reset_toolbar_style)
        self.toolbar_size_text = ElectroStaticText(self, id=wx.ID_ANY, label=_("Icon size:"))
        self.toolbar_size_choice = wx.Choice(self, choices=(_("Small"), _("Normal"), _("Large")))
        self.toolbar_config_to_choice(wx.the_app.config['toolbar_size'])
        self.toolbar_size_choice.Bind(wx.EVT_CHOICE, self.toolbar_choice_to_config)

        # toolbar sizers
        self.toolbar_sizer = HSizer()
        self.toolbar_sizer.AddFirst(self.toolbar_text, flag=wx.ALIGN_CENTER_VERTICAL)
        line = wx.StaticLine(self, id=wx.ID_ANY, style=wx.VERTICAL)
        self.toolbar_sizer.Add(line,
                               flag=wx.ALIGN_CENTER_VERTICAL|wx.GROW)
        self.toolbar_sizer.Add(self.toolbar_size_text, flag=wx.ALIGN_CENTER_VERTICAL)
        self.toolbar_sizer.Add(self.toolbar_size_choice, flag=wx.GROW|wx.ALIGN_TOP, proportion=1)

        self.toolbar_box_sizer = wx.StaticBoxSizer(self.toolbar_box, wx.VERTICAL)
        self.toolbar_box_sizer.Add(self.toolbar_sizer, flag=wx.GROW)

        self.sizer.Add(self.toolbar_box_sizer, flag=wx.GROW)

        if wx.the_app.config['debug']:
            # the T-Word widgets
            self.themes = []
            self.theme_choice = wx.Choice(self, choices=[])
            self.theme_choice.Enable(False)
            self.theme_choice.Bind(wx.EVT_CHOICE, self.set_theme)
            self.restart_hint = ElectroStaticText(self, id=wx.ID_ANY, label=_("(Changing themes requires restart.)"))
            self.theme_static_box = wx.StaticBox(self, label=_("Theme:"))

            # the T-Word sizers
            self.theme_sizer = VSizer()
            self.theme_sizer.AddFirst(self.theme_choice, flag=wx.GROW|wx.ALIGN_RIGHT)
            self.theme_sizer.Add(self.restart_hint, flag=wx.GROW|wx.ALIGN_RIGHT)

            self.theme_static_box_sizer = wx.StaticBoxSizer(self.theme_static_box, wx.VERTICAL)
            self.theme_static_box_sizer.Add(self.theme_sizer, flag=wx.GROW)
            self.sizer.Add(self.theme_static_box_sizer, flag=wx.GROW)

            self.get_themes()


    def get_themes(self):
        def _callback(themes):
            self.themes.extend(themes)
            self.theme_choice.AppendItems(strings=themes)

            curr_theme = wx.the_app.config['theme']
            if curr_theme not in self.themes:
                self.settings_window.setfunc('theme', 'default')
                curr_theme = wx.the_app.config['theme']

            curr_idx = self.themes.index(curr_theme)
            self.theme_choice.SetSelection(curr_idx)
            self.theme_choice.Enable(True)

        def callback(themes):
            gui_wrap(_callback, themes)

        df = list_themes()
        df.addCallback(callback)
        df.getResult()


    def set_theme(self, e):
        i = self.theme_choice.GetSelection()
        t = self.themes[i]
        self.settings_window.setfunc('theme', t)


    def toolbar_choice_to_config(self, *a):
        i = self.toolbar_size_choice.GetSelection(),
        size = 8*(i[0]+2)
        self.settings_window.setfunc('toolbar_size', size)
        wx.the_app.reset_toolbar_style()


    def toolbar_config_to_choice(self, value):
        i = (value//8) - 2
        self.toolbar_size_choice.SetSelection(i)


    def new_sample(self, sample_class, value):
        sample = sample_class(self, size=wx.Size(-1, 20), style=wx.SUNKEN_BORDER)
        # I happen to know 200 is the right number because I looked.
        sample.SetValue(self.sample_value, 'running', (200, 0, self.sample_data))
        sample.Bind(wx.EVT_LEFT_DOWN, self.sample)
        sample.Bind(wx.EVT_CONTEXT_MENU, None)
        sample.value = value
        return sample


    def radio(self, event):
        widget = event.GetEventObject()
        value = widget.value
        self.settings_window.setfunc(self.pb_config_key, value)
        gui_wrap(wx.the_app.main_window.torrentlist.change_gauge_type, value)


    def sample(self, event):
        self.radio(event)
        pb = event.GetEventObject()
        value = pb.value
        for p in self.pb_group:
            if p.value == value:
                p.SetValue(True)
                break



class LanguageSettingsPanel(LanguageSettings):
    label = _("Language")

    def __init__(self, parent, *a, **k):
        LanguageSettings.__init__(self, parent, *a, **k)
        parent.AddPage(self, self.label)
        self.settings_window = parent.GetParent()



class SettingsWindow(BTDialog):

    def __init__(self, main_window, config, setfunc):
        BTDialog.__init__(self, main_window, style=wx.DEFAULT_DIALOG_STYLE|wx.CLIP_CHILDREN|wx.WANTS_CHARS)
        self.Bind(wx.EVT_CLOSE, self.close)
        self.Bind(wx.EVT_CHAR, self.key)
        self.SetTitle(_("%s Settings")%app_name)

        self.setfunc = setfunc
        self.config = config

        self.notebook = wx.Notebook(self)

        self.notebook.Bind(wx.EVT_CHAR, self.key)

        self.general_panel    =    GeneralSettingsPanel(self.notebook)
        self.saving_panel     =     SavingSettingsPanel(self.notebook)
        self.network_panel    =    NetworkSettingsPanel(self.notebook)
        self.appearance_panel = AppearanceSettingsPanel(self.notebook)
        self.language_panel   =   LanguageSettingsPanel(self.notebook)

        self.vbox = VSizer()
        self.vbox.AddFirst(self.notebook, proportion=1, flag=wx.GROW)

        self.vbox.Layout()

        self.SetSizerAndFit(self.vbox)
        self.SetFocus()


    def key(self, event):
        c = event.GetKeyCode()
        if c == wx.WXK_ESCAPE:
            self.close()
        event.Skip()


    def get_save_in(self, *e):
        d = wx.DirDialog(self, "", style=wx.DD_DEFAULT_STYLE|wx.DD_NEW_DIR_BUTTON)
        d.SetPath(self.config['save_in'])
        if d.ShowModal() == wx.ID_OK:
            path = d.GetPath()
            self.saving_panel.save_in_button.SetLabel(path)
            self.setfunc('save_in', path)


    def start_torrent_behavior_changed(self, event):
        widget = event.GetEventObject()
        state_name = widget.state_name
        self.setfunc('start_torrent_behavior', state_name)


    def close(self, *e):
        self.Hide()

