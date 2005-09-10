# Written by Bram Cohen, Myers Carpenter and John Hoffman
# Modifications by various people
# see LICENSE.txt for license information

from BitTornado import PSYCO
if PSYCO.psyco:
    try:
        import psyco.__version__
        assert psyco.__version__ >= 0x010100f0
    except:
        pass

from wxPython.wx import *

from common import FONT, ICON, _StaticText
from exception import exception
from threading import Thread
from webbrowser import open_new
import sys
from BitTornado import version

try:
    True
except:
    True = 1
    False = 0


class CreditsBox:

    def __init__(self):
        self.frame = wxFrame(None, -1, 'Credits', size = (1,1))
        if ICON():
            self.frame.SetIcon(ICON())

        panel = wxPanel(self.creditsBox, -1)        

        StaticText = _StaticText(panel)

        colSizer = wxFlexGridSizer(cols = 1, vgap = 3)

        titleSizer = wxBoxSizer(wxHORIZONTAL)
        aboutTitle = StaticText('Credits', FONT()+4)
        titleSizer.Add (aboutTitle)
        colSizer.Add (titleSizer)
        colSizer.Add (StaticText(
          'The following people have all helped with this\n' +
          'version of BitTorrent in some way (in no particular order) -\n'));
        creditSizer = wxFlexGridSizer(cols = 3)
        creditSizer.Add(StaticText(
          'Bill Bumgarner\n' +
          'David Creswick\n' +
          'Andrew Loewenstern\n' +
          'Ross Cohen\n' +
          'Jeremy Avnet\n' +
          'Greg Broiles\n' +
          'Barry Cohen\n' +
          'Bram Cohen\n' +
          'sayke\n' +
          'Steve Jenson\n' +
          'Myers Carpenter\n' +
          'Francis Crick\n' +
          'Petru Paler\n' +
          'Jeff Darcy\n' +
          'John Gilmore\n' +
          'Xavier Bassery\n' +
          'Pav Lucistnik'))
        creditSizer.Add(StaticText('  '))
        creditSizer.Add(StaticText(
          'Yann Vernier\n' +
          'Pat Mahoney\n' +
          'Boris Zbarsky\n' +
          'Eric Tiedemann\n' +
          'Henry "Pi" James\n' +
          'Loring Holden\n' +
          'Robert Stone\n' +
          'Michael Janssen\n' +
          'Eike Frost\n' +
          'Andrew Todd\n' +
          'otaku\n' +
          'Edward Keyes\n' +
          'John Hoffman\n' +
          'Uoti Urpala\n' +
          'Jon Wolf\n' +
          'Christoph Hohmann'))
        colSizer.Add (creditSizer, flag = wxALIGN_CENTER_HORIZONTAL)
        okButton = wxButton(panel, -1, 'Ok')
#        okButton.SetFont(self.default_font)
        colSizer.Add(okButton, 0, wxALIGN_RIGHT)
        colSizer.AddGrowableCol(0)

        border = wxBoxSizer(wxHORIZONTAL)
        border.Add(colSizer, 1, wxEXPAND | wxALL, 4)
        panel.SetSizer(border)
        panel.SetAutoLayout(True)

        EVT_BUTTON(self.frame, okButton.GetId(), self.close)
        EVT_CLOSE(self.frame, self.close)

        self.frame.Show()
        border.Fit(panel)
        self.frame.Fit()

    def close(self, evt=None):
        if self.frame:
            self.frame.Destroy()
            self.frame = None


