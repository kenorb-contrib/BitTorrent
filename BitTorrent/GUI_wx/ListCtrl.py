# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# written by Matt Chisholm, Steven Hazel, and Greg Hazel

import locale
import traceback
import wx
from UserDict import IterableUserDict
from wx.lib.mixins.listctrl import ColumnSorterMixin
from wx.lib.mixins.listctrl import getListCtrlSelection
import os
import sys
if os.name == 'nt':
    LVM_FIRST = 0x1000
    LVM_SETSELECTEDCOLUMN = (LVM_FIRST + 140)
    import win32gui


def highlight_color(c):
    if c > 240:
        c *= 0.97
    else:
        c = min(c * 1.10, 255)
    return int(c)


SEL_FOC = wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED
def selectBeforePopup(ctrl, pos):
    """Ensures the item the mouse is pointing at is selected before a popup.

    Works with both single-select and multi-select lists."""

    if not isinstance(ctrl, wx.ListCtrl):
        return

    n, flags = ctrl.HitTest(pos)
    if n < 0:
        return

    if not ctrl.GetItemState(n, wx.LIST_STATE_SELECTED):
        for i in xrange(ctrl.GetItemCount()):
            ctrl.SetItemState(i, 0, SEL_FOC)
        ctrl.SetItemState(n, SEL_FOC, SEL_FOC)

class ContextMenuMixin(object):
    def __init__(self):
        self.context_menu = None
        self.column_context_menu = None
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        self.Bind(wx.EVT_LIST_COL_RIGHT_CLICK, self.OnColumnContextMenu)

    def SetContextMenu(self, menu):
        self.context_menu = menu

    def SetColumnContextMenu(self, menu):
        self.column_context_menu = menu

    def OnColumnContextMenu(self, event):
        if self.column_context_menu:
            self.PopupMenu(self.column_context_menu)

    def OnContextMenu(self, event):
        pos = self.ScreenToClient(event.GetPosition())
        top = self.GetItemRect(self.GetTopItem())
        if pos[1] < top.y:
            event.Skip()
            return

        pos -= self._get_origin_offset()
        self.DoPopup(pos)

    def DoPopup(self, pos):
        """ pos should be in client coords """
        if self.context_menu:
            selectBeforePopup(self, pos)
            selection = getListCtrlSelection(self)
            if len(selection) > 0:
                self.PopupMenu(self.context_menu)
                return


class BTListColumn(wx.ListItem):

    def __init__(self, text, sample_data, renderer=None, comparator=None, enabled=True, width=50):
        wx.ListItem.__init__(self)
        self.SetText(text)
        self.renderer = renderer
        self.comparator = comparator
        self.enabled = enabled
        self.sample_data = sample_data
        self.width = width


class BTListRow(IterableUserDict):
    __slots__ = ['data', 'index']

    def __init__(self, index, data):
        self.data = data
        self.index = index

    def __getitem__(self, i):
        return self.data[i]


