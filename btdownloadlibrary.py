# Written by Bram Cohen
# This file is public domain
# The authors disclaim all liability for any damages resulting from
# any use of this software.

import BitTorrent.download
from threading import Event

def download(url, file):
    return BitTorrent.download.download(['--url=' + url, '--saveas=' + file], 
        lambda x: x, lambda a, b: None, Event(), 80)
