# Written by Bram Cohen
# this file is public domain

from sha import sha
from cStringIO import StringIO
from binaryint import int_to_binary, binary_to_int
from StreamEncrypter import make_encrypter
import socket
true = 1
false = 0

protocol_name = 'BitTorrent by Bram Cohen protocol version 1.0'

# see http://www.ietf.org/internet-drafts/draft-ietf-ipsec-ike-modp-groups-01.txt
p = long('FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1' +
'29024E088A67CC74020BBEA63B139B22514A08798E3404DD' +
'EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245' +
'E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED' +
'EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D' +
'C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F' +
'83655D23DCA3AD961C62F356208552BB9ED529077096966D' +
'670C354E4ABC9804F1746C08CA237327FFFFFFFFFFFFFFFF', 16)

class EncryptedConnection:
    def __init__(self, encrypter, connection, dns):
        self.encrypter = encrypter
        self.connection = connection
        self.dns = dns
        self.complete = false
        self.nonce = encrypter.noncefunc()
        self.buffer = StringIO()
        self.closed = false
        self.next_len = 1
        self.next_func = self.read_header_len
        connection.write(chr(len(protocol_name)) + protocol_name + 
            (chr(0) * 8) + encrypter.public_key + self.nonce)

    def get_ip(self):
        return self.connection.get_ip()

    def read_header_len(self, s):
        if ord(s) != len(protocol_name):
            return None, None
        return len(protocol_name), self.read_header

    def read_header(self, s):
        if s != protocol_name:
            return None, None
        return 8, self.read_reserved

    def read_reserved(self, s):
        return 212, self.read_crypto

    def read_crypto(self, s):
        otherpk = binary_to_int(s[:192])
        if otherpk >= p - 1 or otherpk <= 1:
            return None, None
        if s[:192] == self.encrypter.public_key:
            return None, None
        self.id = sha(s[:192]).digest()
        shared_key = int_to_binary(pow(otherpk, self.encrypter.private_key, p), 192)
        othernonce = s[192:]
        if othernonce == self.nonce:
            return None, None
        self.encrypt = make_encrypter(sha(self.nonce + othernonce + shared_key).digest()[:16])
        self.decrypt = make_encrypter(sha(othernonce + self.nonce + shared_key).digest()[:16])
        self.connection.write(self.encrypt(chr(0) * 16))
        return 16, self.read_auth

    def read_auth(self, s):
        if self.decrypt(s) != chr(0) * 16:
            return None, None
        self.complete = true
        if self.dns is not None:
            self.encrypter.connecter.locally_initiated_connection_completed(self)
        return 4, self.read_len

    def read_len(self, s):
        l = binary_to_int(self.decrypt(s))
        if l > self.encrypter.max_len:
            return None, None
        return l, self.read_message

    def read_message(self, s):
        m = self.decrypt(s)
        self.encrypter.connecter.got_message(self, m)
        return 4, self.read_len

    def close(self):
        self.closed = true
        del self.next_func
        c = self.connection
        del self.connection
        del self.encrypter.connections[c]
        c.close()
        
    def get_id(self):
        assert self.complete
        return self.id
        
    def get_dns(self):
        return self.dns
        
    def is_locally_initiated(self):
        return self.dns != None

    def send_message(self, message):
        self.connection.write(self.encrypt(int_to_binary(len(message), 4)))
        self.connection.write(self.encrypt(message))
        
    def data_came_in(self, s):
        i = self.next_len - self.buffer.tell()
        if i > len(s):
            self.buffer.write(s)
            return 1
        self.buffer.write(s[:i])
        self.next_len, self.next_func = self.next_func(self.buffer.getvalue())
        if self.next_func is None or self.closed:
            return 0
        while self.next_len + i <= len(s):
            n = i + self.next_len
            self.next_len, self.next_func = self.next_func(s[i:n])
            if self.next_func is None or self.closed:
                return 0
            i = n
        self.buffer.reset()
        self.buffer.truncate()
        self.buffer.write(s[i:])
        return 1

class Encrypter:
    def __init__(self, connecter, noncefunc, private_key, max_len):
        self.connecter = connecter
        self.noncefunc = noncefunc
        self.max_len = max_len
        self.connections = {}
        assert len(private_key) == 20
        self.private_key = binary_to_int(private_key)
        self.public_key = int_to_binary(pow(2, self.private_key, p), 192)

    def get_id(self):
        return sha(self.public_key).digest()

    def set_raw_server(self, raw_server):
        self.raw_server = raw_server
    
    def start_connection(self, dns):
        try:
            c = self.raw_server.start_connection(dns)
            self.connections[c] = EncryptedConnection(self, c, dns)
        except socket.error:
            pass
        
    def external_connection_made(self, connection):
        assert not self.connections.has_key(connection)
        self.connections[connection] = EncryptedConnection(self, connection, None)
        
    def connection_lost(self, connection):
        ec = self.connections[connection]
        ec.closed = true
        del ec.connection
        del ec.next_func
        del self.connections[connection]
        if ec.complete:
            self.connecter.connection_lost(ec)
        
    def data_came_in(self, connection, data):
        c = self.connections[connection]
        if not c.data_came_in(data) and not c.closed:
            c.connection.close()
            self.connection_lost(connection)

