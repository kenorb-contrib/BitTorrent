import lsprof
import lspstats
import time
import test.pystone

def Tester():
	test.pystone.main()
	
def RawTest():
	print "Doing raw test"
	Tester()
	
def ProfTest():
	print "Doing new profiler test"
	p = lsprof.Profiler()
	p.enable(2)
	Tester()
	p.disable()
	stats = p.getstats()
	p.clear()
	lspstats.display(stats, "TotalTime", 20)
	p = None
	
def OtherTest():
	print "Doing hotshot test"
	import hotshot
	import hotshot.stats
	prof = hotshot.Profile("stones.prof")
	benchtime = prof.runcall(Tester)
	stats = hotshot.stats.load("stones.prof")
	stats.strip_dirs()
	stats.sort_stats('time', 'calls')
	stats.print_stats(20)
	
def ThirdTest():
	print "Doing old profiler test"
	import profile
	import pstats
	
	benchtime = profile.run('Tester()', 'fooprof')
	stats = pstats.Stats('fooprof')
	stats.strip_dirs()
	stats.sort_stats('time', 'calls')
	stats.print_stats(20)

import sys
sys.RawTest = RawTest
sys.ProfTest = ProfTest
sys.ThirdTest = ThirdTest
sys.OtherTest = OtherTest
import timeit
print timeit.Timer('import sys; sys.RawTest()').timeit(3)	
print timeit.Timer('import sys; sys.ProfTest()').timeit(3)	
print timeit.Timer('import sys; sys.ThirdTest()').timeit(3)
print timeit.Timer('import sys; sys.OtherTest()').timeit(3)
