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
        self.buf = ''
        self.closed = false
        self.done = false
        self.donereading = false
        self.next_func = self.read_type

    def get_ip(self):
        return self.connection.get_ip()

    def data_came_in(self, data):
        if self.done:
            return true
        self.buf += data
        while true:
            try:
                i = self.buf.index('\n')
            except ValueError:
                return true
            val = self.buf[:i]
            self.buf = self.buf[i+1:]
            self.next_func = self.next_func(val)
            if self.donereading:
                return true
            if self.next_func is None or self.closed:
                return false

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
        if self.command not in ('HEAD', 'GET'):
            return None
        self.headers = {}
        return self.read_header

    def read_header(self, data):
        data = data.strip()
        if data == '':
            self.donereading = true
            r = self.handler.getfunc(self, self.path, self.headers)
            if r is not None:
                self.answer(r)
            return None
        try:
            i = data.index(':')
        except ValueError:
            return None
        self.headers[data[:i].strip().lower()] = data[i+1:].strip()
        return self.read_header

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
            self.connection.close()
        self.done = true

class HTTPHandler:
    def __init__(self, getfunc):
        self.connections = {}
        self.getfunc = getfunc

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
            c.close()

