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

# DO NOT USE THIS MODULE!
# this is for khashmir compatability only. new application should use BTL.defer

class Deferred(object):
    __slots__ = ['callbacks', 'errbacks',
                 'calledBack', 'erredBack',
                 'results', 'failures',]
    def __init__(self):
        self.callbacks = []
        self.errbacks = []
        self.calledBack = False
        self.erredBack = False
        self.results = []
        self.failures = []

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
            self.doCallbacks([failed], self.errbacks)

    def doCallbacks(self, results, callbacks):
        for result in results:
            for cb, args, kwargs in callbacks:
                result = cb(result, *args, **kwargs)
