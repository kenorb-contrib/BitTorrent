# Written by Bram Cohen
# see LICENSE.txt for license information

from urllib import urlopen
from btformats import check_peers
from bencode import bdecode
from threading import Thread
from traceback import print_exc

class Rerequester:
    def __init__(self, url, interval, sched, howmany, 
            minpeers, connect, externalsched):
        self.url = url
        self.interval = interval
        self.sched = sched
        self.howmany = howmany
        self.minpeers = minpeers
        self.connect = connect
        self.externalsched = externalsched
        sched(self.c, interval)

    def rerequest(self):
        try:
            h = urlopen(self.url)
            r = bdecode(h.read())
            h.close()
            check_peers(r)
            def add(r = r, connect = self.connect):
                for x in r['peers']:
                    connect((x['ip'], x['port']), x['peer id'])
            self.externalsched(add, 0)
        except IOError:
            print_exc()
            pass
        except ValueError:
            print_exc()
            pass

    def c(self):
        self.sched(self.c, self.interval)
        if self.howmany() < self.minpeers:
            Thread(target = self.rerequest).start()
