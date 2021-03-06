#
# Copyright (c) 2001-2004 Twisted Matrix Laboratories.
# See LICENSE for details.

# 

"""Test SOAP support."""

import time

try:
    import SOAPpy
except ImportError:
    SOAPpy = None
    class SOAPPublisher: pass
else:
    from twisted.web import soap
    SOAPPublisher = soap.SOAPPublisher

from twisted.trial import unittest
from twisted.web import server
from twisted.internet import reactor, defer
from twisted.python import log


class Test(SOAPPublisher):

    def soap_add(self, a, b):
        return a + b

    def soap_kwargs(self, a=1, b=2):
        return a + b
    soap_kwargs.useKeywords=True
    
    def soap_triple(self, string, num):
        return [string, num, None]

    def soap_struct(self):
        return SOAPpy.structType({"a": "c"})
    
    def soap_defer(self, x):
        return defer.succeed(x)

    def soap_deferFail(self):
        return defer.fail(ValueError())

    def soap_fail(self):
        raise RuntimeError

    def soap_deferFault(self):
        return defer.fail(ValueError())

    def soap_complex(self):
        return {"a": ["b", "c", 12, []], "D": "foo"}

    def soap_dict(self, map, key):
        return map[key]


class SOAPTestCase(unittest.TestCase):

    def setUp(self):
        self.p = reactor.listenTCP(0, server.Site(Test()),
                                   interface="127.0.0.1")
        self.port = self.p.getHost().port

    def tearDown(self):
        return self.p.stopListening()

    def proxy(self):
        return soap.Proxy("http://127.0.0.1:%d/" % self.port)

    def testResults(self):
        inputOutput = [
            ("add", (2, 3), 5),
            ("defer", ("a",), "a"),
            ("dict", ({"a": 1}, "a"), 1),
            ("triple", ("a", 1), ["a", 1, None])]

        dl = []
        for meth, args, outp in inputOutput:
            d = self.proxy().callRemote(meth, *args)
            d.addCallback(self.assertEquals, outp)
            dl.append(d)

        # SOAPpy kinda blows.
        d = self.proxy().callRemote('complex')
        d.addCallback(lambda result: result._asdict())
        d.addCallback(self.assertEquals, {"a": ["b", "c", 12, []], "D": "foo"})
        dl.append(d)

        # We now return to our regularly scheduled program, already in progress.
        return defer.DeferredList(dl, fireOnOneErrback=True)

if not SOAPpy:
    SOAPTestCase.skip = "SOAPpy not installed"