# everything below is for testing

class DummyConnecter:
    def __init__(self):
        self.c_made = []
        self.c_lost = []
        self.m_rec = []
        self.close_next = false
    
    def locally_initiated_connection_completed(self, connection):
        self.c_made.append(connection)
        
    def connection_lost(self, connection):
        self.c_lost.append(connection)
        
    def got_message(self, connection, message):
        self.m_rec.append((connection, message))
        if self.close_next:
            connection.close()

class DummyRawServer:
    def __init__(self):
        self.connects = []
    
    def start_connection(self, dns):
        c = DummyRawConnection()
        self.connects.append((dns[0], dns[1], c))
        return c

class DummyRawConnection:
    def __init__(self):
        self.closed = false
        self.data = []

    def get_ip(self):
        return 'fake.ip'

    def write(self, data):
        assert not self.closed
        self.data.append(data)
        
    def close(self):
        assert not self.closed
        self.closed = true

def flush(c1, e1, c2, e2):
    while len(c1.data) > 0 or len(c2.data) > 0:
        s1 = ''.join(c1.data)
        del c1.data[:]
        e2.data_came_in(c2, s1)
        s2 = ''.join(c2.data)
        del c2.data[:]
        e1.data_came_in(c1, s2)

def flush2(c1, e1, c2, e2):
    while len(c1.data) > 0 or len(c2.data) > 0:
        s1 = ''.join(c1.data)
        del c1.data[:]
        i = 0
        while i <= len(s1):
            e2.data_came_in(c2, s1[i:i+5])
            i += 5
        s2 = ''.join(c2.data)
        del c2.data[:]
        i = 0
        while i <= len(s1):
            e1.data_came_in(c1, s2[i:i+5])
            i += 5

def test_proper_communication_initiating_side_close():
    dc1 = DummyConnecter()
    e1 = Encrypter(dc1, lambda: 'a' * 20, 'b' * 20, 500)
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    rs1 = DummyRawServer()
    e1.set_raw_server(rs1)
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    dc2 = DummyConnecter()
    e2 = Encrypter(dc2, lambda: 'c' * 20, 'd' * 20, 500)
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    rs2 = DummyRawServer()
    e2.set_raw_server(rs2)
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    e1.start_connection(('spam.com', 69))
    assert len(rs1.connects) == 1 and rs1.connects[0][0] == 'spam.com' and rs1.connects[0][1] == 69
    c1 = rs1.connects[0][2]
    del rs1.connects[:]
    assert not c1.closed
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    c2 = DummyRawConnection()
    e2.external_connection_made(c2)
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert len(dc1.c_made) == 1
    ec1 = dc1.c_made[0]
    del dc1.c_made[:]
    assert ec1.get_id() == e2.get_id()
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    ec1.send_message('message 0')
    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert len(dc2.m_rec) == 1 and dc2.m_rec[0][1] == 'message 0'
    ec2 = dc2.m_rec[0][0]
    assert ec2.get_id() == e1.get_id()
    del dc2.m_rec[:]

    ec1.send_message('message 1')
    ec1.send_message('message 2')
    ec2.send_message('message 3')
    ec2.send_message('message 4')
    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == [(ec1, 'message 3'), (ec1, 'message 4')]
    del dc1.m_rec[:]
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == [(ec2, 'message 1'), (ec2, 'message 2')]
    del dc2.m_rec[:]
        
    ec1.close()
    assert c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    e2.connection_lost(c2)
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == [ec2]
    del dc2.c_lost[:]
    assert dc2.m_rec == []

