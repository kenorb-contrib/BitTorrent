# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

import sys
import weakref
import traceback
#import thread
import BitTorrent.stackthreading as threading
from twisted.internet import defer
from twisted.python import failure

debug = False

# backport
def getResult(self):
    if isinstance(self.result, failure.Failure):
        r = self.result
        self.addErrback(lambda fuckoff: None)
        r.raiseException()
    return self.result
defer.Deferred.getResult = getResult


class Deferred(object):
    __slots__ = ['callbacks', 'errbacks',
                 'calledBack', 'erredBack', 'called_errbacks',
                 'results', 'failures',
                 'weakref', '__weakref__',
                 'stack']
    def __init__(self):
        if debug:
            self.stack = traceback.format_stack()[:-1]
        else:
            self.stack = None
        #self.ident = thread.get_ident()
        self.callbacks = []
        self.errbacks = []
        self.calledBack = False
        self.erredBack = False
        # python is really, really dumb
        self.called_errbacks = [False,]
        self.results = []
        self.failures = []
        def pseudo_del(ref, failures=self.failures,
                       called_errbacks=self.called_errbacks,
                       stack=self.stack):
            # iterpreter shutdown
            if sys is None:
                return
            # so this checks to see if -any- errback has been called, not -all-.
            # See twisted deferreds for a better (although still broken!)
            # implementation of the correct metric.
            if failures and not called_errbacks[0]:
                sys.stderr.write("Unhandled error in BT Deferred:\n")
                if stack:
                    sys.stderr.writelines(stack)
                for failure in failures:
                    try:
                        traceback.print_exception(*failure)
                    except Exception, e:
                        sys.stderr.write("%s\n" % str(failure))
        self.weakref = weakref.ref(self, pseudo_del)

    def getResult(self):
        #if self.ident != thread.get_ident():
        #    sys.stderr.write("getResult from the wrong thread!\n")
        #    sys.stderr.writelines(self.stack)
        #assert self.ident == thread.get_ident()
        self.called_errbacks[0] = True
        if self.failures:
            # what should I do with multiple failures?
            assert isinstance(self.failures[0], tuple), "Not a known failure type:" + str(self.failures[0])
            exc_type, value, tb = self.failures[0]
            try:
                if tb.__class__.__name__ == 'FakeTb':
                    tb = tb.tb_orig
            except:
                pass
            raise exc_type, value, tb
        if len(self.results) > 1:
            return self.results
        elif len(self.results) == 1:
            return self.results[0]
        return None

    def addCallback(self, cb, *args, **kwargs):
        assert callable(cb)
        t = (cb, args, kwargs)
        self.callbacks.append(t)
        if self.calledBack:
            self.doCallbacks(self.results, [t])
        return self

    def addErrback(self, cb, *args, **kwargs):
        assert callable(cb)
        t = (cb, args, kwargs)
        self.errbacks.append(t)
        if self.erredBack:
            self.called_errbacks[0] = True
            self.doCallbacks(self.failures, [t])
        return self

    def addCallbacks(self, cb, eb, args=(), kwargs={},
                     ebargs=(), ebkwargs={}):
        self.addCallback(cb, *args, **kwargs)
        self.addErrback(eb, *ebargs, **ebkwargs)

    def chainDeferred(self, d):
        return self.addCallbacks(d.callback, d.errback)

    def callback(self, result):
        self.results.append(result)
        self.calledBack = True
        if self.callbacks:
            self.doCallbacks([result], self.callbacks)

    def errback(self, failed):
        self.failures.append(failed)
        self.erredBack = True
        if self.errbacks:
            self.called_errbacks[0] = True
            self.doCallbacks([failed], self.errbacks)

    def doCallbacks(self, results, callbacks):
        #if self.ident != thread.get_ident():
        #    sys.stderr.write("doCallbacks from the wrong thread!\n")
        #    sys.stderr.writelines(self.stack)
        #assert self.ident == thread.get_ident()
        for result in results:
            for cb, args, kwargs in callbacks:
                result = cb(result, *args, **kwargs)


# not totally safe, but a start.
# This lets you call callback/errback from any thread.
# The next step would be for addCallbak and addErrback to be safe.
class ThreadableDeferred(Deferred):
    def __init__(self, queue_func):
        assert callable(queue_func)
        self.queue_func = queue_func
        Deferred.__init__(self)

    def callback(self, result):
        self.queue_func(Deferred.callback, self, result)

    def errback(self, result):
        self.queue_func(Deferred.errback, self, result)
        

# go ahead and forget to call start()!
class ThreadedDeferred(Deferred):

    def __init__(self, queue_func, f, *args, **kwargs):
        Deferred.__init__(self)
        daemon = False
        if 'daemon' in kwargs:
            daemon = kwargs.pop('daemon')
        self.f = f
        start = True
        if queue_func is None:
            start = False
            queue_func = lambda f, *a, **kw : f(*a, **kw)
        self.queue_func = queue_func
        self.args = args
        self.kwargs = kwargs
        self.t = threading.Thread(target=self.run)
        self.t.setDaemon(daemon)
        if start:
            self.start()

    def start(self):
        self.t.start()

    def run(self):
        try:
            r = self.f(*self.args, **self.kwargs)
            self.queue_func(self.callback, r)
        except:
            self.queue_func(self.errback, sys.exc_info())


class DeferredEvent(Deferred, threading._Event):
    def __init__(self, *a, **kw):
        threading._Event.__init__(self)
        Deferred.__init__(self, *a, **kw)
        
    def set(self):
        threading._Event.set(self)
        self.callback(None) # hmm, None?


def run_deferred(df, f, *a, **kw):
    try:
        v = f(*a, **kw)
    except:
        df.errback(sys.exc_info())
    else:
        df.callback(v)
    return df
        
