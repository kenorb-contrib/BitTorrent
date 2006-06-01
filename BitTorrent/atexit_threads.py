# threads are dumb, this module is smart.
#
# by Greg Hazel

import time
import atexit
import threading

def _get_non_daemons():
    return [d for d in threading.enumerate() if not d.isDaemon() and d != threading.currentThread()]

def register(func, *targs, **kargs):
    def duh():
        nondaemons = _get_non_daemons()
        for th in nondaemons:
            th.join()
        func(*targs, **kargs)
    atexit.register(duh)


def register_verbose(func, *targs, **kargs):
    def duh():
        nondaemons = _get_non_daemons()
        timeout = 4
        for th in nondaemons:
            start = time.time()
            th.join(timeout)
            timeout = max(0, timeout - (time.time() - start))
            if timeout == 0:
                break
        if timeout == 0:
            print "non-daemon threads not shutting down in a timely fashion:"
            nondaemons = _get_non_daemons()
            for th in nondaemons:
                print " ", th
            for th in nondaemons:
                th.join()
                
        func(*targs, **kargs)
    atexit.register(duh)

