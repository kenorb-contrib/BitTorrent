# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# written by Matt Chisholm and Greg Hazel

from __future__ import division

import os
import sys

try:
    import wxversion
except:
    pass
else:
    # doesn't work in py2exe
    try:
        wxversion.select('2.6')
    except:
        pass
    
import wx
import wx.grid
import wxPython
from BTL.translation import _

from BitTorrent.platform import image_root
import BTL.stackthreading as threading
from BTL.defer import ThreadedDeferred
import bisect

vs = wxPython.__version__
min_wxpython = "2.6"
assert vs >= min_wxpython, _("wxPython version %s or newer required") % min_wxpython
assert 'unicode' in wx.PlatformInfo, _("The Unicode versions of wx and wxPython are required")

text_wrappable = wx.__version__[4] >= '2'

profile = False
if profile:
    from BTL.profile import Profiler, Stats
    prof_file_name = 'ui.mainloop.prof'

def gui_wrap(_f, *args, **kwargs):
    wx.the_app.CallAfter(_f, *args, **kwargs)

SPACING = 8  # default pixels between widgets
PORT_RANGE = 5 # how many ports to try

WILDCARD = _("Torrent files (*.torrent)|*.torrent|"\
             "All files (*.*)|*.*")

def get_theme_root(theme_name):
    for t in (theme_name, 'default'):
        td = os.path.join(image_root, 'themes', t)
        if os.path.exists(td):
            return td


def list_themes():
    def _lt():
        themes = []
        tr = os.path.join(image_root, 'themes')
        ld = os.listdir(tr)
        for d in ld:
            if os.path.isdir(os.path.join(tr, d)):
                themes.append(d)
        return themes
    df = ThreadedDeferred(None, _lt, daemon=True)
    df.start()
    return df


class ImageLibrary(object):

    def __init__(self, image_root):
        self.image_root = image_root
        self._data = {}

    def resolve_filename(self, key, size=None, base=None, ext='.png'):
        if base is None:
            base = self.image_root

        name = os.path.join(base, *key)
        name = os.path.abspath(name)

        if size is not None:
            sized_name = name + '_%d' % size + ext
            if os.path.exists(sized_name):
                name = sized_name
            else:
                name += ext
        else:
            name += ext
        name = os.path.abspath(name)

        if not os.path.exists(name):
            raise IOError(2, "No such file or directory: %r" % name)

        return name        
        

    def get(self, key, size=None, base=None, ext='.png'):
        if self._data.has_key((key, size)):
            return self._data[(key, size)]

        name = self.resolve_filename(key, size, base, ext)

        i = wx.Image(name, wx.BITMAP_TYPE_PNG)
        if not i.Ok():
            raise Exception("The image is not valid: %r" % name)

        self._data[(key, size)] = i

        return i



class ThemeLibrary(ImageLibrary):

    def __init__(self, themes_root, theme_name):
        self.themes_root = themes_root
        for t in (theme_name, 'default'):
            image_root = os.path.join(themes_root, 'themes', t)
            if os.path.exists(image_root):
                self.theme_name = t
                ImageLibrary.__init__(self, image_root)
                return
        raise IOError("default theme path must exist: %r" % image_root)

    def resolve_filename(self, key, size=None, base=None, ext='.png'):
        try:
            return ImageLibrary.resolve_filename(self, key, size, base, ext)
        except Exception, e:
            default_base = os.path.join(self.themes_root, 'themes', 'default')
            return ImageLibrary.resolve_filename(self, key, size,
                                                 base=default_base,
                                                 ext=ext)            


class XSizer(wx.BoxSizer):
    notfirst = wx.ALL
    direction = wx.HORIZONTAL

    def __init__(self, **k):
        wx.BoxSizer.__init__(self, self.direction)

    def Add(self, widget, proportion=0, flag=0, border=SPACING):
        flag = flag | self.notfirst
        wx.BoxSizer.Add(self, widget, proportion=proportion, flag=flag, border=border)

    def AddFirst(self, widget, proportion=0, flag=0, border=SPACING):
        flag = flag | wx.ALL
        self.Add(widget, proportion=proportion, flag=flag, border=border)



