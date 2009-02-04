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

import unittest
from BTLR.platform import bttime
from time import sleep

from kstore import KStore
if __name__ =="__main__":
    tests = unittest.defaultTestLoader.loadTestsFromNames(['test_kstore'])
    result = unittest.TextTestRunner().run(tests)


class BasicTests(unittest.TestCase):
    def setUp(self):
        self.k = KStore()
        
    def testNoKeys(self):
        self.assertEqual(self.k.keys(), [])

    def testKey(self):
        self.k['foo'] = 'bar'
        self.assertEqual(self.k.keys(), ['foo'])

    def testKeys(self):
        self.k['foo'] = 'bar'
        self.k['wing'] = 'wang'
        l = self.k.keys()
        l.sort()
        self.assertEqual(l, ['foo', 'wing'])
        
    def testInsert(self):
        self.k['foo'] = 'bar'
        self.assertEqual(self.k['foo'], ['bar'])

    def testInsertTwo(self):
        self.k['foo'] = 'bar'
        self.k['foo'] = 'bing'
        l = self.k['foo']
        l.sort()
        self.assertEqual(l, ['bar', 'bing'])
        
    def testExpire(self):
        self.k['foo'] = 'bar'
        self.k.expire(bttime() - 1)
        l = self.k['foo']
        l.sort()
        self.assertEqual(l, ['bar'])
        self.k['foo'] = 'bing'
        t = bttime()
        self.k.expire(bttime() - 1)
        l = self.k['foo']
        l.sort()
        self.assertEqual(l, ['bar', 'bing'])        
        self.k['foo'] = 'ding'
        self.k['foo'] = 'dang'
        l = self.k['foo']
        l.sort()
        self.assertEqual(l, ['bar', 'bing', 'dang', 'ding'])
        self.k.expire(t)
        l = self.k['foo']
        l.sort()
        self.assertEqual(l, ['dang', 'ding'])
        
    def testDup(self):
        self.k['foo'] = 'bar'
        self.k['foo'] = 'bar'
        self.assertEqual(self.k['foo'], ['bar'])

    def testSample(self):
        for i in xrange(2):
            self.k['foo'] = i
        l = self.k.sample('foo', 5)
        l.sort()
        self.assertEqual(l, [0, 1])

        for i in xrange(10):
            for i in xrange(10):
                self.k['bar'] = i
            l = self.k.sample('bar', 5)
            self.assertEqual(len(l), 5)
            for i in xrange(len(l)):
                self.assert_(l[i] not in l[i+1:])
        
