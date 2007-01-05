# Author: David Harrison
# Windows version: Greg Hazel

import os
if os.name == "nt":
    import win32pdh

class CPUMeterBase(object):

    def __init__(self, update_interval = 2):
        from twisted.internet import reactor
        self.reactor = reactor
        self._util = 0.0
        self._interval = update_interval
        self.reactor.callLater(self._interval, self._update)

    def _update(self):
        self.update()
        self.reactor.callLater(self._interval, self._update)
        
    def update(self):
        raise NotImplementedError

    def get_utilization(self):
        return self._util

    def get_interval(self):
        return self._interval


class CPUMeterUnix(CPUMeterBase):
    """Averages CPU utilization over an update_interval."""
    
    def __init__(self, update_interval = 2):
        self._old_stats = self._get_stats()
        CPUMeterBase.__init__(self, update_interval)

    def _get_stats(self):
        fp = open("/proc/stat")
        ln = fp.readline()
        stats = ln[3:].strip().split()[:4]
        return [long(x) for x in stats]
        
    def update(self):
        old_user, old_nice, old_sys, old_idle = self._old_stats
        user, nice, sys, idle = self._old_stats = self._get_stats()
        user -= old_user
        nice -= old_nice
        sys -= old_sys
        idle -= old_idle
        total = user + nice + sys + idle
        self._util =  float((user + nice + sys)) / total


class CPUMeterWin32(CPUMeterBase):
    """Averages CPU utilization over an update_interval."""
    
    def __init__(self, update_interval = 2):
        inum = -1
        instance = None
        machine = None
        self.format = win32pdh.PDH_FMT_DOUBLE
        object = "Processor(_Total)"
        counter = "% Processor Time"
        path = win32pdh.MakeCounterPath( (machine, object, instance,
                                          None, inum, counter) )
        self.hq = win32pdh.OpenQuery()
        try:
            self.hc = win32pdh.AddCounter(self.hq, path)
        except:
            self.close()
            raise
        self._old_stats = self._get_stats()
        CPUMeterBase.__init__(self, update_interval)

    def close(self):
        if self.hc:
            try:
                win32pdh.RemoveCounter(self.hc)
            except:
                pass
            self.hc = None
        if self.hq:
            try:
                win32pdh.CloseQuery(self.hq)
            except:
                pass
            self.hq = None        

    def _get_stats(self):
        win32pdh.CollectQueryData(self.hq)
        type, val = win32pdh.GetFormattedCounterValue(self.hc, self.format)
        val = val / 100.0
        return val
        
    def update(self):
        self._util = self._get_stats()


if os.name == "nt":
    CPUMeter = CPUMeterWin32
else:
    CPUMeter = CPUMeterUnix
        
if __name__ == "__main__":

    cpu = CPUMeter()

    def print_util():
        print cpu.get_utilization()
        reactor.callLater(1, print_util)
    reactor.run(print_util)
