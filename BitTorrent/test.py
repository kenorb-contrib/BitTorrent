#!/usr/bin/env python

# Written by Bram Cohen
# this file is public domain

import sys
assert sys.version >= '2', "Install Python 2.0 or greater"

import testtest
import download

testtest.try_all(['urllib', 'StringIO', 'random', 'urlparse'])
