#written by John Hoffman

from ConnChoice import *
from wxPython.wx import *
from types import IntType, FloatType, StringType
import sys,os
import socket
from parseargs import defaultargs

try:
    True
except:
    True = 1
    False = 0
    
basepath=os.path.abspath(os.path.dirname(sys.argv[0]))

class configReader:

    def __init__(self, defaults = None):
        self.configfile = wxConfig("BitTorrent",style=wxCONFIG_USE_LOCAL_FILE)
        self.configMenuBox = None
        self.advancedMenuBox = None
        self.configReset = True         # run reset for the first time

        self.configFileDefaults = {
            #args only available here:
            'win32_taskbar_icon': 1,
                # "whether to iconize do system try or not on win32"),
            'gui_stretchwindow': 0,
                # "whether to stretch the download status window to fit the torrent name"),
            'gui_displaystats': 1,
                # "whether to display statistics on peers and seeds"),
            'gui_displaymiscstats': 1,
                # "whether to display miscellaneous other statistics"),
            'gui_ratesettingsdefault': 'unlimited',
                # "the default setting for maximum upload rate and users"),
            'gui_ratesettingsmode': 'full',
                # "what rate setting controls to display; options are 'none', 'basic', and 'full'"),
            'gui_forcegreenonfirewall': 0,
                # "forces the status icon to be green even if the client seems to be firewalled")
            'gui_checkingcolor': 'FF FF FF',
            'gui_downloadcolor': '00 00 00',
            'gui_seedingcolor': '00 FF 00',
            'gui_default_savedir': '',
            'last_saved': '',       # hidden; not set in config
            }

        if (sys.platform == 'win32'):
            self.FONT = 9
        else:
            self.FONT = 10
        self.configFileDefaults['gui_font'] = self.FONT

        self.configFileDefaults['gui_checkingcolor'] = self.ColorToHex(wxSystemSettings_GetColour(wxSYS_COLOUR_3DSHADOW))
        self.configFileDefaults['gui_downloadcolor'] = self.ColorToHex(wxSystemSettings_GetColour(wxSYS_COLOUR_ACTIVECAPTION))
        
        self.gui_ratesettingslist = []
        for x in connChoices:
            if not x.has_key('super-seed'):
                self.gui_ratesettingslist.append(x['name'])
        self.configFileDefaults['gui_ratesettingsdefault'] = self.gui_ratesettingslist[0]

        configfileargs = {
            # args listed in download.py:
            'minport': None,
            'maxport': None,
            'ip': None,
            'bind': None,
            'min_peers': None,
            'max_initiate': None,
            'display_interval': None,
            'alloc_type': None,
            'alloc_rate': None,
            'buffer_reads': None,
            'write_buffer_size': None,
            'max_files_open': None,
            'security': None,
            'super_seeder': None,
            'max_connections': None,
            'auto_kick': None,
            'ipv6_enabled': None,
            'ipv6_binds_v4': None,
            'double_check': None,
            'triple_check': None,
            'lock_files': None,
            'lock_while_reading': None,
            }

        self.downloaddefaultargs = configfileargs.keys()        

        for name in self.configFileDefaults:
            configfileargs[name] = self.configFileDefaults[name]
        self.configfileargs = configfileargs

        self.import_defaults(self.configFileDefaults.keys())

        self.checkingcolor = self.HexToColor(self.configfileargs['gui_checkingcolor'])
        self.downloadcolor = self.HexToColor(self.configfileargs['gui_downloadcolor'])
        self.seedingcolor = self.HexToColor(self.configfileargs['gui_seedingcolor'])
        self.FONT = self.configfileargs['gui_font']
        self.default_font = wxFont(self.FONT, wxDEFAULT, wxNORMAL, wxNORMAL, False)

        if defaults is not None:
            self.setDownloadDefaults(defaults)


    def setDownloadDefaults(self, defaults = None):
        defaults = defaultargs(defaults)
        self.defaults = defaults
        self.import_defaults(self.downloaddefaultargs)

        updated = False     # make all config default changes here
        if self.configfileargs['gui_ratesettingsdefault'] not in self.gui_ratesettingslist:
            self.configfileargs['gui_ratesettingsdefault'] = (
                                self.configFileDefaults['gui_ratesettingsdefault'])
            updated = True
        if self.configfileargs['ipv6_enabled'] and (
                        sys.version_info < (2,3) or not socket.has_ipv6 ):
            self.configfileargs['ipv6_enabled'] = 0
            updated = True
        if updated:
            self.writeConfigFile()
                

    def import_defaults(self,list):
        for name in list:
            try:
                default = self.defaults[name]
            except:
                default = self.configFileDefaults[name]
            if type(default) is IntType:
                if self.configfile.Exists(name):
                    try:
                        setting = self.configfile.ReadInt(name,0)
                    except:
                        setting = None
                    if setting is None:
                        setting = default
                        self.configfile.WriteInt(name,default)
                    self.configfileargs[name] = setting
                else:
                    self.configfileargs[name] = default
                    self.configfile.WriteInt(name,default)
            elif type(default) is FloatType:
                if self.configfile.Exists(name):
                    try:
                        setting = self.configfile.ReadFloat(name,0.0)
                    except:
                        setting = None
                    if setting is None:
                        setting = default
                        self.configfile.WriteFloat(name,default)
                    self.configfileargs[name] = setting
                else:
                    self.configfileargs[name] = default
                    self.configfile.WriteFloat(name,default)
            elif type(default) is StringType:
                if self.configfile.Exists(name):
                    try:
                        setting = self.configfile.Read(name,'')
                    except:
                        setting = None
                    if (setting is None) or (setting == '') or (setting == 'None'):
                        setting = default
                        self.configfile.Write(name,default)
                    self.configfileargs[name] = setting
                else:
                    self.configfileargs[name] = default
                    self.configfile.Write(name,default)
            #else skip it...
        self.configfile.Flush()
        

    def HexToColor(self, s):
        r,g,b = s.split(' ')
        return wxColour(red=int(r,16), green=int(g,16), blue=int(b,16))
        
        
    def ColorToHex(self, c):
        return hex(c.Red()) + ' ' + hex(c.Green()) + ' ' + hex(c.Blue())


    def resetConfigDefaults(self):
        for name in self.configFileDefaults:
            self.configfileargs[name] = self.configFileDefaults[name]
        for name in self.configfileargs:
            default = self.defaults.get(name)
            if default is not None:
                self.configfileargs[name] = default
        writeConfigFile()



    def writeConfigFile(self):
        for name in self.configfileargs:
            default = self.configfileargs[name]
            if type(default) is IntType:
                self.configfile.WriteInt(name,default)
            elif type(default) is FloatType:
                self.configfile.WriteFloat(name,default)
            else:  # assume StringType:
                self.configfile.Write(name,str(default))
        self.configfile.Flush()


    def WriteLastSaved(self, l):
        self.configfileargs['last_saved'] = l
        self.configfile.Write('last_saved',l)
        self.configfile.Flush()


    def setColorIcon(self, xxicon, xxiconptr, xxcolor):
        idata = wxMemoryDC()
        idata.SelectObject(xxicon)
        idata.SetBrush(wxBrush(xxcolor,wxSOLID))
        idata.DrawRectangle(0,0,16,16)
        idata.SelectObject(wxNullBitmap)
        xxiconptr.Refresh()


    def getColorFromUser(self, parent, colInit):
        data = wxColourData()
        if colInit.Ok():
            data.SetColour(colInit)
        data.SetCustomColour(0, self.checkingcolormenu)
        data.SetCustomColour(1, self.downloadcolormenu)
        data.SetCustomColour(2, self.seedingcolormenu)
        dlg = wxColourDialog(parent,data)
        if not dlg.ShowModal():
            return colInit
        return dlg.GetColourData().GetColour()



    def configMenu(self, parent):
      self.parent = parent
      try:
        self.checkingcolormenu = self.checkingcolor
        self.downloadcolormenu = self.downloadcolor
        self.seedingcolormenu = self.seedingcolor
        
        if (self.configMenuBox is not None):
            try:
                self.configMenuBox.Close ()
            except wxPyDeadObjectError, e:
                self.configMenuBox = None

        self.configMenuBox = wxFrame(None, -1, 'BitTorrent Preferences', size = (1,1))
        if (sys.platform == 'win32'):
            self.icon = wxIcon(os.path.join(basepath,'icon_bt.ico'), wxBITMAP_TYPE_ICO)
            self.configMenuBox.SetIcon(self.icon)

        panel = wxPanel(self.configMenuBox, -1)
        self.panel = panel

        def StaticText(text, font = self.FONT, underline = False, color = None, panel = panel):
            x = wxStaticText(panel, -1, text, style = wxALIGN_LEFT)
            x.SetFont(wxFont(font, wxDEFAULT, wxNORMAL, wxNORMAL, underline))
            if color is not None:
                x.SetForegroundColour(color)
            return x

        colsizer = wxFlexGridSizer(cols = 1, vgap = 8)

        self.gui_stretchwindow_checkbox = wxCheckBox(panel, -1, "Stretch window to fit torrent name *")
        self.gui_stretchwindow_checkbox.SetFont(self.default_font)
        self.gui_stretchwindow_checkbox.SetValue(self.configfileargs['gui_stretchwindow'])

        self.gui_displaystats_checkbox = wxCheckBox(panel, -1, "Display peer and seed statistics")
        self.gui_displaystats_checkbox.SetFont(self.default_font)
        self.gui_displaystats_checkbox.SetValue(self.configfileargs['gui_displaystats'])

        self.gui_displaymiscstats_checkbox = wxCheckBox(panel, -1, "Display miscellaneous other statistics")
        self.gui_displaymiscstats_checkbox.SetFont(self.default_font)
        self.gui_displaymiscstats_checkbox.SetValue(self.configfileargs['gui_displaymiscstats'])

        self.security_checkbox = wxCheckBox(panel, -1, "Don't allow multiple connections from the same IP")
        self.security_checkbox.SetFont(self.default_font)
        self.security_checkbox.SetValue(self.configfileargs['security'])

        self.autokick_checkbox = wxCheckBox(panel, -1, "Kick/ban clients that send you bad data *")
        self.autokick_checkbox.SetFont(self.default_font)
        self.autokick_checkbox.SetValue(self.configfileargs['auto_kick'])

        self.buffering_checkbox = wxCheckBox(panel, -1, "Enable read/write buffering *")
        self.buffering_checkbox.SetFont(self.default_font)
        self.buffering_checkbox.SetValue(self.configfileargs['buffer_reads'])

        if sys.version_info >= (2,3) and socket.has_ipv6:
            self.ipv6enabled_checkbox = wxCheckBox(panel, -1, "Initiate and receive connections via IPv6 *")
            self.ipv6enabled_checkbox.SetFont(self.default_font)
            self.ipv6enabled_checkbox.SetValue(self.configfileargs['ipv6_enabled'])

        self.gui_forcegreenonfirewall_checkbox = wxCheckBox(panel, -1,
                            "Force icon to display green when firewalled")
        self.gui_forcegreenonfirewall_checkbox.SetFont(self.default_font)
        self.gui_forcegreenonfirewall_checkbox.SetValue(self.configfileargs['gui_forcegreenonfirewall'])

        self.minport_data = wxSpinCtrl(panel, -1, '', (-1,-1), (self.FONT*7, -1))
        self.minport_data.SetFont(self.default_font)
        self.minport_data.SetRange(1,65535)
        self.minport_data.SetValue(self.configfileargs['minport'])

        self.maxport_data = wxSpinCtrl(panel, -1, '', (-1,-1), (self.FONT*7, -1))
        self.maxport_data.SetFont(self.default_font)
        self.maxport_data.SetRange(1,65535)
        self.maxport_data.SetValue(self.configfileargs['maxport'])
        
        self.gui_font_data = wxSpinCtrl(panel, -1, '', (-1,-1), (self.FONT*5, -1))
        self.gui_font_data.SetFont(self.default_font)
        self.gui_font_data.SetRange(8,16)
        self.gui_font_data.SetValue(self.configfileargs['gui_font'])

        self.gui_ratesettingsdefault_data=wxChoice(panel, -1, choices = self.gui_ratesettingslist )
        self.gui_ratesettingsdefault_data.SetFont(self.default_font)
        self.gui_ratesettingsdefault_data.SetStringSelection(self.configfileargs['gui_ratesettingsdefault'])

        self.gui_ratesettingsmode_data=wxRadioBox(panel, -1, 'Rate Settings Mode',
                 choices = [ 'none', 'basic', 'full' ] )
        self.gui_ratesettingsmode_data.SetFont(self.default_font)
        self.gui_ratesettingsmode_data.SetStringSelection(self.configfileargs['gui_ratesettingsmode'])

        if (sys.platform == 'win32'):
            self.win32_taskbar_icon_checkbox = wxCheckBox(panel, -1, "Minimize to system tray")
            self.win32_taskbar_icon_checkbox.SetFont(self.default_font)
            self.win32_taskbar_icon_checkbox.SetValue(self.configfileargs['win32_taskbar_icon'])

        self.gui_default_savedir_ctrl = wxTextCtrl(parent = panel, id = -1, 
                            value = self.configfileargs['gui_default_savedir'],        
                            size = (26*self.FONT, -1), style = wxTE_PROCESS_TAB)
        self.gui_default_savedir_ctrl.SetFont(self.default_font)

        self.checkingcolor_icon = wxEmptyBitmap(16,16)
        self.checkingcolor_iconptr = wxStaticBitmap(panel, -1, self.checkingcolor_icon)
        self.setColorIcon(self.checkingcolor_icon, self.checkingcolor_iconptr, self.checkingcolormenu)

        self.downloadcolor_icon = wxEmptyBitmap(16,16)
        self.downloadcolor_iconptr = wxStaticBitmap(panel, -1, self.downloadcolor_icon)
        self.setColorIcon(self.downloadcolor_icon, self.downloadcolor_iconptr, self.downloadcolormenu)

        self.seedingcolor_icon = wxEmptyBitmap(16,16)
        self.seedingcolor_iconptr = wxStaticBitmap(panel, -1, self.seedingcolor_icon)
        self.setColorIcon(self.seedingcolor_icon, self.downloadcolor_iconptr, self.seedingcolormenu)
        
        rowsizer = wxFlexGridSizer(cols = 2, hgap = 20)

        block12sizer = wxFlexGridSizer(cols = 1, vgap = 7)

        block1sizer = wxFlexGridSizer(cols = 1, vgap = 2)
        if (sys.platform == 'win32'):
            block1sizer.Add(self.win32_taskbar_icon_checkbox)
        block1sizer.Add(self.gui_stretchwindow_checkbox)
        block1sizer.Add(self.gui_displaystats_checkbox)
        block1sizer.Add(self.gui_displaymiscstats_checkbox)
        block1sizer.Add(self.security_checkbox)
        block1sizer.Add(self.autokick_checkbox)
        block1sizer.Add(self.buffering_checkbox)
        if sys.version_info >= (2,3) and socket.has_ipv6:
            block1sizer.Add(self.ipv6enabled_checkbox)
        block1sizer.Add(self.gui_forcegreenonfirewall_checkbox)

        block12sizer.Add(block1sizer)

        colorsizer = wxStaticBoxSizer(wxStaticBox(panel, -1, "Gauge Colors:"), wxVERTICAL)
        colorsizer1 = wxFlexGridSizer(cols = 7)
        colorsizer1.Add(StaticText('           Checking: '), 1, wxALIGN_BOTTOM)
        colorsizer1.Add(self.checkingcolor_iconptr, 1, wxALIGN_BOTTOM)
        colorsizer1.Add(StaticText('   Downloading: '), 1, wxALIGN_BOTTOM)
        colorsizer1.Add(self.downloadcolor_iconptr, 1, wxALIGN_BOTTOM)
        colorsizer1.Add(StaticText('   Seeding: '), 1, wxALIGN_BOTTOM)
        colorsizer1.Add(self.seedingcolor_iconptr, 1, wxALIGN_BOTTOM)
        colorsizer1.Add(StaticText('  '))
        minsize = self.checkingcolor_iconptr.GetBestSize()
        minsize.SetHeight(minsize.GetHeight()+5)
        colorsizer1.SetMinSize(minsize)
        colorsizer.Add(colorsizer1)
       
        block12sizer.Add(colorsizer, 1, wxALIGN_LEFT)

        rowsizer.Add(block12sizer)

        block3sizer = wxFlexGridSizer(cols = 1)

        portsettingsSizer = wxStaticBoxSizer(wxStaticBox(panel, -1, "Port Range:*"), wxVERTICAL)
        portsettingsSizer1 = wxGridSizer(cols = 2, vgap = 1)
        portsettingsSizer1.Add(StaticText('From: '), 1, wxALIGN_CENTER_VERTICAL|wxALIGN_RIGHT)
        portsettingsSizer1.Add(self.minport_data, 1, wxALIGN_BOTTOM)
        portsettingsSizer1.Add(StaticText('To: '), 1, wxALIGN_CENTER_VERTICAL|wxALIGN_RIGHT)
        portsettingsSizer1.Add(self.maxport_data, 1, wxALIGN_BOTTOM)
        portsettingsSizer.Add(portsettingsSizer1)
        block3sizer.Add(portsettingsSizer, 1, wxALIGN_CENTER)
        block3sizer.Add(StaticText(' '))

        block3sizer.Add(self.gui_ratesettingsmode_data, 1, wxALIGN_CENTER)
        
        rowsizer.Add(block3sizer)
        colsizer.Add(rowsizer)

        block4sizer = wxFlexGridSizer(cols = 3, hgap = 15)        
        savepathsizer = wxFlexGridSizer(cols = 2, vgap = 1)
        savepathsizer.Add(StaticText('Default Save Path: *'))
        savepathsizer.Add(StaticText(' '))
        savepathsizer.Add(self.gui_default_savedir_ctrl, 1, wxEXPAND)
        savepathButton = wxButton(panel, -1, '...', size = (18,18))
