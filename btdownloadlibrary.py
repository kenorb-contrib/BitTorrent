from BitTorrent.download import downloadurl
from threading import Event

def download(url, filename):
    return downloadurl(url, lambda x, f = filename: f, lambda p, q: None, Event(), {})
