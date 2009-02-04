#!/usr/bin/env python

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

# Author: David Harrison 
# some of the twisted code for dealing with reactors was copied from 
# RawServer_twisted.py. RawServer_twisted was written by Greg Hazel.

#############################################################
# xicmp.py is intended to run as a separate process executed as root so that
# it can access raw sockets.  THIS FILE MUST NOT BE WRITABLE BY ANY
# UNPRIVILEGED USER.  xicmp only allows functionality already
# commonly available to end-users via the common ping and traceroute commands,
# except this capability is provided via an XML-RPC interface.  This XML-RPC
# interface only accepts calls from the local host.

import sys
#if __name__ == "__main__":
#  sys.path = [".."] + sys.path

debug = True

from BTL.platform import bttime
from BitTorrent.RawServer_twisted import RawServer, Handler
from BTL import BTFailure

ICMP_ECHO_REQUEST = 8          # from RFC
ICMP_ECHO_REPLY = 0            # from RFC
ICMP_TTL_EXPIRED = 11          # from RFC
IP_TTL_EXPIRED_TRANSIT = 11031 # same as MS Windows.
IP_SUCCESS = 0                 # same as MS Windows
INVALID_HANDLE_VALUE = -1      # same as MS Windows
ICMP_TIMEOUT = -2              # pulled from #$!!. lazy
BUFSIZE = 1500

import struct,socket,sys,time, os
from binascii import b2a_hex
from BTL.platform import get_dot_dir
from BitTorrent.platform import spawn, app_root

def toint(s):
    return int(b2a_hex(s), 16)

def tobinary(i):
    return (chr(i >> 24) + chr((i >> 16) & 0xFF) +
        chr((i >> 8) & 0xFF) + chr(i & 0xFF))

class IcmpSocketListener(Handler):
    # a listener is similar to a twisted factory.  It's role is to
    # create a Handler when the connection has completed opening.
    def __init__(self, callback):
        self.callback = callback

    def connection_made(self, connection):
        connection.handler = IcmpMessageReceiver(self.callback)

class IcmpMessageReceiver(Handler):
    # Handlers are analagous to twisted Protocol objects.
                                 
    # This handler listens to a UNIX socket to get datagrams coming from
    # xicmp process.
    
    def __init__(self, callback):
        self.callback = callback
        self._buffer = []
        self._buffer_len = 0
        self._reader = self._read_messages()
        self._next_len = self._reader.next()

    def _read_messages(self):
        while True:
            yield 4
            l = toint(self._message)
            yield l
            data = self._message
            
            self.callback(data)

    # copied from Connecter.py
    def data_came_in(self, conn, s):
        while True:
            i = self._next_len - self._buffer_len
            if i > len(s):
                self._buffer.append(s)
                self._buffer_len += len(s)
                return
            m = s[:i]
            if self._buffer_len > 0:
                self._buffer.append(m)
                m = ''.join(self._buffer)
                self._buffer = []
                self._buffer_len = 0
            s = s[i:]
            self._message = m
            try:
                self._next_len = self._reader.next()
            except StopIteration:
                self._reader = None
                conn.close()
                return

    def connection_lost(self, conn):
        self._reader = None
        pass

    def connection_flushed(self, conn):
        pass


