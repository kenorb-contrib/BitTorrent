# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bram Cohen and Greg Hazel

#import pdb
import os
import Queue
from array import array
from bisect import bisect_right
from BitTorrent.translation import _

from BitTorrent.obsoletepythonsupport import *

from BitTorrent import BTFailure, app_name
from BitTorrent.defer import Deferred, ThreadedDeferred
from BitTorrent.yielddefer import launch_coroutine, _wrap_task
from BitTorrent.platform import get_sparse_files_support, get_allocated_regions
from BitTorrent.sparse_set import SparseSet
from BitTorrent.DictWithLists import DictWithLists, DictWithSets
import BitTorrent.stackthreading as threading


resume_version = 'BitTorrent resume state file, version 1\n'

if os.name == 'nt':
    import win32file
    FSCTL_SET_SPARSE = 0x900C4

    def _sparse_magic(handle, length=0):
        win32file.DeviceIoControl(handle, FSCTL_SET_SPARSE, '', 0, None)

        win32file.SetFilePointer(handle, length, win32file.FILE_BEGIN)
        win32file.SetEndOfFile(handle)

        win32file.SetFilePointer(handle, 0, win32file.FILE_BEGIN)

    def make_sparse_file(path, length=0):
        supported = get_sparse_files_support(path)
        if not supported:
            raise Exception("No sparse files, use file()")

        # If the hFile handle is opened with the
        # FILE_FLAG_NO_BUFFERING flag set, an application can move the
        # file pointer only to sector-aligned positions.  A
        # sector-aligned position is a position that is a whole number
        # multiple of the volume sector size. An application can
        # obtain a volume sector size by calling the GetDiskFreeSpace
        # function.

        handle = win32file.CreateFile(path,
                                      win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                                      win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                                      None,
                                      win32file.CREATE_NEW,
                                      #win32file.FILE_ATTRIBUTE_NORMAL,
                                      win32file.FILE_FLAG_NO_BUFFERING,
                                      None)

        _sparse_magic(handle, length)
        fd = win32file._open_osfhandle(handle, os.O_BINARY)
        handle.Detach()

        f = os.fdopen(fd, "wa")
        return f

    def make_file_sparse(path, f, length=0):
        supported = get_sparse_files_support(path)
        if not supported:
            return

        handle = win32file._get_osfhandle(f.fileno())
        _sparse_magic(handle, length)

else:
    # TODO: sparse files on other platforms?
    def make_sparse_file(*args, **kwargs):
        return
    def make_file_sparse(*args, **kwargs):
        return

