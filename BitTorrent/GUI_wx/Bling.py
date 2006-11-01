# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# written by Steven Hazel

from __future__ import division

import sys
import wx

from BTL.translation import _
from BitTorrent.UI import Rate
from BitTorrent.GUI_wx import SPACING, BTFrame, BTPanel, CustomWidgets
from BTL.Lists import SizedList


class HistoryCollector(object):

    def __init__(self, span, interval):
        self.max_len = int(span / (interval / 1000))
        self.interval = interval
        self.upload_data = SizedList(self.max_len)
        self.download_data = SizedList(self.max_len)
        self.max_upload_rate = 0
        self.max_download_rate = 0
        self.variance = 0
        self.max_variance = 1
        self.viewer = None

    def update(self, upload_rate, download_rate,
               max_upload_rate, max_download_rate,
               variance, max_variance):
#         if (len(self.data) == 0):
#             self.data.append(random.random() * 500.0)
#         else:
#             self.data.append(self.data[-1] * ((random.random() * 0.04) + 0.98))

        self.upload_data.append(upload_rate or 0)
        self.download_data.append(download_rate or 0)
        self.max_upload_rate = max_upload_rate
        self.max_download_rate = max_download_rate
        self.variance = variance
        self.max_variance = max_variance
        if self.viewer:
            self.viewer()

