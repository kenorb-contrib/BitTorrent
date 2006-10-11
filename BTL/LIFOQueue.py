from Queue import Queue

class LIFOQueue(Queue):
    
    # Get an item from the queue
    def _get(self):
        return self.queue.pop()

if __name__ == '__main__':
    l = LIFOQueue()
    for i in xrange(10):
        l.put(i)
    j = 9
    for i in xrange(10):
        assert l.get() == j - i