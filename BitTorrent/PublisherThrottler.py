# written by Bram Cohen
# this file is public domain

true = 1
false = 0

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

class DummyConnection:
    def __init__(self, id, t):
        self.throttled = false
        self.uploading = false
        self.id = id
        self.t = t

    def start_uploading(self):
        self.uploading = true
        self.t.upload_started(self)

    def stop_uploading(self):
        self.uploading = false
        self.t.upload_stopped(self)
        
    def is_uploading(self):
        return self.uploading

    def get_id(self):
        return self.id

    def is_throttled(self):
        return self.throttled

    def throttle(self):
        self.throttled = true
        
    def unthrottle(self):
        self.throttled = false

def test():
    t = Throttler(2)
    da = DummyConnection('a', t)
    db = DummyConnection('b', t)
    dc = DummyConnection('c', t)
    dd = DummyConnection('d', t)
    t.upload_connected(da)
    assert not da.throttled
    
    t.upload_connected(db)
    assert not da.throttled
    assert not db.throttled
    
    t.upload_connected(dc)
    assert not da.throttled
    assert not db.throttled
    assert not dc.throttled

    da.start_uploading()
    assert not da.throttled
    assert not db.throttled
    assert not dc.throttled
    
    db.start_uploading()
    assert not da.throttled
    assert not db.throttled
    assert dc.throttled
    
    db.stop_uploading()
    assert not da.throttled
    assert not db.throttled
    assert not dc.throttled
    
    dc.start_uploading()
    assert not da.throttled
    assert db.throttled
    assert not dc.throttled
    
    t.upload_connected(dd)
    assert not da.throttled
    assert db.throttled
    assert not dc.throttled
    assert dd.throttled
    
    t.upload_disconnected(dc)
    assert not da.throttled
    assert not db.throttled
    assert not dd.throttled
