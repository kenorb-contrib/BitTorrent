# Written by Bram Cohen
# this file is public domain

from btemplate import compile_template, ListMarker, string_template, exact_length
from bencode import bencode, bdecode
from traceback import print_exc
true = 1
false = 0

message_template = compile_template({'type': string_template})

have_files_template = compile_template({'type': 'I have', 
    'files': ListMarker(exact_length(20))})

here_is_a_slice_template = compile_template({'type': 'slice', 
    'file': exact_length(20), 'begin': 0, 'slice': string_template})

done_message = bencode({'type': 'done'})

interested_message = bencode({'type': 'interested'})

class SingleDownload:
    def __init__(self, downloader, connection):
        self.downloader = downloader
        self.connection = connection
        self.choked = false
        self.interested = false

    def got_message(self, message):
        try:
            m = bdecode(message)
            message_template(m)
            mtype = m.get('type')
            if mtype == 'slice':
                self.got_slice_message(m)
            elif mtype == "choke":
                self.got_choked_message(m)
            elif mtype == "unchoke":
                self.got_unchoked_message(m)
            elif mtype == 'I have':
                self.got_files_message(m)
        except ValueError:
            print_exc()

    def got_choked_message(self, message):
        if self.choked:
            return 
        self.choked = true
        for i in self.downloader.data.cleared(self):
            i.adjust()

    def got_unchoked_message(self, message):
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
        while true:
            if data.num_current(self) >= self.downloader.backlog:
                if self.interested:
                    self.interested = false
                    self.connection.send_message(done_message)
                return
            s = data.get_next(self)
            if s is None:
                return
            blob, begin, length, full = s
            self.connection.send_message(bencode({'type': 'send slice', 
                'file': blob, 'begin': begin, 'length': length}))
            for f in full:
                f.adjust()

    def got_slice_message(self, message):
        here_is_a_slice_template(message)
        check = self.downloader.data.came_in(self, message['blob'], 
            message['begin'], message['slice'])
        self.adjust()
        for c in check:
            c.adjust()

    def got_files_message(self, message):
        have_files_template(message)
        self.downloader.data.has_blobs(self, message['files'])
        self.adjust()

class Downloader:
    def __init__(self, data, backlog):
        self.data = data
        self.backlog = backlog
        self.downloads = {}

    def connection_made(self, connection):
        down = SingleDownload(self, connection)
        self.downloads[connection] = down
        self.data.connected(down)

    def connection_lost(self, connection):
        down = self.downloads[connection]
        del down.connection
        del down.downloader
        del self.downloads[connection]
        for i in self.data.disconnected(down):
            i.adjust()

    def got_message(self, connection, message):
        self.downloads[connection].got_message(message)

# everything below is just for testing

class DummyConnection:
    def __init__(self):
        self.messages = []

    def send_message(self, message):
        self.messages.append(message)
