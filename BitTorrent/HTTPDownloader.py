# Written by John Hoffman
# see LICENSE.txt for license information

from CurrentRateMeasure import Measure
from random import shuffle, randint
from time import time
from math import sqrt
from urlparse import urlparse
from httplib import HTTPConnection
from urllib import quote
from threading import Thread
from __init__ import version_short
true = 1
false = 0

EXPIRE_TIME = 60 * 60

class SingleDownload:
    def __init__(self, downloader, url):
        self.downloader = downloader
        self.baseurl = url
        try:
            (scheme, self.netloc, path, pars, query, fragment) = urlparse(url)
        except:
            self.downloader.errorfunc('cannot parse http seed address: '+url)
            return
        if scheme != 'http':
            self.downloader.errorfunc('http seed url not http: '+url)
            return
        try:
            self.connection = HTTPConnection(self.netloc)
        except:
            self.downloader.errorfunc('cannot connect to http seed: '+url)
            return
        self.seedurl = path
        if pars:
            self.seedurl += ';'+pars
        self.seedurl += '?'
        if query:
            self.seedurl += query+'&'
        self.seedurl += 'info_hash='+quote(self.downloader.infohash)

        self.measure = Measure(downloader.max_rate_period)
        self.index = None
        self.url = ''
        self.requests = []
        self.request_size = 0
        self.endflag = false
        self.error = None
        self.retry_period = 30
        self._retry_period = None
        self.errorcount = 0
        self.goodseed = false
        self.active = false
        self.resched(randint(2,10))

    def resched(self, len = None):
        if len is None:
            len = self.retry_period
        if self.errorcount > 3:
            len = len * (self.errorcount - 2)
        self.downloader.rawserver.add_task(self.download, len)

    def _want(self, index):
        if self.endflag:
            return self.downloader.storage.do_I_have_requests(index)
        else:
            return self.downloader.storage.is_unstarted(index)

    def download(self):
        if self.downloader.picker.am_I_complete():
            self.downloader.downloads.remove(self)
            return
        self.index = self.downloader.picker.next(self._want, true)
        if ( self.index is None and not self.endflag
                     and not self.downloader.peerdownloader.has_downloaders() ):
            self.endflag = true
            self.index = self.downloader.picker.next(self._want, true)
        if self.index is None:
            self.endflag = true
            self.resched()
        else:
            self.url = ( self.seedurl+'&piece='+str(self.index) )
            self._get_requests()
            if self.request_size < self.downloader.storage._piecelen(self.index):
                self.url += '&ranges='+self._request_ranges()
            rq = Thread(target = self._request)
            rq.setDaemon(false)
            rq.start()
            self.active = true

    def _request(self):
        import encodings.ascii
        import encodings.punycode
        import encodings.idna
        
        self.error = None
        self.received_data = None
        try:
            self.connection.request('GET',self.url, None,
                                {'User-Agent': 'BitTorrent/' + version_short})
            r = self.connection.getresponse()
            self.connection_status = r.status
            self.received_data = r.read()
        except Exception, e:
            self.error = 'error accessing http seed: '+str(e)
            try:
                self.connection.close()
            except:
                pass
            try:
                self.connection = HTTPConnection(self.netloc)
            except:
                self.connection = None  # will cause an exception and retry next cycle
        self.downloader.rawserver.external_add_task(self.request_finished)

    def request_finished(self):
        self.active = false
        if self.error is not None:
            if self.goodseed:
                self.downloader.errorfunc(self.error)
            self.errorcount += 1
        if self.received_data:
            self.errorcount = 0
            if not self._got_data():
                self.received_data = None
        if not self.received_data:
            self._release_requests()
            self.downloader.peerdownloader.piece_flunked(self.index)
        if self._retry_period:
            self.resched(self._retry_period)
            self._retry_period = None
            return
        self.resched()

    def _got_data(self):
        if self.connection_status == 503:   # seed is busy
            try:
                self.retry_period = max(int(self.received_data),5)
            except:
                pass
            return false
        if self.connection_status != 200:
            self.errorcount += 1
            return false
        self._retry_period = 1
        if len(self.received_data) != self.request_size:
            if self.goodseed:
                self.downloader.errorfunc('corrupt data from http seed - redownloading')
            return false
        self.measure.update_rate(len(self.received_data))
        self.downloader.measurefunc(len(self.received_data))
        self.downloader.downmeasure.update_rate(len(self.received_data))
        if self._fulfill_requests():
            if not self.goodseed:
                self.goodseed = true
                self.downloader.seedsfound += 1
            if self.downloader.storage.do_I_have(self.index):
                self.downloader.picker.complete(self.index)
                self.downloader.peerdownloader.check_complete(self.index)
                self.downloader.gotpiecefunc(self.index)
        else:
            return false
        return true
    
    def _get_requests(self):
        self.requests = []
        self.request_size = 0L
        while self.downloader.storage.do_I_have_requests(self.index):
            r = self.downloader.storage.new_request(self.index)
            self.requests.append(r)
            self.request_size += r[1]
        self.requests.sort()

    def _fulfill_requests(self):
        start = 0L
        success = true
        for i in range(len(self.requests)):
            begin, length = self.requests[i]
            if not self.downloader.storage.piece_came_in(self.index, begin,
                            self.received_data[start:start+length]):
                success = false
            start += length
        self.requests = []
        return success

    def _release_requests(self):
        for begin, length in self.requests:
            self.downloader.storage.request_lost(self.index, begin, length)
        self.requests = []

    def _request_ranges(self):
        s = ''
        begin, length = self.requests[0]
        for begin1, length1 in self.requests[1:]:
            if begin + length == begin1:
                length += length1
                continue
            else:
                if s:
                    s += ','
                s += str(begin)+'-'+str(begin+length-1)
                begin, length = begin1, length1
        if s:
            s += ','
        s += str(begin)+'-'+str(begin+length-1)
        return s
        
    
class HTTPDownloader:
    def __init__(self, storage, picker, rawserver,
                 finflag, errorfunc, peerdownloader,
                 max_rate_period, infohash, downmeasure, gotpiecefunc,
                 measurefunc = lambda x: None):
        self.storage = storage
        self.picker = picker
        self.rawserver = rawserver
        self.finflag = finflag
        self.errorfunc = errorfunc
        self.peerdownloader = peerdownloader
        self.infohash = infohash
        self.max_rate_period = max_rate_period
        self.downmeasure = downmeasure
        self.gotpiecefunc = gotpiecefunc
        self.measurefunc = measurefunc
        self.downloads = []
        self.seedsfound = 0

    def make_download(self, url):
        self.downloads.append(SingleDownload(self, url))
        return self.downloads[-1]

    def get_downloads(self):
        if self.finflag.isSet():
            return []
        return self.downloads
