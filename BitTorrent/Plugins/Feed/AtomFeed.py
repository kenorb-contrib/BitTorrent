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

class AtomFeed(FeedPlugin):
    namespace_prefix = 'atom'
    subtype = 'atom'

    def __init__(self, ui_wrap_func, main, url, doc=None):
        root = doc.children
        self.namespace = root.ns().content
        context = self._new_context(doc)
        title = get_content(context.xpathEval(self._add_ns('/feed/title')))
        description = title
        FeedPlugin.__init__(self, ui_wrap_func, main, url, title, description, doc)
        context.xpathFreeContext()

    def _supports(version):
        if version >= '4.3.0':
            return True
        return False

    supports = staticmethod(_supports)

    def _matches_type(mimetype, subtype):
        if (mimetype == AtomFeed.mimetype and 
            subtype  == AtomFeed.subtype     ):
            return True
        return False

    matches_type = staticmethod(_matches_type)
    
    def _add_ns(self, xpath_expression):
        return xpath_expression.replace('/', '/%s:' % self.namespace_prefix)

    def _new_context(self, doc=None):
        if doc is None:
            doc = self.doc
        context = doc.xpathNewContext()
        context.xpathRegisterNs(self.namespace_prefix, self.namespace)
        return context

    def get_items(self):
        items = []
        if self.doc is None:
            return items
        context = self._new_context()
        res = context.xpathEval( self._add_ns('/feed/entry') )
        for i in res:
            DISGUSTING_HACK = "*[local-name()='%%s' and namespace-uri()='%s']" % self.namespace
            desc  = get_content(i.xpathEval(DISGUSTING_HACK % 'summary'))
            title = get_content(i.xpathEval(DISGUSTING_HACK % 'title'))
            url   = get_content(i.xpathEval(DISGUSTING_HACK % 'link' + '/@href'))
            title = title.strip()
            item = (url, title, desc)
            items.append(item)
        
        return items