class VSizer(XSizer):
    notfirst = wx.BOTTOM|wx.LEFT|wx.RIGHT
    direction = wx.VERTICAL



class HSizer(XSizer):
    notfirst = wx.BOTTOM|wx.RIGHT|wx.TOP
    direction = wx.HORIZONTAL



class LabelValueFlexGridSizer(wx.FlexGridSizer):

    def __init__(self, parent_widget, *a, **k):
        wx.FlexGridSizer.__init__(self, *a, **k)
        self.parent_widget = parent_widget


    def add_label(self, label):
        h = ElectroStaticText(self.parent_widget, label=label)
        f = h.GetFont()
        f.SetWeight(wx.FONTWEIGHT_BOLD)
        h.SetFont(f)
        self.Add(h)


    def add_value(self, value, dotify=False):
        t = ElectroStaticText(self.parent_widget, id=wx.ID_ANY, label="",
                              dotify=dotify)
        self.Add(t, flag=wx.FIXED_MINSIZE|wx.GROW)
        t.SetLabel(value)
        return t


    def add_pair(self, label, value, dotify_value=False):
        self.add_label(label)
        t = self.add_value(value, dotify=dotify_value)
        return t



class ElectroStaticText(wx.StaticText):
    def __init__(self, parent, id=wx.ID_ANY, label='', dotify=False):
        wx.StaticText.__init__(self, parent, id, label)
        self.label = label
        self._string = self.label
        if dotify:
            self.Bind(wx.EVT_PAINT, self.DotifyOnPaint)

    def SetLabel(self, label):
        if label != self.label:
            self.label = label
            self._string = self.label
            wx.StaticText.SetLabel(self, self.label)

    def dotdotdot(self, label, width, max_width):

        label_reverse = label[::-1]

        beginning_values = self.dc.GetPartialTextExtents(label)
        ending_values = self.dc.GetPartialTextExtents(label_reverse)

        halfwidth = (width - self.dc.GetTextExtent("...")[0]) / 2

        beginning = bisect.bisect_left(beginning_values, halfwidth)
        ending = bisect.bisect_left(ending_values, halfwidth)

        if ending > 0:
            string = label[:beginning] + "..." + label[(0 - ending):]
        else:
            string = label[:beginning] + "..."

        return string

    def DotifyOnPaint(self, event):
        self.dc = wx.PaintDC(self)
        self.dc.SetFont(self.GetFont())

        width = self.GetSize().width
        str_width = self.dc.GetTextExtent(self._string)[0]
        max_width = self.dc.GetTextExtent(self.label)[0]

        if width >= max_width:
            self._string = self.label
        elif width != str_width:
            string = self.dotdotdot(self.label, width, max_width)
            self._string = string
        wx.StaticText.SetLabel(self, self._string)

        event.Skip()


class ElectroStaticBitmap(wx.Window):
    def __init__(self, parent, bitmap=None, *a, **k):
        wx.Window.__init__(self, parent, *a, **k)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.bitmap = None
        if bitmap:
            self.SetBitmap(bitmap)
        else:
            self.SetSize((0, 0))
            

    def SetBitmap(self, bitmap):
        self.bitmap = bitmap
        w, h = self.bitmap.GetWidth(), self.bitmap.GetHeight()
        self.SetSize((w, h))
        self.SetMinSize((w, h))


    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        if self.bitmap:
            dc.DrawBitmap(self.bitmap, 0, 0, True)


    def GetSize(self):
        if self.bitmap:
            return wx.Size(self.bitmap.GetWidth(), self.bitmap.GetHeight())
        else:
            return 0, 0



