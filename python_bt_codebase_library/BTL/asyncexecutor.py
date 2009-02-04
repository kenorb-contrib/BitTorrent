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

""" An simple lightweight asynchronous executor class with nice
    java type static methods """
from twisted.python.threadpool import ThreadPool



class AsyncExecutor(object):
    """ defaults to minthreads=5, maxthreads=20 """
    pool = ThreadPool( name = 'AsyncExecutorPool')

    def _execute(self,  func, *args, **kwargs):
        if not self.pool.started:
            self.pool.start()
        self.pool.dispatch(None, func, *args, **kwargs)
    
    execute = classmethod(_execute)
    stop = pool.stop
    
def test():
    import random
    import time

    def test(digit):
        print 'Testing %d' % digit
        time.sleep(random.randint(1, 5000)/1000)
        print '     finished with test %d' % digit
    for i in xrange(10):
        AsyncExecutor.execute(test, )
    AsyncExecutor.stop() 

if __name__ == '__main__':
    test()
    
    
    
    
