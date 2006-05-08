import sys
sys.path = ['.',] + sys.path #HACK

import os
from BitTorrent.platform import plugin_path, app_root
plugin_path.append(os.path.join(app_root[:-5], 'BitTorrent', 'Plugins')) #HACK

from BitTorrent.FeedManager import FeedManager

def gui_wrap(f, *a):
    f(*a)

feedmanager = FeedManager({}, gui_wrap)

# Test RSS 2 feed:
feed = 'http://www.prodigem.com/torrents/rss/pep_delicious.xml'
feedmanager.new_channel(feed)

# Test RAW feed:
feed = 'http://search.bittorrent.com/search.jsp?query=Ubuntu&Submit2=Search'
feedmanager.new_channel(feed)

import time
time.sleep(10)