class Validator(wx.TextCtrl):
    valid_chars = '1234567890'
    minimum = None
    maximum = None
    cast = int

    def __init__(self, parent, option_name, config, setfunc):
        wx.TextCtrl.__init__(self, parent)
        self.option_name = option_name
        self.config      = config
        self.setfunc     = setfunc

        self.SetValue(str(config[option_name]))

        self.SetBestFittingSize((self.width,-1))

        self.Bind(wx.EVT_CHAR, self.text_inserted)
        self.Bind(wx.EVT_KILL_FOCUS, self.focus_out)

    def get_value(self):
        value = None
        try:
            value = self.cast(self.GetValue())
        except ValueError:
            pass
        return value

    def set_value(self, value):
        self.SetValue(str(value))
        self.setfunc(self.option_name, value)

    def focus_out(self, event):
        # guard against the the final focus lost event on wxMAC
        if self.IsBeingDeleted():
            return

        value = self.get_value()

        if value is None:
            self.SetValue(str(self.config[self.option_name]))

        if (self.minimum is not None) and (value < self.minimum):
            value = self.minimum
        if (self.maximum is not None) and (value > self.maximum):
            value = self.maximum

        self.set_value(value)

    def text_inserted(self, event):
        key = event.KeyCode()

        if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255:
            event.Skip()
            return

        if (self.valid_chars is not None) and (chr(key) not in self.valid_chars):
            return

        event.Skip()



class IPValidator(Validator):
    valid_chars = '1234567890.'
    width = 128
    cast = str



class PortValidator(Validator):
    width = 64
    minimum = 1024
    maximum = 65535

    def add_end(self, end_name):
        self.end_option_name = end_name

    def set_value(self, value):
        self.SetValue(str(value))
        self.setfunc(self.option_name, value)
        self.setfunc(self.end_option_name, value+PORT_RANGE)



class RatioValidator(Validator):
    width = 48
    minimum = 0



class MinutesValidator(Validator):
    width = 48
    minimum = 1



class PathDialogButton(wx.Button):

    def __init__(self, parent, gen_dialog, setfunc=None,
                 label=_("&Browse...")):
        wx.Button.__init__(self, parent, label=label)

        self.gen_dialog = gen_dialog
        self.setfunc = setfunc

        self.Bind(wx.EVT_BUTTON, self.choose)


    def choose(self, event):
        """Pop up a choose dialog and set the result if the user clicks OK."""
        dialog = self.gen_dialog()
        result = dialog.ShowModal()

        if result == wx.ID_OK:
            path = dialog.GetPath()

            if self.setfunc:
                self.setfunc(path)



class ChooseDirectorySizer(wx.BoxSizer):

    def __init__(self, parent, path='', setfunc=None,
                 editable=True,
                 dialog_title=_("Choose a folder..."),
                 button_label=_("&Browse...")):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        self.parent = parent
        self.setfunc = setfunc
        self.dialog_title = dialog_title
        self.button_label = button_label

        self.pathbox = wx.TextCtrl(self.parent, size=(250, -1))
        self.pathbox.SetEditable(editable)
        self.Add(self.pathbox, proportion=1, flag=wx.RIGHT, border=SPACING)
        self.pathbox.SetValue(path)

        self.button = PathDialogButton(parent,
                                       gen_dialog=self.dialog,
                                       setfunc=self.set_choice,
                                       label=self.button_label)

        self.Add(self.button)


    def set_choice(self, path):
        self.pathbox.SetValue(path)
        if self.setfunc:
            self.setfunc(path)


    def get_choice(self):
        return self.pathbox.GetValue()


    def dialog(self):
        dialog = wx.DirDialog(self.parent,
                              message=self.dialog_title,
                              style=wx.DD_DEFAULT_STYLE|wx.DD_NEW_DIR_BUTTON)
        dialog.SetPath(self.get_choice())
        return dialog



