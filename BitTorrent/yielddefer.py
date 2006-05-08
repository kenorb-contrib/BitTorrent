# yielddefer is an async programming mechanism with a blocking look-alike syntax
#
# from inside a generator launched with launch_coroutine:
# wait on a deferred to be called back by yielding it
# return None by simply returning
# return an exception by throwing one
# return a value by yielding a non-Deferred
#
# launch_coroutine maintains the illusion that the passed function
# (a generator) runs from beginning to end yielding when necessary
# for some job to complete and then continuing where it left off.
# 
# def f():
#    ...
#    df = some_thing_that_takes_time()
#    yield df
#    df.getResult() # Even if not expecting result.
#    ...
#    df = something_else()
#    yield df
#    result = df.getResult()
#    ...
# 
# Upon resuming from a yield point, the generator should 
# call getResult() even if no result is expected, so that
# exceptions generated while yielding are raised.
#
# by Greg Hazel

from __future__ import generators
import sys
import types
import traceback
# (half) CRUFT - remove when bittorrent uses twisted deferreds
from BitTorrent.defer import Deferred
from stackthreading import _print_traceback, _print
from twisted.internet import defer

debug = False

class GenWithDeferred(object):
    __slots__ = ['gen', 'deferred', 'stack']
    def __init__(self, gen, deferred):
        self.gen = gen
        self.deferred = deferred

        if debug:
            try:
                raise ZeroDivisionError
            except ZeroDivisionError:
                f = sys.exc_info()[2].tb_frame.f_back

            self.stack = traceback.extract_stack(f)
            # cut out GenWithDeferred() and launch_coroutine
            self.stack = self.stack[:-2]
        else:
            self.stack = []

def _queue_task_chain(v, queue_task, g):
    queue_task(_recall, queue_task, g)
    # twisted deferreds change the result based on what each callback returns!
    return v

class FakeTb(object):
    __slots__ = ['tb_frame', 'tb_lineno', 'tb_orig', 'tb_next']
    def __init__(self, frame, tb):
        self.tb_frame = frame
        self.tb_lineno = frame.f_lineno
        self.tb_orig = tb
        self.tb_next = tb.tb_next
        
def _recall(queue_task, g):
    try:
        t = g.gen.next()
    except StopIteration:
        g.deferred.callback(None)
        del g.deferred
    except Exception, e:

        exc_type, value, tb = sys.exc_info()

        ## Magic Traceback Hacking
        if debug:
            # interpreter shutdown
            if not sys:
                return
            stream = sys.stderr
            _print_traceback(stream, g.stack,
                             "generator %s" % g.gen.gi_frame.f_code.co_name, 0,
                             exc_type, value, tb)
        else:
            #if (tb.tb_lineno != g.gen.gi_frame.f_lineno or
            #    tb.f_code.co_filename != g.gen.gi_frame.f_code.co_filename):
            #    tb = FakeTb(g.gen.gi_frame, tb)
            pass
        ## Magic Traceback Hacking
            
        g.deferred.errback((exc_type, value, tb))
        del g.deferred
    else:
        # (half) CRUFT - remove when bittorrent uses twisted deferreds
        if not isinstance(t, Deferred) and not isinstance(t, defer.Deferred):
            g.deferred.callback(t)
            del g.deferred
            return

        a = (queue_task, g)
        # CRUFT: twisted deferred and bt deferreds differ in their parameter
        # names, so pass blank dicts.
        t.addCallbacks(_queue_task_chain, _queue_task_chain, a, {}, a, {})
        del t
        del a

def _launch_generator(queue_task, g, main_df):
    g2 = GenWithDeferred(g, main_df)
    ## the first one is fired for you
    ##_recall(queue_task, g2)
    # the first one is not fired for you, because if it errors the sys.exc_info
    # causes an unresolvable circular reference that makes the g2.deferred never
    # be deleted.
    queue_task(_recall, queue_task, g2)

def launch_coroutine(queue_task, f, *args, **kwargs):
    main_df = Deferred()
    try:
        g = f(*args, **kwargs)
    except Exception, e:
        if debug:
            traceback.print_exc()
        main_df.errback(e)
    else:        
        if isinstance(g, types.GeneratorType):
            _launch_generator(queue_task, g, main_df)
        else:
            # we got a non-generator, just callback with the return value
            main_df.callback(g)
    return main_df

def _wrap_task(add_task):
    return lambda _f, *args, **kwargs : add_task(0, _f, *args, **kwargs)
    
