# by Myers Carpenter and John Hoffman
# see LICENSE.txt for license information

from wxPython.wx import *
from common import FONT, ICON, _StaticText, ICONDIR
from threading import Thread

try:
    True
except:
    True = 1
    False = 0

priorityIDs = [wxNewId(),wxNewId(),wxNewId(),wxNewId()]
# prioritycolors = [wxLIGHT_GREY, wxRED, wxBLACK, wxBLUE]
prioritycolors = [ wxColour(160,160,160),
                   wxColour(255,64,0),
                   wxColour(0,0,0),
                   wxColour(64,64,255) ]



def size_format(s):
    if (s < 1024):
        r = str(s) + 'B'
    elif (s < 1048576):
        r = str(int(s/1024)) + 'KiB'
    elif (s < 1073741824L):
        r = str(int(s/1048576)) + 'MiB'
    elif (s < 1099511627776L):
        r = str(int((s/1073741824.0)*100.0)/100.0) + 'GiB'
    else:
        r = str(int((s/1099511627776.0)*100.0)/100.0) + 'TiB'
    return(r)

def comma_format(s):
    r = str(s)
    for i in range(len(r)-3, 0, -3):
        r = r[:i]+','+r[i:]
    return(r)

hexchars = '0123456789abcdef'
hexmap = []
for i in xrange(256):
    x = hexchars[(i&0xF0)/16]+hexchars[i&0x0F]
    hexmap.append(x)

def tohex(s):
    r = []
    for c in s:
        r.append(hexmap[ord(c)])
    return ''.join(r)


class DetailsBox:

    def __init__(self, info_hash, metainfo, priority = None, bgallocfunc = None):
        self.priority = priority
        self.bgallocfunc = bgallocfunc
        self.fileList = None
        self.refresh_details = True

        self.filestatusIcons = wxImageList(16, 16)
        self.filestatusIcons.Add(wxBitmap(os.path.join(ICONDIR,'black1.ico'),wxBITMAP_TYPE_ICO))
        self.filestatusIcons.Add(wxBitmap(os.path.join(ICONDIR,'yellow1.ico'), wxBITMAP_TYPE_ICO))
        self.filestatusIcons.Add(wxBitmap(os.path.join(ICONDIR,'green1.ico'), wxBITMAP_TYPE_ICO))

        announce = metainfo.get('announce',None)
        announce_list = metainfo.get('announce-list',None)
        info = metainfo['info']
        piece_length = info['piece length']
        self.files = info.get('files',None)

        self.frame = wxFrame(None, -1, 'Torrent Details ', size = wxSize(405,230))
        if ICON():
            self.frame.SetIcon(ICON())

        panel = wxPanel(self.frame, -1, size = wxSize (400,220))

        StaticText = _StaticText(panel, style = wxALIGN_CENTER_VERTICAL)

        colSizer = wxFlexGridSizer(cols = 1, vgap = 3)
        colSizer.AddGrowableCol(0)

        titleSizer = wxBoxSizer(wxHORIZONTAL)
        aboutTitle = StaticText('Details about ' + self.filename, +4)

        titleSizer.Add (aboutTitle)
        colSizer.Add (titleSizer)

        detailSizer = wxFlexGridSizer(cols = 2, vgap = 6)

        if self.files:
            detail1Sizer = wxFlexGridSizer(cols = 1, vgap = 6)
            detail1Sizer.Add(StaticText('directory name : ' + info['name']))
            colSizer.Add (detail1Sizer)

            bgallocbuttonSizer = wxFlexGridSizer(cols = 4, hgap = 4, vgap = 0)
            bgallocbuttonSizer.Add(StaticText('(right-click to set priority)',self.FONT-1),0,wxALIGN_BOTTOM)
            bgallocbuttonSizer.Add(StaticText('(finish allocation)'), -1, wxALIGN_CENTER_VERTICAL)
            bgallocButton = wxBitmapButton(panel, -1, self.allocbuttonBitmap, size = (52,20))
            EVT_BUTTON(self.frame, bgallocButton.GetId(), self.bgalloc)
            bgallocbuttonSizer.Add(bgallocButton, -1, wxALIGN_CENTER)
            bgallocbuttonSizer.AddGrowableCol(0)
            colSizer.Add(bgallocbuttonSizer, -1, wxEXPAND)

            total = 0

            fileListID = wxNewId()
            fileList = wxListCtrl(panel, fileListID,
                                  wxPoint(-1,-1), (325,100), wxLC_REPORT)
            self.fileList = fileList
            fileList.SetImageList(self.filestatusIcons, wxIMAGE_LIST_SMALL)

            fileList.SetAutoLayout (True)
            fileList.InsertColumn(0, "file")
            fileList.InsertColumn(1, "", format=wxLIST_FORMAT_RIGHT, width=55)
            fileList.InsertColumn(2, "")

            for i in range(len(info['files'])):
                x = wxListItem()
