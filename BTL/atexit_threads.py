# threads are dumb, this module is smart.
#
# by Greg Hazel

import sys
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


def megadeth():
    time.sleep(10)
    try:
        import wx
        wx.Kill(wx.GetProcessId(), wx.SIGKILL)
    except:
        pass

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

        # kill all the losers
        # remove this when there are no more losers
        t = threading.Thread(target=megadeth)
        t.setDaemon(True)
        t.start()

        if timeout == 0:
            sys.stderr.write("non-daemon threads not shutting down "
                             "in a timely fashion:\n")
            nondaemons = _get_non_daemons()
            for th in nondaemons:
                sys.stderr.write("  %s\n" % th)
            sys.stderr.write("You have no chance to survive make your time.\n")
            for th in nondaemons:
                th.join()

        func(*targs, **kargs)

    atexit.register(duh)

