# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Greg Hazel, ModerateDownloadGauge written by Matt Chisholm

import os
import sys

from BTL.platform import bttime
from BTL.DictWithLists import DictWithLists
from BTL.obsoletepythonsupport import set
from BTL.sparse_set import SparseSet
from BTL.Lists import collapse

import wx

if os.name == 'nt':
    import win32gui
    import win32con


def _ScaleBlit(bmp, dc, dst_rect):
    sX = float(dst_rect.width) / float(bmp.GetWidth())
    sY = float(dst_rect.height) / float(bmp.GetHeight())

    dc.SetUserScale(sX, sY)

    old_mode = None
    if os.name == 'nt':
        h_dst = dc.GetHDC()
        try:
            old_mode = win32gui.SetStretchBltMode(h_dst, win32con.HALFTONE)
        except:
            pass

    if sX == 0:
        x = 0
    else:
        x = dst_rect.x/sX

    if sY == 0:
        y = 0
    else:
        y = dst_rect.y/sY

    if sys.platform == "darwin":
        # magic!
        y = round(y)
        x += 0.2
        dc.SetDeviceOrigin(x, y)
        dc.DrawBitmap(bmp, 0, 0, True)
        dc.SetDeviceOrigin(0, 0)
    else:
        dc.DrawBitmap(bmp, x, y, True)

    if os.name == 'nt':
        try:
            win32gui.SetStretchBltMode(h_dst, old_mode)
        except:
            pass

    dc.SetUserScale(1, 1)


class DoubleBufferedMixin(object):

    def __init__(self):
        self.bind_events()
        self.buffer_size = wx.Size(-1, -1)
        self.last_size = self._calc_size()
        self.init_buffer()

    def _calc_size(self):
        return self.GetClientSize()

    def init_buffer(self):
        size = self._calc_size()
        if ((self.buffer_size.width < size.width) or
            (self.buffer_size.height < size.height)):
            self.buffer = wx.EmptyBitmap(size.width, size.height)
            dc = wx.MemoryDC()
            dc.SelectObject(self.buffer)
            dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
            dc.Clear()
            dc.SelectObject(wx.NullBitmap)
            self.buffer_size = size
            return True
        return False

    def bind_events(self):
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e : None)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def redraw(self):
        dc = wx.MemoryDC()
        dc.SelectObject(self.buffer)
        size = self._calc_size()
        self.last_size = size
        self.draw(dc, size=size)
        dc.SelectObject(wx.NullBitmap)
        self.Refresh()

    def OnSize(self, event):
        reallocated = self.init_buffer()
        if reallocated or self.last_size != self._calc_size():
            self.redraw()
        else:
            self.Refresh()

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self, self.buffer)


class ScaledBufferMixin(DoubleBufferedMixin):

    def __init__(self, w_step=200, h_step=15):
        self.w_step = w_step
        self.h_step = h_step
        # don't go crazy
        self.w_max = 1000
        self.h_max = 100
        DoubleBufferedMixin.__init__(self)

    def _round(self, d, step):
        return max(int(d / step), 1) * step

    def _calc_size(self):
        size = self.GetClientSize()
        # * 2 for the high quality
        w = self._round(size.width*2, self.w_step)
        h = self._round(size.height, self.h_step)
        w = max(w, self.buffer_size.width)
        w = min(w, self.w_max)
        h = max(h, self.buffer_size.height)
        h = min(h, self.h_max)
        return wx.Size(w, h)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        _ScaleBlit(self.buffer, dc, self.GetClientRect(), strip_border=1)