#        savepathButton.SetFont(self.default_font)
        savepathsizer.Add(savepathButton, 0, wxALIGN_CENTER)
        block4sizer.Add(savepathsizer, -1, wxALIGN_BOTTOM)

        fontsizer = wxFlexGridSizer(cols = 1, vgap = 2)
        fontsizer.Add(StaticText('Font: *'), 1, wxALIGN_CENTER)
        fontsizer.Add(self.gui_font_data, 1, wxALIGN_CENTER)
        block4sizer.Add(fontsizer, 1, wxALIGN_BOTTOM)

        ratesettingsSizer = wxGridSizer(cols = 1, vgap = 0)
        ratesettingsSizer.Add(StaticText('Default Rate Setting: *'), 1, wxALIGN_CENTER)
        ratesettingsSizer.Add(self.gui_ratesettingsdefault_data, 1, wxALIGN_CENTER)
        block4sizer.Add(ratesettingsSizer, 1, wxALIGN_BOTTOM)

        colsizer.Add(block4sizer, 0, wxALIGN_CENTER)
        colsizer.Add(StaticText(' '))

        savesizer = wxGridSizer(cols = 4, hgap = 10)
        saveButton = wxButton(panel, -1, 'Save')
#        saveButton.SetFont(self.default_font)
        savesizer.Add(saveButton, 0, wxALIGN_CENTER)

        cancelButton = wxButton(panel, -1, 'Cancel')
