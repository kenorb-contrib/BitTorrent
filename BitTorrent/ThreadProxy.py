import sys
from twisted.internet import reactor
from BitTorrent.defer import Deferred

class ThreadProxy(object):
    __slots__ = ('obj', 'queue_task')
    def __init__(self, obj, queue_task):
        self.obj = obj
        self.queue_task = queue_task

    def __gen_call_wrapper__(self, f):
        def outer(*args, **kwargs):
            df = Deferred()
            def inner(*args, **kwargs):
                try:
                    v = f(*args, **kwargs)
                except:
                    # hm, the exc_info holds a reference to the deferred, I think
                    self.queue_task(df.errback, sys.exc_info())
                    #del df
                else:
                    if isinstance(v, Deferred):
                        # v is owned by the caller, so add the callback
                        # now, but the task itself should queue.
                        # lamdba over df here would break 'del df' above
                        # so do it with a local function.
                        def make_queueback(func):
                            return lambda r : self.queue_task(func, r)
                        v.addCallback(make_queueback(df.callback))
                        v.addErrback(make_queueback(df.errback))
                    else:
                        self.queue_task(df.callback, v)
            reactor.callFromThread(inner, *args, **kwargs)
            return df
        return outer

    def __getattr__(self, attr):
        a = getattr(self.obj, attr)
        if callable(a):
            return self.__gen_call_wrapper__(a)
        return a

    def call_with_obj(self, _f, *a, **k):
        w = self.__gen_call_wrapper__(_f)
        return w(self.obj, *a, **k)