class IcmpIPC(object):
    def __init__(self, rawserver):
        self.rawserver = rawserver
               
    def create(self):
        self.filename = os.path.join(get_dot_dir(), "xicmp-unix-socket")
        
        if os.path.exists(self.filename):
            # HEREDAVE. I might add this check back later. --Dave
            #try:
            #    self.write_message(tobinary(0))
            #except BTFailure:
            #    pass
            #else:
            #    raise BTFailure(_("Could not create icmp unix socket: already in use"))
            try:
                os.unlink(self.filename)
            except OSError, e:
                raise BTFailure(_("Could not remove old icmp socket filename:")
                                + unicode(e.args[0]))
        try:
            icmp_socket = self.rawserver.create_unixserversocket(self.filename)
        except socket.error, e:
            raise BTFailure(_("Could not create icmp socket: ")+unicode(e.args[0]))

        self.icmp_socket = icmp_socket
                
    def start(self, callback):
        #IPC.start(self, callback)
        self.rawserver.start_listening(self.icmp_socket,
                                       IcmpSocketListener(callback))

        print "Spawning xicmp"
        xicmp = os.path.join( app_root, "icmp", "xicmp" )
        spawn( xicmp, self.filename )

    def stop(self):
        # safe double-stop, since MultiTorrent seems to be prone to do so
        if self.icmp_socket:
            # it's possible we're told to stop after icmp_socket creation but
            # before rawserver registration
            if self.rawserver:
                self.rawserver.stop_listening(self.icmp_socket)
            self.icmp_socket.close()
            self.icmp_socket = None

    def write_message( self, buffer ):
        pass
        
class IcmpFile(object):
    """Not really a file, just a handle (ICMP identifier) upon which ICMP
       messages can be sent."""
    def __init__(self, id):
        self.id = id
        self.seqno = 0


