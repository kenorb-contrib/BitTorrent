
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
            self.doCallbacks(self.results, self.callbacks)
            self.results = []
        return self

    def addErrback(self, cb, args=(), kwargs={}):
        self.errbacks.append((cb, args, kwargs))
        if self.erredBack:
            self.doCallbacks(self.failures, self.errbacks)
            self.failures = []
        return self

    def addCallbacks(self, cb, eb, args=(), kwargs={},
                     ebargs=(), ebkwargs={}):
        self.addCallback(cb, args, kwargs)
        self.addErrback(eb, ebargs, ebkwargs)

    def callback(self, result):
        self.results.append(result)
        self.calledBack = True
        if self.callbacks:
            self.doCallbacks(self.results, self.callbacks)
            self.results = []
        
    def errback(self, failed):
        self.failures.append(failed)
        self.erredBack = True
        if self.errbacks:
            self.doCallbacks(self.failures, self.errbacks)
            self.failures = []
        
    def doCallbacks(self, results, callbacks):
        for result in results:
            for cb, args, kwargs in callbacks:
                result = cb(result, *args, **kwargs) 