class BTListCtrl(wx.ListCtrl, ColumnSorterMixin, ContextMenuMixin):
    # Part of this class based on:
    # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/426407
    icon_size = 16

    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, wx.ID_ANY, style=wx.LC_REPORT)
        ContextMenuMixin.__init__(self)

        self.il = wx.ImageList(self.icon_size, self.icon_size)
        # TODO: use a real icon
        self.il.Add(self.draw_blank())
        self.il.Add(self.draw_sort_arrow('up'))
        self.il.Add(self.draw_sort_arrow('down'))
        self.SetImageList(self.il, wx.IMAGE_LIST_SMALL)

        self.update_enabled_columns()

        for i, name in enumerate(self.enabled_columns):
            column = self.columns[name]
            column.SetColumn(i)
            self.InsertColumnItem(i, column)

        self.itemData_to_row = {}
        self.index_to_itemData = {}

        self.selected_column = None
        self.SelectColumn(self.enabled_columns[0])

        cmenu = wx.Menu()
        for name in self.column_order:
            column = self.columns[name]
            id = wx.NewId()
            cmenu.AppendCheckItem(id, column.GetText())
            cmenu.Check(id, column.enabled)
            self.Bind(wx.EVT_MENU,
                      lambda e, c=column, id=id: self.toggle_column(c, id, e),
                      id=id)
        self.SetColumnContextMenu(cmenu)

        ColumnSorterMixin.__init__(self, len(self.enabled_columns))
        self._last_scrollpos = 0
        if sys.platform != "darwin":
            self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)

        self.default_rect = wx.Rect(0,0)

    def OnEraseBackground(self, event=None):
        nsp = self.GetScrollPos(wx.VERTICAL)
        if self._last_scrollpos != nsp:
            self._last_scrollpos = nsp
            # should only refresh visible items, hmm
            wx.CallAfter(self.Refresh)
        dc = wx.ClientDC(self)
        # erase the section of the background which is not covered by the
        # items or the selected column highlighting
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        f = self.GetRect()
        r = wx.Region(0, 0, f.width, f.height)
        x = self.GetVisibleViewRect()
        offset = self._get_origin_offset(include_header=True)
        x.Offset(offset)
        r.SubtractRect(x)
        if '__WXMSW__' in wx.PlatformInfo:
            c = self.GetColumnRect(self.enabled_columns.index(self.selected_column))
            r.SubtractRect(c)
        dc.SetClippingRegionAsRegion(r)
        dc.Clear()

        if '__WXMSW__' in wx.PlatformInfo:
            # draw the selected column highlighting under the items
            dc.DestroyClippingRegion()
            r = wx.Region(0, 0, f.width, f.height)
            r.SubtractRect(x)
            dc.SetClippingRegionAsRegion(r)
            dc.SetPen(wx.TRANSPARENT_PEN)
            hc = wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW)
            r = highlight_color(hc.Red())
            g = highlight_color(hc.Green())
            b = highlight_color(hc.Blue())
            hc.Set(r, g, b)
            dc.SetBrush(wx.Brush(hc))
            dc.DrawRectangle(c.x, c.y, c.width, c.height)

    def update_enabled_columns(self):
        self.enabled_columns = [name for name in self.column_order
                                if self.columns[name].enabled]

    def toggle_column(self, tcolumn, id, event):
        self.update_column_widths()
        sort_col = self.get_sort_column()

        tcolumn.enabled = not tcolumn.enabled
        self.column_context_menu.Check(id, tcolumn.enabled)

        self.update_enabled_columns()

        if not tcolumn.enabled:
            self.DeleteColumn(tcolumn.GetColumn())

        new_col_names = []
        for i, name in enumerate(self.enabled_columns):
            column = self.columns[name]
            column.SetColumn(i)
            if column == tcolumn:
                self.InsertColumnItem(i, column)
                new_col_names.append(name)
            self.SetColumnWidth(column.GetColumn(), column.width)

        self.SetColumnCount(len(self.enabled_columns))
        self.SortListItems(col=sort_col)

        for itemData in self.itemData_to_row.iterkeys():
            self.InsertRow(itemData, self.itemData_to_row[itemData],
                           sort=True, force_update_columns=new_col_names)
        #self.SortItems()

    def set_default_widths(self):
        # must be called before *any* data is put into the control.
        sample_data = {}
        for name in self.column_order:
            sample_data[name] = self.columns[name].sample_data
        sample_row = BTListRow(None, sample_data)

        self.InsertRow(-1, sample_row)
        for name in self.column_order:
            column = self.columns[name]
            if name in self.enabled_columns:
                self.SetColumnWidth(column.GetColumn(), wx.LIST_AUTOSIZE)
                column.width = self.GetColumnWidth(column.GetColumn())
            dc = wx.ClientDC(self)
            header_width = dc.GetTextExtent(column.GetText())[0]
            header_width += 4 # arbitrary allowance for header decorations
            column.width = max(column.width, header_width)
            if name in self.enabled_columns:
                self.SetColumnWidth(column.GetColumn(), column.width)
        self.default_rect = self.GetItemRect(0)
        self.DeleteRow(-1)

    def _get_origin_offset(self, include_header=None):

        if include_header is None:
            # Hm, I think this is a legit bug in wxGTK
            if '__WXGTK__' in wx.PlatformInfo:
                include_header = True
            else:
                include_header = False

        if include_header:            
            i = self.GetTopItem()
            try:
                r = self.GetItemRect(i)
            except wx._core.PyAssertionError:
                r = self.default_rect
            return (r.x, r.y)
        return (0, 0)

    def add_image(self, image):
        b = wx.BitmapFromImage(image)
        if not b.Ok():
            raise Exception("The image (%s) is not valid." % image)

        if (sys.platform == "darwin" and
            (b.GetWidth(), b.GetHeight()) == (self.icon_size, self.icon_size)):
            return self.il.Add(b)
        
        b2 = wx.EmptyBitmap(self.icon_size, self.icon_size)
        dc = wx.MemoryDC()
        dc.SelectObject(b2)
        dc.SetBackgroundMode(wx.TRANSPARENT)
        dc.Clear()
        x = (b2.GetWidth() - b.GetWidth()) / 2
        y = (b2.GetHeight() - b.GetHeight()) / 2
        dc.DrawBitmap(b, x, y, True)
        dc.SelectObject(wx.NullBitmap)
        b2.SetMask(wx.Mask(b2, (255, 255, 255)))

        return self.il.Add(b2)

    # Arrow drawing
    def draw_blank(self):
        b = wx.EmptyBitmap(self.icon_size, self.icon_size)
        dc = wx.MemoryDC()
        dc.SelectObject(b)
        dc.SetBackgroundMode(wx.TRANSPARENT)
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)
        b.SetMask(wx.Mask(b, (255, 255, 255)))
        return b

    # this builds an identical arrow to the windows listctrl arrows, in themed
    # and non-themed mode.
    def draw_sort_arrow(self, direction):
        b = wx.EmptyBitmap(self.icon_size, self.icon_size)
        w, h = b.GetSize()
        ho = (h - 5) / 2
        dc = wx.MemoryDC()
        dc.SelectObject(b)
        colour = wx.SystemSettings_GetColour(wx.SYS_COLOUR_GRAYTEXT)
        dc.SetBackgroundMode(wx.TRANSPARENT)
        dc.Clear()
        dc.SetPen(wx.Pen(colour))
        for i in xrange(5):
            if direction == 'down':
                j = 4 - i
            else:
                j = i
            dc.DrawLine(i,j+ho,9-i,j+ho)
        dc.SelectObject(wx.NullBitmap)
        b.SetMask(wx.Mask(b, (255, 255, 255)))
        return b

    def GetBottomItem(self):
        total = self.GetItemCount()
        top = self.GetTopItem()
        pp = self.GetCountPerPage()
        # I purposefully do not subtract 1 from pp, because pp is whole items
        bottom = min(top + pp, total - 1)
        return bottom

    def SelectColumn(self, col):
        """Color the selected column (MSW only)"""
        if self.selected_column == col:
            return
        col_num = self.enabled_columns.index(col)
        if os.name == 'nt':
            win32gui.PostMessage(self.GetHandle(),
                                 LVM_SETSELECTEDCOLUMN, col_num, 0)

            if self.selected_column is not None:
                self.RefreshCol(self.selected_column)
            self.RefreshCol(col)
            self.selected_column = col

    def render_column_text(self, row, name):
        """Renders the column value into a string"""
        item = self.columns[name]
        value = row[name]
        if value is None:
            text = '?'
        elif item.renderer is not None:
            try:
                text = item.renderer(value)
            except:
                text = '?'
                # BUG: for debugging only
                traceback.print_exc()
        else:
            text = unicode(value)
        return text


    def get_column_image(self, row):
        return None

    def _update_indexes(self, start = 0):
        for i in xrange(start, self.GetItemCount()):
            itemData = self.GetItemData(i)
            self.itemData_to_row[itemData].index = i
            self.index_to_itemData[i] = itemData


    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def SortItems(self, sorter=None):

        if sorter is None:
            sorter = self.GetColumnSorter()

        # TODO:
        # this step is to see if the list needs resorted.
        # improve this by stopping the first time the order would be changed.
        d = [None,] * self.GetItemCount()
        for i in xrange(len(d)):
            # use real GetItemData, so the sorter can translate
            d[i] = wx.ListCtrl.GetItemData(self, i)
        n = list(d)
        n.sort(sorter)

        if n != d:
            wx.ListCtrl.SortItems(self, sorter)

            self._update_indexes()

        self.SelectColumn(self.enabled_columns[self._col])

    def SortListItems(self, col=-1, ascending=1):
        if col in self.enabled_columns:
            col = self.enabled_columns.index(col)
        else:
            col = 0

        ColumnSorterMixin.SortListItems(self, col=col, ascending=ascending)


    def GetSelection(self):
        return getListCtrlSelection(self)


    def GetSelectionData(self):
        indexes = self.GetSelection()
        data = []
        for i in indexes:
            data.append(self.GetItemData(i))
        return data

    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetListCtrl(self):
        return self

    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetSortImages(self):
        return (1, 2)


    def GetColumnSorter(self):
        """Returns a callable object to be used for comparing column values when sorting."""
        return self.__ColumnSorter

    def TranslateItemData(self, itemData):
        return itemData

    def __ColumnSorter(self, itemData1, itemData2):
        """Allows custom compare functions, in self.colcmps."""
        col = self._col
        ascending = self._colSortFlag[col]

        if col < len(self.enabled_columns):
            name = self.enabled_columns[col]
        else:
            name = self.column_order[0]

        itemData1 = self.TranslateItemData(itemData1)
        itemData2 = self.TranslateItemData(itemData2)
        item1 = self.itemData_to_row[itemData1][name]
        item2 = self.itemData_to_row[itemData2][name]

        column = self.columns[name]

        if column.comparator != None:
            # use custom cmp method
            cmpVal = column.comparator(item1, item2)
        elif isinstance(item1, str) or isinstance(item2, str):
            # Internationalization of string sorting with locale module
            cmpVal = locale.strcoll(unicode(item1), unicode(item2))
        else:
            cmpVal = cmp(item1, item2)

        # If the items are equal then pick something else to make the sort value unique
        if cmpVal == 0:
            cmpVal = apply(cmp, self.GetSecondarySortValues(col, itemData1, itemData2))

        if ascending:
            return cmpVal
        else:
            return -cmpVal

    def RefreshCol(self, col):
        if col in self.enabled_columns:
            self.RefreshRect(self.GetColumnRect(self.enabled_columns.index(col)))

    def HitTestColumn(self, pos):
        """ pos should be in client coords """
        i = self.GetTopItem()
        r = self.GetItemRect(i)
        x, y = self._get_origin_offset()
        if pos[1] >= (r.y - y):
            return None
        loc = 0
        for n in xrange(self.GetColumnCount()):
            loc += self.GetColumnWidth(n)
            if pos[0] < loc:
                return n

    def GetVisibleViewRect(self):
        width = 0
        for n in xrange(self.GetColumnCount()):
            width += self.GetColumnWidth(n)
        height = 0
        if self.GetItemCount() > 0:
            i = self.GetTopItem()
            r1 = self.GetItemRect(i)
            last = min(i + self.GetCountPerPage(), self.GetItemCount() - 1)
            r2 = self.GetItemRect(last)
            height = r2.y + r2.height - r1.y
        x, y = self._get_origin_offset()
        # there is a 2 pixel strip on either side which is not part of the item
        if '__WXMSW__' in wx.PlatformInfo:
            x += 2
            width -= 4
            
        return wx.Rect(x, y, x+width, y+height)
        
    def GetViewRect(self):
        width = 0
        for n in xrange(self.GetColumnCount()):
            width += self.GetColumnWidth(n)
        height = 0
        if self.GetItemCount() > 0:
            r1 = self.GetItemRect(0)
            r2 = self.GetItemRect(self.GetItemCount() - 1)
            height = r2.y + r2.height - r1.y
        x, y = self._get_origin_offset()
        return wx.Rect(x, y, x+width, y+height)

    def _GetColumnWidthExtent(self, col):
        col_locs = [0]
        loc = 0
        num_cols = min(col+1, self.GetColumnCount())
        for n in xrange(num_cols):
            loc += self.GetColumnWidth(n)
            col_locs.append(loc)

        x0 = col_locs[col]
        x1 = col_locs[col+1] - 1
        return x0, x1

    def GetColumnRect(self, col):
        x0, x1 = self._GetColumnWidthExtent(col)

        r = self.GetItemRect(0)
        y0 = r.y
        y1 = self.GetClientSize()[1]

        x_scroll = self.GetScrollPos(wx.HORIZONTAL)

        return wx.RectPP(wx.Point(x0 - x_scroll, y0),
                         wx.Point(x1 - x_scroll, y1))


    def GetCellRect(self, row, col):
        x0, x1 = self._GetColumnWidthExtent(col)

        r = self.GetItemRect(row)
        y0 = r.y
        y1 = r.GetBottom()

        x_scroll = self.GetScrollPos(wx.HORIZONTAL)

        return wx.RectPP(wx.Point(x0 - x_scroll, y0),
                         wx.Point(x1 - x_scroll, y1))

    def DeselectAll(self):
        self.SetItemState(-1, 0, wx.LIST_STATE_SELECTED)
        # fallback. for extremely long lists a generator should be used
        #for i in xrange(self.GetItemCount()):
        #    self.SetItemState(i, 0, wx.LIST_STATE_SELECTED)

    def InsertRow(self, itemData, lr, sort=True, colour=None,
                  force_update_columns=[]):

        # pre-render all data
        image_id = self.get_column_image(lr)
        row_text = {}
        for i, name in enumerate(self.enabled_columns):
            row_text[i] = self.render_column_text(lr, name)

        if itemData not in self.itemData_to_row:
            # this is Add
            # TODO: insert in sorted order instead of sorting
            i = self.InsertStringItem(self.GetItemCount(), '')
            lr.index = i
            self.SetItemData(i, itemData)
            for col in xrange(len(self.enabled_columns)):
                self.SetStringItem(index=lr.index, col=col,
                                   label=row_text[col])
        else:
            # this is Update
            old_lr = self.itemData_to_row[itemData]
            lr.index = old_lr.index
            for col, colname in enumerate(self.enabled_columns):
                if lr[colname] != old_lr[colname] or \
                       colname in force_update_columns:
                    self.SetStringItem(index=lr.index, col=col,
                                       label=row_text[col])
        self.itemData_to_row[itemData] = lr
        self.index_to_itemData[i] = itemData

        if colour is not None:
            if self.GetItemTextColour(lr.index) != colour:
                self.SetItemTextColour(lr.index, colour)

        self.SetItemImage(lr.index, image_id)

        if sort:
            # TODO: move to update-only once things are inserted in sorted order
            self.SortItems()

    def SetItemImage(self, index, image_id):
        item = self.GetItem(index)
        if item.GetImage() != image_id:
            wx.ListCtrl.SetItemImage(self, index, image_id)

    def DeleteRow(self, itemData):
        lr = self.itemData_to_row.pop(itemData)
        self.DeleteItem(lr.index)
        self._update_indexes(lr.index)

    def GetRow(self, index):
        itemData = self.index_to_itemData[index]
        return self.itemData_to_row[itemData]

    def HasRow(self, itemData):
        return itemData in self.itemData_to_row

    # Persistence methods
    def get_column_widths(self):
        widths = {}
        for name in self.column_order:
            column = self.columns[name]
            if column.enabled:
                column.width = self.GetColumnWidth(column.GetColumn())
            widths[name] = column.width
        return widths

    def set_column_widths(self, widths):
        # backward compatibility with development versions
        if isinstance(widths, list):
            return

        for name, width in widths.iteritems():
            column = self.columns[name]
            column.width = width
            if column.enabled:
                self.SetColumnWidth(column.GetColumn(), column.width)

    def update_column_widths(self):
        for name in self.enabled_columns:
            column = self.columns[name]
            column.width = self.GetColumnWidth(column.GetColumn())

    def get_sort_column(self):
        if self._col < len(self.enabled_columns):
            sort_col = self.enabled_columns[self._col]
        else:
            sort_col = None

        return sort_col

    def get_sort_order(self):
        return self._colSortFlag[self._col]


