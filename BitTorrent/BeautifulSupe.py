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

# A very very minimal BeautifulSoup immitation.
#
# BS uses SGMLlib to parse, which converts everything to lower case.
# This uses real xml parsing to mimic the parts of BS we use.

import xml.dom.minidom

def _getText(node):
    nodelist = node.childNodes
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(str(node.data))
    return rc

def _getNodesAsTags(root):
    nodelist = root.childNodes
    tags = []
    for node in nodelist:
        if node.nodeType == node.ELEMENT_NODE:
            tags.append(Tag(node))
    return tags

class Tag(object):
    def __init__(self, node):
        self.node = node
        self.name = node.nodeName
        self.contents = _getNodesAsTags(self.node)
        text = _getText(self.node)
        self.contents += text
        self.text = ''.join(text)

    def child_elements(self):
        children = []
        for tag in self.contents:
            if isinstance(tag, Tag):
                children.append(tag)
        return children

    def get(self, tagname):
        got = self.first(tagname)
        if got:
            return got.text

    def first(self, tagname):
        found = None
        
        for tag in self.contents:
            if isinstance(tag, Tag):
                if tag.name == tagname:
                    found = tag
                    break
        
        return found
   
class BeautifulSupe(object):

    def __init__(self, data):
        #please don't give us your null terminators
        data = data.strip(chr(0))
        self.dom = xml.dom.minidom.parseString(data)
    
    def first(self, tagname, root = None):
        found = None
        if root == None:
            e = self.dom.getElementsByTagName(tagname)
            if len(e) > 0:
                found = e[0]
        else:
            for node in root.childNodes:
                if node.nodeName == tagname:
                    found = node
                    break

        if not found:
            return None

        tag = Tag(found)
        return tag

    def fetch(self, tagname, restraints = {}):
        e = self.dom.getElementsByTagName(tagname)

        matches = []

        for node in e:
            match = 1
            
            for restraint in restraints:
                f = self.first(restraint, node)
                if not f:
                    match = 0
                    break
                text = restraints[restraint]
                if not f.contents[0].startswith(text):
                    match = 0
                    break
                
            if match:
                tag = Tag(node)
                matches.append(tag)

        return matches


    def scour(self, prefix, suffix = None, node = None):
        if node is None:
            root = self.dom.getElementsByTagName(self.dom.documentElement.tagName)[0]
            node = root

        matches = []

        for node in node.childNodes:
            match = 0
            
            name = node.nodeName

            if name.startswith(prefix):
                if suffix:
                    if name.endswith(suffix):
                        match = 1
                else:
                    match = 1
                    
            if match:
                tag = Tag(node)
                matches.append(tag)

            matches += self.scour(prefix, suffix, node)

        return matches        

