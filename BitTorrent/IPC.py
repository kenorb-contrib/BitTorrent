# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Greg Hazel
# based on code by Uoti Urpala
from __future__ import generators

import os
import socket
import sys
import traceback
if os.name == 'nt':
    import win32api
    import win32event
    import winerror
    import win32ui
    import dde
    import pywin.mfc.object

from binascii import b2a_hex

from BitTorrent.RawServer_magic import RawServer, Handler
from BitTorrent.platform import get_home_dir, get_config_dir
from BitTorrent import INFO, WARNING, ERROR, CRITICAL, BTFailure, app_name

def toint(s):
    return int(b2a_hex(s), 16)

def tobinary(i):
    return (chr(i >> 24) + chr((i >> 16) & 0xFF) +
        chr((i >> 8) & 0xFF) + chr(i & 0xFF))

CONTROL_SOCKET_PORT = 46881

class ControlsocketListener(Handler):

    def __init__(self, callback):
        self.callback = callback

    def connection_made(self, connection):
        connection.handler = MessageReceiver(self.callback)


class MessageReceiver(Handler):

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
            action = self._message
            
            if action in ('no-op',):
                self.callback(action, None)
            else:
                yield 4
                l = toint(self._message)
                yield l
                data = self._message
                if action in ('show_error',):
                    self.callback(action, data)
                else:
                    yield 4
                    l = toint(self._message)
                    yield l
                    path = self._message
                    if action in ('start_torrent'):
                        self.callback(action, data, path)

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

class IPC(object):
    def __init__(self, config, log):
        self.config = config
        self.log = log
        self.rawserver = None
        self.callback = None        

    def create(self):
        pass

    def start(self, callback):
        self.callback = callback

    def send_command(self, command, *args):
        pass

    def handle_command(self, command, *args):
        if callable(self.callback):
            return self.callback(command, *args)
        self.log(WARNING, _("Unhandled command: %s %s"  % (str(command), str(args))))

    def set_rawserver(self, rawserver):
        self.rawserver = rawserver

    def stop(self):
        pass

class IPCSocketBase(IPC):

    def __init__(self, *args):
        IPC.__init__(self, *args)
        self.port = CONTROL_SOCKET_PORT

        self.controlsocket = None        

    def start(self, callback):
        IPC.start(self, callback)
        self.rawserver.start_listening(self.controlsocket,
                                       ControlsocketListener(self.handle_command))

    def stop(self):
        # safe double-stop, since TorrentQueue seems to be prone to do so
        if self.controlsocket:
            # it's possible we're told to stop after controlsocket creation but
            # before rawserver registration
            if self.rawserver:
                self.rawserver.stop_listening(self.controlsocket)
            self.controlsocket.close()
            self.controlsocket = None
        
class IPCUnixSocket(IPCSocketBase):

    def __init__(self, *args):
        IPCSocketBase.__init__(self, *args)
        self.socket_filename = os.path.join(self.config['data_dir'], 'ui_socket')
        
    def create(self):
        filename = self.socket_filename
        if os.path.exists(filename):
            try:
                self.send_command('no-op')
            except BTFailure:
                pass
            else:
                raise BTFailure(_("Could not create control socket: already in use"))

            try:
                os.unlink(filename)
            except OSError, e:
                raise BTFailure(_("Could not remove old control socket filename:")
                                + str(e))
        try:
            controlsocket = RawServer.create_unixserversocket(filename)
        except socket.error, e:
            raise BTFailure(_("Could not create control socket: ")+str(e))

        self.controlsocket = controlsocket

    # blocking version without rawserver
    def send_command(self, command, *args):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        filename = self.socket_filename
        try:
            s.connect(filename)
            s.send(tobinary(len(command)))
            s.send(command)
            for arg in args:
                s.send(tobinary(len(arg)))
                s.send(arg)
            s.close()
        except socket.error, e:
            s.close()
            raise BTFailure(_("Could not send command: ") + str(e))


