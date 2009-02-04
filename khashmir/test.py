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

import ktable, khashmir
import khash, node, knode
import actions
import test_krpc
import test_khashmir
import kstore

tests = unittest.defaultTestLoader.loadTestsFromNames(['kstore', 'khash', 'node', 'knode', 'actions',  'ktable', 'test_krpc', 'test_khashmir'])
result = unittest.TextTestRunner().run(tests)
