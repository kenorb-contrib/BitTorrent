# Written by Bram Cohen
# see LICENSE.txt for license information

from cStringIO import StringIO
from binascii import b2a_hex
from socket import error as socketerror
from urllib import quote
from traceback import print_exc
try:
    True
except:
    True = 1
    False = 0

protocol_name = 'BitTorrent protocol'
option_pattern = chr(0)*8

def toint(s):
    return long(b2a_hex(s), 16)

def tobinary(i):
    return (chr(i >> 24) + chr((i >> 16) & 0xFF) + 
        chr((i >> 8) & 0xFF) + chr(i & 0xFF))

hexmap = '0123456789ABCDEF'
def tohex(s):
    r = []
    for c in s:
        c = ord(c)
        r.append(hexmap[(c&0xF0)/16]+hexmap[c&0x0F])
    return ''.join(r)

def make_readable(s):
    if not s:
        return ''
    x = quote(s)
    if x.find('%') >= 0:
        x = '0x '+tohex(s)
    return x
   

# header, reserved, download id, my id, [length, message]

class Connection:
    def __init__(self, Encoder, connection, id, ext_handshake=False):
        self.Encoder = Encoder
        self.connection = connection
        self.connecter = Encoder.connecter
        self.id = id
        self.readable_id = make_readable(id)
        self.locally_initiated = (id != None)
        self.complete = False
        self.closed = False
        self.buffer = StringIO()
        if self.locally_initiated or ext_handshake:
            self.connection.write(chr(len(protocol_name)) + protocol_name + 
                option_pattern + self.Encoder.download_id)
        if ext_handshake:
            self.connection.write(self.Encoder.my_id)
            self.next_len, self.next_func = 20, self.read_peer_id
        else:
            self.next_len, self.next_func = 1, self.read_header_len

    def get_ip(self, real=False):
        return self.connection.get_ip(real)

    def get_id(self):
        return self.id

    def get_readable_id(self):
        return self.readable_id

    def is_locally_initiated(self):
        return self.locally_initiated

    def is_flushed(self):
        return self.connection.is_flushed()

    def read_header_len(self, s):
        if ord(s) != len(protocol_name):
            return None
        return len(protocol_name), self.read_header

    def read_header(self, s):
        if s != protocol_name:
            return None
        return 8, self.read_reserved

    def read_reserved(self, s):
        return 20, self.read_download_id

    def read_download_id(self, s):
        if s != self.Encoder.download_id:
            return None
        if not self.locally_initiated:
            self.Encoder.connecter.external_connection_made += 1
            self.connection.write(chr(len(protocol_name)) + protocol_name + 
                option_pattern + self.Encoder.download_id + self.Encoder.my_id)
        return 20, self.read_peer_id

    def read_peer_id(self, s):
        if not self.id:
            self.id = s
            self.readable_id = make_readable(s)
        else:
            if s != self.id:
                return None
        self.complete = self.Encoder.got_id(self)
        if self.complete:
            if self.locally_initiated:
                self.connection.write(self.Encoder.my_id)
            self.Encoder.connecter.connection_made(self)
        else:
            return None
        return 4, self.read_len

    def read_len(self, s):
        l = toint(s)
        if l > self.Encoder.max_len:
            return None
        return l, self.read_message

    def read_message(self, s):
        if s != '':
            self.connecter.got_message(self, s)
        return 4, self.read_len

    def read_dead(self, s):
        return None

    def close(self):
        if not self.closed:
            self.connection.close()
            self.sever()

    def sever(self):
        self.closed = True
        del self.Encoder.connections[self.connection]
        if self.complete:
            self.connecter.connection_lost(self)

    def send_message(self, message):
        if not self.closed:
            self.connection.write(message)

    def data_came_in(self, connection, s):
        while True:
            if self.closed:
                return
            i = self.next_len - self.buffer.tell()
            if i > len(s):
                self.buffer.write(s)
                return
            self.buffer.write(s[:i])
            s = s[i:]
            m = self.buffer.getvalue()
            self.buffer.reset()
            self.buffer.truncate()
            try:
                x = self.next_func(m)
            except:
                self.next_len, self.next_func = 1, self.read_dead
                raise
            if x is None:
                self.close()
                return
            self.next_len, self.next_func = x

    def connection_flushed(self, connection):
        if self.complete:
            self.connecter.connection_flushed(self)

    def connection_lost(self, connection):
        if self.Encoder.connections.has_key(connection):
            self.sever()


