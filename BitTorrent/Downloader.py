# Written by Bram Cohen
# this file is public domain

from btemplate import compile_template, ListMarker, string_template, exact_length
true = 1
false = 0

have_files_template = compile_template({'type': 'I have', 
    'blobs': ListMarker(exact_length(20))})

here_is_a_slice_template = compile_template({'type': 'slice', 
    'blob': exact_length(20), 'begin': 0, 'slice': string_template})

done_message = {'type': 'done'}

interested_message = {'type': 'interested'}

class Download:
    def __init__(self, connection, data, backlog):
        self.connection = connection
        self.data = data
        self.backlog = backlog
        self.choked = false
        self.interested = false

    def got_choke(self, message):
        if self.choked:
            return 
        self.choked = true
        for i in self.downloader.data.cleared(self):
            i.adjust()

    def got_unchoke(self, message):
        if not self.choked:
            return
        self.choked = false
        self.adjust()

    def adjust(self):
        data = self.downloader.data
        if self.choked:
            if self.interested:
                if not data.want_more(self):
                    self.interested = false
                    self.connection.send_message(done_message)
            else:
                if data.want_more(self):
                    self.interested = true
                    self.connection.send_message(interested_message)
            return
        f = {}
        while true:
            if data.num_current(self) >= self.downloader.backlog:
                if self.interested:
                    self.interested = false
                    self.connection.send_message(done_message)
                break
            s = data.get_next(self)
            if s is None:
                if self.interested:
                    self.interested = false
                    self.connection.send_message(done_message)
                break
            blob, begin, length, full = s
            self.connection.send_message({'type': 'send', 
                'blob': blob, 'begin': begin, 'length': length})
            for x in full:
                f[x] = 1
        for x in f.keys():
            if x is not self:
                x.adjust()

    def got_slice(self, message):
        here_is_a_slice_template(message)
        complete, check = self.downloader.data.came_in(self, 
            message['blob'], message['begin'], message['slice'])
        self.adjust()
        for c in check:
            c.adjust()
        if complete:
            return message['blob']
        return None

    def got_I_have(self, message):
        have_files_template(message)
        if self.downloader.data.has_blobs(self, 
                message['blobs']) and not self.interested:
            self.adjust()

    def disconnected(self):
        for i in self.data.disconnected(self):
            i.adjust()
        del self.connection
        del self.data
        del self.choked

# everything below is just for testing

class DummyConnection:
    def __init__(self):
        self.messages = []

    def send_message(self, message):
        self.messages.append(message)
