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

import sys
from unittest import *

from BTL.translation import _

from BitTorrent.RawServer_twisted import RawServer
from BitTorrent.defaultargs import common_options, rare_options
from threading import Event

if __name__ =="__main__":
    tests = defaultTestLoader.loadTestsFromNames([sys.argv[0][:-3]])
    result = TextTestRunner().run(tests)


class SimpleTests(TestCase):
    def setUp(self):
        d = dict([(x[0],x[1]) for x in common_options + rare_options])
        self.r = RawServer(d)
        self.a = self.r.create_udpsocket(8051, '127.0.0.1')
        self.b = self.r.create_udpsocket(8052, '127.0.0.1')

    def tearDown(self):
        self.a.close()
        self.b.close()
        
    def Handler(self, expected):
        class h(object):
            def __init__(self, expected, a=self.assertEqual):
                self.expected = expected
                self.a = a
            def data_came_in(self, connection, data):
                self.a(self.expected, data)
        return h(expected)

    def testFoo(self):
        self.r.start_listening_udp(self.a, self.Handler(''))
        self.r.start_listening_udp(self.b, self.Handler('foo'))
        self.a.sendto("foo", 0, ('127.0.0.1', 8052))
        self.r.listen_once()

    def testBackForth(self):
        self.r.start_listening_udp(self.a, self.Handler('bar'))
        self.r.start_listening_udp(self.b, self.Handler('foo'))
        self.a.sendto("foo", 0, ('127.0.0.1', 8052))
        self.r.listen_once()
        self.b.sendto("bar", 0, ('127.0.0.1', 8051))        
        self.r.listen_once()