class Encoder:
    def __init__(self, connecter, raw_server, my_id, max_len,
            schedulefunc, keepalive_delay, download_id, 
            config):
        self.raw_server = raw_server
        self.connecter = connecter
        self.my_id = my_id
        self.max_len = max_len
        self.schedulefunc = schedulefunc
        self.keepalive_delay = keepalive_delay
        self.download_id = download_id
        self.config = config
        self.connections = {}
        self.banned = {}
        self.to_connect = []
        if self.config['max_connections'] == 0:
            self.max_connections = 2 ** 30
        else:
            self.max_connections = self.config['max_connections']
        schedulefunc(self.send_keepalives, keepalive_delay)

    def send_keepalives(self):
        self.schedulefunc(self.send_keepalives, self.keepalive_delay)
        for c in self.connections.values():
            if c is not None and c.complete:
                c.send_message('')

    def start_connections(self, list):
        if not self.to_connect:
            self.raw_server.external_add_task(self._start_connection_from_queue)
        self.to_connect = list

    def _start_connection_from_queue(self):
        if len(self.connections) > self.max_connections:
            delay = 60
        else:
            delay = 0
            dns, id = self.to_connect.pop(0)
            self.start_connection(dns, id)
        if self.to_connect:
            self.raw_server.external_add_task(self._start_connection_from_queue, delay)

    def start_connection(self, dns, id):
        if len(self.connections) > self.max_connections:
            return True
        if self.connecter.external_connection_made:
            max_initiate = self.config['max_initiate']
        else:
            max_initiate = int(self.config['max_initiate']*1.5)
        if len(self.connections) >= max_initiate:
            return True
        if id == self.my_id:
            return True
        if self.banned.has_key(dns[0]):
            return True
        for v in self.connections.values():
            if v is None:
                continue
            if id and v.id == id:
                return True
            ip = v.get_ip(True)
            if self.config['security'] and ip != 'unknown' and ip == dns[0]:
                return True
        try:
            c = self.raw_server.start_connection(dns)
            con = Connection(self, c, id)
            self.connections[c] = con
            c.set_handler(con)
        except socketerror:
            return False
        return True

    def _start_connection(self, dns, id):
        def foo(self=self, dns=dns, id=id):
            self.start_connection(dns, id)
        
        self.schedulefunc(foo, 0)

    def got_id(self, connection):
        if connection.id == self.my_id:
            self.connecter.external_connection_made -= 1
            return False
        ip = connection.get_ip(True)
        if self.config['security'] and self.banned.has_key(ip):
            return False
        for v in self.connections.values():
            if connection is not v:
                if connection.id == v.id:
                    return False
                if self.config['security'] and ip != 'unknown' and ip == v.get_ip(True):
                    v.close()
        return True

    def external_connection_made(self, connection):
        if len(self.connections) > self.max_connections:
            connection.close()
            return False
        con = Connection(self, connection, None)
        self.connections[connection] = con
        connection.set_handler(con)
        return True

    def externally_handshaked_connection_made(self, connection, options, already_read):
        if len(self.connections) > self.max_connections:
            connection.close()
            return False
        con = Connection(self, connection, None, True)
        self.connections[connection] = con
        connection.set_handler(con)
        if already_read:
            con.data_came_in(con, already_read)
        return True

    def close_all(self):
        cons = self.connections
        self.connections = {}
        for c in cons.values():
            if not c.closed:
                c.connection.close()    # don't bother cleaning up
                c.closed = True

    def ban(self, ip):
        self.banned[ip] = 1

# everything below is for testing

class DummyConnecter:
    def __init__(self):
        self.log = []
        self.close_next = False
    
    def connection_made(self, connection):
        self.log.append(('made', connection))
        
    def connection_lost(self, connection):
        self.log.append(('lost', connection))

    def connection_flushed(self, connection):
        self.log.append(('flushed', connection))

    def got_message(self, connection, message):
        self.log.append(('got', connection, message))
        if self.close_next:
            connection.close()

class DummyRawServer:
    def __init__(self):
        self.connects = []
    
    def start_connection(self, dns):
        c = DummyRawConnection()
        self.connects.append((dns, c))
        return c