class ListCtrlPassThrough(object):
    def __init__(self, listctrl):
        # I'll be nice and ignore you.
        if not isinstance(listctrl, wx.ListCtrl):
            return
        self.listctrl = listctrl
        self.Bind(wx.EVT_LEFT_DOWN, self.LeftDown)
        self.Bind(wx.EVT_LEFT_DCLICK, self.LeftDClick)
        self.Bind(wx.EVT_CONTEXT_MENU, self.ContextMenu)

    def _resolve_position(self):
        p = self.GetPosition()
        p -= self.listctrl._get_origin_offset()
        return p

    def _resolve_index(self):
        p = self._resolve_position()
        try:
            i, flags = self.listctrl.HitTest(p)
        except TypeError:
            # unpack non-sequence
            return
        return i

    def ContextMenu(self, event):
        self.listctrl.DoPopup(self._resolve_position())

    def LeftDClick(self, event):
        i = self._resolve_index()
        if i is None:
            return

        e = wx.ListEvent(wx.wxEVT_COMMAND_LIST_ITEM_ACTIVATED)
        e.m_itemIndex = i
        self.listctrl.ProcessEvent(e)

    def LeftDown(self, event):
        i = self._resolve_index()
        if i is None:
            return

        if not event.ControlDown():
            if event.ShiftDown():
                if '__WXMSW__' in wx.PlatformInfo:
                    self.listctrl.DeselectAll()
                f = self.listctrl.GetFocusedItem()
                if f > -1:
                    for j in xrange(min(i,f), max(i,f)):
                        self.listctrl.Select(j)
                    self.listctrl.Select(f)
            else:
                self.listctrl.DeselectAll()

        self.listctrl.Select(i)
        self.listctrl.SetFocus()
        self.listctrl.Focus(i)



class NullGauge(object):
    def NullMethod(*a):
        pass
    __init__ = NullMethod
    def __getattr__(self, attr):
        return self.NullMethod


