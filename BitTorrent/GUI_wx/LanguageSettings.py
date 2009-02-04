# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# written by Matt Chisholm

import wx

from BTL.defer import ThreadedDeferred
from BTL.language import languages, language_names
from BTL.platform import app_name
from BitTorrent.platform import read_language_file, write_language_file

from BitTorrent.GUI_wx import SPACING, VSizer, gui_wrap, text_wrappable


error_color = wx.Colour(192,0,0)

class LanguageSettings(wx.Panel):

    def __init__(self, parent, *a, **k):
        wx.Panel.__init__(self, parent, *a, **k)
        self.sizer = VSizer()
        self.SetSizer(self.sizer)
        if 'errback' in k:
            self.errback = k.pop('errback')
        else:
            self.errback = self.set_language_failed

        # widgets
        self.box = wx.StaticBox(self, label="Translate %s into:" % app_name)

        self.language_names = ["System default",] + [language_names[l] for l in languages]
        languages.insert(0, '')
        self.languages = languages
        self.choice = wx.Choice(self, choices=self.language_names)
        self.Bind(wx.EVT_CHOICE, self.set_language, self.choice)

        restart = wx.StaticText(self, -1,
                                "You must restart %s for the\nlanguage "
                                "setting to take effect." % app_name)

        self.bottom_error = wx.StaticText(self, -1, '')
        self.bottom_error.SetForegroundColour(error_color)

        # sizers
        self.box_sizer = wx.StaticBoxSizer(self.box, wx.VERTICAL)

        # set menu selection and warning item if necessary
        self.valid = True
        lang = read_language_file()
        if lang is not None:
            try:
                i = self.languages.index(lang)
                self.choice.SetSelection(i)
            except ValueError, e:
                self.top_error = wx.StaticText(self, -1,
                                     "This version of %s does not \nsupport the language '%s'."%(app_name,lang),)
                self.top_error.SetForegroundColour(error_color)

                self.box_sizer.Add(self.top_error, flag=wx.TOP|wx.LEFT|wx.RIGHT, border=SPACING)
                # BUG add menu separator
                # BUG change color of extra menu item
                self.choice.Append(lang)
                self.choice.SetSelection(len(self.languages))
                self.valid = False
        else:
            self.choice.SetSelection(0)

        # other sizers
        self.box_sizer.Add(self.choice, flag=wx.GROW|wx.ALL, border=SPACING)
        self.box_sizer.Add(restart, flag=wx.BOTTOM|wx.LEFT|wx.RIGHT, border=SPACING)
        self.box_sizer.Add(self.bottom_error, flag=wx.BOTTOM|wx.LEFT|wx.RIGHT, border=SPACING)

        # clear out bottom error
        self.clear_error()

        self.sizer.AddFirst(self.box_sizer, flag=wx.GROW)
        self.sizer.Fit(self)


    def set_language(self, *a):
        index = self.choice.GetSelection()
        if index >= len(self.languages):
            return
        l = self.languages[index]
        if not self.valid:
            self.choice.Delete(len(self.languages))
            self.choice.SetSelection(index)
            self.valid = True
            self.box_sizer.Detach(0)
            self.top_error.Destroy()
            self.box_sizer.Layout()
            self.sizer.Layout()

        d = ThreadedDeferred(gui_wrap, write_language_file, l)
        d.addErrback(lambda e: self.set_language_failed(e, l))
        d.addCallback(lambda r: self.language_was_set())


    def language_was_set(self, *a):
        self.clear_error()
        wx.MessageBox("You must restart %s for the language "
                      "setting to take effect." % app_name,
                      "%s translation" % app_name,
                      style=wx.ICON_INFORMATION)

    def clear_error(self):
        index = self.box_sizer.GetItem(self.bottom_error)
        if index:
           self.box_sizer.Detach(self.bottom_error)
        self.bottom_error.SetLabel('')

        self.refit()

    def set_error(self, errstr):
        index = self.box_sizer.GetItem(self.bottom_error)
        if not index:
            self.box_sizer.Add(self.bottom_error, flag=wx.BOTTOM|wx.LEFT|wx.RIGHT, border=SPACING)
        self.bottom_error.SetLabel(errstr)
        if text_wrappable: self.bottom_error.Wrap(250)

        self.refit()


    def set_language_failed(self, e, l):
        errstr = 'Could not find translation for language "%s"' % l
        wx.the_app.logger.error(errstr, exc_info=e)
        errstr = errstr + '\n%s: %s' % (str(e[0]), unicode(e[1].args[0]))
        self.set_error(errstr)


    def refit(self):
        self.box_sizer.Layout()
        self.sizer.Layout()
        #self.sizer.Fit(self)
        self.GetParent().Fit()