class AboutBox:

    def __init__(self):
        self.frame = wxFrame(None, -1, 'About BitTornado', size = (1,1))
        if ICON():
            self.frame.SetIcon(ICON())

        panel = wxPanel(self.frame, -1)

        StaticText = _StaticText(panel)

        colSizer = wxFlexGridSizer(cols = 1, vgap = 3)

        titleSizer = wxBoxSizer(wxHORIZONTAL)
        aboutTitle = StaticText('BitTorrent ' + version + '  ', self.FONT+4)
        titleSizer.Add (aboutTitle)
        linkDonate = StaticText('Donate to Bram', self.FONT, True, 'Blue')
        titleSizer.Add (linkDonate, 1, wxALIGN_BOTTOM&wxEXPAND)
        colSizer.Add(titleSizer, 0, wxEXPAND)

        colSizer.Add(StaticText('created by Bram Cohen, Copyright 2001-2003,'))
        colSizer.Add(StaticText('experimental version maintained by John Hoffman 2003'))
        colSizer.Add(StaticText('modified from experimental version by Eike Frost 2003'))
        credits = StaticText('full credits\n', self.FONT, True, 'Blue')
        colSizer.Add(credits);

        si = ( 'exact Version String: ' + version + '\n' +
               'Python version: ' + sys.version + '\n' +
               'wxWindows version: ' + wxVERSION_STRING + '\n' )
        try:
            si += 'Psyco version: ' + hex(psyco.__version__)[2:] + '\n'
        except:
            pass
        colSizer.Add(StaticText(si))

        babble1 = StaticText(
         'This is an experimental, unofficial build of BitTorrent.\n' +
         'It is Free Software under an MIT-Style license.')
        babble2 = StaticText('BitTorrent Homepage (link)', self.FONT, True, 'Blue')
        babble3 = StaticText("TheSHAD0W's Client Homepage (link)", self.FONT, True, 'Blue')
        babble4 = StaticText("Eike Frost's Client Homepage (link)", self.FONT, True, 'Blue')
        babble6 = StaticText('License Terms (link)', self.FONT, True, 'Blue')
        colSizer.Add (babble1)
        colSizer.Add (babble2)
        colSizer.Add (babble3)
        colSizer.Add (babble4)
        colSizer.Add (babble6)

        okButton = wxButton(panel, -1, 'Ok')
#        okButton.SetFont(self.default_font)
        colSizer.Add(okButton, 0, wxALIGN_RIGHT)
        colSizer.AddGrowableCol(0)

        border = wxBoxSizer(wxHORIZONTAL)
        border.Add(colSizer, 1, wxEXPAND | wxALL, 4)
        panel.SetSizer(border)
        panel.SetAutoLayout(True)

        EVT_LEFT_DOWN(linkDonate, self.donatelink)
        EVT_LEFT_DOWN(babble2, self.aboutlink)
        EVT_LEFT_DOWN(babble3, self.shadlink)
        EVT_LEFT_DOWN(babble4, self.explink)
        EVT_LEFT_DOWN(babble6, self.licenselink)

        self.credits = None
        EVT_LEFT_DOWN(credits, self.openCredits)
        
        EVT_BUTTON(self.frame, okButton.GetId(), self._close)
        EVT_CLOSE(self.frame, self.close)

        self.frame.Show ()
        border.Fit(panel)
        self.frame.Fit()

    def donatelink(self, evt):
        Thread(target = open_new('https://www.paypal.com/cgi-bin/webscr?cmd=_xclick&business=bram@bitconjurer.org&item_name=BitTorrent&amount=5.00&submit=donate')).start()
    def aboutlink(self, evt):
        Thread(target = open_new('http://bitconjurer.org/BitTorrent/')).start()
    def shadlink(self, evt):
        Thread(target = open_new('http://www.bittornado.com/')).start()
    def explink(self, evt):
        Thread(target = open_new('http://ei.kefro.st/projects/btclient/')).start()
    def licenselink(self, evt):
        Thread(target = open_new('http://ei.kefro.st/projects/btclient/LICENSE.TXT')).start()

    def openCredits(self, evt=None):
        try:
            if self.credits:
                self.credits.close()
            self.credits = CreditsBox()
        except:
            exception()

    def close(self, evt=None):
        if self.frame:
            self.frame.Destroy()
            self.frame = None
        if self.credits:
            self.credits.close()
            self.credits = None