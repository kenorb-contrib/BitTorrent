# Written by John Hoffman
# see LICENSE.txt for license information


from wxPython.wx import *
from BitTornado.ConfigDir import ConfigDir
from BitTornado.download_bt1 import defaults

if (sys.platform == 'win32'):
    _FONT = 9
else:
    _FONT = 10
def FONT(newval = None):
    global _FONT
    if newval:
        _FONT = newval
    return _FONT


_ICON = None
def ICON(newval = None):
    global _ICON
    if newval:
        _ICON = newval
    return _ICON


class _StaticTextClass:
    def __init__(self, panel, style):
        self.panel = panel
        self.style = style

    def call(text, font = 0, underline = False, color = None):
        x = wxStaticText(self.panel, -1, text, style = self.style)
        x.SetFont(wxFont(_FONT+font, wxDEFAULT, wxNORMAL, wxNORMAL, underline))
        if color is not None:
            x.SetForegroundColour(color)
        return x

def _StaticText(panel, style = wxALIGN_LEFT):
    return _StaticTextClass(panel, style).call


CONFIGDIR = ConfigDir('gui')
_defaultsToIgnore = ['responsefile', 'url', 'priority']
CONFIGDIR.setDefaults(defaults,_defaultsToIgnore)
ICONDIR = CONFIGDIR.getIconDir()