def test_reconstruction():
    dc1 = DummyConnecter()
    e1 = Encrypter(dc1, lambda: 'a' * 20, 'b' * 20, 500)
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    rs1 = DummyRawServer()
    e1.set_raw_server(rs1)
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    dc2 = DummyConnecter()
    e2 = Encrypter(dc2, lambda: 'c' * 20, 'd' * 20, 500)
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    rs2 = DummyRawServer()
    e2.set_raw_server(rs2)
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    e1.start_connection(('spam.com', 69))
    assert len(rs1.connects) == 1 and rs1.connects[0][0] == 'spam.com' and rs1.connects[0][1] == 69
    c1 = rs1.connects[0][2]
    del rs1.connects[:]
    assert not c1.closed
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    c2 = DummyRawConnection()
    e2.external_connection_made(c2)
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert len(dc1.c_made) == 1
    ec1 = dc1.c_made[0]
    del dc1.c_made[:]
    assert ec1.get_id() == e2.get_id()
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    ec1.send_message('message 0')
    flush2(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert len(dc2.m_rec) == 1 and dc2.m_rec[0][1] == 'message 0'
    ec2 = dc2.m_rec[0][0]
    assert ec2.get_id() == e1.get_id()
    del dc2.m_rec[:]

    ec1.send_message('message 1')
    ec1.send_message('message 2')
    ec2.send_message('message 3')
    ec2.send_message('message 4')
    flush2(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == [(ec1, 'message 3'), (ec1, 'message 4')]
    del dc1.m_rec[:]
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == [(ec2, 'message 1'), (ec2, 'message 2')]
    del dc2.m_rec[:]
        
    ec1.close()
    assert c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    e2.connection_lost(c2)
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == [ec2]
    del dc2.c_lost[:]
    assert dc2.m_rec == []

def test_proper_communication_receiving_side_close():
    dc1 = DummyConnecter()
    e1 = Encrypter(dc1, lambda: 'a' * 20, 'b' * 20, 500)
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    rs1 = DummyRawServer()
    e1.set_raw_server(rs1)
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    dc2 = DummyConnecter()
    e2 = Encrypter(dc2, lambda: 'c' * 20, 'd' * 20, 500)
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    rs2 = DummyRawServer()
    e2.set_raw_server(rs2)
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    e1.start_connection(('spam.com', 69))
    assert len(rs1.connects) == 1 and rs1.connects[0][0] == 'spam.com' and rs1.connects[0][1] == 69
    c1 = rs1.connects[0][2]
    del rs1.connects[:]
    assert not c1.closed
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    c2 = DummyRawConnection()
    e2.external_connection_made(c2)
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert len(dc1.c_made) == 1
    ec1 = dc1.c_made[0]
    del dc1.c_made[:]
    assert ec1.get_id() == e2.get_id()
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    ec1.send_message('message 0')
    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert len(dc2.m_rec) == 1 and dc2.m_rec[0][1] == 'message 0'
    ec2 = dc2.m_rec[0][0]
    assert ec2.get_id() == e1.get_id()
    del dc2.m_rec[:]

    ec1.send_message('message 1')
    ec1.send_message('message 2')
    ec2.send_message('message 3')
    ec2.send_message('message 4')
    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == [(ec1, 'message 3'), (ec1, 'message 4')]
    del dc1.m_rec[:]
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == [(ec2, 'message 1'), (ec2, 'message 2')]
    del dc2.m_rec[:]
        
    ec2.close()
    assert c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    e1.connection_lost(c1)
    assert not c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == [ec1]
    del dc1.c_lost[:]
    assert dc1.m_rec == []

def test_garbage_data_before_completion():
    dc1 = DummyConnecter()
    e1 = Encrypter(dc1, lambda: 'a' * 20, 'b' * 20, 500)
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    rs1 = DummyRawServer()
    e1.set_raw_server(rs1)
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    c1 = DummyRawConnection()
    e1.external_connection_made(c1)
    e1.data_came_in(c1, chr(2))

    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert c1.closed

def test_rejected_data_after_completion():
    dc1 = DummyConnecter()
    e1 = Encrypter(dc1, lambda: 'a' * 20, 'b' * 20, 5)
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    rs1 = DummyRawServer()
    e1.set_raw_server(rs1)
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    dc2 = DummyConnecter()
    e2 = Encrypter(dc2, lambda: 'c' * 20, 'd' * 20, 5)
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    rs2 = DummyRawServer()
    e2.set_raw_server(rs2)
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    e1.start_connection(('spam.com', 69))
    assert len(rs1.connects) == 1 and rs1.connects[0][0] == 'spam.com' and rs1.connects[0][1] == 69
    c1 = rs1.connects[0][2]
    del rs1.connects[:]
    assert not c1.closed
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    c2 = DummyRawConnection()
    e2.external_connection_made(c2)
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert len(dc1.c_made) == 1
    ec1 = dc1.c_made[0]
    del dc1.c_made[:]
    assert ec1.get_id() == e2.get_id()
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    ec1.send_message('m0')
    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert len(dc2.m_rec) == 1 and dc2.m_rec[0][1] == 'm0'
    ec2 = dc2.m_rec[0][0]
    assert ec2.get_id() == e1.get_id()
    del dc2.m_rec[:]

    ec1.send_message('message 1')
    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == [ec2]
    del dc2.c_lost[:]
    assert dc2.m_rec == []

def test_local_close_in_data_received():
    dc1 = DummyConnecter()
    e1 = Encrypter(dc1, lambda: 'a' * 20, 'b' * 20, 5)
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    rs1 = DummyRawServer()
    e1.set_raw_server(rs1)
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    dc2 = DummyConnecter()
    e2 = Encrypter(dc2, lambda: 'c' * 20, 'd' * 20, 5)
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    rs2 = DummyRawServer()
    e2.set_raw_server(rs2)
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    e1.start_connection(('spam.com', 69))
    assert len(rs1.connects) == 1 and rs1.connects[0][0] == 'spam.com' and rs1.connects[0][1] == 69
    c1 = rs1.connects[0][2]
    del rs1.connects[:]
    assert not c1.closed
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    c2 = DummyRawConnection()
    e2.external_connection_made(c2)
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert len(dc1.c_made) == 1
    ec1 = dc1.c_made[0]
    del dc1.c_made[:]
    assert ec1.get_id() == e2.get_id()
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    ec1.send_message('m0')
    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert len(dc2.m_rec) == 1 and dc2.m_rec[0][1] == 'm0'
    ec2 = dc2.m_rec[0][0]
    assert ec2.get_id() == e1.get_id()
    del dc2.m_rec[:]

    dc2.close_next = true
    ec1.send_message('m1')
    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == [(ec2, 'm1')]
    del dc2.m_rec[:]

def test_local_close_and_extra_data():
    dc1 = DummyConnecter()
    e1 = Encrypter(dc1, lambda: 'a' * 20, 'b' * 20, 5)
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    rs1 = DummyRawServer()
    e1.set_raw_server(rs1)
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    dc2 = DummyConnecter()
    e2 = Encrypter(dc2, lambda: 'c' * 20, 'd' * 20, 5)
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    rs2 = DummyRawServer()
    e2.set_raw_server(rs2)
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    e1.start_connection(('spam.com', 69))
    assert len(rs1.connects) == 1 and rs1.connects[0][0] == 'spam.com' and rs1.connects[0][1] == 69
    c1 = rs1.connects[0][2]
    del rs1.connects[:]
    assert not c1.closed
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    c2 = DummyRawConnection()
    e2.external_connection_made(c2)
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert len(dc1.c_made) == 1
    ec1 = dc1.c_made[0]
    del dc1.c_made[:]
    assert ec1.get_id() == e2.get_id()
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    ec1.send_message('m0')
    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert len(dc2.m_rec) == 1 and dc2.m_rec[0][1] == 'm0'
    ec2 = dc2.m_rec[0][0]
    assert ec2.get_id() == e1.get_id()
    del dc2.m_rec[:]

    dc2.close_next = true
    ec1.send_message('m1')
    ec1.send_message('m2')
    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == [(ec2, 'm1')]
    del dc2.m_rec[:]

def test_local_close_and_rejected_data():
    dc1 = DummyConnecter()
    e1 = Encrypter(dc1, lambda: 'a' * 20, 'b' * 20, 5)
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    rs1 = DummyRawServer()
    e1.set_raw_server(rs1)
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    dc2 = DummyConnecter()
    e2 = Encrypter(dc2, lambda: 'c' * 20, 'd' * 20, 5)
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    rs2 = DummyRawServer()
    e2.set_raw_server(rs2)
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    e1.start_connection(('spam.com', 69))
    assert len(rs1.connects) == 1 and rs1.connects[0][0] == 'spam.com' and rs1.connects[0][1] == 69
    c1 = rs1.connects[0][2]
    del rs1.connects[:]
    assert not c1.closed
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []

    c2 = DummyRawConnection()
    e2.external_connection_made(c2)
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert len(dc1.c_made) == 1
    ec1 = dc1.c_made[0]
    del dc1.c_made[:]
    assert ec1.get_id() == e2.get_id()
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == []

    ec1.send_message('m0')
    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert not c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert len(dc2.m_rec) == 1 and dc2.m_rec[0][1] == 'm0'
    ec2 = dc2.m_rec[0][0]
    assert ec2.get_id() == e1.get_id()
    del dc2.m_rec[:]

    dc2.close_next = true
    ec1.send_message('m1')
    ec1.send_message('message 2')
    flush(c1, e1, c2, e2)
    assert not c1.closed
    assert rs1.connects == []
    assert dc1.c_made == []
    assert dc1.c_lost == []
    assert dc1.m_rec == []
    assert c2.closed
    assert rs2.connects == []
    assert dc2.c_made == []
    assert dc2.c_lost == []
    assert dc2.m_rec == [(ec2, 'm1')]
    del dc2.m_rec[:]



