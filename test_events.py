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

import time
try:
    import stackless
    from BitTorrent.stackless_yielddefer import like_yield as like_yield_stackless
    from BitTorrent.stackless_yielddefer import launch_coroutine as launch_coroutine_stackless
except ImportError:
    stackless = None

from BTL.greenlet_yielddefer import like_yield as like_yield_greenlet
from BTL.greenlet_yielddefer import launch_coroutine as launch_coroutine_greenlet

from BTL.defer import Deferred, DeferredEvent, wrap_task
from BTL.yielddefer import launch_coroutine
from BitTorrent.RawServer_twisted import RawServer
from twisted.internet import defer
from twisted.internet import reactor

config = {'max_incomplete': 10,
          'max_upload_rate': 350000,
          'bind': '',
          'close_with_rst': False,
          'socket_timeout': 3000}

m = 20000
a = [None] * m
i = 0

if __name__ == '__main__':
    rawserver = RawServer(config=config, noisy=True)

    rawserver.install_sigint_handler()    

    def avg_dist(l):
        d = []
        p = None
        for x in l:
            if p is not None:
                d.append(x - p)
            p = x
        return sum(d) / len(d)

    def rerun():
        #print '.'
        global i
        global a
        a[i] = time.clock()
        i += 1
        if i >= m:
            print 'add_task\t', len(a), a[-1] - a[0], '\t', avg_dist(a)
            i = 0
            if stackless:
                rawserver.add_task(0, rerun_stackless)
            else:
                rawserver.add_task(0, rerun_a)
        else:
            rawserver.add_task(0, rerun)

    def rerun_stackless():
        def inner():
            global i
            global a
            a[i] = time.clock()
            i += 1
            if i >= m:
                print 'add_stack\t', len(a), a[-1] - a[0], '\t', avg_dist(a)
                i = 0
                rawserver.add_task(0, rerun_a)
            else:
                stackless.tasklet(inner)()
                rawserver.add_task(0, stackless.schedule)
        stackless.tasklet(inner)()
        rawserver.add_task(0, stackless.schedule)

    def rerun_a():
        #print '.'
        global i
        global a
        a[i] = time.clock()
        i += 1
        if i >= m:
            print 'callAfter\t', len(a), a[-1] - a[0], '\t', avg_dist(a)
            i = 0
            run_gen()
        else:
            reactor.callLater(0, rerun_a)

##    def rerun_e():
##        #print '.'
##        global i
##        global a
##        a[i] = time.clock()
##        i += 1
##        if i >= m:
##            print 'e_add_task\t', len(a), a[-1] - a[0], '\t', avg_dist(a)
##            i = 0
##            rawserver.add_task(0, run_gen)
##        else:
##            rawserver.external_add_task(0, rerun_e)
    
    def run_gen():
        def gen():
            global a
            for i in xrange(m):
                df = Deferred()
                #rawserver.add_task(0, df.callback, lambda r: r)
                df.callback(1)
                yield df
                df.getResult()
                a[i] = time.clock()
                
        mdf = launch_coroutine(wrap_task(rawserver.add_task), gen)
        def done(r=None):
            print 'yielddefer\t', len(a), a[-1] - a[0], '\t', avg_dist(a)
            i = 0
            if stackless:
                print 'stackless'
                run_gen2()
            else:
                run_gen3()
        mdf.addCallback(done)


    def run_gen2():
        def gen():
            global a
            for i in xrange(m):
                df = Deferred()
                #rawserver.add_task(0, df.callback, lambda r: r)
                df.callback(1)
                like_yield_stackless(df)
                a[i] = time.clock()
                
        mdf = launch_coroutine_stackless(gen)
        def done(r=None):
            print 'stackless\t', len(a), a[-1] - a[0], '\t', avg_dist(a)
            i = 0
            run_gen3()
        mdf.addCallback(done)

    def run_gen3():
        def gen():
            global a
            for i in xrange(m):
                df = defer.Deferred()
                #rawserver.add_task(0, df.callback, lambda r: r)
                df.callback(1)
                r = like_yield_greenlet(df)
                #print repr(r)
                a[i] = time.clock()
                
        mdf = launch_coroutine_greenlet(gen)
        def done(r=None):
            print 'greenlet\t', len(a), a[-1] - a[0], '\t', avg_dist(a)
            i = 0
            rawserver.stop()
        mdf.addCallback(done)
        
##    def run_gen2():
##        def gen():
##            global a
##            for i in xrange(m):
##                df = Deferred()
##                df.callback(lambda r: r)
##                yield df
##                df.getResult()
##                a[i] = time.clock()
##                
##        mdf = launch_coroutine(reactor.callLater, 0, gen)
##        def done(r=None):
##            print 'yielddefer\t', len(a), a[-1] - a[0], '\t', avg_dist(a)
##            i = 0
##            rawserver.stop()
##        mdf.addCallback(done)

    import psyco
    #psyco.full(memory=0.1)
    #psyco.log()
    #psyco.profile()
    d = dict(globals())
##    count = 0
##    for f in RawServer.__dict__.itervalues():
##        if callable(f):
##            if count > 20:
##                print 'BIND', f
##            psyco.bind(f)
##            count += 1
##        if count > 25:
##            break
    psyco.bind(RawServer.listen_forever)
    #psyco.bind(RawServer.add_task)
    #psyco.bind(RawServer.external_add_task)
##    count = 0
##    for v in d.itervalues():
##        try:
##            if callable(v):
##                print v
##                psyco.bind(v)
##                count += 1
##        except:
##            pass
##        print count
##        if count > 0:
##            break

    rerun()
        
    if stackless:
        print 'stackless'
        stackless.tasklet(lambda : rawserver.listen_forever())()
        stackless.run()  
    else:
        print 'stack'
        rawserver.listen_forever()

    n = 0
    i = 0
    def rerun2():
        global i
        global a
        a[i] = time.clock()
        i += 1
        if i < n:
            rerun2()
    while n < m:
        n += 500
        rerun2()
    print 'deepstack\t', len(a), a[-1] - a[0], '\t', avg_dist(a)
    i = 0
