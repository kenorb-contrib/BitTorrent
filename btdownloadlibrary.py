from BitTorrent.download import downloadurl, defaults
from BitTorrent.parseargs import parseargs
from threading import Event

def download(url, filename):
    return downloadurl(url, lambda x, f = filename: f, lambda p, q: None, Event(), parseargs([], defaults, 0, 0)[0])
