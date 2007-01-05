import win32gui
TTS_BALLOON = 0x40
WM_USER = 1024
WM_TRAYMESSAGE = WM_USER + 20

def _get_nid(hwnd, id, flags, callbackmessage, hicon, title, msg):
        nid = (hwnd, id, flags, callbackmessage, hicon)
        nid = list(nid)

        nid.append('') # the tip
        nid.append(msg) # the balloon message
        nid.append(15000) # the timeout
        nid.append(title) # the title
        nid.append(win32gui.NIIF_INFO) # also warning and error available

        return tuple(nid)

_hwnd = None
def find_traywindow_hwnd():
    global _hwnd
    if _hwnd is None:
        try:
            _hwnd = win32gui.FindWindowEx(0, 0, 'wxWindowClassNR', '')
        except:
            pass
    return _hwnd

def SetBalloonTip(hicon, title, msg):
    hwnd = find_traywindow_hwnd()
    id = 99 # always 99
    flags = win32gui.NIF_MESSAGE | win32gui.NIF_ICON | win32gui.NIF_INFO
    callbackmessage = WM_TRAYMESSAGE
    nid = _get_nid(hwnd, id, flags, callbackmessage, hicon, title, msg)
    try:
        win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, nid)
    except:
        pass
