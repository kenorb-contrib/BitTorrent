# Written by Bram Cohen
# see LICENSE.txt for license information

from sha import sha
from cStringIO import StringIO
from threading import Lock
from time import time, strftime, localtime
from bisect import bisect_right
from os.path import getsize, getmtime
import os
try:
    from os import fsync
except ImportError:
    fsync = lambda x: None
    
true = 1
false = 0

DEBUG = false

MAXLOCKSIZE = 1000000000

def dummy_status(fractionDone = None, activity = None):
    pass

class Storage:
    def __init__(self, files, open, exists, statusfunc, doneflag, config):
        # can raise IOError and ValueError
        self.doneflag = doneflag
        self.ranges = []
        numfiles = 0
        total = 0l
        so_far = 0l
        self.handles = {}
        self.whandles = {}
        self.tops = {}
        self.sizes = {}
        self.mtimes = {}
        if config.get('lock_files', true):
            self.lock_file, self.unlock_file = self._lock_file, self._unlock_file
        else:
            self.lock_file, self.unlock_file = lambda x1,x2: None, lambda x1,x2: None
        self.lock_while_reading = config.get('lock_while_reading', false)
        self.lock = Lock()

        for file, length in files:
            if doneflag.isSet():    # bail out if doneflag is set
                return
            if length != 0:
                self.ranges.append((total, total + length, file))
                numfiles += 1
                total += length
                if exists(file):
                    l = getsize(file)
                    if l > length:
                        h = open(file, 'rb+')
                        h.truncate(length)
                        h.flush()
                        h.close()
                        l = length
                else:
                    l = 0
                    h = open(file, 'wb+')
                    h.flush()
                    h.close()
                    
                self.tops[file] = l
                self.sizes[file] = length
                self.mtimes[file] = getmtime(file)
                so_far += l

        self.begins = [i[0] for i in self.ranges]
        self.total_length = total


        self.max_files_open = config['max_files_open']
        if self.max_files_open > 0 and numfiles > self.max_files_open:
            self.handlebuffer = []
        else:
            self.handlebuffer = None


    if os.name == 'nt':
        def _lock_file(self, name, f):
            import msvcrt
            for p in range(0, self.sizes[name], MAXLOCKSIZE):
                f.seek(p)
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK,
                               min(MAXLOCKSIZE,self.sizes[name]-p))

        def _unlock_file(self, name, f):
            import msvcrt
            for p in range(0, self.sizes[name], MAXLOCKSIZE):
                f.seek(p)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK,
                               min(MAXLOCKSIZE,self.sizes[name]-p))

    elif os.name == 'posix':
        def _lock_file(self, name, f):
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)

        def _unlock_file(self, name, f):
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    else:
        def _lock_file(self, name, f):
            pass
        def _unlock_file(self, name, f):
            pass


    def was_preallocated(self, pos, length):
        for file, begin, end in self._intervals(pos, length):
            if self.tops.get(file, 0) < end:
                return false
        return true


    def set_readonly(self):
        # may raise IOError or OSError
        for file in self.whandles.keys():
            self._close(file)
            if self.handlebuffer:
                self.handlebuffer.remove(file)


    def get_total_length(self):
        return self.total_length


    def _open(self, file, mode):
        try:
          if self.handlebuffer is not None:
            assert getsize(file) == self.tops[file] and getmtime(file) <= self.mtimes[file]+1
        except:
            if DEBUG:
                print ( file+' modified: '
                        +strftime('(%y/%m/%d %H:%M:%S)',localtime(self.mtimes[file]))
                        +strftime(' != (%y/%m/%d %H:%M:%S) ?',localtime(getmtime(file))) )
            raise IOError('modified during download')
        return open(file, mode)


    def _close(self, file):
        f = self.handles[file]
        del self.handles[file]
        if self.whandles.has_key(file):
            del self.whandles[file]
            f.flush()
            self.unlock_file(file, f)
            f.close()
            self.tops[file] = getsize(file)
            self.mtimes[file] = getmtime(file)
        else:
            if self.lock_while_reading:
                self.unlock_file(file, f)
            f.close()


    def _get_file_handle(self, file, for_write):
        if self.handles.has_key(file):
            if for_write and not self.whandles.has_key(file):
                self._close(file)
                try:
                    f = self._open(file, 'rb+')
                    self.handles[file] = f
                    self.whandles[file] = 1
                    self.lock_file(file, f)
                except (IOError, OSError), e:
                    raise IOError('unable to reopen '+file+': '+str(e))

            if self.handlebuffer:
                if self.handlebuffer[-1] != file:
                    self.handlebuffer.remove(file)
                    self.handlebuffer.append(file)
            elif self.handlebuffer is not None:
                self.handlebuffer.append(file)
        else:
            try:
                if for_write:
                    f = self._open(file, 'rb+')
                    self.handles[file] = f
                    self.whandles[file] = 1
                    self.lock_file(file, f)
                else:
                    f = self._open(file, 'rb')
                    self.handles[file] = f
                    if self.lock_while_reading:
                        self.lock_file(file, f)
            except (IOError, OSError), e:
                raise IOError('unable to open '+file+': '+str(e))
            
            if self.handlebuffer is not None:
                self.handlebuffer.append(file)
                if len(self.handlebuffer) > self.max_files_open:
                    self._close(self.handlebuffer.pop(0))

        return self.handles[file]

    def _intervals(self, pos, amount):
        r = []
        stop = pos + amount
        p = bisect_right(self.begins, pos) - 1
        while p < len(self.ranges) and self.ranges[p][0] < stop:
            begin, end, file = self.ranges[p]
            r.append((file, max(pos, begin) - begin, min(end, stop) - begin))
            p += 1
        return r

    def read(self, pos, amount, flush_first = false):
        r = []
        for file, pos, end in self._intervals(pos, amount):
            self.lock.acquire()
            h = self._get_file_handle(file, false)
            if flush_first and self.whandles.has_key(file):
                h.flush()
                fsync(h)
            h.seek(pos)
            r.append(h.read(end - pos))
            self.lock.release()
        r = ''.join(r)
        if len(r) != amount:
            raise IOError('error reading data from '+file)
        return r

    def write(self, pos, s):
        # might raise an IOError
        total = 0
        for file, begin, end in self._intervals(pos, len(s)):
            self.lock.acquire()
            h = self._get_file_handle(file, true)
            h.seek(begin)
            h.write(s[total: total + end - begin])
            self.lock.release()
            total += end - begin

    def top_off(self):
        for begin, end, file in self.ranges:
            l = end - begin
            if l > self.tops.get(file, 0):
                self.lock.acquire()
                h = self._get_file_handle(file, true)
                h.seek(l-1)
                h.write(chr(0xFF))
                self.lock.release()

    def flush(self):
        # may raise IOError or OSError
        for file in self.whandles.keys():
            self.lock.acquire()
            self.handles[file].flush()
            self.lock.release()

    def close(self):
        for file, f in self.handles.items():
            try:
                self.unlock_file(file, f)
            except:
                pass
            try:
                f.close()
            except:
                pass
        self.handles = {}
        self.whandles = {}
        self.handlebuffer = None

