# written by Bram Cohen
# this file is public domain

true = 1
false = 0

class Throttler:
    def __init__(self, throttle_diff, unthrottle_diff, max_uploads, max_downloads):
        assert throttle_diff > 0 and unthrottle_diff > 0
        assert unthrottle_diff > throttle_diff
        self.throttle_diff = throttle_diff
        self.unthrottle_diff = unthrottle_diff
        self.max_uploads = max_uploads
        self.max_downloads = max_downloads
        # {id: balance}
        self.balances = {}
        # {id: download}
        self.downloads = {}
        # {id: upload}
        self.uploads = {}

    def rethrottle(self):
        current_uploads = len([1 for up in \
            self.uploads.values() if up.is_uploading()])
        if current_uploads < self.max_uploads:
            for u in self.uploads.values():
                u.unthrottle()
            return
        if current_uploads > self.max_uploads:
            bs = [(self.balances[uid], up) for uid, up in \
                self.uploads.items() if up.is_uploading()]
            bs.sort()
            for balance, up in bs[self.max_uploads:]:
                up.throttle()
        highest_balance = max([self.balances[uid] for uid, up in \
            self.uploads.items() if up.is_uploading()])
        ucutoff = highest_balance - self.unthrottle_diff
        cutoff = highest_balance - self.throttle_diff
        for u, upload in self.uploads.items():
            if upload.is_uploading():
                continue
            if upload.is_throttled():
                if self.balances[u] < ucutoff:
                    upload.unthrottle()
            else:
                if self.balances[u] > cutoff:
                    upload.throttle()

    def upload_connected(self, up):
        self.balances.setdefault(up.get_id(), 0)
        self.uploads[up.get_id()] = up
        self.rethrottle()

    def upload_disconnected(self, up):
        del self.uploads[up.get_id()]
        self.rethrottle()

    def upload_started(self, up):
        self.rethrottle()

    def upload_stopped(self, up):
        self.rethrottle()

    def download_more(self):
        num = len([1 for d in self.downloads.values() if d.is_downloading()])
        if num >= self.max_downloads:
            return
        bs = [(self.balances[did], d) for did, d in self.downloads.items() if not d.is_downloading()]
        bs.sort()
        bs.reverse()
        for balance, d in bs:
            if d.start_downloading():
                num += 1
                if num >= self.max_downloads:
                    return

    def download_connected(self, down):
        self.balances.setdefault(down.get_id(), 0)
        self.downloads[down.get_id()] = down
        self.download_more()

    def download_disconnected(self, down):
        del self.downloads[down.get_id()]
        self.download_more()

    def download_throttled(self, down):
        self.download_more()

    def download_unthrottled(self, down):
        self.download_more()

    def download_possible(self, down):
        if not down.is_throttled() and not down.is_downloading():
            self.download_more()

    def download_hiccuped(self, down, exhausted):
        self.download_more()

    def data_came_in(self, down, amount, exhausted):
        self.balances[down.get_id()] -= amount
        self.rethrottle()
        if exhausted:
            self.download_more()

    def data_sent_out(self, up, amount):
        self.balances[up.get_id()] += amount
        self.rethrottle()

    def get_balances(self):
        return self.balances

# everything below is for testing

class DummyUpload:
    def __init__(self, myid, throttler):
        self.id = myid
        self.throttled = false
        self.uploading = false
        self.disconnected = false
        self.throttler = throttler

    def spontaneous_disconnect(self):
        assert not self.disconnected
        self.disconnected = true
        self.throttler.upload_disconnected(self)

    def spontaneous_upload(self):
        assert not self.disconnected
        assert not self.throttled
        assert not self.uploading
        self.uploading = true
        self.throttler.upload_started(self)

    def spontaneous_sent_out(self, amount):
        assert not self.disconnected
        assert self.uploading
        self.throttler.data_sent_out(self, amount)

    def get_id(self):
        return self.id
        
    def disconnect(self):
        assert not self.disconnected
        self.disconnected = true
        
    def throttle(self):
        assert not self.disconnected
        self.throttled = true
        self.uploading = false
    
    def unthrottle(self):
        assert not self.disconnected
        self.throttled = false
    
    def is_connected(self):
        return not self.disconnected
    
    def is_throttled(self):
        assert not self.disconnected
        return self.throttled
        
    def is_uploading(self):
        assert not self.disconnected
        return self.uploading

