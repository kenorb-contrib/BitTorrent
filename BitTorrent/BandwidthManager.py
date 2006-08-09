# By Greg Hazel

debug = False

import math
import socket
import itertools
from BitTorrent.obsoletepythonsupport import set
from BitTorrent.RTTMonitor import RTTMonitor
from BitTorrent.yielddefer import _wrap_task
from BitTorrent.HostIP import get_deferred_host_ips#get_host_ips
from BitTorrent.platform import bttime
from BitTorrent.Lists import SizedList

class NodeFeeder(object):
    def __init__(self, external_add_task,
                 get_remote_endpoints, rttmonitor):
        self.external_add_task = external_add_task
        self.get_remote_endpoints = get_remote_endpoints
        self.rttmonitor = rttmonitor
        self.external_add_task(3, self._start)

    def _start(self):
        df = get_deferred_host_ips()
        df.addCallback(self._collect_nodes)

    def _collect_nodes(self, local_ips):
        addrs = self.get_remote_endpoints()
        
        ips = set()
        for (ip, port) in addrs:
            if ip is not None and ip != "0.0.0.0" and ip not in local_ips:
                assert isinstance(ip, str)
                assert isinstance(port, int)
                ips.add(ip)
        
        self.rttmonitor.set_nodes_restart(ips)

        delay = 5
        if len(ips) > 0:
            delay = 300
    
        self.external_add_task(delay, self._collect_nodes, local_ips)


def ratio_sum_lists(a, b):
    tx = float(sum(a))
    ty = float(sum(b))
    return tx / max(ty, 0.0001)


def standard_deviation(l):
    N = len(l)
    x = 0
    
    total = float(sum(l))
    
    mean = total/N
    
    # Subtract the mean from each data item and square the difference.
    # Sum all the squared deviations.
    for i in l:
        x += (i - mean)**2.0
    
    try:
        if False:
            # Divide sum of squares by N-1 (sample variance).
            variance = x / (N - 1)
        else:
            # Divide sum of squares by N (population variance).
            variance = x / N
    except ZeroDivisionError:
        variance = 0

    stddev = math.sqrt(variance)
    
    return stddev


