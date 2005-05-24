
class Deferred(object):
    def __init__(self):
        self.callbacks = []
        self.errbacks = []
        self.calledBack = False
        self.erredBack = False
        self.results = []
        self.failures = []
        
    def addCallback(self, cb, args=(), kwargs={}):
        self.callbacks.append((cb, args, kwargs))
        if self.calledBack:
            self.doCallbacks(self.results, [(cb, args, kwargs)])
        return self

    def addErrback(self, cb, args=(), kwargs={}):
        self.errbacks.append((cb, args, kwargs))
        if self.erredBack:
            self.doCallbacks(self.failures, [(cb, args, kwargs)])
        return self

    def addCallbacks(self, cb, eb, args=(), kwargs={},
                     ebargs=(), ebkwargs={}):
        self.addCallback(cb, args, kwargs)
        self.addErrback(eb, ebargs, ebkwargs)

    def callback(self, result):
        self.results.append(result)
        self.calledBack = True
        if self.callbacks:
            self.doCallbacks([result], self.callbacks)
        
    def errback(self, failed):
        self.failures.append(failed)
        self.erredBack = True
        if self.errbacks:
            self.doCallbacks([failed], self.errbacks)
        
    def doCallbacks(self, results, callbacks):
        for result in results:
            for cb, args, kwargs in callbacks:
                result = cb(result, *args, **kwargs) 