class IcmpClient(object):
  def __init__(self, unix_socket_fname = ""):
    Thread.__init__(self)
    self.id = os.getpid()
    if not unix_socket_fname:
        unix_socket_fname = os.path.join(platform.get_dot_dir(),
                                         "xicmp-unix-socket" )
    self.ux_fname = unix_socket_fname
    self.files = {} # id -> IcmpFile
    self.dfs = {}   # id -> deferreds.  A given id may have multiple deferreds.
    #self.sock = socket.socket(socket.AF_INET,socket.SOCK_RAW,
    #                             socket.getprotobyname('icmp'))
    self.sock = open( unix_socket_fname, "rw" )
    os.setuid(os.getuid())      # give up root access as quickly as possible.
    self.sock.settimeout(2.0)   # times out to periodically check done flag.
                                # Separate from time outs on icmp messages.
    #self.lock = Condition()     # simliar to a semaphore, but has only two
    #                            # states: locked and unlocked.

  def create_file(self):
    for i in xrange(2**16):
        self.id = (self.id+1) % ((2**16)-1)  # hopefully no collisions occur
                                             # with other apps using icmp.
        if not self.files.has_key(self.id):
            break
    else:
        return INVALID_HANDLE_VALUE

    self.server = server
    self.files[self.id] = IcmpFile(self.id)
    return self.id

  def close(self, id):
    if not self.files.has_key(id):
       raise Fault(8002, "Asked to close ICMP file that is closed or "
                    "was never opened." )
    del self.files[id]
    #self.lock.acquire()
    try:
        lst = None
        if self.dfs.has_key(id):
            lst = dfs[id]
            del self.dfs[id]
    finally:
        pass
    #    self.lock.release()

    if lst is not None:
        for df in lst:
            df.errback(Fault(8002,"ICMP id closed while outstanding request"))

    return IP_SUCCESS
            
  def _calc_checksum(self, packet):
        """ICMP checksum"""
        #Header Checksum (rfc 792)
        #
        #The 16 bit one's complement of the one's complement sum of all 16
        #bit words in the header.  For computing the checksum, the checksum
        #field should be zero.  This checksum may be replaced in the
        #future.
        if len(packet) % 2 == 1:
            packet += "\x00"
        shorts = struct.unpack("!%sH" % (len(packet)/2), packet)
        sum = 0
        for s in shorts:
            sum += s
        sum = (sum >> 16) + (sum & 0xFFFF)
        sum += sum >> 16
        return ~sum

  def send_echo_request(self, id, addr, ttl, timeout):
      self.sock.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)

      if not self.files.has_key(id):
        raise Fault(8002, "asked to send ICMP echo request for id not open.")
      
      file = self.files[id]
      type = ICMP_ECHO_REQUEST     
      buf = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0x00, 0x0000,
                                  id, file.seqno )  
      sum = self._calc_checksum(buf)    
      buf = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0x00, sum,
                                  id, file.seqno )  

      df = Deferred() 
      df.seqno = file.seqno
      file.seqno += 1
      df.id = id
      if not self.dfs.has_key(df.id):
          self.dfs[df.id] = [df]
      else:
          self.dfs[df.id].append(df)  # deferreds for this id.
      df.timestamp = bttime()
      self.sock.sendto(buf, (addr,22))
      reactor.callLater( timeout, self._handle_timeout, df.id, df.seqno )
      return df

  def _find_and_remove( self, id, seqno):
      """finds deferred for the passed id and seqno and then removes it
         from dfs."""
      # lock ensures that searching and removing are done as an atomic step.
      # This eliminates a race condition between the reactor and
      # IcmpClient threads.
      #self.lock.acquire()
      try:
        df = None
        if self.dfs.has_key(id):
          for df in self.dfs[id]:
            if df.seqno == seqno:
              self.dfs[id].remove(df)
              if len(self.dfs[id]) == 0:
                del self.dfs[id]
              break
      finally:
        #self.lock.release()
        pass
      return df
    
  def _handle_timeout(self, id, seqno):
      """called when an icmp message times out."""

      df = self._find_and_remove(id,seqno)
      if df is None:
          pass # request was already satisfied.
      else:
          df.errback(Fault(ICMP_TIMEOUT,"timeout"))
        
  def recv_datagram(self, buf):
      current_time = bttime()
      icmp = buf[20:]       # removes IP header. Assumes IPv4. blech.
      type = ord(icmp[0])
      if type == ICMP_TTL_EXPIRED:
          type = IP_TTL_EXPIRED_TRANSIT
          # type (1 byte), code (1 byte), chksum (2 bytes)
          # unused(4 bytes)
          # original internet header (20)
          # first 8 bytes of original ICMP (type,code,chksum,id,seq)
          icmp = icmp[4+4+20:]  # strips outer header.
      elif type == ICMP_ECHO_REPLY:
          pass
      else:
          return   # ignore other ICMP messages
      
      # parse ICMP echo reply
      (orig_type,code,chksum,id,seqno) = \
          struct.unpack("!BBHHH",icmp[0:8])
      
      # find appropriate deferred. If found then remove it from dfs.
      df = self._find_and_remove(id,seqno)
      
      # callback the appropriate deferred after adjusting to millisecs.
      if df is not None:
          rtt = current_time - df.timestamp
          rtt *= 1000
          if debug:
            print "Reply from %s: id=%s, seqno=%u, time=%.3f ms" %\
              (addr[0], id, seqno, rtt)
          
          df.callback( (addr[0], type, rtt) )
            
#  def run(self):
#      while not self.done.isSet():
#          try:
#              buf, addr = self.sock.recvfrom(1500)
#              buf = self.sock.read()
#              current_time = bttime()
#              icmp = buf[20:]       # removes IP header. Assumes IPv4. blech.
#              type = ord(icmp[0])
#              if type == ICMP_TTL_EXPIRED:
#                  type = IP_TTL_EXPIRED_TRANSIT
#                  # type (1 byte), code (1 byte), chksum (2 bytes)
#                  # unused(4 bytes)
#                  # original internet header (20)
#                  # first 8 bytes of original ICMP (type,code,chksum,id,seq)
#                  icmp = icmp[4+4+20:]  # strips outer header.
#              elif type == ICMP_ECHO_REPLY:
#                  pass
#              else:
#                  continue   # ignore other ICMP messages
#        
#              # parse ICMP echo reply
#              (orig_type,code,chksum,id,seqno) = \
#                  struct.unpack("!BBHHH",icmp[0:8])
#        
#              # find appropriate deferred. If found then remove it from dfs.
#              df = self._find_and_remove(id,seqno)
#
#              # callback the appropriate deferred after adjusting to millisecs.
#              if df is not None:
#                  rtt = current_time - df.timestamp
#                  rtt *= 1000
#                  if debug:
#                    print "Reply from %s: id=%s, seqno=%u, time=%.3f ms" %\
#                      (addr[0], id, seqno, rtt)
#                  
#                  reactor.callFromThread( df.callback, (addr[0], type, rtt) )
#              
#          except socket.timeout:
#              pass  # occassionally times out to check done flag.
#                    # This has nothing to do with time outs on ICMP messages.
           