#                x.SetFont(self.default_font)
                fileList.InsertItem(x)

            x = 0
            for file in info['files']:
                path = ' '
                for item in file['path']:
                    if (path != ''):
                        path = path + "/"
                    path = path + item
                path += ' (' + str(file['length']) + ')'
                fileList.SetStringItem(x, 0, path)
                if file.has_key('md5sum'):
                    fileList.SetStringItem(x, 2, '    [' + str(file['md5sum']) + ']')
                x += 1
                total += file['length']
            fileList.SetColumnWidth(0,wxLIST_AUTOSIZE)
            fileList.SetColumnWidth(2,wxLIST_AUTOSIZE)

            total_name = 'archive size'
            colSizer.Add(fileList, 1, wxEXPAND)
            colSizer.AddGrowableRow(3)
        else:
            fileListID = None
            detailSizer.Add(StaticText('file name :'))
            detailSizer.Add(StaticText(info['name']))
            if info.has_key('md5sum'):
                detailSizer.Add(StaticText('MD5 hash :'))
                detailSizer.Add(StaticText(info['md5sum']))
            total = info['length']
            total_name = "file size"


        detailSizer.Add(StaticText('info_hash :'),0,wxALIGN_CENTER_VERTICAL)
        detailSizer.Add(wxTextCtrl(panel, -1, tohex(info_hash), size = (325, -1), style = wxTE_READONLY))
        num_pieces = int((file_length+piece_length-1)/piece_length)
        detailSizer.Add(StaticText(total_name + ' : '))
        detailSizer.Add(StaticText('%s (%s bytes)' % (size_format(file_length), comma_format(file_length))))
        detailSizer.Add(StaticText('pieces : '))
        if num_pieces > 1:
            detailSizer.Add(StaticText('%i (%s bytes each)' % (num_pieces, comma_format(piece_length))))
        else:
            detailSizer.Add(StaticText('1'))

        if announce_list is None:
            detailSizer.Add(StaticText('announce url : '),0,wxALIGN_CENTER_VERTICAL)
            detailSizer.Add(wxTextCtrl(panel, -1, announce, size = (325, -1), style = wxTE_READONLY))
        else:
            detailSizer.Add(StaticText(''))
            trackerList = wxListCtrl(panel, -1, wxPoint(-1,-1), (325,75), wxLC_REPORT)
            trackerList.SetAutoLayout (True)
            trackerList.InsertColumn(0, "")
            trackerList.InsertColumn(1, "announce urls")

            for tier in range(len(announce_list)):
                for t in range(len(announce_list[tier])):
                    i = wxListItem()
#                    i.SetFont(self.default_font)
                    trackerList.InsertItem(i)
            if announce is not None:
                for l in [1,2]:
                    i = wxListItem()
#                    i.SetFont(self.default_font)
                    trackerList.InsertItem(i)

            x = 0
            for tier in range(len(announce_list)):
                for t in range(len(announce_list[tier])):
                    if t == 0:
                        trackerList.SetStringItem(x, 0, 'tier '+str(tier)+':')
                    trackerList.SetStringItem(x, 1, announce_list[tier][t])
                    x += 1
            if announce is not None:
                trackerList.SetStringItem(x+1, 0, 'single:')
                trackerList.SetStringItem(x+1, 1, announce)
            trackerList.SetColumnWidth(0,wxLIST_AUTOSIZE)
            trackerList.SetColumnWidth(1,wxLIST_AUTOSIZE)
            detailSizer.Add(trackerList)

        if announce is None and announce_list is not None:
            announce = announce_list[0][0]
        if announce is not None:
            detailSizer.Add(StaticText('likely tracker :'))
            p = re.compile( '(.*/)[^/]+')
            self.turl = p.sub (r'\1', announce)
            trackerUrl = StaticText(self.turl, self.FONT, True, 'Blue')
            detailSizer.Add(trackerUrl)
        if metainfo.has_key('comment'):
            detailSizer.Add(StaticText('comment :'))
            detailSizer.Add(StaticText(metainfo['comment']))
        if metainfo.has_key('creation date'):
            detailSizer.Add(StaticText('creation date :'))
            try:
                detailSizer.Add(StaticText(
                    strftime('%x %X',localtime(metainfo['creation date']))))
            except:
                try:
                    detailSizer.Add(StaticText(metainfo['creation date']))
                except:
                    detailSizer.Add(StaticText('<cannot read date>'))

        detailSizer.AddGrowableCol(1)
        colSizer.Add (detailSizer, 1, wxEXPAND)

        okButton = wxButton(panel, -1, 'Ok')
