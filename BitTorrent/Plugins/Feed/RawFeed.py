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
#
# Written by Matt Chisholm
import sre
from BitTorrent import zurllib
from BitTorrent.FeedManager import FeedPlugin

class RawFeed(FeedPlugin):

    torrent_pattern = sre.compile("(http://[a-zA-Z0-9._~:/?#\[\]@!$&'()*+,;=-]+?\.torrent)")

    def __init__(self, main, url, doc=None):
        FeedPlugin.__init__(self, main, url, url, url, doc)
        self.main = main
        self.data = None

    def _supports(version):
        if version >= '4.3.0':
            return True
        return False

    supports = staticmethod(_supports)

    def _matches_type(mimetype, subtype):
        if (mimetype is None and 
            subtype.lower()  == subtype     ):
            return True
        return False

    matches_type = staticmethod(_matches_type)

    def _update(self, doc=None):
        u = zurllib.urlopen(self.url)
        self.data = u.read()
        u.close()
        self.main.show_status(self.get_items())
        self.main.feed_was_updated(self.url)
        
    def get_items(self):
        items = []
        if self.data is None:
            return items
        urls = self.torrent_pattern.findall(self.data)
        for u in urls:
            i = (u, u, u)
            items.append(i)
        return items
