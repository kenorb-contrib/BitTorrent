## some python code to handle managing multiple DL's at once
import callbacks
from BitTorrent.download import download
from threading import Event
from thread import start_new_thread

# internal functions
def _newDlWithUrl(url, cookie, flag):
    prox = callbacks.getProxy(cookie)
    download(['--url=%s' % url], prox.chooseFile, prox.display, prox.finished, flag, 80)
    
def _newDlWithFile(file, cookie, flag):
    prox = callbacks.getProxy(cookie)
    download(['--responsefile=%s' % file], prox.chooseFile, prox.display, prox.finished, flag, 80)

# external API
def newDlWithUrl(url, cookie, flag):
    start_new_thread(_newDlWithUrl, (url, cookie, flag))
def newDlWithFile(file, cookie, flag):
    start_new_thread(_newDlWithFile, (file, cookie, flag))