#        cancelButton.SetFont(self.default_font)
        savesizer.Add(cancelButton, 0, wxALIGN_CENTER)

        defaultsButton = wxButton(panel, -1, 'Revert to Defaults')
#        defaultsButton.SetFont(self.default_font)
        savesizer.Add(defaultsButton, 0, wxALIGN_CENTER)

        advancedButton = wxButton(panel, -1, 'Advanced...')
#        advancedButton.SetFont(self.default_font)
        savesizer.Add(advancedButton, 0, wxALIGN_CENTER)
        colsizer.Add(savesizer, 1, wxALIGN_CENTER)

        resizewarningtext=StaticText('* These settings will not take effect until the next time you start BitTorrent', self.FONT-2)
        colsizer.Add(resizewarningtext, 1, wxALIGN_CENTER)

        border = wxBoxSizer(wxHORIZONTAL)
        border.Add(colsizer, 1, wxEXPAND | wxALL, 4)
        
        panel.SetSizer(border)
        panel.SetAutoLayout(True)

        self.advancedConfig = {}

        def setDefaults(self, ref = self):
          try:
            ref.minport_data.SetValue(ref.defaults.get('minport'))
            ref.maxport_data.SetValue(ref.defaults.get('maxport'))
            ref.gui_stretchwindow_checkbox.SetValue(ref.configFileDefaults['gui_stretchwindow'])
            ref.gui_displaystats_checkbox.SetValue(ref.configFileDefaults['gui_displaystats'])
            ref.gui_displaymiscstats_checkbox.SetValue(ref.configFileDefaults['gui_displaymiscstats'])
            ref.security_checkbox.SetValue(ref.configfileargs['security'])
            ref.autokick_checkbox.SetValue(ref.configfileargs['auto_kick'])
            ref.buffering_checkbox.SetValue(ref.configfileargs['buffer_reads'])
            if sys.version_info >= (2,3) and socket.has_ipv6:
                ref.ipv6enabled_checkbox.SetValue(ref.configfileargs['ipv6_enabled'])
            ref.gui_forcegreenonfirewall_checkbox.SetValue(ref.configFileDefaults['gui_forcegreenonfirewall'])
            ref.gui_font_data.SetValue(ref.configFileDefaults['gui_font'])
            ref.gui_ratesettingsdefault_data.SetStringSelection(ref.configFileDefaults['gui_ratesettingsdefault'])
            ref.gui_ratesettingsmode_data.SetStringSelection(ref.configFileDefaults['gui_ratesettingsmode'])
            ref.gui_default_savedir_ctrl.SetValue(ref.configFileDefaults['gui_default_savedir'])

            ref.checkingcolormenu = ref.HexToColor(ref.configFileDefaults['gui_checkingcolor'])
            ref.setColorIcon(ref.checkingcolor_icon, ref.checkingcolor_iconptr, ref.checkingcolormenu)
            ref.downloadcolormenu = ref.HexToColor(ref.configFileDefaults['gui_downloadcolor'])
            ref.setColorIcon(ref.downloadcolor_icon, ref.downloadcolor_iconptr, ref.downloadcolormenu)
            ref.seedingcolormenu = ref.HexToColor(ref.configFileDefaults['gui_seedingcolor'])
            ref.setColorIcon(ref.seedingcolor_icon, ref.seedingcolor_iconptr, ref.seedingcolormenu)

            if (sys.platform == 'win32'):
                ref.win32_taskbar_icon_checkbox.SetValue(ref.configFileDefaults['win32_taskbar_icon'])

            # reset advanced too
            for key in ['ip', 'bind', 'min_peers', 'max_initiate', 'display_interval',
        'alloc_type', 'alloc_rate', 'max_files_open', 'max_connections', 'super_seeder',
        'ipv6_binds_v4', 'double_check', 'triple_check', 'lock_files', 'lock_while_reading']:
                ref.configfileargs[key] = ref.defaults.get(key)
            ref.advancedConfig = {}
            ref.CloseAdvanced()
          except:
            ref.parent.exception()


        def saveConfigs(self, ref = self):
          try:
            ref.configfileargs['gui_stretchwindow']=int(ref.gui_stretchwindow_checkbox.GetValue())
            ref.configfileargs['gui_displaystats']=int(ref.gui_displaystats_checkbox.GetValue())
            ref.configfileargs['gui_displaymiscstats']=int(ref.gui_displaymiscstats_checkbox.GetValue())
            ref.configfileargs['security']=int(ref.security_checkbox.GetValue())
            ref.configfileargs['auto_kick']=int(ref.autokick_checkbox.GetValue())
            buffering=int(ref.buffering_checkbox.GetValue())
            ref.configfileargs['buffer_reads']=buffering
            if buffering:
                ref.configfileargs['write_buffer_size']=ref.defaults.get('write_buffer_size')
            else:
                ref.configfileargs['write_buffer_size']=0
            if sys.version_info >= (2,3) and socket.has_ipv6:
                ref.configfileargs['ipv6_enabled']=int(ref.ipv6enabled_checkbox.GetValue())
            ref.configfileargs['gui_forcegreenonfirewall']=int(ref.gui_forcegreenonfirewall_checkbox.GetValue())
            ref.configfileargs['minport']=ref.minport_data.GetValue()
            ref.configfileargs['maxport']=ref.maxport_data.GetValue()
            ref.configfileargs['gui_font']=ref.gui_font_data.GetValue()
            ref.configfileargs['gui_ratesettingsdefault']=ref.gui_ratesettingsdefault_data.GetStringSelection()
            ref.configfileargs['gui_ratesettingsmode']=ref.gui_ratesettingsmode_data.GetStringSelection()
            ref.configfileargs['gui_default_savedir']=ref.gui_default_savedir_ctrl.GetValue()

            ref.checkingcolor = ref.checkingcolormenu
            ref.configfileargs['gui_checkingcolor']=ref.ColorToHex(ref.checkingcolor)
            ref.downloadcolor = ref.downloadcolormenu
            ref.configfileargs['gui_downloadcolor']=ref.ColorToHex(ref.downloadcolor)
            ref.seedingcolor = ref.seedingcolormenu
            ref.configfileargs['gui_seedingcolor']=ref.ColorToHex(ref.seedingcolor)
            
            if (sys.platform == 'win32'):
                ref.configfileargs['win32_taskbar_icon']=int(ref.win32_taskbar_icon_checkbox.GetValue())

            if ref.advancedConfig:
                for key,val in ref.advancedConfig.items():
                    ref.configfileargs[key] = val

            ref.writeConfigFile()
            ref.configReset = True
            ref.Close()
          except:
            ref.parent.exception()

        def cancelConfigs(self, ref = self):            
            ref.Close()

        def savepath_set(self, ref = self):
          try:
            d = ref.gui_default_savedir_ctrl.GetValue()
            if d == '':
                d = ref.configfileargs['last_saved']
            dl = wxDirDialog(ref.panel, 'Choose a default directory to save to', 
                d, style = wxDD_DEFAULT_STYLE | wxDD_NEW_DIR_BUTTON)
            if dl.ShowModal() == wxID_OK:
                ref.gui_default_savedir_ctrl.SetValue(dl.GetPath())
          except:
            ref.parent.exception()

        def checkingcoloricon_set(self, ref = self):
          try:
            newcolor = ref.getColorFromUser(ref.panel,ref.checkingcolormenu)
            ref.setColorIcon(ref.checkingcolor_icon, ref.checkingcolor_iconptr, newcolor)
            ref.checkingcolormenu = newcolor
          except:
            ref.parent.exception()

        def downloadcoloricon_set(self, ref = self):
          try:
            newcolor = ref.getColorFromUser(ref.panel,ref.downloadcolormenu)
            ref.setColorIcon(ref.downloadcolor_icon, ref.downloadcolor_iconptr, newcolor)
            ref.downloadcolormenu = newcolor
          except:
            ref.parent.exception()

        def seedingcoloricon_set(self, ref = self):
          try:
            newcolor = ref.getColorFromUser(ref.panel,ref.seedingcolormenu)
            ref.setColorIcon(ref.seedingcolor_icon, ref.seedingcolor_iconptr, newcolor)
            ref.seedingcolormenu = newcolor
          except:
            ref.parent.exception()
            
        EVT_BUTTON(self.configMenuBox, saveButton.GetId(), saveConfigs)
        EVT_BUTTON(self.configMenuBox, cancelButton.GetId(), cancelConfigs)
        EVT_BUTTON(self.configMenuBox, defaultsButton.GetId(), setDefaults)
        EVT_BUTTON(self.configMenuBox, advancedButton.GetId(), self.advancedMenu)
        EVT_BUTTON(self.configMenuBox, savepathButton.GetId(), savepath_set)
        EVT_LEFT_DOWN(self.checkingcolor_iconptr, checkingcoloricon_set)
        EVT_LEFT_DOWN(self.downloadcolor_iconptr, downloadcoloricon_set)
        EVT_LEFT_DOWN(self.seedingcolor_iconptr, seedingcoloricon_set)

        self.configMenuBox.Show ()
        border.Fit(panel)
        self.configMenuBox.Fit()
      except:
        self.parent.exception()


    def advancedMenu(self, event = None):
      try:
        if len(self.advancedConfig) == 0:
            for key in ['ip', 'bind', 'min_peers', 'max_initiate', 'display_interval',
        'alloc_type', 'alloc_rate', 'max_files_open', 'max_connections', 'super_seeder',
        'ipv6_binds_v4', 'double_check', 'triple_check', 'lock_files', 'lock_while_reading']:
                self.advancedConfig[key] = self.configfileargs[key]

        if (self.advancedMenuBox is not None):
            try:
                self.advancedMenuBox.Close ()
            except wxPyDeadObjectError, e:
                self.advancedMenuBox = None

        self.advancedMenuBox = wxFrame(None, -1, 'BitTorrent Advanced Preferences', size = (1,1))
        if (sys.platform == 'win32'):
            self.advancedMenuBox.SetIcon(self.icon)

        panel = wxPanel(self.advancedMenuBox, -1)