class DummyRawConnection:
    def __init__(self):
        self.closed = False
        self.data = []
        self.flushed = True

    def get_ip(self):
        return 'fake.ip'

    def is_flushed(self):
        return self.flushed

    def write(self, data):
        assert not self.closed
        self.data.append(data)
        
    def close(self):
        assert not self.closed
        self.closed = True

    def pop(self):
        r = ''.join(self.data)
        del self.data[:]
        return r

def dummyschedule(a, b):
    pass

def test_messages_in_and_out():
    c = DummyConnecter()
    rs = DummyRawServer()
    e = Encoder(c, rs, 'a' * 20, 500, dummyschedule, 30, 'd' * 20)
    c1 = DummyRawConnection()
    e.external_connection_made(c1)
    assert c1.pop() == chr(len(protocol_name)) + protocol_name + \
        chr(0) * 8 + 'd' * 20 + 'a' * 20
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed

    e.data_came_in(c1, chr(len(protocol_name)) + protocol_name + \
        chr(0) * 8 + 'd' * 20)
    assert c1.pop() == ''
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed

    e.data_came_in(c1, 'b' * 20)
    assert c1.pop() == ''
    assert len(c.log) == 1
    assert c.log[0][0] == 'made'
    ch = c.log[0][1]
    del c.log[:]
    assert rs.connects == []
    assert not c1.closed
    assert ch.get_ip() == 'fake.ip'
    
    ch.send_message('abc')
    assert c1.pop() == chr(0) * 3 + chr(3) + 'abc'
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed
    
    e.data_came_in(c1, chr(0) * 3 + chr(3) + 'def')
    assert c1.pop() == ''
    assert c.log == [('got', ch, 'def')]
    del c.log[:]
    assert rs.connects == []
    assert not c1.closed

def test_flushed():
    c = DummyConnecter()
    rs = DummyRawServer()
    e = Encoder(c, rs, 'a' * 20, 500, dummyschedule, 30, 'd' * 20)
    c1 = DummyRawConnection()
    e.external_connection_made(c1)
    assert c1.pop() == chr(len(protocol_name)) + protocol_name + \
        chr(0) * 8 + 'd' * 20 + 'a' * 20
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed

    e.data_came_in(c1, chr(len(protocol_name)) + protocol_name + \
        chr(0) * 8 + 'd' * 20)
    assert c1.pop() == ''
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed
    
    e.connection_flushed(c1)
    assert c1.pop() == ''
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed

    e.data_came_in(c1, 'b' * 20)
    assert c1.pop() == ''
    assert len(c.log) == 1
    assert c.log[0][0] == 'made'
    ch = c.log[0][1]
    del c.log[:]
    assert rs.connects == []
    assert not c1.closed
    assert ch.is_flushed()
    
    e.connection_flushed(c1)
    assert c1.pop() == ''
    assert c.log == [('flushed', ch)]
    assert rs.connects == []
    assert not c1.closed
    
    c1.flushed = False
    assert not ch.is_flushed()
    
def test_wrong_header_length():
    c = DummyConnecter()
    rs = DummyRawServer()
    e = Encoder(c, rs, 'a' * 20, 500, dummyschedule, 30, 'd' * 20)
    c1 = DummyRawConnection()
    e.external_connection_made(c1)
    assert c1.pop() == chr(len(protocol_name)) + protocol_name + \
        chr(0) * 8 + 'd' * 20 + 'a' * 20
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed

    e.data_came_in(c1, chr(5) * 30)
    assert c.log == []
    assert c1.closed

def test_wrong_header():
    c = DummyConnecter()
    rs = DummyRawServer()
    e = Encoder(c, rs, 'a' * 20, 500, dummyschedule, 30, 'd' * 20)
    c1 = DummyRawConnection()
    e.external_connection_made(c1)
    assert c1.pop() == chr(len(protocol_name)) + protocol_name + \
        chr(0) * 8 + 'd' * 20 + 'a' * 20
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed

    e.data_came_in(c1, chr(len(protocol_name)) + 'a' * len(protocol_name))
    assert c.log == []
    assert c1.closed
    
