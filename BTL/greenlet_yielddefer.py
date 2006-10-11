# Copyright (c) 2005 Greg Hazel
#
# screw all those other people

import greenlet
from BTL import defer

class GreenletWithDeferred(greenlet.greenlet):

    __slots__ = ['deferred', 'yielded_once']
    
    def __init__(self, deferred, _f, *a, **kw):
        self.deferred = deferred
        self.yielded_once = False
        greenlet.greenlet.__init__(self, lambda : self.body(_f, *a, **kw))

    def body(self, _f, *a, **kw):
        try:
            r = _f(*a, **kw)
        except:
            self.deferred.errback(defer.Failure())
        else:
            self.deferred.callback(r)        

    def _recall(self, r=None):
        self.switch()


def launch_coroutine(_f, *a, **kw):
    g = greenlet.getcurrent()
    main_df = defer.Deferred()
    g = GreenletWithDeferred(main_df, _f, *a, **kw)
    g._recall()
    return main_df

def coroutine(func):
    def replacement(*a, **kw):
        return launch_coroutine(func, *a, **kw)
    return replacement

def like_yield(df):
    assert isinstance(df, defer.Deferred)
    if not df.called:
        g = greenlet.getcurrent()
        assert isinstance(g, GreenletWithDeferred)
        df.addBoth(g._recall)
        if not g.yielded_once:
            g.yielded_once = True
            g = g.parent
        else:
            while g.parent:
                g = g.parent
        g.switch()
    return df.getResult()