#        okButton.SetFont(self.default_font)
        colSizer.Add(okButton, 0, wxALIGN_RIGHT)
        colSizer.AddGrowableCol(0)

        if not self.configfileargs['gui_stretchwindow']:
            aboutTitle.SetSize((400,-1))
        else:
            panel.SetAutoLayout(True)

        border = wxBoxSizer(wxHORIZONTAL)
        border.Add(colSizer, 1, wxEXPAND | wxALL, 4)
        panel.SetSizer(border)
        panel.SetAutoLayout(True)

        if self.fileList and self.priority:        
            self.refresh_priority()
            EVT_LIST_ITEM_RIGHT_CLICK(self.frame, fileListID, self.set_priority)

        EVT_LEFT_DOWN(trackerUrl, self.open_trackerurl)
        EVT_CLOSE(self.frame, self.close)

        self.frame.Show ()
        border.Fit(panel)
        self.frame.Fit()

#        self.dow.filedatflag.set()


    def close(self, evt=None):
        self.frame.Destroy()
        self.frame = None
        self.fileList = None
#        self.dow.filedatflag.clear()


    def refresh_priority(self):
        for i in xrange(len(self.files)):
            item = self.fileList.GetItem(i)
            p = self.priority[i]
            item.SetTextColour(prioritycolors[p+1])
            self.fileList.SetItem(item)
        self.fileList.Refresh()
        return True


    def set_priority(self, evt):
        self.selected = []
        i = -1
        while True:
            i = self.fileList.GetNextItem(i,state=wxLIST_STATE_SELECTED)
            if i == -1:
                break
            self.selected.append(i)
        if not self.selected:   # just in case
            return
        oldstate = self.priority[self.selected[0]]
        kind=wxITEM_RADIO
        for i in self.selected[1:]:
            if self.priority[i] != oldstate:
                oldstate = None
                kind = wxITEM_NORMAL
                break
        menu = wxMenu()
        menu.Append(priorityIDs[1], "download first", kind=kind)
        menu.Append(priorityIDs[2], "download normally", kind=kind)
        menu.Append(priorityIDs[3], "download later", kind=kind)
        menu.Append(priorityIDs[0], "download never", kind=kind)
        if oldstate is not None:
            menu.Check(self.priorityIDs[oldstate+1], True)
            
        for id in priorityIDs:
            EVT_MENU(self.frame, id, self.do_set_priority)

        self.frame.PopupMenu(menu, evt.GetPoint())
            

    def do_set_priority(self, evt):
        p = evt.GetId()
        priorities = self.priority.get_priorities()
        for i in xrange(len(self.priorityIDs)):
            if p == priorityIDs[i]:
                break
        else:
            raise Exception('engine malfunction')
        for ss in self.selected:
            priorities[ss] = i-1
        self.priority.set_priorities(priorities)
        self.refresh_priority()
        self.refresh_details = True
        self.selected = []


    def open_trackerurl(self, evt):
        try:
            Thread(target = open_new(self.turl)).start()
        except:
            pass


    def update(self, statistics):
        if not (self.fileList and statistics):
            return
        if not (self.refresh_details or statistics.filelistupdated):
            return
        self.refresh_details = False
        statistics.filelistupdated = False
        for i in range(len(statistics.filecomplete)):
            if self.priority[i] == -1:
                self.fileList.SetItemImage(i,0,0)
                self.fileList.SetStringItem(i,1,'')
                continue
            if statistics.fileinplace[i]:
                self.fileList.SetItemImage(i,2,2)
                self.fileList.SetStringItem(i,1,"done")
                continue
            if statistics.filecomplete[i]:
                self.fileList.SetItemImage(i,1,1)
                self.fileList.SetStringItem(i,1,"100%")
                continue
            self.fileList.SetItemImage(i,0,0)
            frac = int((len(statistics.filepieces2[i])-len(statistics.filepieces[i]))*100
                    /len(statistics.filepieces2[i]))
            if frac:
                self.fileList.SetStringItem(i,1,'%d%%' % (frac))
            else:
                self.fileList.SetStringItem(i,1,'')