class BandwidthManager(object):
    
    def __init__(self, external_add_task, config, set_option,
                       get_remote_endpoints, get_rates):
        self.external_add_task = external_add_task
        self.config = config
        self.set_option = set_option
        self.get_rates = get_rates
        def got_new_rtt(rtt):
            self.external_add_task(0, self._inspect_rates, rtt)
        self.rttmonitor = RTTMonitor(got_new_rtt)
        self.nodefeeder = NodeFeeder(external_add_task=external_add_task,
                                     get_remote_endpoints=get_remote_endpoints,
                                     rttmonitor=self.rttmonitor)

        self.start_time = None

        self.max_samples = 10 # hmm...
        self.u = SizedList(self.max_samples)
        self.d = SizedList(self.max_samples)
        self.t = SizedList(self.max_samples * 10)
        self.ur = SizedList(self.max_samples)
        self.dr = SizedList(self.max_samples)

        self.current_std = 0.001        
        self.max_std = 0.001

        self.max_rates = {}
        self.max_rates["upload"] = 1.0
        self.max_rates["download"] = 1.0
        self.max_p = 1.0
        self.min_p = 2**500
        self.mid_p = ((self.max_p - self.min_p) / 2.0) + self.min_p
        self.old_p = None

    # I pulled these numbers out of my ass.

    def _method_1(self, type, t, c, old_c, rate):
        # This concept is:
        # if the correlation is high and the latency is high
        # then lower the bandwidth limit.
        # otherwise, raise it.

        if ((c > 0.96) and (t > 100)): 
            rate /= 2.0
            if debug:
                print type, "down to", rate
        else:
            rate += 500 # hmm
            if debug:
                print type, "up to", rate
        return rate
    
    def _method_2(self, type, t, c, old_c, rate):
        # This concept is:
        # if the correlation is low and the latency is high, lower the limit
        # otherwise raise it

        if ((c < 0.60) and (t > 100)): 
            rate /= 2.0
            if debug: 
                print type, "down to", rate
        else:
            rate += 500 # hmm
            if debug:
                print type, "up to", rate
        return rate

    def _method_vegasish(self, type, t, c, old_c, rate):

        middle_rtt = ((self.rttmonitor.get_min_rtt() +
                       self.rttmonitor.get_max_rtt()) / 2.0)
        if t > middle_rtt:
            rate *= 1.0/8.0
            if debug:
                print type, "down to", rate
        else:
            rate += 1000 # hmm
            if debug:
                print type, "up to", rate
        return rate            

    def _method_vegas_greg(self, type, t, c, old_c, rate):

        middle_rtt = ((self.rttmonitor.get_min_rtt() +
                       self.rttmonitor.get_max_rtt()) / 2.0)
        if t > middle_rtt and c < 0.5:
            rate *= 1.0/8.0
            if debug:
                print type, "down to", rate
        else:
            rate += 1000 # hmm
            if debug:
                print type, "up to", rate
        return rate            

    def _method_ratio(self, type, t, p, min_p, max_p, rate):
        ratio = p / max_p
        if debug:
            print "RATIO", ratio
        if ratio < 0.5:
            rate = ratio * self.max_rates[type]
            if debug:
                print type.upper(), "SET to", rate
        else:
            rate += rate * (ratio/10.0) # hmm
            if debug:
                print type.upper(), "UP to", rate
                
        return max(rate, 1000)


    def _method_stddev(self, type, std, max_std, rate):
        if std > (max_std * 0.80): # FUDGE
            rate *= 0.80 # FUDGE
            if debug:
                print type.upper(), "DOWN to", rate
        else:
            rate += 1000 # FUDGE
            if debug:
                print type.upper(), "UP to", rate

        return max(rate, 1000) # FUDGE
    
    
    def _affect_rate(self, type, std, max_std, rate, set):
        rate = self._method_stddev(type, std, max_std, rate)

        rock_bottom = False
        if rate <= 4096:
            if debug:
                print "Rock bottom"
            rock_bottom = True
            rate = 4096
    
        set(int(rate))

        return rock_bottom
        

    def _inspect_rates(self, t = None):

        if t == None:
            t = self.rttmonitor.get_current_rtt()

        if t == None:
            # this makes timeouts reduce the maximum std deviation
            self.max_std *= 0.80 # FUDGE
            return

        if self.start_time == None:
            self.start_time = bttime()
        def set_if_enabled(option, value):
            if not self.config['bandwidth_management']:
                return
            #print "Setting rate to ", value
            self.set_option(option, value)

        # TODO: slow start should be smarter than this
        if self.start_time + 20 > bttime():
            set_if_enabled('max_upload_rate', 10000000)
            set_if_enabled('max_download_rate', 10000000)

        if t < 3:
            # I simply don't believe you. Go away.
            return

        tup = self.get_rates()
        if tup == None:
            return
        u, d = tup
        #print "udt", u, d, t
        #print "uprate, downrate=", u, d

        self.u.append(u)
        self.d.append(d)
        self.t.append(t)
        self.ur.append(self.config['max_upload_rate'])
        self.dr.append(self.config['max_download_rate'])

        #s = time.time()
        #cu = correlation(self.u, self.t)
        #cd = correlation(self.d, self.t)
        #cur = correlation(self.u, self.ur)
        #cdr = correlation(self.d, self.dr)
        #e = time.time()

        self.current_std = standard_deviation(self.t)
        
        pu = ratio_sum_lists(self.u, self.t)
        pd = ratio_sum_lists(self.d, self.t)
        if len(self.u) > 2:
            lp = [ x/y for x, y in itertools.izip(self.u, self.t) ]
            min_pu = min(*lp)
            max_pu = max(*lp)
        else:
            min_pu = u / t
            max_pu = u / t
        pu = u / t

        self.max_rates["upload"] = max(max(self.u), self.max_rates["upload"])
        self.max_rates["download"] = max(max(self.d), self.max_rates["download"])

        if debug:
            print "STDDEV", u, self.config['max_upload_rate'], \
                  self.max_std, self.current_std, pu, pd
        
        rb = self._affect_rate("upload", self.current_std, self.max_std,
                               self.config['max_upload_rate'],
                               lambda r : set_if_enabled('max_upload_rate', r))
        # don't adjust download rate, it's not nearly correlated enough
##        if rb:
##            v = int(self.config['max_download_rate'] * 0.90) # FUDGE
##            v = max(v, 2000) # FUDGE
##            set_if_enabled('max_download_rate', v) 
##        else:
##            v = int(self.config['max_download_rate'] + 6000) # FUDGE
##            set_if_enabled('max_download_rate', v) 
##        if debug:
##            print "DOWNLOAD SET to", v
            
        #self._affect_rate("download", t, cd, self.last_cd, pd,
        #                  self.config['max_download_rate'],
        #                  lambda r : self.set_option('max_download_rate', r))

        self.max_std = max(self.max_std, self.current_std)

        #self.last_cu = cu
        #self.last_cd = cd

        # we're re-called by the pinging thing
        #self.external_add_task(0.1, self._inspect_rates)
        
        