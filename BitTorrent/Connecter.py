# written by Bram Cohen
# this file is public domain

from bencode import bencode, bdecode
from btemplate import compile_template
true = 1
false = 0

message_template = compile_template({'type': ['choke', 'unchoke',
    'slice', 'I have', 'send', 'interested', 'done']})

class Connection:
    def __init__(self, connection):
        self.connection = connection

    def is_locally_initiated(self):
        return self.connection.is_locally_initiated()

    def get_ip(self):
        return self.connection.get_ip()

    def is_flushed(self):
        return self.connection.is_flushed()

    def send_message(self, message):
        self.connection.send_message(bencode(message))

    def get_upload(self):
        return self.upload

    def get_download(self):
        return self.download

class Connecter:
    def __init__(self, make_upload, make_download, choker):
        self.make_download = make_download
        self.make_upload = make_upload
        self.choker = choker
        self.connections = {}

    def locally_initiated_connection_completed(self, connection):
        for c in self.connections.keys():
            if c.get_id() == connection.get_id():
                connection.close()
                return
        connection.send_message('transfer')
        self._make_connection(connection)

    def _make_connection(self, connection):
        c = Connection(self)
        upload = self.make_upload(c)
        download = self.make_download(c)
        c.upload = upload
        c.download = download
        self.connections[connection] = c
        self.choker.connection_made(c)

    def connection_lost(self, connection):
        c = self.connections[connection]
        del self.connections[connection]
        c.upload.disconnected()
        c.download.disconnected()
        del c.connection
        self.choker.connection_lost(c)

    def connection_flushed(self, connection):
        self.connections[connection].upload.flushed()

    def got_message(self, connection, message):
        if not self.connections.has_key(connection):
            if message != 'transfer':
                connection.close()
                return
            self._make_connection(connection)
        c = self.connections[connection]
        try:
            m = bdecode(message)
            message_template(m)
            mtype = m['type']
            if mtype == 'send':
                c.upload.got_send(m)
            elif mtype == 'interested':
                c.upload.got_interested(m)
            elif mtype == 'done':
                c.upload.got_done(m)
            elif mtype == 'choke':
                c.download.got_choke(m)
            elif mtype == 'unchoke':
                c.download.got_unchoke(m)
            elif mtype == 'I have':
                c.download.got_I_have(m)
            else:
                blob = c.download.got_slice(m)
                if blob is not None:
                    for c in self.connections.values():
                        c.received_blob(blob)
        except ValueError:
            print_exc()

"""

def test_connect_and_disconnect():
    connect something
    send a message
    call get_ip(), get_upload(), get_download(), is_local, send_message()
    call disconnect

def test_flunk_not_transfer():
    connect something
    send first message other than transfer()
    assert disconnected

def test_remote_disconnect():
    connect something
    remote disconnect, check reports up

def test_flushed():
    connect something
    check is_flushed true and false
    assert flush callback bubbles up

def test_bifurcation():
    connect something
    send each type of message
    do a got_slice with blob return

def test_close_duplicate():
    connect two with same id, assert second closed
"""