class FilePool(object):

    def __init__(self, doneflag, max_files_open, num_disk_threads):
        self.doneflag = doneflag
        self.file_to_torrent = {}

        self.free_handle_condition = threading.Condition()
        self.active_file_to_handles = DictWithSets()
        self.open_file_to_handles = DictWithLists()

        self.set_max_files_open(max_files_open)
        
        self.diskq = Queue.Queue()
        for i in xrange(num_disk_threads):
            t = threading.Thread(target=self._disk_thread,
                                 name="disk_thread-%s" % (i+1))
            t.start()

    def close_all(self):
        failures = {}
        self.free_handle_condition.acquire()
        while self.get_open_file_count() > 0:
            while len(self.open_file_to_handles) > 0:
                filename, handle = self.open_file_to_handles.popitem()
                try:
                    handle.close()
                except Exception, e:
                    failures[self.file_to_torrent[filename]] = e
                self.free_handle_condition.notify()
            if self.get_open_file_count() > 0:
                self.free_handle_condition.wait(1)
        self.free_handle_condition.release()
            
        for torrent, e in failures.iteritems():
            torrent.got_exception(e)

    def close_files(self, file_set):
        failures = set()
        self.free_handle_condition.acquire()
        done = False

        while not done:        

            filenames = list(self.open_file_to_handles.iterkeys())
            for filename in filenames:
                if filename not in file_set:
                    continue
                handles = self.open_file_to_handles.poprow(filename)
                for handle in handles:
                    try:
                        handle.close()
                    except Exception, e:
                        failures.add(e)
                    self.free_handle_condition.notify()

            done = True
            for filename in file_set.iterkeys():
                if filename in self.active_file_to_handles:
                    done = False
                    break

            if not done:
                self.free_handle_condition.wait(0.5)
        self.free_handle_condition.release()
        if len(failures) > 0:
            raise failures.pop()

    def set_max_files_open(self, max_files_open):
        if max_files_open <= 0:
            max_files_open = 1e100
        self.max_files_open = max_files_open
        self.close_all()

    def add_files(self, files, torrent):
        for filename in files:
            if filename in self.file_to_torrent:
                raise BTFailure(_("File %s belongs to another running torrent")
                                % filename)
        for filename in files:
            self.file_to_torrent[filename] = torrent

    def remove_files(self, files):
        for filename in files:
            del self.file_to_torrent[filename]

    def _ensure_exists(self, filename, length=0):
        if not os.path.exists(filename):
            f = os.path.split(filename)[0]
            if f != '' and not os.path.exists(f):
                os.makedirs(f)
            f = file(filename, 'wb')
            make_file_sparse(filename, f, length)
            f.close()

    def get_open_file_count(self):
        t = self.open_file_to_handles.total_length()
        t += self.active_file_to_handles.total_length()
        return t            
            
    def acquire_handle(self, filename, for_write, length=0):
        # this will block until a new file handle can be made
        self.free_handle_condition.acquire()

        # abort disk ops on unregistered files
        if filename not in self.file_to_torrent:
            self.free_handle_condition.release()
            return None

        while self.active_file_to_handles.total_length() == self.max_files_open:
            self.free_handle_condition.wait()

        if filename in self.open_file_to_handles:
            handle = self.open_file_to_handles.pop_from_row(filename)
            if for_write and not is_open_for_write(handle):
                handle.close()
                handle = file(filename, 'rb+', 0)
                make_file_sparse(filename, handle, length=length)
            #elif not for_write and is_open_for_write(handle):
            #    handle.close()
            #    handle = file(filename, 'rb', 0)
        else:
            if self.get_open_file_count() == self.max_files_open:
                oldfname, oldhandle = self.open_file_to_handles.popitem()
                oldhandle.close()
            self._ensure_exists(filename, length)
            if for_write:
                handle = file(filename, 'rb+', 0)
                make_file_sparse(filename, handle, length=length)
            else:
                handle = file(filename, 'rb', 0)
                    
        self.active_file_to_handles.push_to_row(filename, handle)
        self.free_handle_condition.release()
        return handle

    def release_handle(self, filename, handle):
        self.free_handle_condition.acquire()
        self.active_file_to_handles.remove_fom_row(filename, handle)
        self.open_file_to_handles.push_to_row(filename, handle)
        self.free_handle_condition.notify()
        self.free_handle_condition.release()
        
    def _create_op(self, _f, *args, **kwargs):
        df = Deferred()
        self.diskq.put((df, _f, args, kwargs))
        return df
    read = _create_op
    write = _create_op

    def _disk_thread(self):
        while not self.doneflag.isSet():
            try:
                df, func, args, kwargs = self.diskq.get(True, 1)
            except Queue.Empty:
                pass
            else:
                try:
                    func(df, *args, **kwargs)
                except Exception, e:
                    print "DISK ERROR", e
                    import traceback
                    traceback.print_exc()
    
# Make this a separate function because having this code in Storage.__init__()
# would make python print a SyntaxWarning (uses builtin 'file' before 'global')

def bad_libc_workaround():
    global file
    def file(name, mode = 'r', buffering = None):
        return open(name, mode)

def is_open_for_write(f):
    if 'w' in f.mode:
        return True
    if 'r' in f.mode and '+' in f.mode:
        return True
    return False