def lrange(a, b, c):
    r = []
    while a < b:
        r.append(a)
        a += c
    return r

# everything below is for testing

from fakeopen import FakeOpen

def test_Storage_simple():
    f = FakeOpen()
    m = Storage([('a', 5)], f.open, f.exists, f.getsize, dummy_status)
    assert f.files.keys() == ['a']
    m.write(0, 'abc')
    assert m.read(0, 3) == 'abc'
    m.write(2, 'abc')
    assert m.read(2, 3) == 'abc'
    m.write(1, 'abc')
    assert m.read(0, 5) == 'aabcc'
    
def test_Storage_multiple():
    f = FakeOpen()
    m = Storage([('a', 5), ('2', 4), ('c', 3)], 
        f.open, f.exists, f.getsize, dummy_status)
    x = f.files.keys()
    x.sort()
    assert x == ['2', 'a', 'c']
    m.write(3, 'abc')
    assert m.read(3, 3) == 'abc'
    m.write(5, 'ab')
    assert m.read(4, 3) == 'bab'
    m.write(3, 'pqrstuvw')
    assert m.read(3, 8) == 'pqrstuvw'
    m.write(3, 'abcdef')
    assert m.read(3, 7) == 'abcdefv'

def test_Storage_zero():
    f = FakeOpen()
    Storage([('a', 0)], f.open, f.exists, f.getsize, dummy_status)
    assert f.files == {'a': []}

def test_resume_zero():
    f = FakeOpen({'a': ''})
    Storage([('a', 0)], f.open, f.exists, f.getsize, dummy_status)
    assert f.files == {'a': []}

def test_Storage_with_zero():
    f = FakeOpen()
    m = Storage([('a', 3), ('b', 0), ('c', 3)], 
        f.open, f.exists, f.getsize, dummy_status)
    m.write(2, 'abc')
    assert m.read(2, 3) == 'abc'
    x = f.files.keys()
    x.sort()
    assert x == ['a', 'b', 'c']
    assert len(f.files['a']) == 3
    assert len(f.files['b']) == 0

def test_Storage_resume():
    f = FakeOpen({'a': 'abc'})
    m = Storage([('a', 4)], 
        f.open, f.exists, f.getsize, dummy_status)
    assert f.files.keys() == ['a']
    assert m.read(0, 3) == 'abc'

def test_Storage_mixed_resume():
    f = FakeOpen({'b': 'abc'})
    m = Storage([('a', 3), ('b', 4)], 
        f.open, f.exists, f.getsize, dummy_status)
    x = f.files.keys()
    x.sort()
    assert x == ['a', 'b']
    assert m.read(3, 3) == 'abc'
