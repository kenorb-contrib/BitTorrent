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

from __future__ import generators

app_name = "test"
from BTL.defer import Deferred, Failure
from BTL.yielddefer import launch_coroutine, wrap_task
from BTL.reactor_magic import reactor

import time
import thread
import threading

def wait(df, v):
    if v == 'bar':
        df.errback(ValueError("The value was bar!"))
        return
    time.sleep(1)
    #print "done:", v
    df.callback("post " + v)

rawserver = None

import Queue
queue = Queue.Queue()
def run():
    global queue
    while True:
        df = queue.get()
        if df is None:
            break
        if df.error:
            try:
                fdsfs = tasty
            except:
                reactor.callFromThread(df.errback, Failure())
        else:
            reactor.callFromThread(df.callback, 'post')
        
mt = threading.Thread(target=run).start()
def task(name, error=False):
    df = Deferred()
    df.error = error
    queue.put(df)
    return df
foo = lambda : task('foo')
bar = lambda : task('bar')
baz = lambda : task('baz', error=True)


class Worker(object):
    def __init__(self):
        self.holder = None
        self.ident = thread.get_ident()

    def do_some_things(self):
        for t in [foo, bar, baz]:
            df = t()
            yield df
            try:
                r = df.getResult()
                if t == baz: assert False
                #print "result:", r
            except Exception, e:
                if t != baz: assert False
                #print "An (expected) error occurred:", e
                pass
            

if __name__ == '__main__':
   
    w = Worker()

    w.total = 0
    def set_event(x):
        w.total -= 1
        assert w.total >= 0
        if w.total == 0:
            reactor.stop()
    def set_event_error(x):
        print "A critical error occured:", str(x[0]), ":", str(x[1])
        reactor.stop()

    def run_task_and_exit():
        #for i in xrange(1000):
        for i in xrange(100040):
            w.total += 1
            df = launch_coroutine(wrap_task(reactor.callLater),
                                  w.do_some_things)
            df.addCallback(set_event)
            df.addErrback(set_event_error)
    #reactor.callLater(0, run_task_and_exit)

    w.total = 0
    def run(r=None):
        if w.total > 1000:
            reactor.stop()
            return
        w.total += 1
        df = launch_coroutine(wrap_task(reactor.callLater),
                              w.do_some_things)
        df.addCallback(run)
        df.addErrback(set_event_error)
    reactor.callLater(0, run)    
        
    reactor.run()

    queue.put(None)
    