class Storage(object):

    def __init__(self, config, filepool, save_path, files, add_task,
                 external_add_task, df, doneflag):
        self.filepool = filepool
        self.config = config
        self.doneflag = doneflag
        self.add_task = add_task
        self.external_add_task = external_add_task        
        # a list of bytes ranges and filenames for window-based IO
        self.ranges = []
        # a dict of filename-to-ranges for piece priorities and filename lookup
        self.range_by_name = {}
        # a sparse set for smart allocation detection
        self.allocated_regions = SparseSet()
        
        # dict of filename-to-length on disk (for % complete in the file view)
        self.undownloaded = {}
        self.save_path = save_path

        # Rather implement this as an ugly hack here than change all the
        # individual calls. Affects all torrent instances using this module.
        if config['bad_libc_workaround']:
            bad_libc_workaround()

        self.initialized = False
        tdf = ThreadedDeferred(_wrap_task(external_add_task),
                               self._build_file_structs, filepool, files)
        tdf.addCallback(df.callback)
        self.startup_df = tdf

    def _build_file_structs(self, filepool, files):
        total = 0
        for filename, length in files:
            # we're shutting down, abort.
            if self.doneflag.isSet():
                return False
            
            self.undownloaded[filename] = length
            if length > 0:
                self.ranges.append((total, total + length, filename))

            self.range_by_name[filename] = (total, total + length)

            if os.path.exists(filename):
                if not os.path.isfile(filename):
                    raise BTFailure(_("File %s already exists, but is not a "
                                      "regular file") % filename)
                l = os.path.getsize(filename)
                if l > length:
                    h = file(filename, 'rb+')
                    make_file_sparse(filename, h, length)
                    # This is the truncation Bram was talking about that no one
                    # else thinks is a good idea.
                    #h.truncate(length)
                    h.close()
                    l = length

                a = get_allocated_regions(filename, begin=0, length=l)
                if a is not None:
                    a.offset(total)
                else:
                    a = SparseSet()
                    if l > 0:
                        a.add(total, total + l)
                self.allocated_regions += a
            total += length
        self.total_length = total
        self.initialized = True
        return True

    def get_byte_range_for_filename(self, filename):
        if filename not in self.range_by_name:
            filename = os.path.normpath(filename)
            filename = os.path.join(self.save_path, filename)
        return self.range_by_name[filename]

    def was_preallocated(self, pos, length):
        return self.allocated_regions.is_range_in(pos, pos+length)

    def get_total_length(self):
        return self.total_length

    def _intervals(self, pos, amount):
        r = []
        stop = pos + amount
        p = max(bisect_right(self.ranges, (pos, )) - 1, 0)
        for begin, end, filename in self.ranges[p:]:
            if begin >= stop:
                break
            r.append((filename, max(pos, begin) - begin, min(end, stop) - begin))
        return r

    def _read(self, df, filename, pos, amount):
        begin, end = self.get_byte_range_for_filename(filename)
        length = end - begin
        h = self.filepool.acquire_handle(filename, for_write=False, length=length)
        if h is None:
            return
        try:        
            h.seek(pos)
            r = h.read(amount)
        finally:
            self.filepool.release_handle(filename, h)
        self.external_add_task(0, df.callback, r)

    def _batch_read(self, pos, amount):
        dfs = []
        r = []

        # queue all the reads
        for filename, pos, end in self._intervals(pos, amount):
            df = self.filepool.read(self._read, filename, pos, end - pos)
            dfs.append(df)

        # yield on all the reads - they complete in any order
        for df in dfs:
            yield df
            r.append(df.getResult())

        r = ''.join(r)

        if len(r) != amount:
            raise BTFailure(_("Short read - something truncated files?"))

        yield r 

    def read(self, pos, amount):
        df = launch_coroutine(_wrap_task(self.add_task),
                              self._batch_read, pos, amount)
        return df

    def _write(self, df, filename, pos, s):
        begin, end = self.get_byte_range_for_filename(filename)
        length = end - begin
        h = self.filepool.acquire_handle(filename, for_write=True, length=length)
        if h is None:
            return
        try:        
            h.seek(pos)
            h.write(s)
        finally:
            self.filepool.release_handle(filename, h)
        self.external_add_task(0, df.callback, len(s))
        
    def _batch_write(self, pos, s):
        dfs = []

        total = 0
        amount = len(s)

        # queue all the writes        
        for filename, begin, end in self._intervals(pos, amount):
            length = end - begin
            d = buffer(s, total, length)
            total += length
            df = self.filepool.write(self._write, filename, begin, d)
            dfs.append(df)

        # yield on all the writes - they complete in any order
        for df in dfs:
            yield df
        
        yield total

    def write(self, pos, s):
        df = launch_coroutine(_wrap_task(self.add_task),
                              self._batch_write, pos, s)
        return df
        
    def close(self):
        if not self.initialized:
            self.startup_df.addCallback(lambda *a : self.filepool.close_files(self.range_by_name))
            return self.startup_df
        self.filepool.close_files(self.range_by_name)

    def downloaded(self, pos, length):
        for filename, begin, end in self._intervals(pos, length):
            self.undownloaded[filename] -= end - begin