#class XIcmpClient(xmlrpc.XMLRPC):
#    """XML-RPC interface exported so that a non-superuser process can
#       use ICMP via a programmatic interface.  This is an interface to a
#       client with respect to ICMP, but a server with respect to
#       XML-RPC.  This XML-RPC interface only accepts calls from the
#       local machine.
#       """
#    
#    def __init__(self, client):
#        self.client = client
#        sys.stdout.flush()
#        self.local_ips = ["127.0.0.1"]
#        df = get_host_ips(wrap_task(reactor.callLater))
#        def add_host_ips(ips):
#            self.local_ips.extend(ips)
#        df.addCallback(add_host_ips)
#
#    # match naming scheme used by win32icmp.
#    def render(self,request):
#        if request.client.host in self.local_ips:
#            return xmlrpc.XMLRPC.render(self,request)
#        else:
#            self._cbRender(Fault(8002, "Only local requests allowed"),request)
#        return server.NOT_DONE_YET
#    
#    def xmlrpc_IcmpCreateFile(self):
#        return self.client.create_file()
#    
#    def xmlrpc_IcmpSendEcho( self, id, addr, ttl, timeout ):
#        return self.client.send_echo_request(id,addr,ttl,timeout)
#
#    def xmlrpc_IcmpCloseHandle( self, id ):
#        return self.client.close(id)
    
#PORT = 19669
#def main():
#    global PORT, noSignals
#
#    if len(sys.argv) == 2:
#      port = int(sys.argv[1])
#    else:
#      port = PORT
#      
#    done = Event()    # threads know to gracefully die when done is set.
#    def stop():
#      done.set()
#      reactor.stop()
#    def handler(signum,frame):
#      reactor.callFromThread(stop) 
#    signal.signal(signal.SIGINT, handler)  # handle ctrl-c gracefully
#    
#    try:
#        icmp_client = IcmpClient(done)     # runs in its own thread.
#        icmp_client.start()
#
#        factory = server.Site(XIcmpClient(icmp_client))
#        factory.resource.base = factory
#        print "listening on port", port
#        sys.stdout.flush()
#        reactor.listenTCP(port, factory)
#
#        try:
#            if noSignals:
#                reactor.run(installSignalHandlers=False)
#            else:
#                reactor.run()
#        except KeyboardInterrupt:
#            print 'CTRL-C. Shutting down.'
#        except Exception, err:
#            print 'Problem with running ICMP XML-RPC: %s' % err
#    finally:
#        print "setting done."
#        try:
#          reactor.stop()
#        except RuntimeError:
#          pass # don't respond to: "can't stop reactor that isn't running"
#        done.set()
#
#def test():
#    time.sleep(2)  # time for xml-rpc server to startup.
#    proxy = xmlrpclib.ServerProxy('http://localhost:%d' % PORT )
#    id = proxy.IcmpCreateFile()
#    print "test: IcmpCreateFile returned id=", id
#    rtt = proxy.IcmpSendEcho(id, addr=sys.argv[1], ttl=int(sys.argv[2]),
#                             timeout=3)
#    print "ping %s rtt=%s" % (sys.argv[1], rtt)
#
#def test():
#    client = IcmpClient();
#      
#if __name__=='__main__':
#    import sys
#
#    if "--test" in sys.argv:
#        th = Thread(target=test)
#        th.start()
#    main()
