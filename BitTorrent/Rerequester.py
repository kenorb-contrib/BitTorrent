# Written by Bram Cohen
# modified for multitracker operation by John Hoffman
# see LICENSE.txt for license information

from zurllib import urlopen, quote
from urlparse import urlparse, urlunparse
from socket import gethostbyname
from btformats import check_peers
from bencode import bdecode
from threading import Thread, Lock
from traceback import print_exc
from socket import error
from random import shuffle

true = 1
false = 0

class Rerequester:
    def __init__(self, trackerlist, interval, sched, howmany, minpeers, 
            connect, externalsched, amount_left, up, down,
            port, ip, myid, infohash, timeout, errorfunc, maxpeers, doneflag,
            upratefunc, downratefunc):

        newtrackerlist = []        
        for tier in trackerlist:
            if len(tier)>1:
                shuffle(tier)
            newtrackerlist += [tier]
        self.trackerlist = newtrackerlist
        self.lastsuccessful = ''
        self.rejectedmessage = 'rejected by tracker - '
        
        self.url = ('?info_hash=%s&peer_id=%s&port=%s' %
            (quote(infohash), quote(myid), str(port)))
        if ip != '':
            self.url += '&ip=' + quote(ip)
        self.interval = interval
        self.last = None
        self.trackerid = None
        self.announce_interval = 30 * 60
        self.sched = sched
        self.howmany = howmany
        self.minpeers = minpeers
        self.connect = connect
        self.externalsched = externalsched
        self.amount_left = amount_left
        self.up = up
        self.down = down
        self.timeout = timeout
        self.errorfunc = errorfunc
        self.maxpeers = maxpeers
        self.doneflag = doneflag
        self.upratefunc = upratefunc
        self.downratefunc = downratefunc
        self.last_failed = true
        self.never_succeeded = true
        self.errorcodes = {}
        self.lock = SuccessLock()
        self.started = false
        self.special = None

    def c(self):
        if self.howmany() < self.minpeers:
            self.announce(3, self._c)

    def _c(self):            
        self.sched(self.c, self.interval)

    def d(self, event = 3):
        if not self.started:
            self.started = true
            self.sched(self.c, self.interval/2)
        self.announce(event, self._d)

    def _d(self):
        if self.never_succeeded:
            self.sched(self.d, 60)  # retry in 60 seconds
        else:
            self.sched(self.d, self.announce_interval)


    def announce(self, event = 3, callback = lambda: None, specialurl = None):

        if specialurl is not None:
            s = self.url+'&uploaded=0&downloaded=0&left=1'   # don't add to statistics
            if self.howmany() >= self.maxpeers:
                s += '&numwant=0'
            else:
                s += '&no_peer_id=1'
            self.last_failed = true         # force true, so will display an error
            self.special = specialurl
            self.rerequest(s, callback)
            return
        
        else:
            s = ('%s&uploaded=%s&downloaded=%s&left=%s' %
                (self.url, str(self.up()), str(self.down()), 
                str(self.amount_left())))
        if self.last is not None:
            s += '&last=' + quote(str(self.last))
        if self.trackerid is not None:
            s += '&trackerid=' + quote(str(self.trackerid))
        if self.howmany() >= self.maxpeers:
            s += '&numwant=0'
        else:
            s += '&no_peer_id=1'
        if event != 3:
            s += '&event=' + ['started', 'completed', 'stopped'][event]
            
        self.rerequest(s, callback)


    def snoop(self, peers, callback = lambda: None):  # tracker call support
        self.rerequest(self.url
            +'&event=stopped&port=0&uploaded=0&downloaded=0&left=1&tracker=1&numwant='
            +str(peers), callback)


    def rerequest(self, s, callback):
        if not self.lock.isfinished():  # still waiting for prior cycle to complete??
            def retry(self = self, s = s, callback = callback):
                self.rerequest(s, callback)
            self.sched(retry,5)         # retry in 5 seconds
            return
        self.lock.reset()
        rq = Thread(target = self._rerequest, args = [s, callback])
        rq.setDaemon(false)
        rq.start()

    def _rerequest(self, s, callback):
        self.errorcodes = {}
        if self.special is None:
            for t in range(len(self.trackerlist)):
                for tr in range(len(self.trackerlist[t])):
                    tracker  = self.trackerlist[t][tr]
                    if self.rerequest_single(tracker, s, callback):
                        if not self.last_failed and tr != 0:
                            del self.trackerlist[t][tr]
                            self.trackerlist[t] = [tracker] + self.trackerlist[t]
                        return
        else:
            tracker = self.special
            self.special = None
            if self.rerequest_single(tracker, s, callback):
                return
        # no success from any tracker
        def fail (self = self, callback = callback):
            self._fail(callback)
        self.externalsched(fail)


    def _fail(self, callback):
        if self.upratefunc() < 100 and self.downratefunc() < 100:
            for f in ['rejected', 'bad_data', 'troublecode']:
                if self.errorcodes.has_key(f):
                    r = self.errorcodes[f]
                    break
            else:
                r = 'Problem connecting to tracker - unspecified error'
            self.errorfunc(r)

        self.last_failed = true
        self.lock.give_up()
        self.externalsched(callback)


    def rerequest_single(self, t, s, callback):
        l = self.lock.set()
        rq = Thread(target = self._rerequest_single, args = [t+s, l, callback])
        rq.setDaemon(false)
        rq.start()
        self.lock.wait()
        if self.lock.success:
            self.lastsuccessful = t
            self.last_failed = false
            self.never_succeeded = false
            return true
        if not self.last_failed and self.lastsuccessful == t:
            # if the last tracker hit was successful, and you've just tried the tracker
            # you'd contacted before, don't go any further, just fail silently.
            self.last_failed = true
            self.externalsched(callback)
            self.lock.give_up()
            return true
        return false    # returns true if it wants rerequest() to exit


    def _rerequest_single(self, url, l, callback):
        
        def timedout(self = self, l = l):
            if self.lock.trip(l):
                self.errorcodes['troublecode'] = 'Problem connecting to tracker - timeout exceeded'
                self.lock.unwait(l)
        self.externalsched(timedout, self.timeout)

        try:
            h = urlopen(url)
            data = h.read()
            h.close()
        except (IOError, error), e:
            if self.lock.trip(l):
                self.errorcodes['troublecode'] = 'Problem connecting to tracker - ' + str(e)
                self.lock.unwait(l)
            return
        except:
            if self.lock.trip(l):
                self.errorcodes['troublecode'] = 'Problem connecting to tracker'
                self.lock.unwait(l)
            return

        if data == '':
            if self.lock.trip(l):
                self.errorcodes['troublecode'] = 'no data from tracker'
                self.lock.unwait(l)
            return
        
        try:
            r = bdecode(data)
            check_peers(r)
        except ValueError, e:
            if self.lock.trip(l):
                self.errorcodes['bad_data'] = 'bad data from tracker - ' + str(e)
                self.lock.unwait(l)
            return
        
        if r.has_key('failure reason'):
            if self.lock.trip(l):
                self.errorcodes['rejected'] = self.rejectedmessage + r['failure reason']
                self.lock.unwait(l)
            return
            
        if self.lock.trip(l, true):     # success!
            self.lock.unwait(l)
        else:
            callback = lambda: None     # attempt timed out, don't do a callback

        # even if the attempt timed out, go ahead and process data
        def add(self = self, r = r, callback = callback):
            self.postrequest(r, callback)
        self.externalsched(add)


    def postrequest(self, r, callback):
        if r.has_key('warning message'):
                self.errorfunc('warning from tracker - ' + r['warning message'])
        self.announce_interval = r.get('interval', self.announce_interval)
        self.interval = r.get('min interval', self.interval)
        self.trackerid = r.get('tracker id', self.trackerid)
        self.last = r.get('last')
        ps = len(r['peers']) + self.howmany()
        if ps < self.maxpeers:
            if self.doneflag.isSet():
                if r.get('num peers', 1000) - r.get('done peers', 0) > ps * 1.2:
                    self.last = None
            else:
                if r.get('num peers', 1000) > ps * 1.2:
                    self.last = None
        for x in r['peers']:
            self.connect((x['ip'], x['port']), x.get('peer id',0))
        callback()


class SuccessLock:
    def __init__(self):
        self.lock = Lock()
        self.pause = Lock()
        self.code = 0L
        self.success = false
        self.finished = true

    def reset(self):
        self.success = false
        self.finished = false

    def set(self):
        self.lock.acquire()
        if not self.pause.locked():
            self.pause.acquire()
        self.first = true
        self.code += 1L
        self.lock.release()
        return self.code

    def trip(self, code, s = false):
        self.lock.acquire()
        try:
            if code == self.code and not self.finished:
                r = self.first
                self.first = false
                if s:
                    self.finished = true
                    self.success = true
                return r
        finally:
            self.lock.release()

    def give_up(self):
        self.lock.acquire()
        self.success = false
        self.finished = true
        self.lock.release()

    def wait(self):
        self.pause.acquire()

    def unwait(self, code):
        if code == self.code and self.pause.locked():
            self.pause.release()

    def isfinished(self):
        self.lock.acquire()
        x = self.finished
        self.lock.release()
        return x