class ChooseFileSizer(ChooseDirectorySizer):

    def __init__(self, parent, path='', setfunc=None,
                 editable=True,
                 dialog_title=_("Choose a file..."),
                 button_label=_("&Browse..."),
                 wildcard=_("All files (*.*)|*.*"),
                 dialog_style=wx.OPEN):
        ChooseDirectorySizer.__init__(self, parent, path=path, setfunc=setfunc,
                                      editable=editable,
                                      dialog_title=dialog_title,
                                      button_label=button_label)
        self.wildcard = wildcard
        self.dialog_style = dialog_style


    def dialog(self):
        directory, file = os.path.split(self.get_choice())
        dialog = wx.FileDialog(self.parent,
                               defaultDir=directory,
                               defaultFile=file,
                               message=self.dialog_title,
                               wildcard=self.wildcard,
                               style=self.dialog_style)
        #dialog.SetPath(self.get_choice())
        return dialog



class ChooseFileOrDirectorySizer(wx.BoxSizer):

    def __init__(self, parent, path='', setfunc=None,
                 editable=True,
                 file_dialog_title=_("Choose a file..."),
                 directory_dialog_title=_("Choose a folder..."),
                 file_button_label=_("Choose &file..."),
                 directory_button_label=_("Choose f&older..."),
                 wildcard=_("All files (*.*)|*.*"),
                 file_dialog_style=wx.OPEN):
        wx.BoxSizer.__init__(self, wx.VERTICAL)

        self.parent = parent
        self.setfunc = setfunc
        self.file_dialog_title = file_dialog_title
        self.directory_dialog_title = directory_dialog_title
        self.file_button_label = file_button_label
        self.directory_button_label = directory_button_label
        self.wildcard = wildcard
        self.file_dialog_style = file_dialog_style

        self.pathbox = wx.TextCtrl(self.parent, size=(250, -1))
        self.pathbox.SetEditable(editable)
        self.Add(self.pathbox, flag=wx.EXPAND|wx.BOTTOM, border=SPACING)
        self.pathbox.SetValue(path)

        self.subsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.Add(self.subsizer, flag=wx.ALIGN_RIGHT, border=0)

        self.fbutton = PathDialogButton(parent,
                                        gen_dialog=self.file_dialog,
                                        setfunc=self.set_choice,
                                        label=self.file_button_label)
        self.subsizer.Add(self.fbutton, flag=wx.LEFT, border=SPACING)

        self.dbutton = PathDialogButton(parent,
                                        gen_dialog=self.directory_dialog,
                                        setfunc=self.set_choice,
                                        label=self.directory_button_label)
        self.subsizer.Add(self.dbutton, flag=wx.LEFT, border=SPACING)


    def set_choice(self, path):
        self.pathbox.SetValue(path)
        if self.setfunc:
            self.setfunc(path)


    def get_choice(self):
        return self.pathbox.GetValue()


    def directory_dialog(self):
        dialog = wx.DirDialog(self.parent,
                              message=self.directory_dialog_title,
                              style=wx.DD_DEFAULT_STYLE|wx.DD_NEW_DIR_BUTTON)
        dialog.SetPath(self.get_choice())
        return dialog

    def file_dialog(self):
        dialog = wx.FileDialog(self.parent,
                               message=self.file_dialog_title,
                               defaultDir=self.get_choice(),
                               wildcard=self.wildcard,
                               style=self.file_dialog_style)
        dialog.SetPath(self.get_choice())
        return dialog




class Grid(wx.grid.Grid):

    def SetColRenderer(self, col, renderer):
        table = self.GetTable()
        attr = table.GetAttr(-1, col, wx.grid.GridCellAttr.Col)

        if (not attr):
            attr = wx.grid.GridCellAttr()

        attr.SetRenderer(renderer)
        self.SetColAttr(col, attr)


    def SetColEditor(self, col, editor):
        table = self.GetTable()
        attr = table.GetAttr(-1, col, wx.grid.GridCellAttr.Col)

        if (not attr):
            attr = wx.grid.GridCellAttr()

        attr.SetEditor(editor)
        self.SetColAttr(col, attr)



