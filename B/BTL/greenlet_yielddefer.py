# The contents of this file are subject to the Python Software Foundation
# License Version 2.3 (the License).  You may not copy or use this file, in
# either source code or executable form, except in compliance with the License.
# You may obtain a copy of the License at http://www.python.org/license.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.
#
# by Greg Hazel

import greenlet
from BTL import defer


class GreenletWithDeferred(greenlet.greenlet):

    __slots__ = ['root', 'yielded_once']
    
    def __init__(self, root, df, _f, *a, **kw):
        self.root = root
        self.yielded_once = False
        greenlet.greenlet.__init__(self,
                                   lambda : self.body(df, _f, *a, **kw))
            
    def body(self, df, _f, *a, **kw):
        return defer.run_deferred(df, _f, *a, **kw)


def launch_coroutine(_f, *a, **kw):
    parent = greenlet.getcurrent()
    if isinstance(parent, GreenletWithDeferred):
        parent = parent.root
    df = defer.Deferred()
    g = GreenletWithDeferred(parent, df, _f, *a, **kw)
    g.switch()
    return df

def coroutine(_f):
    def replacement(*a, **kw):
        return launch_coroutine(_f, *a, **kw)
    return replacement

def like_yield(df):
    assert isinstance(df, defer.Deferred)
    if not df.called or df.paused:
        g = greenlet.getcurrent()
        assert isinstance(g, GreenletWithDeferred)
        df.addBoth(g.switch)
        if not g.yielded_once:
            g.yielded_once = True
            g = g.parent
        else:
            g = g.root
        g.switch()
    assert df.called and not df.paused
    return df.getResult()
