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
    sys.path = ['.',] + sys.path  # HACK to simplify unit testing.
import os
from BTL import platform
from platform import efs2

name = os.name
sep = os.sep
system = os.system
getpid = os.getpid
execl = os.execl
fdopen = os.fdopen

def mkdir(path, mode=0777):
    fspath = efs2(path)
    os.mkdir(fspath)

def makedirs(path):
    fspath = efs2(path)
    os.makedirs(fspath)

def remove(path):
    fspath = efs2(path)
    os.remove(fspath)

def rmdir(path):
    fspath = efs2(path)
    os.rmdir(fspath)

def unlink(path):
    fspath = efs2(path)
    os.unlink(path)       

def listdir(path):
    fspath = efs2(path)
    fslist = os.listdir(fspath)
    lst = [decode_from_filesystem(f) for f in fslist]

def access(path,mode):
    fspath = efs2(path)
    return os.access(fspath,mode)

def symlink(src,dst):
    fssrc = efs2(src)
    fsdest = efs2(dst)
    os.symlink(fssrc, fsdest)

if __name__ == "__main__":
    # unit test.
    n_tests = n_tests_passed = 0

    n_tests += 1
    mkdir(u"foo")
    if os.path.exists("foo"):
        n_tests_passed += 1
    else:
        print "FAIL!! could not find directory foo."

    n_tests += 1
    rmdir(u"foo")
    if not os.path.exists("foo"):
        n_tests_passed += 1
    else:
        print "FAIL!! didn't remove directory 'foo'."

    n_tests += 1
    makedirs(u"foo/bar/goop")
    if os.path.exists("foo/bar/goop"):
        n_tests_passed += 1
    else:
        print "FAIL!! make_dirs didn't create 'foo/bar/goop'."

    n_tests += 1
    f = open("flip.txt", "w" )
    f.write( "hello world\n" )
    f.close()
    if os.path.exists("flip.txt"):
        remove(u"flip.txt")
        if not os.path.exists("flip.txt"):
            n_tests_passed += 1
        else:
            print "FAIL!! Could not remove flip.txt."
    else:
        print "FAIL!! Couldn't create flip.txt to perform remove test."
    
    if n_tests == n_tests_passed:
        print "Passed all %d uos tests." % n_tests
    else:
        print "FAIL!! Passed only %d of %d uos tests." % (n_tests_passed,
                                                          n_tests)