#        self.panel = panel

        def StaticText(text, font = self.FONT, underline = False, color = None, panel = panel):
            x = wxStaticText(panel, -1, text, style = wxALIGN_LEFT)
            x.SetFont(wxFont(font, wxDEFAULT, wxNORMAL, wxNORMAL, underline))
            if color is not None:
                x.SetForegroundColour(color)
            return x

        colsizer = wxFlexGridSizer(cols = 1, hgap = 13, vgap = 13)
        warningtext = StaticText('CHANGE THESE SETTINGS AT YOUR OWN RISK', self.FONT+4, True, 'Red')
        colsizer.Add(warningtext, 1, wxALIGN_CENTER)

        self.ip_data = wxTextCtrl(parent = panel, id = -1, 
                    value = self.advancedConfig['ip'],
                    size = (self.FONT*13, int(self.FONT*2.2)), style = wxTE_PROCESS_TAB)
        self.ip_data.SetFont(self.default_font)
        
        self.bind_data = wxTextCtrl(parent = panel, id = -1, 
                    value = self.advancedConfig['bind'],
                    size = (self.FONT*13, int(self.FONT*2.2)), style = wxTE_PROCESS_TAB)
        self.bind_data.SetFont(self.default_font)
        
        if sys.version_info >= (2,3) and socket.has_ipv6:
            self.ipv6bindsv4_data=wxChoice(panel, -1,
                             choices = ['separate sockets', 'single socket'])
            self.ipv6bindsv4_data.SetFont(self.default_font)
            self.ipv6bindsv4_data.SetSelection(self.advancedConfig['ipv6_binds_v4'])

        self.minpeers_data = wxSpinCtrl(panel, -1, '', (-1,-1), (self.FONT*7, -1))
        self.minpeers_data.SetFont(self.default_font)
        self.minpeers_data.SetRange(10,100)
        self.minpeers_data.SetValue(self.advancedConfig['min_peers'])
        # max_initiate = 2*minpeers

        self.displayinterval_data = wxSpinCtrl(panel, -1, '', (-1,-1), (self.FONT*7, -1))
        self.displayinterval_data.SetFont(self.default_font)
        self.displayinterval_data.SetRange(100,2000)
        self.displayinterval_data.SetValue(int(self.advancedConfig['display_interval']*1000))

        self.alloctype_data=wxChoice(panel, -1,
                         choices = ['normal', 'background', 'pre-allocate', 'sparse'])
        self.alloctype_data.SetFont(self.default_font)
        self.alloctype_data.SetStringSelection(self.advancedConfig['alloc_type'])

        self.allocrate_data = wxSpinCtrl(panel, -1, '', (-1,-1), (self.FONT*7,-1))
        self.allocrate_data.SetFont(self.default_font)
        self.allocrate_data.SetRange(1,100)
        self.allocrate_data.SetValue(int(self.advancedConfig['alloc_rate']))

        self.locking_data=wxChoice(panel, -1,
                           choices = ['no locking', 'lock while writing', 'lock always'])
        self.locking_data.SetFont(self.default_font)
        if self.advancedConfig['lock_files']:
            if self.advancedConfig['lock_while_reading']:
                self.locking_data.SetSelection(2)
            else:
                self.locking_data.SetSelection(1)
        else:
            self.locking_data.SetSelection(0)

        self.doublecheck_data=wxChoice(panel, -1,
                           choices = ['no extra checking', 'double-check', 'triple-check'])
        self.doublecheck_data.SetFont(self.default_font)
        if self.advancedConfig['double_check']:
            if self.advancedConfig['triple_check']:
                self.doublecheck_data.SetSelection(2)
            else:
                self.doublecheck_data.SetSelection(1)
        else:
            self.doublecheck_data.SetSelection(0)

        self.maxfilesopen_choices = ['50', '100', '200', 'no limit ']
        self.maxfilesopen_data=wxChoice(panel, -1, choices = self.maxfilesopen_choices)
        self.maxfilesopen_data.SetFont(self.default_font)
        setval = self.advancedConfig['max_files_open']
        if setval == 0:
            setval = 'no limit '
        else:
            setval = str(setval)
        if not setval in self.maxfilesopen_choices:
            setval = self.maxfilesopen_choices[0]
        self.maxfilesopen_data.SetStringSelection(setval)

        self.maxconnections_choices = ['no limit ', '20', '30', '40', '60', '100', '200']
        self.maxconnections_data=wxChoice(panel, -1, choices = self.maxconnections_choices)
        self.maxconnections_data.SetFont(self.default_font)
        setval = self.advancedConfig['max_connections']
        if setval == 0:
            setval = 'no limit '
        else:
            setval = str(setval)
        if not setval in self.maxconnections_choices:
            setval = self.maxconnections_choices[0]
        self.maxconnections_data.SetStringSelection(setval)

        self.superseeder_data=wxChoice(panel, -1,
                         choices = ['normal', 'super-seed'])
        self.superseeder_data.SetFont(self.default_font)
        self.superseeder_data.SetSelection(self.advancedConfig['super_seeder'])

        twocolsizer = wxFlexGridSizer(cols = 2, hgap = 20)
        datasizer = wxFlexGridSizer(cols = 2, vgap = 2)
        datasizer.Add(StaticText('Local IP: '), 1, wxALIGN_CENTER_VERTICAL)
        datasizer.Add(self.ip_data)
        datasizer.Add(StaticText('IP to bind to: '), 1, wxALIGN_CENTER_VERTICAL)
        datasizer.Add(self.bind_data)
        if sys.version_info >= (2,3) and socket.has_ipv6:
            datasizer.Add(StaticText('IPv6 socket handling: '), 1, wxALIGN_CENTER_VERTICAL)
            datasizer.Add(self.ipv6bindsv4_data)
        datasizer.Add(StaticText('Minimum number of peers: '), 1, wxALIGN_CENTER_VERTICAL)
        datasizer.Add(self.minpeers_data)
        datasizer.Add(StaticText('Display interval (ms): '), 1, wxALIGN_CENTER_VERTICAL)
        datasizer.Add(self.displayinterval_data)
        datasizer.Add(StaticText('Disk allocation type:'), 1, wxALIGN_CENTER_VERTICAL)
        datasizer.Add(self.alloctype_data)
        datasizer.Add(StaticText('Allocation rate (MiB/s):'), 1, wxALIGN_CENTER_VERTICAL)
        datasizer.Add(self.allocrate_data)
        datasizer.Add(StaticText('File locking:'), 1, wxALIGN_CENTER_VERTICAL)
        datasizer.Add(self.locking_data)
        datasizer.Add(StaticText('Extra data checking:'), 1, wxALIGN_CENTER_VERTICAL)
        datasizer.Add(self.doublecheck_data)
        datasizer.Add(StaticText('Max files open:'), 1, wxALIGN_CENTER_VERTICAL)
        datasizer.Add(self.maxfilesopen_data)
        datasizer.Add(StaticText('Max peer connections:'), 1, wxALIGN_CENTER_VERTICAL)
        datasizer.Add(self.maxconnections_data)
        datasizer.Add(StaticText('Default seeding mode:'), 1, wxALIGN_CENTER_VERTICAL)
        datasizer.Add(self.superseeder_data)
        
        twocolsizer.Add(datasizer)

        infosizer = wxFlexGridSizer(cols = 1)
        self.hinttext = StaticText('', self.FONT, False, 'Blue')
        infosizer.Add(self.hinttext, 1, wxALIGN_LEFT|wxALIGN_CENTER_VERTICAL)
        infosizer.SetMinSize((180,100))
        twocolsizer.Add(infosizer, 1, wxEXPAND)

        colsizer.Add(twocolsizer)

        savesizer = wxGridSizer(cols = 3, hgap = 20)
        okButton = wxButton(panel, -1, 'OK')