class IPCWin32Socket(IPCSocketBase):
    def __init__(self, *args):
        IPCSocketBase.__init__(self, *args)
        self.socket_filename = os.path.join(self.config['data_dir'], 'ui_socket')
        self.mutex = None
        self.master = 0

    def _get_sic_path(self):
        directory = get_config_dir()
        configdir = os.path.join(directory, '.bittorrent')
        filename = os.path.join(configdir, ".btcontrol")
        return filename

    def create(self):
        obtain_mutex = 1
        mutex = win32event.CreateMutex(None, obtain_mutex, app_name)

        # prevent the PyHANDLE from going out of scope, ints are fine
        self.mutex = int(mutex)
        mutex.Detach()

        lasterror = win32api.GetLastError()
        
        if lasterror == winerror.ERROR_ALREADY_EXISTS:
            takeover = 0

            try:
                # if the mutex already exists, discover which port to connect to.
                # if something goes wrong with that, tell us to take over the
                # role of master
                takeover = self.discover_sic_socket()
            except:
                pass
            
            if not takeover:
                raise BTFailure(_("Global mutex already created."))

        self.master = 1

        # lazy free port code
        port_limit = 50000
        while self.port < port_limit:
            try:
                controlsocket = RawServer.create_serversocket(self.port,
                                                              '127.0.0.1', reuse=True)
                self.controlsocket = controlsocket
                break
            except socket.error, e:
                self.port += 1

        if self.port >= port_limit:
            raise BTFailure(_("Could not find an open port!"))

        filename = self._get_sic_path()
        (path, name) = os.path.split(filename)
        try:
            os.makedirs(path)
        except OSError, e:
            # 17 is dir exists
            if e.errno != 17:
                BTFailure(_("Could not create application data directory!"))
        f = open(filename, "w")
        f.write(str(self.port))
        f.close()
        
        # we're done writing the control file, release the mutex so other instances can lock it and read the file
        # but don't destroy the handle until the application closes, so that the named mutex is still around
        win32event.ReleaseMutex(self.mutex)

    def discover_sic_socket(self):
        takeover = 0
        
        # mutex exists and has been opened (not created, not locked).
        # wait for it so we can read the file
        r = win32event.WaitForSingleObject(self.mutex, win32event.INFINITE)

        # WAIT_OBJECT_0 means the mutex was obtained
        # WAIT_ABANDONED means the mutex was obtained, and it had previously been abandoned
        if (r != win32event.WAIT_OBJECT_0) and (r != win32event.WAIT_ABANDONED):
            raise BTFailure(_("Could not acquire global mutex lock for controlsocket file!"))

        filename = self._get_sic_path()
        try:
            f = open(filename, "r")
            self.port = int(f.read())
            f.close()
        except:
            if (r == win32event.WAIT_ABANDONED):
                self.log(WARNING, _("A previous instance of BT was not cleaned up properly. Continuing."))
                # take over the role of master
                takeover = 1
            else:
                self.log(WARNING, (_("Another instance of BT is running, but \"%s\" does not exist.\n") % filename)+
                                  _("I'll guess at the port."))
                try:
                    self.port = CONTROL_SOCKET_PORT
                    self.send_command('no-op')
                    self.log(WARNING, _("Port found: %d") % self.port)
                    try:
                        f = open(filename, "w")
                        f.write(str(self.port))
                        f.close()
                    except:
                        traceback.print_exc()
                except:
                    # this is where this system falls down.
                    # There's another copy of BitTorrent running, or something locking the mutex,
                    # but I can't communicate with it.
                    self.log(WARNING, _("Could not find port."))
                
        
        # we're done reading the control file, release the mutex so other instances can lock it and read the file
        win32event.ReleaseMutex(self.mutex)

        return takeover        

    #blocking version without rawserver
    def send_command(self, command, *datas):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('127.0.0.1', self.port))
            s.send(tobinary(len(command)))
            s.send(command)
            for data in datas:
                s.send(tobinary(len(data)))
                s.send(data)
            s.close()
        except socket.error, e:
            try:
                s.close()
            except:
                pass
            raise BTFailure(_("Could not send command: ") + str(e))

   
    def stop(self):
        if self.master:
            r = win32event.WaitForSingleObject(self.mutex, win32event.INFINITE)
            filename = self._get_sic_path()
            try:
                os.remove(filename)
            except OSError, e:
                # print, but continue
                traceback.print_exc()
            self.master = 0
            win32event.ReleaseMutex(self.mutex)
            # close it so the named mutex goes away
            win32api.CloseHandle(self.mutex)
            self.mutex = None

if os.name == 'nt':
    class HandlerObject(pywin.mfc.object.Object):
        def __init__(self, handler, target):
            self.handler = handler
            pywin.mfc.object.Object.__init__(self, target)

    class Topic(HandlerObject):
        def __init__(self, handler, target):
            target.AddItem(dde.CreateStringItem(""))
            HandlerObject.__init__(self, handler, target)

        def Request(self, x):
            # null byte hack
            x = x.replace("\\**0", "\0")
            items = x.split("|")
            self.handler(items[0], *items[1:])
            return ("OK")

        # remote procedure call
        #def Exec(self, x):
        #    exec x

    class Server(HandlerObject):
        def __init__(self, log, *args):
            self.log = log
            HandlerObject.__init__(self, *args)

        def CreateSystemTopic(self):
            return Topic(self.handler, dde.CreateServerSystemTopic())

        def Status(self, s):
            #if self.log:
            #    self.log(INFO, _("IPC Status: %s") % s)
            pass

        def stop(self):
            self.Shutdown()
            self.Destroy()

class IPCWin32DDE(IPC):
    def create(self):
        self.server = None

        # try to connect first
        self.client = Server(None, None, dde.CreateServer())
        self.client.Create(app_name, dde.CBF_FAIL_SELFCONNECTIONS|dde.APPCMD_CLIENTONLY)
        self.conversation = dde.CreateConversation(self.client)
        try:
            self.conversation.ConnectTo(app_name, "controlsocket")
            raise BTFailure(_("DDE Conversation connected."))
        except dde.error, e:
            # no one is listening
            pass

        # clean up
        self.client.stop()
        del self.client
        del self.conversation

        # start server
        self.server = Server(self.log, self.handle_command, dde.CreateServer())
        self.server.Create(app_name, dde.CBF_FAIL_SELFCONNECTIONS|dde.APPCLASS_STANDARD)
        self.server.AddTopic(Topic(self.handle_command, dde.CreateTopic("controlsocket")))

    def send_command(self, command, *args):
        s = '|'.join([command, ] + list(args))
        # null byte hack
        if s.count("\0") > 0:
            self.log(WARNING, "IPC: String with null byte(s):" + s)
            s = s.replace("\0", "\\**0")
        result = self.conversation.Request(s)

    def stop(self):
        if self.server:
            server = self.server
            self.server = None
            server.stop()

if os.name == 'nt':
    #ipc_interface = IPCWin32Socket
    ipc_interface = IPCWin32DDE
else:
    ipc_interface = IPCUnixSocket
    