class DummyDownload:
    def __init__(self, myid, throttler, can_download = true):
        self.id = myid
        self.throttled = false
        self.downloading = false
        self.disconnected = false
        self.throttler = throttler
        self.can_download = can_download

    def spontaneous_disconnect(self):
        assert not self.disconnected
        self.disconnected = true
        self.throttler.download_disconnected(self)

    def spontaneous_possible(self):
        assert not self.disconnected
        self.can_download = true
        self.throttler.download_possible(self)

    def spontaneous_exhausted(self):
        assert not self.disconnected
        assert self.downloading
        self.downloading = false
        self.can_download = false
        self.throttler.download_hiccuped(self, true)

    def spontaneous_throttled(self):
        assert not self.disconnected
        assert not self.throttled
        self.throttled = true
        self.downloading = false
        self.throttler.download_throttled(self)
        
    def spontaneous_unthrottled(self):
        assert not self.disconnected
        assert self.throttled
        self.throttled = false
        self.throttler.download_unthrottled(self)

    def spontaneous_came_in(self, amount):
        assert not self.disconnected
        assert self.downloading
        self.throttler.data_came_in(self, amount, false)

    def get_id(self):
        return self.id
        
    def disconnect(self):
        assert not self.disconnected
        self.disconnected = true

    def is_connected(self):
        return not self.disconnected

    def is_throttled(self):
        assert not self.disconnected
        return self.throttled
        
    def is_downloading(self):
        assert not self.disconnected
        return self.downloading

    def start_downloading(self):
        assert not self.disconnected
        if self.throttled or not self.can_download:
            return false
        self.downloading = true
        return true

