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
                        if h2.has_key(blob):
                            f.append(d2)
                return blob, begin, length, f
        for blob in self.blobs.get_list_of_files_I_want():
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
                return blob, begin, length, self.downloads.keys()
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
                if len(self.priority_dict[blob][1]) != 0:
                    hit = true
        return hit
        
    def connected(self, d):
        self.downloads[d] = ([], {})
        
    def disconnected(self, d):
        self.cleared(d)
        del self.downloads[d]
        return self.downloads.keys()

def test_normal():
    start three things both which want three pieces
    make first one get two
    make second one get one
    disconnect first
    make second one get two more
    make all three come in

def test_multiple():
    make a single thing with two blobs
    make first blob arrive, then get flunked, then arrive properly
    make second blob arrive properly

def test_short_blob():
    make two connections each of which want a single blob with only one chunk
    start download from one


