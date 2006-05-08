# QList:
# basically a python 2.3 compatible interface if you want deque
#
# SizedList:
# handy class for keeping a fixed-length history
# uses deque if available
#
# by Greg Hazel

try:
    from collections import deque
    base_list_class = deque
    popleft = deque.popleft
    clear = deque.clear
except ImportError:
    from UserList import UserList
    base_list_class = UserList
    def popleft(l):
        return l.pop(0)
    def clear(l):
        l[:] = []

class QList(base_list_class):

    def __init__(self, *a, **kw):
        base_list_class.__init__(self, *a, **kw)

    def popleft(self):
        return popleft(self)

    def clear(self):
        return clear(self)

    # dequeu doesn't have __add__ ?
    def __add__(self, l):
        n = base_list_class(self)
        n.extend(l)
        return n

# I use QList becuase deque.popleft is faster than list.pop(0)
class SizedList(QList):

    def __init__(self, max_items):
        self.max_items = max_items
        QList.__init__(self)

    def append(self, v):
        QList.append(self, v)
        if len(self) > self.max_items:
            self.popleft()        
            
if __name__ == '__main__':
    l = SizedList(10)
    for i in xrange(50):
        l.append(i)
    assert list(l) == range(40, 50)    