def test_wrong_download_id():
    c = DummyConnecter()
    rs = DummyRawServer()
    e = Encoder(c, rs, 'a' * 20, 500, dummyschedule, 30, 'd' * 20)
    c1 = DummyRawConnection()
    e.external_connection_made(c1)
    assert c1.pop() == chr(len(protocol_name)) + protocol_name + \
        chr(0) * 8 + 'd' * 20 + 'a' * 20
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed

    e.data_came_in(c1, chr(len(protocol_name)) + protocol_name + 
        chr(0) * 8 + 'e' * 20)
    assert c.log == []
    assert c1.closed

def test_wrong_other_id():
    c = DummyConnecter()
    rs = DummyRawServer()
    e = Encoder(c, rs, 'a' * 20, 500, dummyschedule, 30, 'd' * 20)
    e.start_connection('dns', 'o' * 20)
    assert c.log == []
    assert len(rs.connects) == 1
    assert rs.connects[0][0] == 'dns'
    c1 = rs.connects[0][1]
    del rs.connects[:]
    assert c1.pop() == chr(len(protocol_name)) + protocol_name + \
        chr(0) * 8 + 'd' * 20 + 'a' * 20
    assert not c1.closed

    e.data_came_in(c1, chr(len(protocol_name)) + protocol_name + 
        chr(0) * 8 + 'd' * 20 + 'b' * 20)
    assert c.log == []
    assert c1.closed

def test_over_max_len():
    c = DummyConnecter()
    rs = DummyRawServer()
    e = Encoder(c, rs, 'a' * 20, 500, dummyschedule, 30, 'd' * 20)
    c1 = DummyRawConnection()
    e.external_connection_made(c1)
    assert c1.pop() == chr(len(protocol_name)) + protocol_name + \
        chr(0) * 8 + 'd' * 20 + 'a' * 20
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed

    e.data_came_in(c1, chr(len(protocol_name)) + protocol_name + 
        chr(0) * 8 + 'd' * 20 + 'o' * 20)
    assert len(c.log) == 1 and c.log[0][0] == 'made'
    ch = c.log[0][1]
    del c.log[:]
    assert not c1.closed

    e.data_came_in(c1, chr(1) + chr(0) * 3)
    assert c.log == [('lost', ch)]
    assert c1.closed

def test_keepalive():
    s = []
    def sched(interval, thing, s = s):
        s.append((interval, thing))
    c = DummyConnecter()
    rs = DummyRawServer()
    e = Encoder(c, rs, 'a' * 20, 500, sched, 30, 'd' * 20)
    assert len(s) == 1
    assert s[0][1] == 30
    kfunc = s[0][0]
    del s[:]
    c1 = DummyRawConnection()
    e.external_connection_made(c1)
    assert c1.pop() == chr(len(protocol_name)) + protocol_name + \
        chr(0) * 8 + 'd' * 20 + 'a' * 20
    assert c.log == []
    assert not c1.closed

    kfunc()
    assert c1.pop() == ''
    assert c.log == []
    assert not c1.closed
    assert s == [(kfunc, 30)]
    del s[:]

    e.data_came_in(c1, chr(len(protocol_name)) + protocol_name + 
        chr(0) * 8 + 'd' * 20 + 'o' * 20)
    assert len(c.log) == 1 and c.log[0][0] == 'made'
    del c.log[:]
    assert c1.pop() == ''
    assert not c1.closed

    kfunc()
    assert c1.pop() == chr(0) * 4
    assert c.log == []
    assert not c1.closed

def test_swallow_keepalive():
    c = DummyConnecter()
    rs = DummyRawServer()
    e = Encoder(c, rs, 'a' * 20, 500, dummyschedule, 30, 'd' * 20)
    c1 = DummyRawConnection()
    e.external_connection_made(c1)
    assert c1.pop() == chr(len(protocol_name)) + protocol_name + \
        chr(0) * 8 + 'd' * 20 + 'a' * 20
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed

    e.data_came_in(c1, chr(len(protocol_name)) + protocol_name + 
        chr(0) * 8 + 'd' * 20 + 'o' * 20)
    assert len(c.log) == 1 and c.log[0][0] == 'made'
    del c.log[:]
    assert not c1.closed

    e.data_came_in(c1, chr(0) * 4)
    assert c.log == []
    assert not c1.closed