class SimpleDownloadGauge(ListCtrlPassThrough, ScaledBufferMixin, wx.Window):

    def __init__(self, parent,
                 completed_color=None,
                 remaining_color=None,
                 border_color=None,
                 border=True,
                 size=(0,0),
                 top_line=True,
                 **k):
        original = {
            "smooth": True,
            "border color": wx.NamedColour("light gray"),
            "completed color": wx.Colour(0, 230, 50),
            "line color"     : wx.Colour(0, 178, 39),
            "remaining color": wx.NamedColour("white"),
            "transferring color": wx.NamedColour("yellow"),
            "missing color": wx.NamedColour("red"),
            "rare colors": [wx.Colour(235, 235, 255),
                            wx.Colour(215, 215, 255),
                            wx.Colour(195, 195, 255),
                            wx.Colour(175, 175, 255),
                            wx.Colour(155, 155, 255),
                            wx.Colour(135, 135, 255),
                            wx.Colour(115, 115, 255),
                            wx.Colour(95, 95, 255),
                            wx.Colour(75, 75, 255),
                            wx.Colour(55, 55, 255),
                            wx.Colour(50, 50, 255)]
            }

        new_green = {
            "smooth": True,
            "border color": wx.Colour(111, 111, 111),
            "completed color": wx.Colour(14, 183, 19),
            "line color"     : wx.Colour(255, 255, 0),
            "remaining color": wx.NamedColour("white"),
            "transferring color": wx.Colour(94, 243, 99),
            "missing color": wx.Colour(255, 0, 0),
            "rare colors": [wx.Colour(185, 185, 185),
                            wx.Colour(195, 195, 195),
                            wx.Colour(205, 205, 205),
                            wx.Colour(215, 215, 215),
                            wx.Colour(225, 225, 225),
                            wx.Colour(235, 235, 235),
                            wx.Colour(245, 245, 245),
                            wx.Colour(255, 255, 255)]
            }

        new_blue = {
            "smooth": True,
            "border color": wx.NamedColour("light gray"),
            "completed color": wx.NamedColour("blue"),
            "line color"     : wx.NamedColour("blue"),
            "remaining color": wx.NamedColour("white"),
            "transferring color": wx.NamedColour("yellow"),
            "missing color": wx.Colour(255, 0, 0),
            "rare colors": [wx.Colour(185, 185, 185),
                            wx.Colour(195, 195, 195),
                            wx.Colour(205, 205, 205),
                            wx.Colour(215, 215, 215),
                            wx.Colour(225, 225, 225),
                            wx.Colour(235, 235, 235),
                            wx.Colour(245, 245, 245),
                            wx.Colour(255, 255, 255)]
            }

        self.gauge_theme = new_green

        wx.Window.__init__(self, parent, size=size, **k)
        #wx.Gauge.__init__(self, parent, 0, 10000, style=wx.GA_SMOOTH)
        ListCtrlPassThrough.__init__(self, parent)
        if border_color == None:
            border_color = self.gauge_theme["border color"]
        if completed_color == None:
            completed_color = self.gauge_theme["completed color"]
        if remaining_color == None:
            remaining_color = self.gauge_theme["remaining color"]
        self.completed_color = completed_color
        self.remaining_color = remaining_color
        self.border_color = border_color
        self.border = border
        self.line_color = self.gauge_theme["line color"]
        self.top_line = top_line
        self.smoother = wx.BitmapFromImage(
            wx.GetApp().theme_library.get(("progressbar",)))
        self.percent = None
        ScaledBufferMixin.__init__(self)

    def invalidate(self):
        pass

    def SetValue(self, value, state=None, data=None, redraw=True):
        #wx.Gauge.SetValue(self, value * 10000)
        if value != self.percent:
            self.percent = value
            self.redraw()

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        rect = self.GetClientRect()

        if self.border:
            dc.SetPen(wx.Pen(self.border_color))
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.DrawRectangle(0, 0, rect.width, rect.height)
            rect = wx.Rect(rect.x + 1, rect.y + 1,
                           rect.width - 2, rect.height - 2)

        _ScaleBlit(self.buffer, dc, rect)

    def draw(self, dc, size):
        srect = wx.Rect(0, 0, size.width, size.height)
        self.draw_bar(dc, srect)

        # dear god, I hope it's smooth
        if self.gauge_theme["smooth"]:
            dc.SetClippingRegion(srect.x, srect.y, srect.width, srect.height)
            _ScaleBlit(self.smoother, dc,
                       wx.Rect(0, 0, srect.width, srect.height))

        # top-line
        if self.top_line and self.percent is not None:
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.SetPen(wx.Pen(self.line_color))
            line_width = 1
            # top:
            line_position = 0
            # middle:
            #line_position = (srect.height) // 2
            # bottom:
            #line_position = srect.height - line_width
            dc.DrawRectangle(srect.x, line_position,
                             srect.width * self.percent, line_width)
            dc.SetPen(wx.Pen(self.border_color))
            dc.DrawRectangle(srect.x + srect.width * self.percent, line_position,
                             srect.width, line_width)

    def draw_bar(self, dc, rect):
        if self.percent == None:
            return 0
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.SetBrush(wx.Brush(self.remaining_color))
        dc.DrawRectangle(rect.x, rect.y,
                         rect.width, rect.height)
        dc.SetBrush(wx.Brush(self.completed_color))
        dc.DrawRectangle(rect.x, rect.y,
                         rect.width * self.percent, rect.height)
        return 0

REFRESH_MAX_SEC = 3

