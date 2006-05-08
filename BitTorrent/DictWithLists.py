# These are some handy dict types:
#
# DictWithLists:
#   acts like a dict, but adding a key,value appends value to a list at that key
#   getting a value at a key returns the first value in the list
#   a key is only removed when the list is empty
#
# OrderedDict:
#  just like a dict, but d.keys() is in insertion order
#
# OrderedDictWithLists:
#  a combination of the two concepts that keeps lists at key locations in
#  insertion order
#
# by Greg Hazel
# with code from David Benjamin and contributers

from BitTorrent.Lists import QList
from BitTorrent.obsoletepythonsupport import set
from UserDict import IterableUserDict

class DictWithLists(IterableUserDict):

    def __init__(self, dict = None, parent = IterableUserDict):
        self.parent = parent
        self.parent.__init__(self, dict)

    def popitem(self):
        try:
            key = self.keys()[0]
        except IndexError:
            raise KeyError('popitem(): dictionary is empty')
        return (key, self.pop(key))

    def pop(self, key, *args):
        if key not in self and len(args) > 0:
            return args[0]

        l = self.parent.__getitem__(self, key)
        data = l.popleft()

        # so we don't leak blank lists
        if len(l) == 0:
            self.parent.__delitem__(self, key)

        return data
    pop_from_row = pop
    
    def __delitem__(self, key):
        self.pop(key)

    def get_from_row(self, key):
        return self.parent.__getitem__(self, key)[0]
            
    def getrow(self, key):
        return self.parent.__getitem__(self, key)

    def poprow(self, key):
        l = self.parent.__getitem__(self, key)
        self.parent.__delitem__(self, key)
        return l

    def setrow(self, key, l):
        if len(l) == 0:
            return
        self.parent.__setitem__(self, key, l)
        
    def __setitem__(self, key, value):
        if key not in self:
            self.parent.__setitem__(self, key, QList())
        self.parent.__getitem__(self, key).append(value)
    push = __setitem__
    push_to_row = __setitem__

    def keys(self):
        return self.parent.keys(self)

    def total_length(self):
        t = 0
        for k in self.iterkeys():
            t += len(self.getrow(k))
        return t

class DictWithSets(DictWithLists):

    def pop(self, key, *args):
        if key not in self and len(args) > 0:
            return args[0]

        l = self.parent.__getitem__(self, key)
        data = l.pop()

        # so we don't leak blank sets
        if len(l) == 0:
            self.parent.__delitem__(self, key)

        return data
    pop_from_row = pop
                
    def __getitem__(self, key):
        s = self.parent.__getitem__(self, key)
        # ow
        i = s.pop()
        s.add(i)
        return i

    def push(self, key, value):
        if key not in self:
            self.parent.__setitem__(self, key, set())
        self.parent.__getitem__(self, key).add(value)
    push_to_row = push

    def remove_fom_row(self, key, value):
        l = self.parent.__getitem__(self, key)
        l.remove(value)

        # so we don't leak blank sets
        if len(l) == 0:
            self.parent.__delitem__(self, key)
        

# from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/107747
class OrderedDict(IterableUserDict):
    def __init__(self, dict = None):
        self._keys = []
        IterableUserDict.__init__(self, dict)

    def __delitem__(self, key):
        IterableUserDict.__delitem__(self, key)
        self._keys.remove(key)

    def __setitem__(self, key, item):
        IterableUserDict.__setitem__(self, key, item)
        if key not in self._keys:
            self._keys.append(key)

    def clear(self):
        IterableUserDict.clear(self)
        self._keys = []

    def copy(self):
        newInstance = odict()
        newInstance.update(self)
        return newInstance

    def items(self):
        return zip(self._keys, self.values())

    def keys(self):
        return self._keys[:]

    def popitem(self):
        try:
            key = self._keys[-1]
        except IndexError:
            raise KeyError('dictionary is empty')

        val = self[key]
        del self[key]

        return (key, val)

    def setdefault(self, key, failobj = None):
        if key not in self._keys:
            self._keys.append(key)
        return IterableUserDict.setdefault(self, key, failobj)

    def update(self, dict):
        for (key,val) in dict.items():
            self.__setitem__(key,val)

    def values(self):
        return map(self.get, self._keys)

class OrderedDictWithLists(DictWithLists, OrderedDict):

    def __init__(self, dict = None, parent = OrderedDict):
        DictWithLists.__init__(self, dict, parent = parent)


if __name__=='__main__':
    
    d = DictWithLists()

    for i in xrange(50):
        for j in xrange(50):
            d.push(i, j)

    for i in xrange(50):
        for j in xrange(50):
            assert d.pop(i) == j

    od = OrderedDict()

    def make_str(i):
        return str(i) + "extra"

    for i in xrange(50):
        od[make_str(i)] = 1

    for i,j in zip(xrange(50), od.keys()):
        assert make_str(i) == j

    odl = OrderedDictWithLists()

    for i in xrange(50):
        for j in xrange(50):
            odl.push(make_str(i), j)

    for i in xrange(50):
        for j in xrange(50):
            assert odl.pop(make_str(i)) == j

    od = OrderedDict()
    od['2'] = [1,1,1,1,1]
    od['1'] = [2,2,2,2,2]
    od['3'] = [3,3,3,3,3]
    k = od.keys()[0]
    assert k == '2'

    odl = OrderedDictWithLists()
    odl.setrow('2', [1,1,1,1,1])
    odl.setrow('1', [2,2,2,2,2])
    odl.setrow('3', [3,3,3,3,3])
    k = odl.keys()[0]
    assert k == '2'

