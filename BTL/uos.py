# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

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
