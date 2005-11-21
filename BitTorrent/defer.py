# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

class Deferred(object):
    def __init__(self):
        self.callbacks = []
        self.errbacks = []
        self.calledBack = False
        self.erredBack = False
        self.results = []
        self.failures = []
        
    def addCallback(self, cb, args=(), kwargs={}):
        assert callable(cb)
        self.callbacks.append((cb, args, kwargs))
        if self.calledBack:
            self.doCallbacks(self.results, [(cb, args, kwargs)])
        return self

    def addErrback(self, cb, args=(), kwargs={}):
        assert callable(cb)
        self.errbacks.append((cb, args, kwargs))
        if self.erredBack:
            self.doCallbacks(self.failures, [(cb, args, kwargs)])
        return self

    def addCallbacks(self, cb, eb, args=(), kwargs={},
                     ebargs=(), ebkwargs={}):
        assert callable(cb)
        assert callable(eb)
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
