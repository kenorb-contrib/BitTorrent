# Written by Bram Cohen
# this file is public domain

true = 1
false = 0

class DownloaderData:
    def __init__(self, blobs, chunksize):
        self.blobs = blobs
        self.chunksize = chunksize
        # blob, active, inactive
        # [(blob, [(begin, length)], [(begin, length)] )]
        self.priority_list = []
        # blob: active, inactive
        # {blob: ([(begin, length)], [(begin, length)])}
        self.priority_dict = {}
        # download: active, have
        # {download: ([(blob, begin, length)],  {blob: 1})}
        self.downloads = {}
        
    def cleared(self, d):
        for blob, begin, length in self.downloads[d][0]:
            active, inactive = self.priority_dict[blob]
            active.remove((begin, length))
            inactive.append((begin, length))
        del self.downloads[d][0][:]
        return self.downloads.keys()
        
    def do_I_want_more(self, d):
        have = self.downloads[d][1]
        if len(have) > len(self.priority_list):
            return true
        for blob, active, inactive in self.priority_list:
            if len(inactive) > 0 and have.has_key(blob):
                return true
        for b in have.keys():
            if not self.priority_dict.has_key(b):
                return true
        return false
        
    def get_next(self, d):
        have = self.downloads[d][1]
        if len(have) == 0:
            return None
        for blob, active, inactive in self.priority_list:
            if len(inactive) > 0 and have.has_key(blob):
                begin, length = inactive[-1]
                del inactive[-1]
                active.append((begin, length))
                self.downloads[d][0].append((blob, begin, length))
                f = []
                if len(inactive) == 0:
                    for d2, (a2, h2) in self.downloads.items():
                        if h2.has_key(blob) and d2 is not d:
                            f.append(d2)
                return blob, begin, length, f
        for blob in self.blobs.get_list_of_blobs_I_want():
            if not have.has_key(blob):
                continue
            if self.priority_dict.has_key(blob):
                continue
            total = self.blobs.get_size(blob)
            chunk = self.chunksize
            begin = 0
            inactive = []
            while begin + chunk < total:
                inactive.append((begin, chunk))
                begin += chunk
            length = total - begin
            active = [(begin, length)]
            self.downloads[d][0].append((blob, begin, length))
            self.priority_list.append((blob, active, inactive))
            self.priority_dict[blob] = (active, inactive)
            if len(inactive) > 0:
                return blob, begin, length, []
            else:
                return blob, begin, length, [i for i in 
                    self.downloads.keys() if 
                    self.downloads[i][1].has_key(blob)]
        return None
        
    def num_current(self, d):
        return len(self.downloads[d][0])
    
    def came_in(self, d, blob, begin, slice):
        try:
            self.downloads[d][0].remove((blob, begin, len(slice)))
        except ValueError:
            return false, []
        active, inactive = self.priority_dict[blob]
        active.remove((begin, len(slice)))
        self.blobs.save_slice(blob, begin, slice)
        if len(active) == 0 and len(inactive) == 0:
            for i in xrange(len(self.priority_list)):
                if self.priority_list[i][0] == blob:
                    del self.priority_list[i]
                    break
            del self.priority_dict[blob]
            if self.blobs.check_blob(blob):
                for a, have in self.downloads.values():
                    if have.has_key(blob):
                        del have[blob]
                return true, []
            else:
                return false, self.downloads.keys()
        return false, []
        
    def has_blobs(self, d, bs):
        hit = false
        have = self.downloads[d][1]
        for blob in bs:
            if self.blobs.do_I_want(blob) and not have.has_key(blob):
                have[blob] = 1
                if not self.priority_dict.has_key(blob) or len(self.priority_dict[blob][1]) != 0:
                    hit = true
        return hit
        
    def connected(self, d):
        self.downloads[d] = ([], {})
        
    def disconnected(self, d):
        self.cleared(d)
        del self.downloads[d]
        return self.downloads.keys()

