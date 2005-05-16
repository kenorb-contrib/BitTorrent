import unittest
from time import sleep, time

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
        self.k.expire(time() - 1)
        l = self.k['foo']
        l.sort()
        self.assertEqual(l, ['bar'])
        self.k['foo'] = 'bing'
        t = time()
        self.k.expire(time() - 1)
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
