true = 1
false = 0

class DownloaderData:
    def __init__(self, blobs, chunksize, uploader):
        self.blobs = blobs
        self.chunksize = chunksize
        self.uploader = uploader
        # blob, active, inactive
        # [(blob, [(begin, length)], [(begin, length)] )]
        self.priority = []
        # download: active, have
        # {download: ([(blob, begin, length)],  {blob: 1})}
        self.downloads = {}
        
    def cleared(self, d):
        for blob, begin, length in self.downloads[d][0]:
            for blob2, active, inactive in self.priority:
                if blob2 == blob:
                    active.remove((begin, length))
                    inactive.append((begin, length))
                    break
        del self.downloads[d][0][:]
        return self.downloads.keys()
        
    def do_I_want_more(self, d):
        have = self.downloads[d][1]
        if len(have) > len(self.priority):
            return true
        for blob, active, inactive in self.priority:
            if len(inactive) > 0 and have.has_key(blob):
                return true
        for b in have.keys():
            for blob, active, inactive in self.priority:
                if blob == b:
                    break
            else:
                return true
        return false
        
    def get_next(self, d):
        have = self.downloads[d][1]
        if len(have) == 0:
            return None
        for blob, active, inactive in self.priority:
            if len(inactive) > 0 and have.has_key(blob):
                begin, length = inactive[-1]
                del inactive[-1]
                active.append((begin, length))
                self.downloads[d][0].append((blob, begin, length))
                f = []
                for d2, (a2, h2) in self.downloads.items():
                    if d2 != d and h2.has_key(blob):
                        f.append(d2)
                return blob, begin, length, f
        for blob in self.blobs.get_list_of_files_I_want():
            if not have.has_key(blob):
                continue
            for b2, active, inactive in self.priority:
                if b2 == blob:
                    break
            else:
                total = self.blobs.get_size(blob)
                chunk = self.chunksize
                begin = 0
                inactive = []
                while begin + chunk < total:
                    inactive.append((begin, chunk))
                length = total - begin
                active = [(begin, length)]
                self.downloads[d][0].append((blob, begin, length))
                self.priority.append((blob, active, inactive))
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
            return []
        for i in xrange(len(self.priority)):
            blob2, active, inactive = self.priority[i]
            if blob2 == blob:
                active.remove((begin, len(slice)))
                break
        self.blobs.save_slice(blob, begin, slice)
        if len(active) == 0 and len(inactive) == 0:
            del self.priority[i]
            if self.blobs.check_blob(blob):
                for a, have in self.downloads.values():
                    if have.has_key(blob):
                        del have[blob]
                self.uploader.received_file(blob)
            else:
                return self.downloads.keys()
        return []
        
    def has_blobs(self, d, bs):
        for blob in bs:
            if self.blobs.do_I_want(blob):
                self.downloads[d][1][blob] = 1
        
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