class BTMenu(wx.Menu):
    """Base class for menus"""

    def __init__(self, *a, **k):
        wx.Menu.__init__(self, *a, **k)

    def add_item(self, label):
        iid = wx.NewId()
        self.Append(iid, label)
        return iid

    def add_check_item(self, label, value=False):
        iid = wx.NewId()
        self.AppendCheckItem(iid, label)
        self.Check(id=iid, check=value)
        return iid



class CheckButton(wx.CheckBox):
    """Base class for check boxes"""
    def __init__(self, parent, label, main, option_name, initial_value,
                 extra_callback=None):
        wx.CheckBox.__init__(self, parent, label=label)
        self.main = main
        self.option_name = option_name
        self.option_type = type(initial_value)
        self.SetValue(bool(initial_value))
        self.extra_callback = extra_callback
        self.Bind(wx.EVT_CHECKBOX, self.callback)

    def callback(self, *args):
        if self.option_type is not type(None):
            self.main.config[self.option_name] = self.option_type(
                not self.main.config[self.option_name])
            self.main.setfunc(self.option_name, self.main.config[self.option_name])
        if self.extra_callback is not None:
            self.extra_callback()



class BTPanel(wx.Panel):
    sizer_class = wx.BoxSizer
    sizer_args = (wx.VERTICAL,)

    def __init__(self, *a, **k):
        k['style'] = k.get('style', 0) | wx.CLIP_CHILDREN
        wx.Panel.__init__(self, *a, **k)
        self.sizer = self.sizer_class(*self.sizer_args)
        self.SetSizer(self.sizer)

    def Add(self, widget, *a, **k):
        self.sizer.Add(widget, *a, **k)

    def AddFirst(self, widget, *a, **k):
        if hasattr(self.sizer, 'AddFirst'):
            self.sizer.AddFirst(widget, *a, **k)
        else:
            self.sizer.Add(widget, *a, **k)


# handles quirks in the design of wx.  For example, the wx.LogWindow is not
# really a window, but this make it respond to shows as if it were.
def MagicShow_func(win, show=True):
    win.Show(show)
    if show:
        win.Raise()

class MagicShow:
    """You know, like with a guy pulling rabbits out of a hat"""
    def MagicShow(self, show=True):
        if hasattr(self, 'magic_window'):
            # hackery in case we aren't actually a window
            win = self.magic_window
        else:
            win = self

        MagicShow_func(win, show)


class BTDialog(wx.Dialog, MagicShow):
    """Base class for all BitTorrent window dialogs"""

    def __init__(self, *a, **k):
        wx.Dialog.__init__(self, *a, **k)
        if sys.platform == 'darwin':
            self.CenterOnParent()
        self.SetIcon(wx.the_app.icon)
        self.Bind(wx.EVT_KEY_DOWN, self.key)

    def key(self, event):
        c = event.GetKeyCode()
        if c == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
        event.Skip()


class BTFrame(wx.Frame, MagicShow):
    """Base class for all BitTorrent window frames"""

    def __init__(self, *a, **k):
        metal = k.pop('metal', False)
        wx.Frame.__init__(self, *a, **k)
        if sys.platform == 'darwin' and metal:
            self.SetExtraStyle(wx.FRAME_EX_METAL)
        self.SetIcon(wx.the_app.icon)


    def load_geometry(self, geometry, default_size=None):
        if '+' in geometry:
            s, x, y = geometry.split('+')
            x, y = int(x), int(y)
        else:
            x, y = -1, -1
            s = geometry

        if 'x' in s:
            w, h = s.split('x')
            w, h = int(w), int(h)
        else:
            w, h = -1, -1

        i = 0
        if '__WXMSW__' in wx.PlatformInfo:
            i = wx.Display.GetFromWindow(self)
        d = wx.Display(i)
        (x1, y1, x2, y2) = d.GetGeometry()
        x = min(x, x2-64)
        y = min(y, y2-64)

        if (w, h) <= (0, 0) and default_size is not None:
            w = default_size.width
            h = default_size.height

        self.SetDimensions(x, y, w, h, sizeFlags=wx.SIZE_USE_EXISTING)

        if (x, y) == (-1, -1):
            self.CenterOnScreen()


    def _geometry_string(self):
        pos = self.GetPositionTuple()
        size = self.GetSizeTuple()
        g = ''
        g += 'x'.join(map(str, size))
        if pos > (0,0):
            g += '+' + '+'.join(map(str, pos))
        return g


    def SetTitle(self, title):
        if title != self.GetTitle():
            wx.Frame.SetTitle(self, title)



