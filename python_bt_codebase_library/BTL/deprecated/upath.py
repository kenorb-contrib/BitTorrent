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

# by David Harrison

if __name__ == "__main__":
    import sys
    sys.path = ['.','..'] + sys.path  # HACK to simplify unit testing.

import os
from BTL import platform 
from BTL.platform import efs2, decode_from_filesystem

def join(*args):
    fsargs = [efs2(arg) for arg in args]
    os.path.join(*fsargs)

def split(path):
    fspath, fsname = os.path.split(path)
    return decode_from_filesystem(fspath), decode_from_filesystem(fsname)

def exists(path):
    fspath = efs2(path)
    return os.path.exists(fspath)

def getmtime(path):
    fspath = efs2(path)
    return os.path.getmtime(fspath)

def getsize(path):
    fspath = efs2(path)
    return os.path.getsize(fspath)

def isdir(path):
    fspath = efs2(path)
    return os.path.isdir(fspath)

def isfile(path):
    fspath = efs2(path)
    return os.path.isfile(fspath)

def abspath(path):
    fspath = efs2(path)
    return decode_from_filesystem(os.path.abspath(fspath))

def basename(path):
    fspath = efs2(path)
    return decode_from_filesystem(os.path.basename(fspath))

def normpath(path):
    fspath = efs2(path)
    return decode_from_filesystem(os.path.normpath(fspath))

def realpath(path):
    fspath = efs2(path)
    return decode_from_filesystem(os.path.realpath(fspath))

def commonprefx(pathlist):
    fslist = [efs2(path) for path in pathlist]
    return decode_from_filesystem(os.path.commonprefix(fslist))

def expanduser(path):
    user_path = os.path.expanduser(path)
    print "expanduser: user_path=", user_path
    print "str?",  isinstance(user_path,str)
    print "unicode?", isinstance(user_path,unicode)
    return decode_from_filesystem(user_path)
    

if __name__ == "__main__":
    # unit test.
    n_tests = n_tests_passed = 0
    n_tests += 1
    if expanduser(u"~") == os.expanduser("~"):
        n_tests_passed += 1
    else:
        print "FAIL!! expanduser returned %s when expected %s" % (
            expanduser(u"~"), os.expanduser("~"))

    os.mkdir("foo")
    n_tests += 1
    if exists(u"foo" ):
       n_tests_passed += 1
    else:
        print "FAIL!! exists didn't find 'foo'."

    n_tests += 1
    if isdir(u"foo"):
        n_tests_passed += 1
    else:
        print "FAIL!! isdir on 'foo' should return true."
        
    n_tests += 1
    cpref = commonprefix([ "/a/b/c", "/a/b/d"] )
    if cpref == "/a/b":
        n_tests_passed += 1
    else:
        print "FAIL!! commonprefix test failed."

    if n_tests == n_tests_passed:
        print "Passed all %d upath tests." % n_tests
    else:
        print "FAIL!! Passed only %d of %d upath tests." % (n_tests_passed,
                                                          n_tests)
        

    



