Trees! Treeeeeeesss! More treeeeeeees!

Thought in-ordered swigged C++ and Python-only maps might be useful.  I wrote 
these some time ago to support fast ordering of peers in the tracker based
on playback time.

CMap is a swigged wrapper around C++ STL's map<double, PyObject*>.
The RPI and SGI STL map implementations use a threaded red-black tree.
However, the Makefile uses whatever STL map implementation is in your
header include path.  So far it only supports numeric keys (anything
that can be typecast to a double).   Values can be any Python object.
I could extend it to support a wider set of key types if there is a demand.

PMap is a Python list that maintains order by inserting using insort.
Searches are done with bisect.

The CMap is faster than a dict for random inserts and almost as fast as a dict 
for lookups.  CMap is significantly faster than a Python list for 
insort-based inserts of random numbers.  In-order
traversals are about the same for a list as a CMap.  In-order traversal
of a dict is .... uhhh... don't do that.

    Table 1: n random inserts

           n           t
 dict:    100      0.059463
 CMap:    100      0.040030
 PMap:    100      0.066265

 dict:    400      0.148301
 CMap:    400      0.098010
 PMap:    400      0.223216

 dict:    48000    7.060883
 CMap:    48000    10.155016
 PMap:    48000    47.234786



    Table 2: 5000 random searches when n items in data structure

           n           t
 dict:    100      0.069368
 CMap:    100      0.085237
 PMap:    100      0.078076

 dict:    400      0.068410
 CMap:    400      0.085717
 PMap:    400      0.079471

 dict:    48000    0.070615
 CMap:    48000    0.091949
 PMap:    48000    0.080785


The CMap implements all features of a Python container plus it supports
bidirectional iterators that are not invalidated by insertion or
deletion--- unless a deletion wipes out the node pointed to by an
iterator.  Furthermore it supports searches for the smallest key larger
than a number and vice versa.

CIndexedMap has a dict-based cross-index that allows lookups for values in 
O(1) time.  The iterators point at the corresponding tree node.
Thus one can iterate backwards or forwards from the lookup point returned
from the cross-index.

We could also add a dict-based index to speed up key lookups,
but this provides negligible lookup performance benefit except
for REALLY large n and increases constant overhead on almost all
other operations.  