def test_upload():
    t = Throttler(1000, 2000, 2, 10)
    du1 = DummyUpload('a' * 20, t)
    du2 = DummyUpload('b' * 20, t)
    du3 = DummyUpload('c' * 20, t)
    t.upload_connected(du1)
    t.upload_connected(du2)
    t.upload_connected(du3)
    # 0 0 0 0 0
    assert du1.is_connected()
    assert not du1.is_throttled()
    assert not du1.is_uploading()
    assert du2.is_connected()
    assert not du2.is_throttled()
    assert not du2.is_uploading()
    assert du3.is_connected()
    assert not du3.is_throttled()
    assert not du3.is_uploading()

    du1.spontaneous_upload()
    # 0 0 0 0 0
    assert du1.is_connected()
    assert not du1.is_throttled()
    assert du1.is_uploading()
    assert du2.is_connected()
    assert not du2.is_throttled()
    assert not du2.is_uploading()
    assert du3.is_connected()
    assert not du3.is_throttled()
    assert not du3.is_uploading()

    du2.spontaneous_upload()
    # 0 0 0 0 0
    assert du1.is_connected()
    assert not du1.is_throttled()
    assert du1.is_uploading()
    assert du2.is_connected()
    assert not du2.is_throttled()
    assert du2.is_uploading()
    assert du3.is_connected()
    assert du3.is_throttled()
    assert not du3.is_uploading()

    du4 = DummyUpload('d' * 20, t)
    t.upload_connected(du4)
    # 0 0 0 0 0
    assert du1.is_connected()
    assert not du1.is_throttled()
    assert du1.is_uploading()
    assert du2.is_connected()
    assert not du2.is_throttled()
    assert du2.is_uploading()
    assert du3.is_connected()
    assert du3.is_throttled()
    assert not du3.is_uploading()
    assert du4.is_connected()
    assert du4.is_throttled()
    assert not du4.is_uploading()
    
    dd3 = DummyDownload('c' * 20, t)
    t.download_connected(dd3)
    dd3.spontaneous_came_in(2500)
    # 0 0 -2500 0 0
    assert du1.is_connected()
    assert not du1.is_throttled()
    assert du1.is_uploading()
    assert du2.is_connected()
    assert not du2.is_throttled()
    assert du2.is_uploading()
    assert du3.is_connected()
    assert not du3.is_throttled()
    assert not du3.is_uploading()
    assert du4.is_connected()
    assert du4.is_throttled()
    assert not du4.is_uploading()

    dd2 = DummyDownload('b' * 20, t)
    t.download_connected(dd2)
    dd2.spontaneous_came_in(1000)
    dd1 = DummyDownload('a' * 20, t)
    t.download_connected(dd1)
    dd1.spontaneous_came_in(1000)
    # -1000 -1000 -2500 0 0
    assert du1.is_connected()
    assert not du1.is_throttled()
    assert du1.is_uploading()
    assert du2.is_connected()
    assert not du2.is_throttled()
    assert du2.is_uploading()
    assert du3.is_connected()
    assert not du3.is_throttled()
    assert not du3.is_uploading()
    assert du4.is_connected()
    assert du4.is_throttled()
    assert not du4.is_uploading()

    dd2.spontaneous_came_in(900)
    # -1000 -1900 -2500 0 0
    assert du1.is_connected()
    assert not du1.is_throttled()
    assert du1.is_uploading()
    assert du2.is_connected()
    assert not du2.is_throttled()
    assert du2.is_uploading()
    assert du3.is_connected()
    assert not du3.is_throttled()
    assert not du3.is_uploading()
    assert du4.is_connected()
    assert du4.is_throttled()
    assert not du4.is_uploading()

    dd1.spontaneous_came_in(900)
    # -1900 -1900 -2500 0 0
    assert du1.is_connected()
    assert not du1.is_throttled()
    assert du1.is_uploading()
    assert du2.is_connected()
    assert not du2.is_throttled()
    assert du2.is_uploading()
    assert du3.is_connected()
    assert du3.is_throttled()
    assert not du3.is_uploading()
    assert du4.is_connected()
    assert du4.is_throttled()
    assert not du4.is_uploading()

    du1.spontaneous_sent_out(900)
    du2.spontaneous_sent_out(900)
    # -1000 -1000 -2500 0 0
    assert du1.is_connected()
    assert not du1.is_throttled()
    assert du1.is_uploading()
    assert du2.is_connected()
    assert not du2.is_throttled()
    assert du2.is_uploading()
    assert du3.is_connected()
    assert du3.is_throttled()
    assert not du3.is_uploading()
    assert du4.is_connected()
    assert du4.is_throttled()
    assert not du4.is_uploading()

    du1.spontaneous_sent_out(1000)
    # 0 -1000 -2500 0 0
    assert du1.is_connected()
    assert not du1.is_throttled()
    assert du1.is_uploading()
    assert du2.is_connected()
    assert not du2.is_throttled()
    assert du2.is_uploading()
    assert du3.is_connected()
    assert not du3.is_throttled()
    assert not du3.is_uploading()
    assert du4.is_connected()
    assert du4.is_throttled()
    assert not du4.is_uploading()

    du2.spontaneous_sent_out(1000)
    # 0 0 -2500 0 0
    assert du1.is_connected()
    assert not du1.is_throttled()
    assert du1.is_uploading()
    assert du2.is_connected()
    assert not du2.is_throttled()
    assert du2.is_uploading()
    assert du3.is_connected()
    assert not du3.is_throttled()
    assert not du3.is_uploading()
    assert du4.is_connected()
    assert du4.is_throttled()
    assert not du4.is_uploading()
    
    du5 = DummyUpload('e' * 20, t)
    t.upload_connected(du5)
    dd5 = DummyDownload('e' * 20, t)
    t.download_connected(dd5)
    dd5.spontaneous_came_in(2500)
    # 0 0 -2500 0 -2500
    assert du1.is_connected()
    assert not du1.is_throttled()
    assert du1.is_uploading()
    assert du2.is_connected()
    assert not du2.is_throttled()
    assert du2.is_uploading()
    assert du3.is_connected()
    assert not du3.is_throttled()
    assert not du3.is_uploading()
    assert du4.is_connected()
    assert du4.is_throttled()
    assert not du4.is_uploading()
    assert du5.is_connected()
    assert not du5.is_throttled()
    assert not du5.is_uploading()
    
