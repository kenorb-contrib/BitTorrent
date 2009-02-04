# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import generators, nested_scopes

from twisted.internet import reactor

from twisted.trial import unittest, util

from BTL.defer import Deferred
from BTL.greenlet_yielddefer import coroutine, like_yield
from twisted.internet import defer

def getThing():
    d = Deferred()
    reactor.callLater(0, d.callback, "hi")
    return d

def getOwie():
    d = Deferred()
    def CRAP():
        d.errback(ZeroDivisionError('OMG'))
    reactor.callLater(0, CRAP)
    return d

class DefGenTests(unittest.TestCase):
    @coroutine
    def _genWoosh(self):

        x = like_yield(getThing())

        self.assertEquals(x, "hi")

        try:
            like_yield(getOwie())
        except ZeroDivisionError, e:
            self.assertEquals(str(e), 'OMG')
        return "WOOSH"


    def testBasics(self):
        return self._genWoosh().addCallback(self.assertEqual, 'WOOSH')

    def testBuggyGen(self):
        @coroutine
        def _genError():
            like_yield(getThing())
            1/0

        return self.assertFailure(_genError(), ZeroDivisionError)


    def testNothing(self):
        @coroutine
        def _genNothing():
            if 0: return 1

        return _genNothing().addCallback(self.assertEqual, None)

    def testDeferredYielding(self):
        # See the comment _deferGenerator about d.callback(Deferred).
        @coroutine
        def _genDeferred():
            like_yield(getThing())

        #return self.assertFailure(_genDeferred(), TypeError)
        return _genDeferred().addCallback(self.assertEqual, None)


    def testHandledTerminalFailure(self):
        """
        Create a Deferred Generator which yields a Deferred which fails and
        handles the exception which results.  Assert that the Deferred
        Generator does not errback its Deferred.
        """
        class TerminalException(Exception):
            pass

        @coroutine
        def _genFailure():
            x = defer.fail(TerminalException("Handled Terminal Failure"))
            try:
                like_yield(x)
            except TerminalException:
                pass
        return _genFailure().addCallback(self.assertEqual, None)


    def testHandledTerminalAsyncFailure(self):
        """
        Just like testHandledTerminalFailure, only with a Deferred which fires
        asynchronously with an error.
        """
        class TerminalException(Exception):
            pass


        d = defer.Deferred()
        @coroutine
        def _genFailure():
            try:
                like_yield(d)
            except TerminalException:
                pass
        deferredGeneratorResultDeferred = _genFailure()
        d.errback(TerminalException("Handled Terminal Failure"))
        return deferredGeneratorResultDeferred.addCallback(
            self.assertEqual, None)


    def testStackUsage(self):
        # Make sure we don't blow the stack when yielding immediately
        # available values
        @coroutine
        def _loop():
            for x in range(5000):
                # Test with yielding a deferred
                like_yield(defer.succeed(1))
            return 0

        return _loop().addCallback(self.assertEqual, 0)

    def testStackUsage2(self):
        @coroutine
        def _loop():
            for x in range(5000):
                # Test with yielding a random value
                return 1
            return 0

        return _loop().addCallback(self.assertEqual, 1)

