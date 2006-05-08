import sys
from twisted.internet import defer, reactor
from twisted.python import failure

# CRUFT
def getResult(df):
    if isinstance(df.result, failure.Failure):
        if df._debugInfo is not None:
            df._debugInfo.failResult = None
        df.result.raiseException()
    return df.result

class ThreadProxy(object):
    __slots__ = ('obj', 'queue_task')
    def __init__(self, obj, queue_task):
        self.obj = obj
        self.queue_task = queue_task

    def __gen_call_wrapper__(self, f):
        def outer(*args, **kwargs):
            df = defer.Deferred()
            # CRUFT
            df.getResult = lambda : getResult(df)
            def inner(*args, **kwargs):
                try:
                    v = f(*args, **kwargs)
                except:
                    self.queue_task(df.errback, failure.Failure())
                else:
                    if isinstance(v, defer.Deferred):
                        self.queue_task(v.chainDeferred, df)
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