#        okButton.SetFont(self.default_font)
        savesizer.Add(okButton, 0, wxALIGN_CENTER)

        cancelButton = wxButton(panel, -1, 'Cancel')
#        cancelButton.SetFont(self.default_font)
        savesizer.Add(cancelButton, 0, wxALIGN_CENTER)

        defaultsButton = wxButton(panel, -1, 'Revert to Defaults')
#        defaultsButton.SetFont(self.default_font)
        savesizer.Add(defaultsButton, 0, wxALIGN_CENTER)
        colsizer.Add(savesizer, 1, wxALIGN_CENTER)

        resizewarningtext=StaticText('None of these settings will take effect until the next time you start BitTorrent', self.FONT-2)
        colsizer.Add(resizewarningtext, 1, wxALIGN_CENTER)

        border = wxBoxSizer(wxHORIZONTAL)
        border.Add(colsizer, 1, wxEXPAND | wxALL, 4)
        
        panel.SetSizer(border)
        panel.SetAutoLayout(True)

        def setDefaults(self, ref = self):
          try:
            ref.ip_data.SetValue(ref.defaults.get('ip'))
            ref.bind_data.SetValue(ref.defaults.get('bind'))
            if sys.version_info >= (2,3) and socket.has_ipv6:
                ref.ipv6bindsv4_data.SetSelection(ref.defaults.get('ipv6_binds_v4'))
            ref.minpeers_data.SetValue(ref.defaults.get('min_peers'))
            ref.displayinterval_data.SetValue(int(ref.defaults.get('display_interval')*1000))
            ref.alloctype_data.SetStringSelection(ref.defaults.get('alloc_type'))
            ref.allocrate_data.SetValue(int(ref.defaults.get('alloc_rate')))
            if ref.defaults.get('lock_files'):
                if ref.defaults.get('lock_while_reading'):
                    ref.locking_data.SetSelection(2)
                else:
                    ref.locking_data.SetSelection(1)
            else:
                ref.locking_data.SetSelection(0)
            if ref.defaults.get('double_check'):
                if ref.defaults.get('triple_check'):
                    ref.doublecheck_data.SetSelection(2)
                else:
                    ref.doublecheck_data.SetSelection(1)
            else:
                ref.doublecheck_data.SetSelection(0)
            setval = ref.defaults.get('max_files_open')
            if setval == 0:
                setval = 'no limit '
            else:
                setval = str(setval)
            if not setval in ref.maxfilesopen_choices:
                setval = ref.maxfilesopen_choices[0]
            ref.maxfilesopen_data.SetStringSelection(setval)
            setval = ref.defaults.get('max_connections')
            if setval == 0:
                setval = 'no limit '
            else:
                setval = str(setval)
            if not setval in ref.maxconnections_choices:
                setval = ref.maxconnections_choices[0]
            ref.maxconnections_data.SetStringSelection(setval)
            ref.superseeder_data.SetSelection(int(ref.defaults.get('super_seeder')))
          except:
            ref.parent.exception()

        def saveConfigs(self, ref = self):
          try:
            ref.advancedConfig['ip'] = ref.ip_data.GetValue()
            ref.advancedConfig['bind'] = ref.bind_data.GetValue()
            if sys.version_info >= (2,3) and socket.has_ipv6:
                ref.advancedConfig['ipv6_binds_v4'] = ref.ipv6bindsv4_data.GetSelection()
            ref.advancedConfig['min_peers'] = ref.minpeers_data.GetValue()
            ref.advancedConfig['display_interval'] = float(ref.displayinterval_data.GetValue())/1000
            ref.advancedConfig['alloc_type'] = ref.alloctype_data.GetStringSelection()
            ref.advancedConfig['alloc_rate'] = float(ref.allocrate_data.GetValue())
            ref.advancedConfig['lock_files'] = int(ref.locking_data.GetSelection() >= 1)
            ref.advancedConfig['lock_while_reading'] = int(ref.locking_data.GetSelection() > 1)
            ref.advancedConfig['double_check'] = int(ref.doublecheck_data.GetSelection() >= 1)
            ref.advancedConfig['triple_check'] = int(ref.doublecheck_data.GetSelection() > 1)
            try:
                ref.advancedConfig['max_files_open'] = int(ref.maxfilesopen_data.GetStringSelection())
            except:       # if it ain't a number, it must be "no limit"
                ref.advancedConfig['max_files_open'] = 0
            try:
                ref.advancedConfig['max_connections'] = int(ref.maxconnections_data.GetStringSelection())
                ref.advancedConfig['max_initiate'] = min(
                    2*ref.advancedConfig['min_peers'], ref.advancedConfig['max_connections'])
            except:       # if it ain't a number, it must be "no limit"
                ref.advancedConfig['max_connections'] = 0
                ref.advancedConfig['max_initiate'] = 2*ref.advancedConfig['min_peers']
            ref.advancedConfig['super_seeder']=int(ref.superseeder_data.GetSelection())
            ref.advancedMenuBox.Close()
          except:
            ref.parent.exception()

        def cancelConfigs(self, ref = self):            
            ref.advancedMenuBox.Close()

        def ip_hint(self, ref = self):
            ref.hinttext.SetLabel('\n\n\nThe IP reported to the tracker.\n' +
                                  'unless the tracker is on the\n' +
                                  'same intranet as this client,\n' +
                                  'the tracker will autodetect the\n' +
                                  "client's IP and ignore this\n" +
                                  "value.")

        def bind_hint(self, ref = self):
            ref.hinttext.SetLabel('\n\n\nThe IP the client will bind to.\n' +
                                  'Only useful if your machine is\n' +
                                  'directly handling multiple IPs.\n' +
                                  "If you don't know what this is,\n" +
                                  "leave it blank.")

        def ipv6bindsv4_hint(self, ref = self):
            ref.hinttext.SetLabel('\n\n\nCertain operating systems will\n' +
                                  'open IPv4 protocol connections on\n' +
                                  'an IPv6 socket; others require you\n' +
                                  "to open two sockets on the same\n" +
                                  "port, one IPv4 and one IPv6.")

        def minpeers_hint(self, ref = self):
            ref.hinttext.SetLabel('\n\n\nThe minimum number of peers the\n' +
                                  'client tries to stay connected\n' +
                                  'with.  Do not set this higher\n' +
                                  'unless you have a very fast\n' +
                                  "connection and a lot of system\n" +
                                  "resources.")

        def displayinterval_hint(self, ref = self):
            ref.hinttext.SetLabel('\n\n\nHow often to update the\n' +
                                  'graphical display, in 1/1000s\n' +
                                  'of a second. Setting this too low\n' +
                                  "will strain your computer's\n" +
                                  "processor and video access.")

        def alloctype_hint(self, ref = self):
            ref.hinttext.SetLabel('\n\nHow to allocate disk space.\n' +
                                  'normal allocates space as data is\n' +
                                  'received, background also adds\n' +
                                  "space in the background, pre-\n" +
                                  "allocate reserves up front, and\n" +
                                  'sparse is only for filesystems\n' +
                                  'that support it by default.')

        def allocrate_hint(self, ref = self):
            ref.hinttext.SetLabel('\n\n\nAt what rate to allocate disk\n' +
                                  'space when allocating in the\n' +
                                  'background.  Set this too high on a\n' +
                                  "slow filesystem and your download\n" +
                                  "will slow to a crawl.")

        def locking_hint(self, ref = self):
            ref.hinttext.SetLabel('\n\n\n\nFile locking prevents other\n' +
                                  'programs (including other instances\n' +
                                  'of BitTorrent) from accessing files\n' +
                                  "you are downloading.")

        def doublecheck_hint(self, ref = self):
            ref.hinttext.SetLabel('\n\n\nHow much extra checking to do\n' +
                                  'making sure no data is corrupted.\n' +
                                  'Double-check mode uses more CPU,\n' +
                                  "while triple-check mode increases\n" +
                                  "disk accesses.")

        def maxfilesopen_hint(self, ref = self):
            ref.hinttext.SetLabel('\n\n\nThe maximum number of files to\n' +
                                  'keep open at the same time.  Zero\n' +
                                  'means no limit.  Please note that\n' +
                                  "if this option is in effect,\n" +
                                  "files are not guaranteed to be\n" +
                                  "locked.")

        def maxconnections_hint(self, ref = self):
            ref.hinttext.SetLabel('\n\nSome operating systems, most\n' +
                                  'notably Windows 9x/ME combined\n' +
                                  'with certain network drivers,\n' +
                                  "cannot handle more than a certain\n" +
                                  "number of open ports.  If the\n" +
                                  "client freezes, try setting this\n" +
                                  "to 60 or below.")

        def superseeder_hint(self, ref = self):
            ref.hinttext.SetLabel('\n\nThe "super-seed" method allows\n' +
                                  'a single source to more efficiently\n' +
                                  'seed a large torrent, but is not\n' +
                                  "necessary in a well-seeded torrent,\n" +
                                  "and causes problems with statistics.\n" +
                                  "Unless you routinely seed torrents\n" +
                                  "you can enable this by selecting\n" +
                                  '"SUPER-SEED" for connection type.\n' +
                                  '(once enabled it does not turn off.)')

        EVT_BUTTON(self.advancedMenuBox, okButton.GetId(), saveConfigs)
        EVT_BUTTON(self.advancedMenuBox, cancelButton.GetId(), cancelConfigs)
        EVT_BUTTON(self.advancedMenuBox, defaultsButton.GetId(), setDefaults)
        EVT_ENTER_WINDOW(self.ip_data, ip_hint)
        EVT_ENTER_WINDOW(self.bind_data, bind_hint)
        if sys.version_info >= (2,3) and socket.has_ipv6:
            EVT_ENTER_WINDOW(self.ipv6bindsv4_data, ipv6bindsv4_hint)
        EVT_ENTER_WINDOW(self.minpeers_data, minpeers_hint)
        EVT_ENTER_WINDOW(self.displayinterval_data, displayinterval_hint)
        EVT_ENTER_WINDOW(self.alloctype_data, alloctype_hint)
        EVT_ENTER_WINDOW(self.allocrate_data, allocrate_hint)
        EVT_ENTER_WINDOW(self.locking_data, locking_hint)
        EVT_ENTER_WINDOW(self.doublecheck_data, doublecheck_hint)
        EVT_ENTER_WINDOW(self.maxfilesopen_data, maxfilesopen_hint)
        EVT_ENTER_WINDOW(self.maxconnections_data, maxconnections_hint)
        EVT_ENTER_WINDOW(self.superseeder_data, superseeder_hint)

        self.advancedMenuBox.Show ()
        border.Fit(panel)
        self.advancedMenuBox.Fit()
      except:
        self.parent.exception()


    def CloseAdvanced(self):
        if self.advancedMenuBox is not None:
            try:
                self.advancedMenuBox.Close ()
            except wxPyDeadObjectError, e:
                self.advancedMenuBox = None

    def Close(self):
        self.CloseAdvanced()
        if self.configMenuBox is not None:
            try:
                self.configMenuBox.Close ()
            except wxPyDeadObjectError, e:
                self.configMenuBox = None
