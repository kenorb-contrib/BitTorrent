# written by Bram Cohen
# this file is public domain

class Throttler:
    def __init__(self, max_uploads):
        self.max_uploads = max_uploads
        self.uploads = {}
    
    def rethrottle(self):
        current_uploads = len([1 for up in \
            self.uploads.values() if up.is_uploading()])
        if current_uploads < self.max_uploads:
            for u in self.uploads.values():
                if u.is_throttled():
                    u.unthrottle()
        else:
            for u in self.uploads.values():
                if not u.is_uploading():
                    u.throttle()
    
    def upload_connected(self, up):
        self.uploads[up.get_id()] = up
        self.rethrottle()

    def upload_disconnected(self, up):
        del self.uploads[up.get_id()]
        self.rethrottle()

    def upload_started(self, up):
        self.rethrottle()

    def upload_stopped(self, up):
        self.rethrottle()

    def data_sent_out(self, up, amount):
        pass
