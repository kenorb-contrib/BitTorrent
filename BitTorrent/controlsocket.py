# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written my Uoti Urpala
from __future__ import generators

import os
import socket
import sys
if sys.platform.startswith('win'):
    import win32api
    import win32event
    import winerror

from binascii import b2a_hex

from BitTorrent.RawServer_magic import RawServer, Handler
from BitTorrent.platform import get_home_dir, get_config_dir
from BitTorrent import BTFailure, app_name

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


class ControlSocket(object):

    def __init__(self, config):
        self.port = CONTROL_SOCKET_PORT
        self.mutex = None
        self.master = 0

        self.socket_filename = os.path.join(config['data_dir'], 'ui_socket')

        self.rawserver = None
        self.controlsocket = None

    def set_rawserver(self, rawserver):
        self.rawserver = rawserver

    def start_listening(self, callback):
        self.rawserver.start_listening(self.controlsocket,
                                  ControlsocketListener(callback))

    def create_socket_inet(self, port = CONTROL_SOCKET_PORT):
        
        try:
            controlsocket = RawServer.create_serversocket(port,
                                                          '127.0.0.1', reuse=True)
        except socket.error, e:
            raise BTFailure(_("Could not create control socket: ")+str(e))

        self.controlsocket = controlsocket

##    def send_command_inet(self, rawserver, action, data = ''):
##        r = MessageReceiver(lambda action, data: None)
##        try:
##            conn = rawserver.start_connection(('127.0.0.1', CONTROL_SOCKET_PORT), r)
##        except socket.error, e:
##            raise BTFailure(_("Could not send command: ") + str(e))
##        conn.write(tobinary(len(action)))
##        conn.write(action)
##        conn.write(tobinary(len(data)))
##        conn.write(data)

    #blocking version without rawserver
    def send_command_inet(self, action, *datas):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('127.0.0.1', self.port))
            s.send(tobinary(len(action)))
            s.send(action)
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

    def create_socket_unix(self):
        filename = self.socket_filename
        if os.path.exists(filename):
            try:
                self.send_command_unix('no-op')
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

##    def send_command_unix(self, rawserver, action, data = ''):
##        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
##        filename = self.socket_filename
##        try:
##            s.connect(filename)
##        except socket.error, e:
##            raise BTFailure(_("Could not send command: ") + str(e))
##        r = MessageReceiver(lambda action, data: None)
##        conn = rawserver.wrap_socket(s, r, ip = s.getpeername())
##        conn.write(tobinary(len(action)))
##        conn.write(action)
##        conn.write(tobinary(len(data)))
##        conn.write(data)

    # blocking version without rawserver
    def send_command_unix(self, action, *datas):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        filename = self.socket_filename
        try:
            s.connect(filename)
            s.send(tobinary(len(action)))
            s.send(action)
            for data in datas:
                s.send(tobinary(len(data)))
                s.send(data)
            s.close()
        except socket.error, e:
            s.close()
            raise BTFailure(_("Could not send command: ") + str(e))

    def close_socket(self):
        self.rawserver.stop_listening(self.controlsocket)
        self.controlsocket.close()

    def get_sic_path(self):
        directory = get_config_dir()
        configdir = os.path.join(directory, '.bittorrent')
        filename = os.path.join(configdir, ".btcontrol")
        return filename

    def create_sic_socket(self):
        obtain_mutex = 1
        mutex = win32event.CreateMutex(None, obtain_mutex, app_name)

        # prevent the PyHANDLE from going out of scope, ints are fine
        self.mutex = int(mutex)
        mutex.Detach()

        lasterror = win32api.GetLastError()
        
        if lasterror == winerror.ERROR_ALREADY_EXISTS:
            raise BTFailure(_("Global mutex already created."))

        self.master = 1

        # where is the lower limit of the window random port pool? this should stop there
        port_limit = 50000
        while self.port < port_limit:
            try:
                self.create_socket_inet(self.port)
                break
            except BTFailure:
                self.port += 1

        if self.port >= port_limit:
            raise BTFailure(_("Could not find an open port!"))

        filename = self.get_sic_path()
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
        # but don't destroy the handle until the application closes, so that the names mutex is still around
        win32event.ReleaseMutex(self.mutex)

    def discover_sic_socket(self):
        # mutex exists and has been opened (not created). wait for it so we can read the file
        r = win32event.WaitForSingleObject(self.mutex, win32event.INFINITE)

        # WAIT_OBJECT_0 means the mutex was obtained
        # WAIT_ABANDONED means the mutex was obtained, and it had previously been abandoned
        if (r != win32event.WAIT_OBJECT_0) and (r != win32event.WAIT_ABANDONED):
            BTFailure(_("Could not acquire global mutex lock for controlsocket file!"))

        filename = self.get_sic_path()
        try:
            f = open(filename, "r")
            self.port = int(f.read())
            f.close()
        except:
            self.port = CONTROL_SOCKET_PORT
            if (r != win32event.WAIT_ABANDONED):
                sys.stderr.write(_("A previous instance of BT was not cleaned up properly. Continuing."))
                # what I should really do here is assume the role of master.
        
        # we're done reading the control file, release the mutex so other instances can lock it and read the file
        win32event.ReleaseMutex(self.mutex)

    def close_sic_socket(self):
        if self.master:
            r = win32event.WaitForSingleObject(self.mutex, win32event.INFINITE)
            filename = self.get_sic_path()
            os.remove(filename)
            self.master = 0
            win32event.ReleaseMutex(self.mutex)
            # close it so the named mutex goes away
            win32api.CloseHandle(self.mutex)
            self.mutex = None

    if sys.platform.startswith('win'):
        send_command = send_command_inet
        create_socket = create_sic_socket
    else:
        send_command = send_command_unix
        create_socket = create_socket_unix