def test_upload2():
    t = Throttler(1000, 2000, 1, 1)
    du1 = DummyUpload('a' * 20, t)
    t.upload_connected(du1)
    du1.spontaneous_upload()
    assert du1.is_connected()
    assert not du1.is_throttled()
    assert du1.is_uploading()
    
    du2 = DummyUpload('b' * 20, t)
    t.upload_connected(du2)
    assert du1.is_connected()
    assert not du1.is_throttled()
    assert du1.is_uploading()
    assert du2.is_connected()
    assert du2.is_throttled()
    assert not du2.is_uploading()
    
    du1.spontaneous_sent_out(1500)
    assert du1.is_connected()
    assert not du1.is_throttled()
    assert du1.is_uploading()
    assert du2.is_connected()
    assert du2.is_throttled()
    assert not du2.is_uploading()
    
    du3 = DummyUpload('c' * 20, t)
    t.upload_connected(du3)
    assert du1.is_connected()
    assert not du1.is_throttled()
    assert du1.is_uploading()
    assert du2.is_connected()
    assert du2.is_throttled()
    assert not du2.is_uploading()
    assert du3.is_connected()
    assert not du3.is_throttled()
    assert not du3.is_uploading()

def test_download():
    t = Throttler(1000, 2000, 10, 2)
    dd3 = DummyDownload('c' * 20, t)
    t.download_connected(dd3)
    assert dd3.is_connected()
    assert not dd3.is_throttled()
    assert dd3.is_downloading()

    dd3.spontaneous_came_in(3000)
    assert dd3.is_connected()
    assert not dd3.is_throttled()
    assert dd3.is_downloading()

    dd3.spontaneous_exhausted()
    assert dd3.is_connected()
    assert not dd3.is_throttled()
    assert not dd3.is_downloading()

    dd1 = DummyDownload('a' * 20, t)
    t.download_connected(dd1)
    assert dd1.is_connected()
    assert not dd1.is_throttled()
    assert dd1.is_downloading()
    assert dd3.is_connected()
    assert not dd3.is_throttled()
    assert not dd3.is_downloading()

    dd2 = DummyDownload('b' * 20, t)
    t.download_connected(dd2)
    assert dd1.is_connected()
    assert not dd1.is_throttled()
    assert dd1.is_downloading()
    assert dd2.is_connected()
    assert not dd2.is_throttled()
    assert dd2.is_downloading()
    assert dd3.is_connected()
    assert not dd3.is_throttled()
    assert not dd3.is_downloading()

    dd4 = DummyDownload('d' * 20, t)
    t.download_connected(dd4)
    assert dd1.is_connected()
    assert not dd1.is_throttled()
    assert dd1.is_downloading()
    assert dd2.is_connected()
    assert not dd2.is_throttled()
    assert dd2.is_downloading()
    assert dd3.is_connected()
    assert not dd3.is_throttled()
    assert not dd3.is_downloading()
    assert dd4.is_connected()
    assert not dd4.is_throttled()
    assert not dd4.is_downloading()

    dd2.spontaneous_throttled()
    assert dd1.is_connected()
    assert not dd1.is_throttled()
    assert dd1.is_downloading()
    assert dd2.is_connected()
    assert dd2.is_throttled()
    assert not dd2.is_downloading()
    assert dd3.is_connected()
    assert not dd3.is_throttled()
    assert not dd3.is_downloading()
    assert dd4.is_connected()
    assert not dd4.is_throttled()
    assert dd4.is_downloading()
    
    dd2.spontaneous_unthrottled()
    assert dd1.is_connected()
    assert not dd1.is_throttled()
    assert dd1.is_downloading()
    assert dd2.is_connected()
    assert not dd2.is_throttled()
    assert not dd2.is_downloading()
    assert dd3.is_connected()
    assert not dd3.is_throttled()
    assert not dd3.is_downloading()
    assert dd4.is_connected()
    assert not dd4.is_throttled()
    assert dd4.is_downloading()

"""
def test_start_throttled():
    exhaust downloads and connect new, assert throttled
"""