class BandwidthGraphPanel(CustomWidgets.DoubleBufferedMixin, BTPanel):
    MIN_MAX_DATA = 1000.0  # minimum value for the top of the graph

    def __init__(self, parent, history):
        super(BTPanel, self).__init__(parent,
              style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.history = history
        self.history.viewer = self.update
        self.upload_rate = 0
        self.download_rate = 0
        self.SetBackgroundColour("#002000")
        self.max_label_width = None
        CustomWidgets.DoubleBufferedMixin.__init__(self)

    def draw_graph(self, dc, max_len, data, max_data, rect):
        x_div = max_len - 1
        y_div = max_data
        if (y_div == 0.0):
            y_div = 1

        last_datum = (None, None)
        for i, datum in enumerate(data):
            if (last_datum == (None, None)):
                last_datum = (i, datum)
            dc.DrawLine(rect.x + (((last_datum[0] + (max_len - len(data))) / x_div) * (rect.width - 1)),
                        rect.y + ((1.0 - (last_datum[1] / y_div)) * (rect.height - 1)),
                        rect.x + (((i + (max_len - len(data))) / x_div) * (rect.width - 1)),
                        rect.y + ((1.0 - (datum / y_div)) * (rect.height - 1)))
            last_datum = (i, datum)

    def draw_max_line(self, dc, data, max_data, rect, offset=0):
        y_div = float(max_data)
        pos = (1.0 - (data / y_div)) * (rect.height - 1)
        if pos >= 0 and pos < rect.height:
            dc.DrawLine(rect.x + offset, rect.y + pos,
                        rect.x + rect.width, rect.y + pos)

    def update(self, force=False):
        if not self.IsShown() and not force:
            return
        dc = wx.BufferedDC(wx.ClientDC(self), self.buffer)
        self.draw(dc, size = self.GetClientSize())

    def draw(self, dc, size):
        s_rect = wx.Rect(0, 0, size.width, size.height)
        elements = list(self.history.upload_data) + list(self.history.download_data)
        max_data = max(elements + [self.MIN_MAX_DATA])

        interval = self.history.interval / 1000
        seconds = self.history.max_len * interval
        time_label_text = "%d"%seconds + _(" seconds, ")
        time_label_text += str(interval) + _(" second interval")

        dr_label_text = _("Download rate")
        ur_label_text = _("Upload rate")

        text_color = wx.NamedColour("light gray")
        border_color = wx.NamedColour("gray")
        dr_color = wx.NamedColor("green")
        ur_color = wx.NamedColor("slate blue")

        size = 8
        if sys.platform == "darwin":
            size = 10
        dc.SetFont(wx.Font(size, wx.DEFAULT, wx.NORMAL, wx.NORMAL))
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        dc.Clear()


        if (self.max_label_width == None):
            self.max_label_width = dc.GetTextExtent(unicode(Rate(1000000.0)))[0]

        self.max_label_width = max(self.max_label_width,
                                   dc.GetTextExtent(unicode(Rate(max_data)))[0])

        top_label_height = dc.GetTextExtent(unicode(Rate(max_data)))[1]
        bottom_label_height = dc.GetTextExtent(unicode(Rate(0.0)))[1]

        time_label_width = dc.GetTextExtent(unicode(time_label_text))[0]
        time_label_height = dc.GetTextExtent(unicode(time_label_text))[1]

        dr_label_width = dc.GetTextExtent(unicode(dr_label_text))[0]
        dr_label_height = dc.GetTextExtent(unicode(dr_label_text))[1]

        ur_label_width = dc.GetTextExtent(unicode(ur_label_text))[0]
        ur_label_height = dc.GetTextExtent(unicode(ur_label_text))[1]

        label_spacer = 4
        b_spacer = 15

        legend_box_size = 10
        legend_guts_height = max((legend_box_size,
                                  ur_label_height,
                                  dr_label_height))
        legend_height = legend_guts_height + b_spacer


        x1 = b_spacer
        y1 = b_spacer
        x2 = max(x1, s_rect.GetRight() -
                 (label_spacer + self.max_label_width + label_spacer))
        y2 = max(y1 + top_label_height + SPACING + bottom_label_height,
                 s_rect.GetBottom() -
                 (label_spacer + time_label_height + label_spacer +
                  legend_height))
        b_rect = wx.RectPP(wx.Point(x1, y1),
                           wx.Point(x2, y2))

        x1 = b_spacer + b_spacer
        y1 = max((b_rect.GetBottom() +
                  label_spacer + time_label_height + label_spacer),
                 s_rect.GetBottom() - (legend_box_size + b_spacer))
        x2 = x1 + legend_box_size
        y2 = y1 + legend_box_size
        db_rect = wx.RectPP(wx.Point(x1, y1),
                            wx.Point(x2, y2))

        x1 = db_rect.GetRight() + label_spacer + dr_label_width + b_spacer
        y1 = db_rect.y
        x2 = x1 + legend_box_size
        y2 = y1 + legend_box_size
        ub_rect = wx.RectPP(wx.Point(x1, y1),
                            wx.Point(x2, y2))

        x1 = min(b_rect.x + 1, b_rect.GetRight())
        y1 = min(b_rect.y + 1, b_rect.GetBottom())
        x2 = max(x1, b_rect.GetRight() - 1)
        y2 = max(y1, b_rect.GetBottom() - 1)
        i_rect = wx.RectPP(wx.Point(x1, y1),
                           wx.Point(x2, y2))


        bw_label_x = b_rect.GetRight() + label_spacer
        time_label_x = max(b_rect.x,
                           (b_rect.GetRight() / 2) - (time_label_width / 2))


        dc.SetTextForeground(text_color)
        dc.DrawText(unicode(Rate(max_data)),
                    bw_label_x, b_rect.y)
        dc.DrawText(unicode(Rate(0.0)),
                    bw_label_x, b_rect.GetBottom() - bottom_label_height)
        dc.DrawText(unicode(time_label_text),
                    time_label_x,  b_rect.GetBottom() + label_spacer)
        dc.DrawText(unicode(dr_label_text),
                    db_rect.GetRight() + label_spacer,
                    db_rect.y + (legend_box_size / 2) - (dr_label_height / 2))
        dc.DrawText(unicode(ur_label_text),
                    ub_rect.GetRight() + label_spacer,
                    ub_rect.y + (legend_box_size / 2) - (ur_label_height / 2))

        pen = wx.Pen(border_color, 1, wx.SOLID)
        dc.SetPen(pen)

        brush = wx.Brush(dr_color)
        dc.SetBrush(brush)
        dc.DrawRectangle(db_rect.x, db_rect.y,
                         db_rect.GetWidth(), db_rect.GetHeight())

        brush = wx.Brush(ur_color)
        dc.SetBrush(brush)
        dc.DrawRectangle(ub_rect.x, ub_rect.y,
                         ub_rect.GetWidth(), ub_rect.GetHeight())

        dc.DrawLine(b_rect.x, b_rect.y,
                    b_rect.GetRight(), b_rect.y)
        dc.DrawLine(b_rect.x, b_rect.y,
                    b_rect.x, b_rect.GetBottom())
        dc.DrawLine(b_rect.x, b_rect.GetBottom(),
                    b_rect.GetRight(), b_rect.GetBottom())
        dc.DrawLine(b_rect.GetRight(), b_rect.y,
                    b_rect.GetRight(), b_rect.GetBottom())

        pen = wx.Pen(border_color, 1, wx.DOT)
        dc.SetPen(pen)
        dc.DrawLine(i_rect.x, i_rect.y + (i_rect.height * 0.75),
                    i_rect.GetRight(), i_rect.y + (i_rect.height * 0.75))
        dc.DrawLine(i_rect.x, i_rect.y + (i_rect.height * 0.5),
                    i_rect.GetRight(), i_rect.y + (i_rect.height * 0.5))
        dc.DrawLine(i_rect.x, i_rect.y + (i_rect.height * 0.25),
                    i_rect.GetRight(), i_rect.y + (i_rect.height * 0.25))

        pen = wx.Pen(ur_color, 1, wx.SHORT_DASH)
        dc.SetPen(pen)
        self.draw_max_line(dc, self.history.max_upload_rate, max_data, i_rect,
                           offset=3)
        pen = wx.Pen(ur_color, 1, wx.SOLID)
        dc.SetPen(pen)
        self.draw_graph(dc, self.history.max_len, self.history.upload_data,
                        max_data, i_rect)

        pen = wx.Pen(dr_color, 1, wx.SHORT_DASH)
        dc.SetPen(pen)
        self.draw_max_line(dc, self.history.max_download_rate, max_data, i_rect)
        pen = wx.Pen(dr_color, 1, wx.SOLID)
        dc.SetPen(pen)
        self.draw_graph(dc, self.history.max_len, self.history.download_data,
                        max_data, i_rect)

        ## variance line
        if wx.the_app.config['show_variance_line']:
            pen = wx.Pen(wx.NamedColor("yellow"), 1, wx.SHORT_DASH)
            dc.SetPen(pen)
            self.draw_max_line(dc, self.history.variance, self.history.max_variance, i_rect)
        

class StatisticsPanel(wx.Panel):

    def __init__(self, parent, *a, **k):
        wx.Panel.__init__(self, parent, *a, **k)

        self.stats = {}

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.scrolled_window = wx.ScrolledWindow(self)
        self.scrolled_window.SetScrollRate(1, 1)
        self.sizer.Add(self.scrolled_window, flag=wx.GROW, proportion=1)

        self.scroll_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.panel = wx.Panel(self.scrolled_window)
        self.scroll_sizer.Add(self.panel, flag=wx.GROW, proportion=1)

        self.outer = wx.BoxSizer(wx.HORIZONTAL)

        self.left = wx.GridSizer(6, 2, SPACING, SPACING)
        self.outer.Add(self.left, flag=wx.ALL, border=SPACING)

        self.right = wx.GridSizer(6, 2, SPACING, SPACING)
        self.outer.Add(self.right, flag=wx.ALL, border=SPACING)

        self.add_row(self.left, "total_downrate", _("Total Download Rate:"))
        self.add_row(self.left, "total_uprate", _("Total Upload Rate:"))

        self.add_blank_row(self.left)

        self.add_row(self.left, "total_downtotal", _("Total Downloaded:"))
        self.add_row(self.left, "total_uptotal", _("Total Uploaded:"))

        self.add_row(self.right, "num_torrents", _("Torrents:"))
        self.add_row(self.right, "num_running_torrents", _("Running Torrents:"))

        self.add_blank_row(self.right)

        self.add_row(self.right, "num_connections", _("Total Connections:"))
        self.add_row(self.right, "avg_connections", _("Connections per Torrent:"))

        self.panel.SetSizerAndFit(self.outer)
        self.scrolled_window.SetSizer(self.scroll_sizer)
        self.SetSizerAndFit(self.sizer)

        # this fixes background repaint issues on XP w/ themes
        def OnSize(event):
            self.Refresh()
            event.Skip()
        self.Bind(wx.EVT_SIZE, OnSize)

    def add_blank_row(self, sizer):
        sizer.AddSpacer((5, 5))
        sizer.AddSpacer((5, 5))


    def add_row(self, sizer, name, header, value=""):
        h = wx.StaticText(self.panel, label=header)
        f = h.GetFont()
        f.SetWeight(wx.FONTWEIGHT_BOLD)
        h.SetFont(f)
        sizer.Add(h)

        st = wx.StaticText(self.panel, label=value)
        sizer.Add(st)

        self.stats[name] = st


    def update_values(self, values):
        for name, st in self.stats.iteritems():
            if name not in values:
                continue
            s = unicode(values[name])
            if unicode(st.GetLabel()) != s:
                st.SetLabel(s)
        #self.left.Layout()
        #self.right.Layout()
        #self.outer.Layout()



class BlingWindow(BTFrame):
    def __init__(self, parent, history, *a, **k):
        super(BlingWindow, self).__init__(parent, title="Details",
            size=(640, 280),
            style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE|wx.CLIP_CHILDREN)
        self.Bind(wx.EVT_CLOSE, self.close)
        self.bling = BandwidthGraphPanel(self, history)
        self.SetBackgroundColour(self.bling.GetBackgroundColour())
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.bling, flag=wx.GROW, proportion=1)
        self.SetSizer(self.sizer)

    def close(self, *e):
        self.Hide()


class BlingPanel(BTPanel):

    def __init__(self, parent, history, *a, **k):
        BTPanel.__init__(self, parent, *a, **k)
        #self.SetMinSize((200, 200))

        self.notebook = wx.Notebook(self, style=wx.CLIP_CHILDREN)

        self.statistics = StatisticsPanel(self.notebook, style=wx.CLIP_CHILDREN)
        self.notebook.AddPage(self.statistics, _("Statistics"))

        self.bling = BandwidthGraphPanel(self.notebook, history)
        self.speed_tab_index = self.notebook.GetPageCount()
        self.notebook.AddPage(self.bling, _("Speed"))

        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)

        self.sizer.Add(self.notebook, flag=wx.GROW, proportion=1)

        self.Hide()
        self.sizer.Layout()

    def OnPageChanged(self, event):
        if event.GetSelection() == self.speed_tab_index:
            self.bling.update(force=True)
        event.Skip()
