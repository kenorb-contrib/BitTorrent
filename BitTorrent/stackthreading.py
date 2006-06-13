# Import and use just like threading, but enjoy the benefit of seeing the
# calling context prepended to any thread traceback.
#
# by Greg Hazel

import os        
import sys
import threading
import traceback
from threading import *

def _print(stream, str='', terminator='\n'):
    stream.write(str+terminator)

def _print_traceback(stream, base_stack, name, extra, exc_type, value, tb):
    stack2 = traceback.extract_tb(tb)
    # cut off the top
    stack2 = stack2[extra + 1:]
    base_stack.extend(stack2)
    l = traceback.format_list(base_stack)
    _print(stream, "Exception in %s:" % name)
    _print(stream, "Traceback (most recent call last):")
    for s in l:
        _print(stream, s, '')
    
    lines = traceback.format_exception_only(exc_type, value)
    for line in lines[:-1]:
        _print(stream, line, ' ')
    _print(stream, lines[-1], '')
    

base_Thread = Thread

class StackThread(Thread):

    def __init__(self, group=None, target=None, name=None, depth=1,
                 args=(), kwargs={}, verbose=None):

        if name is None:
            try:
                raise ZeroDivisionError
            except ZeroDivisionError:
                f = sys.exc_info()[2].tb_frame.f_back

            stack = traceback.extract_stack(f)
            fn, ln, fc, cd = stack[-depth]
            #sys.stdout.writelines([str(s)+'\n' for s in stack])
            root, fn = os.path.split(fn)
            name = '%s:%s in %s: %s' % (fn, ln, fc, cd)
            
        base_Thread.__init__(self, group=group, target=target, name=name,
                             args=args, kwargs=kwargs, verbose=verbose)
        
        stream = sys.stderr    

        start = self.start
        def save():
            # ha ha ha
            try:
                raise ZeroDivisionError
            except ZeroDivisionError:
                f = sys.exc_info()[2].tb_frame.f_back

            self.stack = traceback.extract_stack(f)
            start()
        
        run = self.run
        def catch():
            try:
                run()
            except:
                # interpreter shutdown
                if not sys:
                    return
                exc_type, value, tb = sys.exc_info()
                _print_traceback(stream, self.stack,
                                 "thread %s" % self.getName(), 1,
                                 exc_type, value, tb)

        self.run = catch
        self.start = save

Thread = StackThread
# this is annoying
_Event = threading._Event

if __name__ == '__main__':
    def foo():
        raise ValueError("boo!")

    t = Thread(target=foo)
    t.start()
