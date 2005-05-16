## Copyright 2002-2003 Andrew Loewenstern, All Rights Reserved
# see LICENSE.txt for license information

import unittest

import ktable, khashmir
import khash, node, knode
import actions
import test_krpc
import test_khashmir
import kstore

tests = unittest.defaultTestLoader.loadTestsFromNames(['kstore', 'khash', 'node', 'knode', 'actions',  'ktable', 'test_krpc', 'test_khashmir'])
result = unittest.TextTestRunner().run(tests)