class DummyBlobs:
    def __init__(self, blobs, prefs = None):
        if prefs is None:
            prefs = blobs.keys()
        self.prefs = prefs
        self.blobs = blobs
        self.expect = false

    def get_list_of_blobs_I_want(self):
        return self.prefs
        
    def get_size(self, blob):
        return len(self.blobs[blob])
    
    def save_slice(self, blob, begin, slice):
        assert self.blobs[blob][begin:begin + len(slice)] == slice
    
    def check_blob(self, blob):
        assert self.expect
        self.expect = false
        if self.result:
            del self.blobs[blob]
            self.prefs.remove(blob)
            return true
        return false
    
    def do_I_want(self, blob):
        return self.blobs.has_key(blob)

class DummyDownloader:
    pass

def test_normal():
    blobs = DummyBlobs({'x': 'abcdefghijk'})
    dd = DownloaderData(blobs, 2)
    a = DummyDownloader()
    b = DummyDownloader()
    c = DummyDownloader()
    dd.connected(a)
    dd.connected(b)
    dd.connected(c)

    assert not dd.do_I_want_more(a)
    assert not dd.do_I_want_more(b)
    assert not dd.do_I_want_more(c)

    assert dd.num_current(a) == 0

    assert dd.get_next(a) is None
    assert dd.get_next(b) is None
    assert dd.get_next(c) is None

    assert not dd.has_blobs(a, ['q'])

    assert dd.has_blobs(a, ['x'])
    assert dd.has_blobs(b, ['x'])
    assert dd.has_blobs(c, ['x'])
    
    assert dd.do_I_want_more(a)
    assert dd.do_I_want_more(b)
    assert dd.do_I_want_more(c)

    assert dd.get_next(a) == ('x', 10, 1, [])
    assert dd.get_next(a) == ('x', 8, 2, [])
    assert dd.get_next(a) == ('x', 6, 2, [])
    
    assert dd.get_next(b) == ('x', 4, 2, [])
    assert dd.get_next(b) == ('x', 2, 2, [])
    spam = dd.get_next(b)
    assert spam[:-1] == ('x', 0, 2)
    assert spam[-1] == [a, c] or spam[-1] == [c, a]

    assert dd.num_current(a) == 3
    assert dd.num_current(b) == 3
    assert dd.num_current(c) == 0

    assert not dd.has_blobs(c, ['x'])

    assert not dd.do_I_want_more(a)
    assert not dd.do_I_want_more(b)
    assert not dd.do_I_want_more(c)

    assert dd.get_next(a) is None
    assert dd.get_next(b) is None
    assert dd.get_next(c) is None

    assert dd.came_in(a, 'x', 8, 'ij') == (false, [])
    assert dd.came_in(a, 'x', 6, 'gh') == (false, [])

    assert dd.num_current(a) == 1
    assert dd.num_current(b) == 3
    assert dd.num_current(c) == 0

    assert not dd.do_I_want_more(a)
    assert not dd.do_I_want_more(b)
    assert not dd.do_I_want_more(c)

    assert dd.get_next(a) is None
    assert dd.get_next(b) is None
    assert dd.get_next(c) is None

    assert dd.came_in(b, 'x', 0, 'ab') == (false, [])

    assert dd.num_current(a) == 1
    assert dd.num_current(b) == 2
    assert dd.num_current(c) == 0

    assert not dd.do_I_want_more(a)
    assert not dd.do_I_want_more(b)
    assert not dd.do_I_want_more(c)

    dd.disconnected(a)

    assert dd.do_I_want_more(b)
    assert dd.do_I_want_more(c)

    assert dd.get_next(c) == ('x', 10, 1, [b])

    assert dd.num_current(b) == 2
    assert dd.num_current(c) == 1

    assert not dd.do_I_want_more(b)
    assert not dd.do_I_want_more(c)
    assert dd.get_next(b) is None
    assert dd.get_next(c) is None

    assert dd.came_in(b, 'x', 2, 'cd') == (false, [])
    assert dd.came_in(b, 'x', 4, 'ef') == (false, [])
    
    blobs.expect = true
    blobs.result = true

    assert dd.came_in(c, 'x', 10, 'k') == (true, [])

    assert not dd.do_I_want_more(b)
    assert not dd.do_I_want_more(c)
    assert dd.get_next(b) is None
    assert dd.get_next(c) is None

    assert dd.num_current(b) == 0
    assert dd.num_current(c) == 0

