"""
A much simpler testing framework than PyUnit

tests a module by running all functions in it whose name starts with 'test'

a test fails if it raises an exception, otherwise it passes

functions are try_all and try_single
"""

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

# Written by Bram Cohen

from traceback import print_exc
import sys

def try_all(excludes = [], excluded_paths=[]):
    """
    tests all imported modules

    takes an optional list of module names and/or module objects to skip over.
    modules from files under under any of excluded_paths are also skipped.
    """
    failed = []
    ms = sys.modules.items()
    ms.sort()
    for modulename, module in ms:
        # skip builtins
        if not hasattr(module, '__file__'):
            continue
        if not modulename.startswith('BitTorrent'):
            continue
        # skip modules under any of excluded_paths
        if [p for p in excluded_paths if module.__file__.startswith(p)]:
            continue
        if modulename not in excludes and module not in excludes:
            modulename = "BitTorrent.tests" + modulename[len('BitTorrent'):] +\
                         "Tests"
            try:
                __import__(modulename)
                module = sys.modules[modulename]
            except ImportError:
                continue
            except:
                print_exc()
                continue
            try_module(module, modulename, failed)
    print_failed(failed)

def try_single(m):
    """
    tests a single module
    
    accepts either a module object or a module name in string form
    """
    if type(m) is str:
        modulename = m
        module = __import__(m)
    else:
        modulename = str(m)
        module = m
    failed = []
    try_module(module, modulename, failed)
    print_failed(failed)

def try_module(module, modulename, failed):
    if not hasattr(module, '__dict__'):
        return
    for n, func in module.__dict__.items():
        if not callable(func) or n[:4] != 'test':
            continue
        name = modulename + '.' + n
        try:
            print 'trying ' + name
            func()
            print 'passed ' + name
        except:
            print_exc()
            failed.append(name)
            print 'failed ' + name

def print_failed(failed):
    print
    if len(failed) == 0:
        print 'everything passed'
    else:
        print 'the following tests failed:'
        for i in failed:
            print i



