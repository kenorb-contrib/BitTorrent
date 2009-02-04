from BTL.reactor_magic import reactor
from BTL.greenlet_yielddefer import like_yield, coroutine
from BTL.greenlet_coro import timeout_yield, wait, default_yield_timeout
from twisted.internet.defer import TimeoutError
from twisted.trial.unittest import TestCase
import sys

default_yield_timeout = 0.5

@coroutine
def f():
    return 5

@coroutine
def g(t):
    sys.stdout.flush()
    like_yield(wait(t))
    return 6

@coroutine
def exc():
    raise Exception( "Bling Bling" )

class TimeoutYieldTest(TestCase):
    def tearDown(self):
        # eliminate all calls in the event queue.
        for dc in reactor.getDelayedCalls():
            dc.cancel()

    @coroutine
    def test0(self):
        self.assert_(like_yield(f()) == 5, "should have returned 5.")
        self.assert_(like_yield(g(1)) == 6, "should have returned 6.")
        try:
            like_yield(exc())
            self.assert_(False, "like_yield should've raised exception.")
        except Exception, e:
            pass

    @coroutine
    def test1(self):
        self.assert_(timeout_yield(f()) == 5, "should return 5" )
        like_yield(wait(1))

    @coroutine
    def test2(self):
        self.assert_(timeout_yield(f(), timeout=1) == 5,
                     "with specified timeout should still return 5" )
        like_yield(wait(1))

    @coroutine
    def test3(self):
        self.assert_( timeout_yield(g(.1), timeout=.5) == 6,
                      "should return 6." )
        like_yield(wait(1))

    @coroutine
    def test4(self):
        try:
            print timeout_yield(g(1), timeout=.5)
            self.assert_(False, "should've timed out." )
        except TimeoutError:
            pass

        like_yield(wait(1)) 

    @coroutine
    def test5(self):
        try:
            print timeout_yield(exc())
            self.assert_(False, "should've raised an exception")
        except:
            pass
        like_yield(wait(1))

