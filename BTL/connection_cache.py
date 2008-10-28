import logging
import pycurllib
from LIFOQueue import LIFOQueue
import Queue

MAX_WAIT = 5
MAX_PER_CACHE_DEFAULT = 15
INF_WAIT_MAX_CONNECTIONS = 1000

logger = logging.getLogger('BTL.connection_cache')

class ConnectionCache(object):
    def __init__(self, max_per_cache=None):
        if None == max_per_cache:
            max_per_cache = MAX_PER_CACHE_DEFAULT
        self.size = 0
        self.max_per_cache = max_per_cache
        self.cache = LIFOQueue(maxsize = self.max_per_cache)

    def get_connection(self):
        try:
            return self.cache.get_nowait()
        except Queue.Empty:
            logger.warn("ConnectionCache queue empty, size=%d, qsize=%d" % (self.size, self.cache.qsize()))
            pass
        # I chose not to lock here. Max is advisory, if two threads
        # eagerly await a connection near max, I say allow them both
        # to make one
        if self.size < self.max_per_cache:
            self.size += 1
            return self._make_connection()
        else:
            logger.warn("ConnectionCache queue over, size=%d, qsize=%d" % (self.size, self.cache.qsize()))
        try:
            return self.cache.get(True, MAX_WAIT)
        except Queue.Empty:
            # ERROR: Should log this!
            logger.error("ConnectionCache waited more than %d seconds, size=%d, qsize=%d" % (MAX_WAIT, self.size, self.cache.qsize()))
            pass
        if self.size > INF_WAIT_MAX_CONNECTIONS:
            logger.warn("ConnectionCache wait forever, size=%d, max_connections=%d, qsize=%d" % (self.size, INF_WAIT_MAX_CONNECTIONS, self.cache.qsize()))
            return self.cache.get()
        self.size += 1
        logger.warn("ConnectionCache wait inf, size=%d, max_connections=%d, qsize=%d" % (self.size, INF_WAIT_MAX_CONNECTIONS, self.cache.qsize()))
        return self._make_connection()

    def destroy_connection(self, c):
        c.c.close()
        self.size -= 1

    def put_connection(self, c):
        self.cache.put(c)

class PyCURL_Cache(ConnectionCache):
    def __init__(self, uri, max_per_cache=None):
        if None == max_per_cache:
            max_per_cache = MAX_PER_CACHE_DEFAULT
        self.uri = uri
        ConnectionCache.__init__(self, max_per_cache=max_per_cache)

    def _make_connection(self):
        r = pycurllib.Request(self.uri)
        return r

class CacheSet(object):
    def __init__(self):
        self.cache = {}

    def get_cache(self, cachetype, url, max_per_cache=None):
        if None == max_per_cache:
            max_per_cache = MAX_PER_CACHE_DEFAULT
        if url not in self.cache:
            self.cache[url] = cachetype(url, max_per_cache=max_per_cache)
        return self.cache[url]

cache_set = CacheSet()