class BTFrameWithSizer(BTFrame):
    """BitTorrent window frames with sizers, which are less flexible than normal windows"""
    panel_class = BTPanel
    sizer_class = wx.BoxSizer
    sizer_args = (wx.VERTICAL,)

    def __init__(self, *a, **k):
        BTFrame.__init__(self, *a, **k)
        try:
            self.SetIcon(wx.the_app.icon)
            self.panel = self.panel_class(self)
            self.sizer = self.sizer_class(*self.sizer_args)
            self.Add(self.panel, flag=wx.GROW, proportion=1)
            self.SetSizer(self.sizer)
        except:
            self.Destroy()
            raise

    def Add(self, widget, *a, **k):
        self.sizer.Add(widget, *a, **k)



class TaskSingleton(object):

    def __init__(self):
        self.handle = None

    def start(self, t, _f, *a, **kw):
        if self.handle:
            self.handle.Stop()
        self.handle = wx.the_app.FutureCall(t, _f, *a, **kw)

    def stop(self):
        if self.handle:
            self.handle.Stop()
            self.handle = None

        
class BTApp(wx.App):
    """Base class for all wx-based BitTorrent applications"""

    def __init__(self, *a, **k):
        self.doneflag = threading.Event()
        wx.App.__init__(self, *a, **k)

    def OnInit(self):
        self.running = True
        if profile:
            try:
                os.unlink(prof_file_name)
            except:
                pass
            self.prof = Profiler()
            self.prof.enable()
        
        wx.the_app = self
        self._DoIterationId = wx.NewEventType()
        self.Connect(-1, -1, self._DoIterationId, self._doIteration)
        self.evt = wx.PyEvent()
        self.evt.SetEventType(self._DoIterationId)
        self.event_queue = []

        # this breaks TreeListCtrl, and I'm too lazy to figure out why
        #wx.IdleEvent_SetMode(wx.IDLE_PROCESS_SPECIFIED)
        # this fixes 24bit-color toolbar buttons
        wx.SystemOptions_SetOptionInt("msw.remap", 0)
        icon_path = os.path.join(image_root, 'bittorrent.ico')
        self.icon = wx.Icon(icon_path, wx.BITMAP_TYPE_ICO)
        return True

    def OnExit(self):
        self.running = False
        if profile:
            self.prof.disable()
            st = Stats(self.prof.getstats())
            st.sort()
            f = open(prof_file_name, 'wb')
            st.dump(file=f)

    def who(self, _f, a):
        if _f.__name__ == "_recall":
            if not hasattr(a[0], 'gen'):
                return str(a[0])
            return a[0].gen.gi_frame.f_code.co_name
        return _f.__name__

    def _doIteration(self, event):

        if self.doneflag.isSet():
            # the app is dying
            return

        _f, a, kw = self.event_queue.pop(0)

##        t = bttime()
##        print self.who(_f, a)
        _f(*a, **kw)
##        print self.who(_f, a), 'done in', bttime() - t
##        if bttime() - t > 1.0:
##            print 'TOO SLOW!'
##            assert False

    def CallAfter(self, callable, *args, **kw):
        """
        Call the specified function after the current and pending event
        handlers have been completed.  This is also good for making GUI
        method calls from non-GUI threads.  Any extra positional or
        keyword args are passed on to the callable when it is called.
        """

        # append (right) and pop (left) are atomic
        self.event_queue.append((callable, args, kw))
        wx.PostEvent(self, self.evt)

    def FutureCall(self, _delay_time, callable, *a, **kw):
        return wx.FutureCall(_delay_time, self.CallAfter, callable, *a, **kw)
