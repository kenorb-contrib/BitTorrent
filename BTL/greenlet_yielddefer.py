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

    __slots__ = ['root', 'yielded_once', 'finished']

    def __init__(self, root, df, _f, *a, **kw):
        self.root = root
        self.yielded_once = False
        self.finished = False
        greenlet.greenlet.__init__(self,
                                   lambda : self.body(df, _f, *a, **kw))

    def body(self, df, _f, *a, **kw):
        try:
            v = _f(*a, **kw)
        except:
            self.finished = True
            df.errback(defer.Failure())
        else:
            self.finished = True
            # trigger the deferred that had been returned from launch_coroutine
            # to the caller of the coroutine.
            df.callback(v)
        return df

    def switch(self, *a):
        g = greenlet.getcurrent()
        if (isinstance(g, GreenletWithDeferred) and
            g.finished and g.parent == self):
            # control will return to the parent anyway, and switching to it
            # causes a memory leak (greenlets don't participate in gc).
            if a:
                return a[0]
            return                
        return greenlet.greenlet.switch(self, *a)


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

# like_yield may be called multiple times in a function.
# 
# @coroutine 
# def f():
#    like_yield(a())
#    ...
#    like_yield(b())
#    ...
#    x = like_yield(c())
#    return x
#
#
# The first like_yield in f, switches to the parent.  This allows the
# parent (i.e., the caller of the coroutine) to set up deferreds or
# perform other operations that should take place while waiting for a
# result.
#
# Subsequent yields to the parent would serve no useful purpose since
# the parent cannot progress until f() provides a result.  Thus
# subsequent like_yields switch to the root greenlet, i.e., the
# reactor's greenlet.  The reactor reenters its main event loop and
# the program progresses until a deferred is triggered which allows f
# to complete.  When f completes, it returns to the outermost
# function in its greenlet, which is GreenletWithDeferred.body().
# body() calls the deferred that had been returned from launch_coroutine.

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
        while not df.called or df.paused:
            g.switch()
    assert df.called and not df.paused
    return df.getResult()
