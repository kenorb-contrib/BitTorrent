# Written by John Hoffman
# see LICENSE.txt for license information

from BitTornado import PSYCO
if PSYCO.psyco:
    try:
        import psyco.__version__
        assert psyco.__version__ >= 0x010100f0
    except:
        pass

from wxPython.wx import *
from common import FONT
from cStringIO import StringIO
from traceback import print_exc
from BitTornado import version, report_email
import sys

try:
    True
except:
    True = 1
    False = 0


class ExceptionClass:

    def __init__(self, invoker):
        self.hit = False
        self.invokeLater = None
        self.config = None
        self.bgalloc_flag = None

    def set_invoker(self, invoker):        
        self.invokeLater = invoker

    def set_config(self, config):
        self.config = config

    def set_bgalloc_flag(self, flagfunc):
        self.bgalloc_flag = flagfunc

    def exception(self, err):
        if self.invokeLater:
            self.invokeLater(self.errorwindow,[err])
        else:
            self.errorwindow(err)
            sleep(3600*24)

    def errorwindow(self, err):
        if self.hit:
            return
        self.hit = True
        w = wxFrame(None, -1, 'BITTORRENT ERROR', size = (1,1))
        panel = wxPanel(w, -1)
        sizer = wxFlexGridSizer(cols = 1)

        t = ( 'BitTorrent ' + version + '\n' +
              'OS: ' + sys.platform + '\n' +
              'Python version: ' + sys.version + '\n' +
              'wxWindows version: ' + wxVERSION_STRING + '\n' )

        try:
            t += 'Psyco version: ' + hex(psyco.__version__)[2:] + '\n'
        except:
            pass
        if self.config:
            t += 'Allocation method: ' + self.config['alloc_type']
            if self.bgalloc_flag:
                if self.bgalloc_flag():
                    t += '*'
            t += '\n'

        sizer.Add(wxTextCtrl(panel, -1, t + '\n' + err,
                            size = (500,300), style = wxTE_READONLY|wxTE_MULTILINE))

        sizer.Add(wxStaticText(panel, -1,
                '\nHelp us iron out the bugs in the engine!'))
        linkMail = wxStaticText(panel, -1,
            'Please report this error to '+report_email)
        linkMail.SetFont(wxFont(FONT(), wxDEFAULT, wxNORMAL, wxNORMAL, True))
        linkMail.SetForegroundColour('Blue')
        sizer.Add(linkMail)

        def maillink(self):
            Thread(target = open_new("mailto:" + report_email
                                     + "?subject=autobugreport")).start()
        EVT_LEFT_DOWN(linkMail, maillink)

        border = wxBoxSizer(wxHORIZONTAL)
        border.Add(sizer, 1, wxEXPAND | wxALL, 4)

        panel.SetSizer(border)
        panel.SetAutoLayout(True)

        w.Show()
        border.Fit(panel)
        w.Fit()
        self._errorwindow = w


_exception_object = ExceptionClass()

set_invoker = _exception_object.set_invoker
set_config = _exception_object.set_config
set_bgalloc_flag = _exception_object.set_bgalloc_flag

def exception():    
    data = StringIO()
    print_exc(file = data)
    err = data.getvalue
    print err
    _exception_object.exception(err)