def test_local_close():
    c = DummyConnecter()
    rs = DummyRawServer()
    e = Encoder(c, rs, 'a' * 20, 500, dummyschedule, 30, 'd' * 20)
    c1 = DummyRawConnection()
    e.external_connection_made(c1)
    assert c1.pop() == chr(len(protocol_name)) + protocol_name + \
        chr(0) * 8 + 'd' * 20 + 'a' * 20
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed

    e.data_came_in(c1, chr(len(protocol_name)) + protocol_name + 
        chr(0) * 8 + 'd' * 20 + 'o' * 20)
    assert len(c.log) == 1 and c.log[0][0] == 'made'
    ch = c.log[0][1]
    del c.log[:]
    assert not c1.closed

    ch.close()
    assert c.log == [('lost', ch)]
    del c.log[:]
    assert c1.closed

def test_local_close_in_message_receive():
    c = DummyConnecter()
    rs = DummyRawServer()
    e = Encoder(c, rs, 'a' * 20, 500, dummyschedule, 30, 'd' * 20)
    c1 = DummyRawConnection()
    e.external_connection_made(c1)
    assert c1.pop() == chr(len(protocol_name)) + protocol_name + \
        chr(0) * 8 + 'd' * 20 + 'a' * 20
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed

    e.data_came_in(c1, chr(len(protocol_name)) + protocol_name + 
        chr(0) * 8 + 'd' * 20 + 'o' * 20)
    assert len(c.log) == 1 and c.log[0][0] == 'made'
    ch = c.log[0][1]
    del c.log[:]
    assert not c1.closed

    c.close_next = True
    e.data_came_in(c1, chr(0) * 3 + chr(4) + 'abcd')
    assert c.log == [('got', ch, 'abcd'), ('lost', ch)]
    assert c1.closed

def test_remote_close():
    c = DummyConnecter()
    rs = DummyRawServer()
    e = Encoder(c, rs, 'a' * 20, 500, dummyschedule, 30, 'd' * 20)
    c1 = DummyRawConnection()
    e.external_connection_made(c1)
    assert c1.pop() == chr(len(protocol_name)) + protocol_name + \
        chr(0) * 8 + 'd' * 20 + 'a' * 20
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed

    e.data_came_in(c1, chr(len(protocol_name)) + protocol_name + 
        chr(0) * 8 + 'd' * 20 + 'o' * 20)
    assert len(c.log) == 1 and c.log[0][0] == 'made'
    ch = c.log[0][1]
    del c.log[:]
    assert not c1.closed

    e.connection_lost(c1)
    assert c.log == [('lost', ch)]
    assert not c1.closed

def test_partial_data_in():
    c = DummyConnecter()
    rs = DummyRawServer()
    e = Encoder(c, rs, 'a' * 20, 500, dummyschedule, 30, 'd' * 20)
    c1 = DummyRawConnection()
    e.external_connection_made(c1)
    assert c1.pop() == chr(len(protocol_name)) + protocol_name + \
        chr(0) * 8 + 'd' * 20 + 'a' * 20
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed

    e.data_came_in(c1, chr(len(protocol_name)) + protocol_name + 
        chr(0) * 4)
    e.data_came_in(c1, chr(0) * 4 + 'd' * 20 + 'c' * 10)
    e.data_came_in(c1, 'c' * 10)
    assert len(c.log) == 1 and c.log[0][0] == 'made'
    del c.log[:]
    assert not c1.closed
    
def test_ignore_connect_of_extant():
    c = DummyConnecter()
    rs = DummyRawServer()
    e = Encoder(c, rs, 'a' * 20, 500, dummyschedule, 30, 'd' * 20)
    c1 = DummyRawConnection()
    e.external_connection_made(c1)
    assert c1.pop() == chr(len(protocol_name)) + protocol_name + \
        chr(0) * 8 + 'd' * 20 + 'a' * 20
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed

    e.data_came_in(c1, chr(len(protocol_name)) + protocol_name + 
        chr(0) * 8 + 'd' * 20 + 'o' * 20)
    assert len(c.log) == 1 and c.log[0][0] == 'made'
    del c.log[:]
    assert not c1.closed

    e.start_connection('dns', 'o' * 20)
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed

def test_ignore_connect_to_self():
    c = DummyConnecter()
    rs = DummyRawServer()
    e = Encoder(c, rs, 'a' * 20, 500, dummyschedule, 30, 'd' * 20)
    c1 = DummyRawConnection()

    e.start_connection('dns', 'a' * 20)
    assert c.log == []
    assert rs.connects == []
    assert not c1.closed

def test_conversion():
    assert toint(tobinary(50000)) == 50000

