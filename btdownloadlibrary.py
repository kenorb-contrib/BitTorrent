# Written by Bram Cohen
# see LICENSE.txt for license information

import BitTorrent.download
from threading import Event

def download(url, file):
    return BitTorrent.download.download(['--url=' + url, '--saveas=' + file], 
        lambda x: x, lambda a, b: None, Event(), 80, close_at_end = 1)
