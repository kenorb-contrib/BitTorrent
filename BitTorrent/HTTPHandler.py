# Written by Bram Cohen
# see LICENSE.txt for license information

from cStringIO import StringIO
import time
true = 1
false = 0

weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

months = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

class HTTPConnection:
    def __init__(self, handler, connection):
        self.handler = handler
        self.connection = connection
        self.buf = StringIO()
        self.amount = None
        self.closed = false
        self.done = false
        self.next_func = self.read_type

    def get_ip(self):
        return self.connection.get_ip()

    def close(self):
        self.closed = true
        del self.next_func
        c = self.connection
        del self.connection
        del self.handler.connections[c]
        c.close()
        
    def data_came_in(self, data):
        while true:
            if self.closed:
                return false
            if self.amount is None:
                try:
                    i = data.index('\n')
                except ValueError:
                    self.buf.write(data)
                    return true
                self.buf.write(data[:i])
                data = data[i+1:]
                val = self.buf.getvalue()
                self.buf.reset()
                self.buf.truncate()
                x = self.next_func(val)
                if x is None:
                    return false
                self.amount, self.next_func = x
            else:
                self.buf.write(data)
                if self.buf.tell() < self.amount:
                    return true
                val = self.buf.getvalue()
                data = val[self.amount:]
                val = val[:self.amount]
                x = self.next_func(val)
                if x is None:
                    return false
                self.amount, self.next_func = x

    def read_type(self, data):
        self.header = data.strip()
        words = data.split()
        if len(words) == 3:
            self.command, self.path, garbage = words
            self.pre1 = false
        elif len(words) == 2:
            self.command, self.path = words
            self.pre1 = true
            if self.command != 'GET':
                return None
        else:
            return None
        if self.command not in ('HEAD', 'GET', 'PUT'):
            return None
        self.headers = {}
        return None, self.read_header

    def read_header(self, data):
        data = data.strip()
        if data == '':
            if self.command == 'PUT':
                try:
                    return long(self.headers.get('content-length')), self.read_data
                except ValueError:
                    return None
            else:
                self.answer(self.handler.getfunc(self, self.path, self.headers))
                return 500, self.read_bitbucket
        try:
            i = data.index(':')
        except ValueError:
            return None
        self.headers[data[:i].strip().lower()] = data[i+1:].strip()
        return None, self.read_header

    def read_data(self, data):
        self.answer(self.handler.putfunc(self, self.path, self.headers, data))
        return 500, self.read_bitbucket

    def read_bitbucket(self, data):
        return 500, self.read_bitbucket

    def answer(self, (responsecode, responsestring, headers, data)):
        year, month, day, hour, minute, second, a, b, c = time.localtime(time.time())
        print '%s - - [%02d/%3s/%04d:%02d:%02d:%02d] "%s" %i %i' % (
            self.connection.get_ip(), day, months[month], year, hour, minute, 
            second, self.header, responsecode, len(data))

        r = StringIO()
        r.write('HTTP/1.0 ' + str(responsecode) + ' ' + 
            responsestring + '\r\n')
        if not self.pre1:
            headers['Content-Length'] = len(data)
            for key, value in headers.items():
                r.write(key + ': ' + str(value) + '\r\n')
            r.write('\r\n')
        if self.command != 'HEAD':
            r.write(data)
        self.connection.write(r.getvalue())
        if self.connection.is_flushed():
            self.close()
        self.done = true

class HTTPHandler:
    def __init__(self, getfunc, putfunc):
        self.connections = {}
        self.getfunc = getfunc
        self.putfunc = putfunc

    def external_connection_made(self, connection):
        self.connections[connection] = HTTPConnection(self, connection)

    def connection_flushed(self, connection):
        c = self.connections[connection]
        if c.done:
            c.close()

    def connection_lost(self, connection):
        ec = self.connections[connection]
        ec.closed = true
        del ec.connection
        del ec.next_func
        del self.connections[connection]

    def data_came_in(self, connection, data):
        c = self.connections[connection]
        if not c.data_came_in(data) and not c.closed:
            c.connection.close()
            self.connection_lost(connection)