class FancyDownloadGauge(SimpleDownloadGauge):

    def __init__(self, *args, **kwargs):
        self.resolution = 1000
        self.grouped = DictWithLists()
        self.missing_known = False
        self.last_time = bttime()
        self.last_update = -1
        SimpleDownloadGauge.__init__(self, *args, **kwargs)
        self.transfering_color = self.gauge_theme["transferring color"]
        self.missing_color = self.gauge_theme["missing color"]
        self.SetValue(None, redraw=False)

    def gradient(self, v):
        if v == 0:
            if self.missing_known:
                c = self.missing_color
            else:
                c = self.gauge_theme["rare colors"][0]
        else:
            v = min(v, len(self.gauge_theme["rare colors"]))
            c = self.gauge_theme["rare colors"][v - 1]
        return c

    def invalidate(self):
        self.last_time = 0

    def SetValue(self, percent, state = None, data = None, redraw=True):
        # only draw if progress moved .01% or it's been REFRESH_MAX_SEC seconds
        if self.percent != None:
            if (percent < (self.percent + 0.0001) and
                bttime() < (self.last_time + REFRESH_MAX_SEC)):
                return
        self.last_time = bttime()

        if not redraw:
            return

        p_dirty = False
        if self.percent != percent:
            p_dirty = True
        self.percent = percent

        missing_known = state == "running"
        if self.missing_known != missing_known:
            p_dirty = True
        self.missing_known = missing_known

        if not data:
            # no data. allow future SetValues to continue passing
            # until we get something
            self.last_time = 0 - REFRESH_MAX_SEC
            # draw an empty bar
            data = (0, -1, {})

        length, update, piece_states = data

        self.resolution = length

        if p_dirty or update != self.last_update:
            self.grouped = piece_states
            self.redraw()
        self.last_update = update

    def draw_bar(self, dc, rect):
        # size events can catch this
        if self.percent is None:
            return

        y1 = rect.y
        w = rect.width
        h = rect.height

        if self.resolution <= 0:
            return

        # sort, so we get 0...N, h, t
        keys = self.grouped.keys()
        keys.sort()
        for k in keys:
            v = self.grouped[k]

            if k == 'h':
                c = self.completed_color
            elif k == 't':
                c = self.transfering_color
            else:
                c = self.gradient(k)

            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.SetBrush(wx.Brush(c))

            def draw(b, e):
                b = float(b)
                e = float(e)
                r = float(self.resolution)
                x1 = (b / r) * w
                x2 = (e / r) * w
                # stupid floats
                x1 = int(rect.x + x1)
                x2 = int(rect.x + x2)
                dc.DrawRectangle(x1, y1,
                                 x2 - x1, h)

            if isinstance(v, SparseSet):
                for (b, e) in v.iterrange():
                    draw(b, e)
            elif isinstance(v, dict):
                for b in v.iterkeys():
                    draw(b, b + 1)
            elif isinstance(v, set):
                #for b in v:
                #   draw(b, b + 1)
                # maybe this is better? (fewer rectangles)
                l = list(v)
                l.sort()
                for (b, e) in collapse(l):
                    draw(b, e)
            else:
                # assumes sorted!
                for (b, e) in collapse(v):
                    draw(b, e)
                    

class ModerateDownloadGauge(FancyDownloadGauge):

    def __init__(self, parent,
                 completed_color=None,
                 remaining_color=None,
                 border_color=None,
                 border=True,
                 size=(0,0),
                 top_line=False,
                 *args, **kwargs):
        FancyDownloadGauge.__init__(self, parent,
                                    completed_color=completed_color,
                                    remaining_color=remaining_color,
                                    border_color=border_color,
                                    border=border,
                                    size=size,
                                    top_line=top_line,
                                    *args, **kwargs)
        self.resolution = 1000

    def sort(a,b):
        if   isinstance(a, str) and isinstance(b, str) : return cmp(a,b)
        elif isinstance(a, int) and isinstance(b, int) : return cmp(b,a)
        elif isinstance(a, str): return -1
        elif isinstance(b, str): return  1

    sort = staticmethod(sort)

    def SetValue(self, value, state=None, data=None, redraw=True):
        if data is not None:
            sorted_data = {}
            length, update, piece_states = data
            self.resolution = length
            keys = piece_states.keys()
            keys.sort(self.sort)
            pos = 0
            h = piece_states.get('h', SparseSet())
            t = piece_states.get('t', set())
            t = list(t)
            t.sort()
            have_trans_sparse_set = h + t
            for k in keys:
                p = piece_states[k]
                if k in ('h', 't'):
                    count = len(p)
                else:
                    count = 0
                    # OW
                    for i in p:
                        if i not in have_trans_sparse_set:
                            count += 1
                if not count:
                    continue
                newpos = pos+count
                s = SparseSet()
                s.add(pos, newpos)
                sorted_data[k] = s
                pos = newpos
            data = (length, update, sorted_data)
        FancyDownloadGauge.SetValue(self, value, state, data, redraw)
