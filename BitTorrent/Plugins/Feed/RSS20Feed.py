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
from BitTorrent.FeedManager import FeedPlugin, get_content

class RSS20Feed(FeedPlugin):
    subtype = 'rss2'

    def __init__(self, main, url, doc=None):
        context = doc.xpathNewContext()
        title       = get_content(context.xpathEval('/rss/channel/title'      ))
        description = get_content(context.xpathEval('/rss/channel/description'))        
        FeedPlugin.__init__(self, main, url, title, description, doc)
        context.xpathFreeContext()

    def _supports(version):
        if version >= '4.3.0':
            return True
        return False

    supports = staticmethod(_supports)
    
    def _matches_type(mimetype, subtype):
        if (mimetype == RSS20Feed.mimetype and 
            subtype  == RSS20Feed.subtype     ):
            return True
        return False

    matches_type = staticmethod(_matches_type)

    def get_items(self):
        if self.doc is None:
            return []
        context = self.doc.xpathNewContext()
        res = context.xpathEval('/rss/channel/item')
        items = []
        for i in res:
            title       = get_content(i.xpathEval('title'         ))
            description = get_content(i.xpathEval('description'   ))
            url         = get_content(i.xpathEval('enclosure/@url'))
            if None not in (title, description, url):
                item = (url, title, description)
                items.append(item)
        context.xpathFreeContext()
        return items
