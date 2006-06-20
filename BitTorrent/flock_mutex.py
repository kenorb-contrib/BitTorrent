# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Author: David Harrison

import os
if os.name == 'nt':
    import win32file
    from win32file import CreateFile, CreateFileW
    import pywintypes

elif os.name == 'posix':
    import fcntl
    from fcntl import flock

class FLockMutex(object):
    """Cross-platform file lock intended solely for providing mutual
       exclusion across processes in a reasonably cross-platform manner.
       It does not implement mutual exclusion between threads in the
       same process.  Use threading.Lock or threading.RLock for mutual
       exclusion between threads.

       Same semantics as directly locking a file: mutual exclusion is
       provided when a process can lock the file.  If
       the file does not exist, it is created. 

       No protection is provided for a process that calls acquire twice
       without unlocking.

       Only supports non-blocking locks.
    """
    def __init__(self, filename):
        self.mylock = False
        self.filename = filename
        self.handle = None
  
    def acquire(self) :   #, wait=True):  for now, always non-blocking
        """Acquires the lock.  Returns true iff acquired."""
 
        if os.path.exists(filename) and not os.path.isfile(filename):
            raise BTFailure( 
                "Cannot lock file that is not regular file." )  
    
        if os.name == 'nt':
            access = win32file.GENERIC_READ
            share = 0  # do not share, i.e., lock.
            flags = 0
    
            if isinstance(filename, unicode):
                CreateFile = win32file.CreateFileW
            else:
                CreateFile = win32file.CreateFile
        
            try:
                self.handle = CreateFile(self.filename, access, share, 
                                         None, win32file.OPEN_ALWAYS,
                                         flags, None)
            except pywintypes.error, details:
                if details[0] == 32:
                     #if wait:
                     #  win32file.LockFileEx(hfile,flags,0,0xffff0000)
                     return False
                raise IOError(details[2])
    
            self.mylock = True
    
        elif os.name == 'posix':
            if not os.path.exists( self.filename ):
                self.handle = open( self.filename, "w" )
                try:
                    flock( self.handle, fcntl.LOCK_EX|fcntl.LOCK_NB)
                except IOError:
                    return False
        else:
            # dangerous, but what should we do if the platform does
            # not support locking?   --Dave
            return True
            
        return True
  
    def release(self):
        if not os.path.exists(self.filename):
            raise IOError( "Non-existent file: %s" % filename )
        if not self.mylock:
            raise IOError( "Don't own lock on file: %s" % filename )

        self.mylock = False

        # unlock
        if os.name == 'nt':
            win32file.CloseHandle(self.handle)
        elif os.name == 'posix':
            flock( self.handle, fcntl.LOCK_UN )
            self.handle.close()
  
    def __del__(self):
        # unlock file if we hold the lock.
        if self.mylock:
            self.release()
   
        # relock file non-blocking.
        if self.acquire():
            # if relock succeeds then unlock and delete.  If delete
            # fails then throw an exception, since this could be
            # caused by a race condition on delete versus another process 
            # performing a lock.
            self.release()
            try:
                os.remove(self.filename)
            except:
                pass


if __name__ == "__main__":
    # perform unit tests.
    pass