def test_multiple():
    blobs = DummyBlobs({'a': 'abcdef', 'b': 'abcdef', 'c': 'abcdef'}, ['a', 'b', 'c'])
    dd = DownloaderData(blobs, 2)
    a = DummyDownloader()
    dd.connected(a)
    assert dd.has_blobs(a, ['b', 'c'])
    assert dd.do_I_want_more(a)
    assert dd.get_next(a) == ('b', 4, 2, [])
    assert dd.do_I_want_more(a)
    assert dd.get_next(a) == ('b', 2, 2, [])
    assert dd.do_I_want_more(a)
    assert dd.get_next(a) == ('b', 0, 2, [])
    assert dd.do_I_want_more(a)
    assert dd.get_next(a) == ('c', 4, 2, [])
    assert dd.do_I_want_more(a)
    assert dd.get_next(a) == ('c', 2, 2, [])
    assert dd.do_I_want_more(a)
    assert dd.get_next(a) == ('c', 0, 2, [])
    assert not dd.do_I_want_more(a)
    assert dd.get_next(a) == None
    assert dd.num_current(a) == 6

    assert dd.came_in(a, 'b', 0, 'ab') == (false, [])
    assert dd.came_in(a, 'b', 2, 'cd') == (false, [])
    blobs.expect = true
    blobs.result = true
    assert dd.came_in(a, 'b', 4, 'ef') == (true, [])
    
    assert dd.came_in(a, 'c', 0, 'ab') == (false, [])
    assert dd.came_in(a, 'c', 2, 'cd') == (false, [])
    blobs.expect = true
    blobs.result = true
    assert dd.came_in(a, 'c', 4, 'ef') == (true, [])

    assert dd.num_current(a) == 0
    assert not dd.do_I_want_more(a)

def test_flunk():
    blobs = DummyBlobs({'a': 'abcdef'})
    dd = DownloaderData(blobs, 2)
    a = DummyDownloader()
    dd.connected(a)

    assert dd.has_blobs(a, ['a'])
    assert dd.do_I_want_more(a)
    assert dd.get_next(a) == ('a', 4, 2, [])
    assert dd.do_I_want_more(a)
    assert dd.get_next(a) == ('a', 2, 2, [])
    assert dd.do_I_want_more(a)
    assert dd.get_next(a) == ('a', 0, 2, [])
    assert not dd.do_I_want_more(a)

    assert dd.came_in(a, 'a', 0, 'ab') == (false, [])
    assert dd.came_in(a, 'a', 2, 'cd') == (false, [])
    blobs.expect = true
    blobs.result = false
    assert dd.came_in(a, 'a', 4, 'ef') == (false, [a])
    assert dd.num_current(a) == 0

    assert dd.do_I_want_more(a)
    assert dd.get_next(a) == ('a', 4, 2, [])
    assert dd.do_I_want_more(a)
    assert dd.get_next(a) == ('a', 2, 2, [])
    assert dd.do_I_want_more(a)
    assert dd.get_next(a) == ('a', 0, 2, [])
    assert not dd.do_I_want_more(a)
    assert dd.num_current(a) == 3

    assert dd.came_in(a, 'a', 0, 'ab') == (false, [])
    assert dd.came_in(a, 'a', 2, 'cd') == (false, [])
    blobs.expect = true
    blobs.result = true
    assert dd.came_in(a, 'a', 4, 'ef') == (true, [])
    assert dd.num_current(a) == 0

def test_short_blob():
    blobs = DummyBlobs({'a': 'a'})
    dd = DownloaderData(blobs, 2)
    a = DummyDownloader()
    dd.connected(a)
    assert dd.has_blobs(a, ['a'])
    b = DummyDownloader()
    dd.connected(b)
    assert dd.has_blobs(b, ['a'])

    spam = dd.get_next(a)
    assert spam[:-1] == ('a', 0, 1)
    assert spam[-1] == [a, b] or spam[-1] == [b, a]
    assert dd.num_current(a) == 1
    assert not dd.do_I_want_more(a)
    assert not dd.do_I_want_more(b)
    assert dd.get_next(a) == None
    assert dd.get_next(b) == None

    blobs.expect = true
    blobs.result = true
    assert dd.came_in(a, 'a', 0, 'a') == (true, [])
    assert dd.num_current(a) == 0
    assert not dd.do_I_want_more(a)
    assert not dd.do_I_want_more(b)
