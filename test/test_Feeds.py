# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
sys.path = ['.',] + sys.path #HACK

import os
from BTL.platform import plugin_path, app_root
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
