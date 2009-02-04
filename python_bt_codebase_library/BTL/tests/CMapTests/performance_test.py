import sys

# if executing from within BitTorrent, make sure we are using path
# to the root of the BitTorrent src code tree.
# HACK! I didn't eliminate the pwd from the path.
sys.path = ['..'] + sys.path

from Map import *
from CMap import *
from PMap import *
import random
from bisect import insort_left, bisect_left
from time import time
import gc



#############
# PERFORMANCE TESTS

MAX_TIME = 60 * 4    # 4 minutes
REPEATS = 10
SEARCH_REPEATS = 4
SEARCHES = 5000
nlist = [100, 400, 800, 1600, 2000, 4000, 8000, 16000, 32000,48000, 64000]

def test_insertions( factory, insert, nlist, fp ):
    """performance test insertions into map collections like dicts and Map."""
    assert callable(factory)
    assert callable(insert)
    assert type(nlist) == list
    assert type(fp) == file

    range = 2**28
    start_run = time()
    for n in nlist:
        print n
        start = time()
        for j in xrange(REPEATS):         # repeat test 5 times.
            m = factory()
            val = 0
            for i in xrange(n):
                r = random.randint(0,range)
                insert(m,r,val)
                val += 1          # val is arbitrary.
                if time() - start_run > MAX_TIME:
                    print ( "* taking too long. aborting this test "
                            "and moving to next one." )
                    return

            del m
            
        run_time = time() - start
        gc.collect()
        fp.write( "%f\t%f\n" % (n, run_time) )

def test_inorder_insertions( factory, append, nlist, fp ):
    assert callable(factory)
    assert callable(append)
    assert type(nlist) == list
    assert type(fp) == file

    start_run = time()
    for n in nlist:
        print n
        range = int(2**28/n)
        start = time()
        for j in xrange(REPEATS):
    
            m = factory()
            val = 0
            r = 0
            for i in xrange(n):
                r += random.randint(0,range)
                append(m,r,val)
                val += 1          # val is arbitrary.
                if time() - start_run > MAX_TIME:
                    print ( "* taking too long. aborting this test "
                            "and moving to next one." )
                    return
    
            del m
            
        run_time = time() - start
        gc.collect()
        fp.write( "%f\t%f\n" % (n, run_time) )

    
def test_searches( factory, insert, search, nlist, fp ):
    assert callable(factory)
    assert callable(search)
    assert type(nlist) == list
    assert type(fp) == file

    start_run = time()
    for n in nlist:
        print n
        for j in xrange(SEARCH_REPEATS): # repeat test 5 times.
            m = factory()
            keys = []
            val = 0
            for i in xrange(n):
                r = random.randint(0,2**30)
                insert(m,r,val)          # val is arbitrary.
                keys.append(r)
                val += 1
                
            start = time()
            for x in xrange(SEARCHES):
                index = random.randint(0,n-1)
                val = search(m,keys[index])    # lookup being measured.
                if time() - start_run > MAX_TIME:
                    print ( "* taking too long. aborting this test "
                            "and moving to next one." )
                    return
               
            run_time = time() - start
    
            del m
            del keys
            gc.collect()
            
            fp.write( "%f\t%f\n" % (n, run_time) )

def test_cross_index_searches(factory, insert, cross_search, nlist,fp):
    assert callable(factory)
    assert callable(cross_search)
    assert type(nlist) == list
    assert type(fp) == file
    
    start_run = time()
    for n in nlist:
        print n
        for j in xrange(SEARCH_REPEATS):      
            m = factory()
            values = []
            for i in xrange(n):
                while True:  # keep trying until a random number is not already
                             # in the list.  Collisions are really unlikely
                             # anyway.
                    k = random.randint(0,2**30)
                    v = random.randint(0,2**30)
                
                    values.append(v)
                    try:
                        insert(m,k,v)         # val is arbitrary.
                        break
                    except ValueError:
                        pass
                    
                
            start = time()
            for x in xrange(SEARCHES):
                index = random.randint(0,n-1)
                val = cross_search(m,values[index])    # lookup being measured.
                if time() - start_run > MAX_TIME:
                    print ( "* taking too long. aborting this test "
                            "and moving to next one." )
                    return
               
            run_time = time() - start
    
            del m
            del values
            gc.collect()
            
            fp.write( "%f\t%f\n" % (n, run_time) )
    

def run_test_suite( name, factory, insert, append, search,cross_search,nlist ):
    # random insertion order.
    if insert != None:
        print "random insertions into a %s." % name
        fp = open( "%s_random_inserts_vs_n.txt" % name, "w" )
        test_insertions(factory,insert,nlist,fp)
        fp.close()

    # insert keys in order.
    if insert != None:
        print "Inserting already ordered numbers into %s." % name
        fp = open( "%s_in_order_inserts_vs_n.txt" % name, "w" )
        test_inorder_insertions(factory,insert,nlist,fp)
        fp.close()

    if search != None:
        # random searchs
        print "Peforming searches into a %s." % name
        fp = open( "%s_%d_searches_vs_n.txt" % (name,SEARCHES), "w" )
        def search(m,k): return m[k]
        test_searches(factory,insert,search,nlist,fp)
        fp.close()   

    if cross_search != None:
        print "Performing cross index searches into a %s." % name
        # search for value.
        fp = open( "%s_%d_cross_index_searches_vs_n.txt" % (name,SEARCHES),"w")
        test_cross_index_searches(factory,insert,cross_search,nlist,fp)
        fp.close()

## test dicts
def ins(m, k, v): m[k]=v
def search(m,k): return m[k]
def cross_search( d, v ):
    for key,value in d.items():
        if v == value: return v
    return None
run_test_suite( "dict", dict, ins, ins, search, cross_search, nlist)

## test Map implemented using a red-black tree.
#run_test_suite( "map", Map, ins, ins, search, cross_search, nlist)

## test fast maps.
#run_test_suite( "fast_map", FastMap, ins, ins, search, cross_search, nlist)

## test CMaps.
def append(m,k,v): m.append(k,v)
run_test_suite( "cmap", CMap, ins, append, search, cross_search, nlist)

## test CIndexedMaps.
def indexed_cross_search(m,v):
    return m.find_key_by_value(v)
run_test_suite( "cindexedmap", CIndexedMap, ins, append, search,
                indexed_cross_search, nlist )

## test PMaps.
print "Inserting numbers that have already been ordered into the PMap."
run_test_suite( "pmap", PMap, ins, append, search, indexed_cross_search,nlist)

