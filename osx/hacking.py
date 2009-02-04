from AppKit import *
from time import time
from gettext import gettext
from khashmir.krpc import KRPC
from khashmir.util import *
from khashmir.khash import *
from BitTorrent.bencode import bencode, bdecode
from BitTorrent.Rerequester import DHTRerequester
from copy import copy
from BitTorrent import NewVersion

import hotshot, hotshot.stats

KRPC.noisy = 0

c = NSApp().delegate()
dht = c.mt.dht
rnd = file('/dev/urandom','r').read

def agetxt(x):
    if x <= 60:
        return "0m"
    x /= 60
    if x < 60:
        return "%dm" % x
    x /= 60
    if x < 24:
        return "%dh" % x
    x /= 24
    if x > 999:
        return "xx"
    return "%dd"%x
    
    
def lastSeen():
    l = []
    i = 0
    s = ""
    s+= dht.table.node.id.encode('base64')
    for bucket in dht.table.buckets:
        if bucket.min <= dht.table.node <= bucket.max:
            s+= "*"
        s+="%d-%d(%d/%d)- "%(i, 2**160 / (bucket.max - bucket.min), len([x for x in bucket.l if not x.invalid]), len(bucket.l))
        def ls(a, b):
            if a.lastSeen > b.lastSeen:
                return 1
            elif b.lastSeen > a.lastSeen:
                return -1
            return 0
        bucket.l.sort(ls)
        for id, ls, age, invalid in [(x.id.encode('base64')[:4],
                                      time() - x.lastSeen,
                                      time() - x.age,
                                      x.invalid)
                                     for x in bucket.l]:
            if not invalid:
                l.append((age, id))
            s+= "%s-%s-%s, " % (agetxt(ls), id, agetxt(age))
        s=s[:-2]
        s+= "\n--------------------------\n"
        i += 1
    l.sort()
    print s +  "estimated total: %s  mean age: %s  oldest: %s - %s" % (`dht.table.numPeers()`, agetxt(reduce(lambda a, b: a+b[0], l,0) / len(l)), l[-1][1], agetxt(l[-1][0]))
ls = lastseen = lastSeen

def dumpBuckets():
    for bucket in dht.table.buckets:
        print bucket.l
    
def getPeers(id):
    def p(v):
        print ">>>", [unpackPeers(x) for x in v]
    dht.getPeers(id, p)

def downsizeBuckets():
    dht.table.buckets = dht.table.buckets[0:1];dht.table.buckets[0].max=2**160
    
def gt():
    __builtins__['_'] = gettext

def showfuncs():
    print [(time() - x[0], x[1]) for x in dht.rawserver.funcs]

def drl():
    print "%s items (%s/%s) %1.1f" % (len(dht.udp.rltransport.q), dht.udp.rltransport.dropped, dht.udp.rltransport.sent, dht.udp.rltransport.dropped*1.0/(dht.udp.rltransport.sent + dht.udp.rltransport.dropped)*100)

def drs():
    dht.udp.rltransport.sent = dht.udp.rltransport.dropped = 0
    
def ss():
    l = [(x.encode('base64')[:4], len(y)) for x,y in dht.store.items()]
    def cmp(a,b):
        if a[1] > b[1]:
            return 1
        elif a[1] < b[1]:
            return -1
        return 0
    l.sort(cmp)
    l.reverse()
    print "%s %s" % (len(dht.store), l)


def stopProfiling():
    c.profile.stop()
    c.profile.close()

    stats = hotshot.stats.load("BT.prof")
    stats.strip_dirs()
    stats.sort_stats('time', 'calls')
    stats.print_stats(20)
    
def totalTorrents():
    l = [intify(x) for x in dht.store.keys()]
    l.sort()
    spread = l[-2] - l[1]
    width = 2**160 / spread
    print "have %s, width 1/%s, total: %s" % (len(dht.store), width, len(l[1:-1]) * width)

def refreshBucket(n):
    b = dht.table.buckets[n]
    dht.findNode(newIDInRange(b.min, b.max), lambda a: a)
             

def count(id):
    d = {}
    def cb(l):
        for x in l:
            d[x] = 1
        if not l:
            print ">>> %s peers for id %s" % (len(d), id.encode('base64')[:4])

    dht.getPeers(id, cb)

gonoisy=1
def donoisy():
    if gonoisy:
        drl();drs()
        dht.rawserver.external_add_task(300, donoisy)

def p(v):
    print ">>>", `v`
    
def hs():
    print [len(x) for x in dht.udp.hammerlock.buckets]


def switchtracker(t):
    x = t._rerequest
    t._rerequest = DHTRerequester(c.config, x.sched, x.howmany, x.connect, x.externalsched, x.amount_left, x.up, x.down, x.port, x.wanted_peerid, x.infohash, x.errorfunc, x.doneflag, x.upratefunc, x.downratefunc, x.ever_got_incoming, x.diefunc, x.successfunc, c.mt.dht)
    c.mt.rawserver.external_add_task(0, t._rerequest.begin)
    
def checkVersion(test_new_version='', test_current_version = ''):
        if c.config.has_key('new_version'):
            test_new_version = c.config['new_version']
        if c.config.has_key('current_version'):
            test_current_version = c.config['current_version']

        try:
            c.vc = NewVersion.Updater(c.vcThreadWrap,
                                         c.alertNewVersion,
                                         lambda a: a,
                                         lambda a: a,
                                         c.versionCheckFailed, test_new_version=test_new_version, test_current_version=test_current_version)
            c.vc.check()
        except:
            import traceback
            traceback.print_exc()
    
