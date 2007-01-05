# Just like ThreadedResolver, but doesn't suck
#
# by Greg Hazel

import socket
import operator
from twisted.internet import error, defer, threads
from twisted.python import failure

class SaneThreadedResolver:
    # I won't do this. Zope.interface sucks.
    #implements(IResolverSimple)

    def __init__(self, reactor):
        self.reactor = reactor
        self._runningQueries = {}

    def _fail(self, name, err):
        err = error.DNSLookupError("address %r not found: %s" % (name, err))
        return failure.Failure(err)

    def _checkTimeout(self, result, name, userDeferred):
        if userDeferred in self._runningQueries:
            cancelCall = self._runningQueries.pop(userDeferred)
            cancelCall.cancel()

        if userDeferred.called:
            return

        if isinstance(result, failure.Failure):
            userDeferred.errback(self._fail(name, result.getErrorMessage()))
        else:
            userDeferred.callback(result)

    def _doGetHostByName(self, name, onStart):
        self.reactor.callFromThread(onStart)
        return socket.gethostbyname(name)

    def getHostByName(self, name, timeout = (1, 3, 11, 45)):
        if timeout:
            timeoutDelay = reduce(operator.add, timeout)
        else:
            timeoutDelay = 60
        userDeferred = defer.Deferred()
        def _onStart():
            cancelCall = self.reactor.callLater(
                timeoutDelay, self._checkTimeout,
                self._fail(name, "timeout error"), name, userDeferred)
            self._runningQueries[userDeferred] = cancelCall
        lookupDeferred = threads.deferToThread(self._doGetHostByName, name, _onStart)
        lookupDeferred.addBoth(self._checkTimeout, name, userDeferred)
        return userDeferred
