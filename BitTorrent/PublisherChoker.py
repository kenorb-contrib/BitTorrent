# written by Bram Cohen
# this file is public domain

true = 1
false = 0

class Choker:
    def __init__(self, max_uploads):
        self.max_uploads = max_uploads
        self.uploads = {}
    
    def rechoke(self):
        current_uploads = len([1 for up in \
            self.uploads.values() if up.is_uploading()])
        if current_uploads < self.max_uploads:
            for u in self.uploads.values():
                if u.is_choked():
                    u.unchoke()
        else:
            for u in self.uploads.values():
                if not u.is_uploading():
                    u.choke()
    
    def upload_connected(self, up):
        self.uploads[up.get_id()] = up
        self.rechoke()

    def upload_disconnected(self, up):
        del self.uploads[up.get_id()]
        self.rechoke()

    def upload_started(self, up):
        self.rechoke()

    def upload_stopped(self, up):
        self.rechoke()

    def data_sent_out(self, up, amount):
        pass

    def download_connected(self, down):
        pass

    def download_disconnected(self, down):
        pass

    def download_choked(self, down):
        pass

    def download_unchoked(self, down):
        pass

    def download_possible(self, down):
        down.start_new_downloads()

    def download_hiccuped(self, down, fin):
        pass

    def data_came_in(self, down, amount, finished):
        pass

class DummyConnection:
    def __init__(self, id, t):
        self.choked = false
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

    def is_choked(self):
        return self.choked

    def choke(self):
        self.choked = true
        
    def unchoke(self):
        self.choked = false

def test():
    t = Choker(2)
    da = DummyConnection('a', t)
    db = DummyConnection('b', t)
    dc = DummyConnection('c', t)
    dd = DummyConnection('d', t)
    t.upload_connected(da)
    assert not da.choked
    
    t.upload_connected(db)
    assert not da.choked
    assert not db.choked
    
    t.upload_connected(dc)
    assert not da.choked
    assert not db.choked
    assert not dc.choked

    da.start_uploading()
    assert not da.choked
    assert not db.choked
    assert not dc.choked
    
    db.start_uploading()
    assert not da.choked
    assert not db.choked
    assert dc.choked
    
    db.stop_uploading()
    assert not da.choked
    assert not db.choked
    assert not dc.choked
    
    dc.start_uploading()
    assert not da.choked
    assert db.choked
    assert not dc.choked
    
    t.upload_connected(dd)
    assert not da.choked
    assert db.choked
    assert not dc.choked
    assert dd.choked
    
    t.upload_disconnected(dc)
    assert not da.choked
    assert not db.choked
    assert not dd.choked