class HashableListView(BTListCtrl):
    """wx.ListCtrl expects integer identifiers for each row.  This
    subclass lets you use any hashable as the identifier instead."""

    def __init__(self, *a, **k):
        BTListCtrl.__init__(self, *a, **k)
        self.itemData_to_hashable = {}
        self.hashable_to_itemData = {}
        self.unique_index = 0

    def GetNewItemData(self):
        self.unique_index += 1
        return self.unique_index

    def GetItemData(self, index):
        itemData = BTListCtrl.GetItemData(self, index)
        return self.itemData_to_hashable[itemData]

    def SetItemData(self, index, hashable):
        itemData = self.hashable_to_itemData[hashable]
        BTListCtrl.SetItemData(self, index, itemData)

    def InsertRow(self, hashable, row, sort=True, colour=None,
                  force_update_columns=[]):
        if hashable not in self.hashable_to_itemData:
            itemData = self.GetNewItemData()
            self.hashable_to_itemData[hashable] = itemData
            self.itemData_to_hashable[itemData] = hashable
        b = BTListCtrl.InsertRow(self, hashable, row, sort=sort,
                                 colour=colour,
                                 force_update_columns=force_update_columns)
        return b

    def DeleteRow(self, hashable):
        itemData = self.hashable_to_itemData.pop(hashable)
        del self.itemData_to_hashable[itemData]
        return BTListCtrl.DeleteRow(self, hashable)

    def TranslateItemData(self, itemData):
        return self.itemData_to_hashable[itemData]

    def GetRowFromKey(self, hashable):
        return self.itemData_to_row[hashable]
