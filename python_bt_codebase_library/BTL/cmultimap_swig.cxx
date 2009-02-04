/**
 * The contents of this file are subject to the Python Software Foundation
 * License Version 2.3 (the License).  You may not copy or use this file, in
 * either source code or executable form, except in compliance with the License.
 * You may obtain a copy of the License at http://www.python.org/license.
 *
 * Software distributed under the License is distributed on an AS IS basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
 * for the specific language governing rights and limitations under the
 * License.
 * 
 *  By David Harrison
 */
#include "Python.h"
#include <map>
#include "cmap_swig.h"
#include "cmultimap_swig.h"
#include <iostream>

using namespace std;

typedef multimap<double,PyObject*> dmmap;
typedef pair<const double, PyObject*> dpair;

/*dmmap*/ void *mmap_constructor() {
  return new dmmap();
}

void mmap_delete( void *voidmmap ) {
    dmmap& m = *((dmmap*) voidmmap);
    dmmap *mp = (dmmap*) voidmmap;
  
    // decrement the referencde to every object in the mmap.
    dmmap::iterator i;
    for ( i = m.begin(); i != m.end(); ++i ) 
        Py_DECREF((*i).second);
  
    delete mp;
}


/*dmmap::iterator*/ void *mmap_begin( void *voidmmap ) {
    dmmap& m = *((dmmap*) voidmmap);
    dmmap::iterator *i = new dmmap::iterator(m.begin());
    if ( i == NULL ) throw MemoryError();
    return i;
}

/*dmmap::iterator*/ void *mmap_end( void *voidmmap ) {
    dmmap& m = *((dmmap*) voidmmap);
    dmmap::iterator *i = new dmmap::iterator(m.end());
    if ( i == NULL ) throw MemoryError();
    return i;
}

bool mmap_iiter_at_end( void *voidmmap, void *iter ) {
    dmmap& m = *((dmmap*) voidmmap);
    dmmap::iterator& i = *((dmmap::iterator*) iter );
    return i == m.end();
}

bool mmap_iiter_at_begin( void *voidmmap, void *iter ) {
    dmmap& m = *((dmmap*) voidmmap);
    dmmap::iterator& i = *((dmmap::iterator*) iter );
    return i == m.begin();
}


int mmap_size( void *voidmmap ) {
    dmmap& m = *((dmmap*) voidmmap);
    return m.size();   
}

PyObject *mmap_find( void *voidmmap, double k ) {
    dmmap& m = *((dmmap*) voidmmap);
    dmmap::iterator i = m.find(k);

    if ( i == m.end()) throw KeyError();
    PyObject *v = (PyObject*) ((*i).second);
    Py_INCREF(v);
    return v;
}

/*dmmap::iterator*/ void *mmap_find_iiter( void *voidmmap, double k ) {
    dmmap& m = *((dmmap*) voidmmap);
    dmmap::iterator *i = new dmmap::iterator(m.find(k));
    if ( i == NULL ) throw MemoryError();
    return i;
}

/**
 * inserts the passed key-value pair into the mmap.  
 *
 * cmultimap supports multiple identical keys.  
 * As a result, cmultimap does not support a mmap_set operation.  
 */
void mmap_insert( /*dmmap*/ void *voidmmap, double k, PyObject *v ) {
    dmmap& m = *((dmmap*) voidmmap);
    dmmap::iterator i = m.insert(dpair(k,v));
    Py_INCREF(v);
}

/*dmmap::iterator*/ void *mmap_insert_iiter( /*dmmap*/ void *voidmmap, double k, 
                                          PyObject *v ) 
{
    dmmap& m = *((dmmap*) voidmmap);
    dmmap::iterator *j = new dmmap::iterator();
    if ( j == NULL ) throw MemoryError();

    dmmap::iterator i = m.insert(dpair(k,v));
    Py_INCREF(v);
    *j = i;

    return j;
}

/**
 * Removes all items with the passed key.  
 */
// DANGEROUS.  Use iiter_erase and check each item about to be erased
// for iterators that should be invalidated.
//void mmap_erase( void *voidmmap, double key ) {
//    dmmap& m = *((dmmap*) voidmmap);
//    dmmap::iterator i = m.find(key);
//    if ( i == m.end() ) throw KeyError();
//    m.erase(key);
//}

void mmap_iiter_erase( /*dmmap*/ void *voidmmap, 
                     /*dmmap::iterator*/ void *voiditer ) 
{
    dmmap& m = *((dmmap*) voidmmap);
    dmmap::iterator& i = *((dmmap::iterator*) voiditer );
    PyObject *v = (*i).second;
    m.erase(i);
    Py_DECREF(v);
}

/**
 * Inserts the object with the hint that it should be appended to the end.
 * 
 * Takes O(log n) time.
 */
void mmap_append( /*dmmap*/ void *voidmmap, double k, PyObject *v ) {
    dmmap& m = *((dmmap*) voidmmap);
    dmmap::iterator i = m.insert(m.end(),dpair(k,v));
    Py_INCREF(v);
}

/**
 * Inserts the object with the hint that it should be appended to the end.
 * 
 * Takes O(log n) time.
 *
 * Differs from mmap_append in that this returns an iterator pointing
 * to the location where the key-value pair was inserted mmap_append
 * also avoids the overhead of dynamically allocating an iterator to
 * return.
 */
/*dmmap::iterator*/ void *mmap_append_iiter( /*dmmap*/ void *voidmmap, double k, 
                                          PyObject *v ) 
{
    dmmap& m = *((dmmap*) voidmmap);
    dmmap::iterator *ip = new dmmap::iterator(); //alloc before changing mmap.
    if ( ip == NULL ) throw MemoryError(); 

    dmmap::iterator i = m.insert(m.end(), dpair(k,v));
    Py_INCREF(v);
    *ip = i;
    return ip;
}

void iiter_delete( /*dmmap::iterator*/ void *voiditer ) {
    dmmap::iterator *i = (dmmap::iterator*) voiditer;
    delete i;
}

int iiter_cmp( /*dmmap*/ void *voidmmap, /*dmmap::iterator*/ void *viter1, 
              /*dmmap::iterator*/ void *viter2 ) {
    dmmap& m = *((dmmap*) voidmmap);
    dmmap::iterator& i1 = *((dmmap::iterator*) viter1 );
    dmmap::iterator& i2 = *((dmmap::iterator*) viter2 );
    if ( i1 == i2 ) return 0;
    if ( i1 == m.end() && i2 != m.end() ) return 1;
    if ( i1 != m.end() && i2 == m.end() ) return -1;
    if ( (*i1).first < (*i2).first ) return -1;
    if ( (*i1).first > (*i2).first ) return 1;
    return 0;
}

void *iiter_copy( /*dmmap::iterator*/ void *voiditer ) {
    dmmap::iterator& i = *((dmmap::iterator*) voiditer );
    dmmap::iterator *newi = new dmmap::iterator(i);
    return newi; 
}

void iiter_assign( /*dmmap::iterator*/ void *voiditer1, 
                    /*dmmap::iterator*/ void *voiditer2 ) {
    dmmap::iterator& i1 = *((dmmap::iterator*) voiditer1 );
    dmmap::iterator& i2 = *((dmmap::iterator*) voiditer2 );
    i1 = i2;
}

void iiter_incr( /*dmmap::iterator*/ void *voiditer ) {
    dmmap::iterator& i = *((dmmap::iterator*) voiditer );
    ++i;
}

void iiter_decr( /*dmmap::iterator*/ void *voiditer ) {
    dmmap::iterator& i = *((dmmap::iterator*) voiditer );
    --i;
}

PyObject *iiter_value( /* dmmap::iterator*/ void *voiditer ) {
    dmmap::iterator& i = *((dmmap::iterator*) voiditer );
    PyObject *v = (*i).second;
    Py_INCREF(v);
    return v;
}

double iiter_key( /*dmmap::iterator*/ void *voiditer ) {
    dmmap::iterator& i = *((dmmap::iterator*) voiditer );
    return (*i).first;
}

void iiter_set( /*dmmap::iterator*/ void *voiditer, PyObject *value ) {
    dmmap::iterator& i = *((dmmap::iterator*) voiditer );
    Py_DECREF((*i).second);
    (*i).second = value;
    Py_INCREF(value);
}

/**
 * same as mmap_iiter_update_key_iiter except this does not allocate and 
 * return an iterator when reordering occurs.
 * 
 * WARNING!! The passed iterator MUST be assumed to be invalid upon return.
 */
void mmap_iiter_update_key( /*dmmap*/ void *voidmmap, 
                          /*dmmap::iterator*/ void *voiditer, double key ) {
    dmmap::iterator& i = *((dmmap::iterator*) voiditer );
    dmmap& m = *((dmmap*) voidmmap);
    double lower, higher;
    dmmap::iterator hint = m.begin();

    // if no change then return.
    if ( key == (*i).first ) return;

    // if key changed so little that reordering does not change then 
    // just forcibly set the key. (HERE: Is forcibly setting the key 
    // dangerous?  It might upset some implementations of STL. Hmmmm....)
    if ( i != m.begin() ) {
	dmmap::iterator before = i;
        --before;
        hint = before;
        lower = (*before).first;
    }
    else lower = (*i).first - 1;  // arbitrarily lower.

    dmmap::iterator after = i;
    ++after;
    if ( after != m.end() ) {
        hint = after;
        higher = (*after).first;
    }
    else higher = (*i).first + 1;  // arbitrarily higher.

    // if ordering didn't change...
    if ( lower <= key && key <= higher )
        ((pair<double,PyObject*>&) (*i)).first = key;

    // else key changed enough that reordering is necessary.
    else {
        double oldkey = (*i).first;
        PyObject *v = (*i).second;
	dmmap::iterator j = m.insert(hint,dpair(key,v));
        if ((*j).second != v )
            throw KeyError();
        m.erase(i);
    }
}

/**
 * Updates the key pointed to by voiditer and updates the ordering.  If
 * the ordering changes, this returns an iterator to the new location; 
 * otherwise, this returns the same iterator that was passed.  
 * 
 * WARNING!!!! If the ordering changes than the passed iterator is NO
 * LONGER VALID and should be deallocated .
 *
 * If the key is equal to an existing key with a different value then
 * this throws a KeyError exception without changing the mmap.
 */
/*dmmap::iterator*/ void *mmap_iiter_update_key_iiter( 
                               /*dmmap*/ void *voidmmap, 
                               /*dmmap::iterator*/ void *voiditer, double key )
{
    dmmap::iterator& i = *((dmmap::iterator*) voiditer );
    dmmap& m = *((dmmap*) voidmmap);
    double lower, higher;
    dmmap::iterator hint = m.begin();

    // if no change then return.
    if ( key == (*i).first ) return voiditer;

    // if key changed so little that reordering does not change then 
    // just forcibly set the key. (HERE: Is forcibly setting the key 
    // dangerous?  It might upset some implementations of STL. Hmmmm....)
    if ( i != m.begin() ) {
	dmmap::iterator before = i;
        --before;
        hint = before;
        lower = (*before).first;
    }
    else lower = (*i).first - 1;  // arbitrarily lower.

    if ( lower < key ) {
        dmmap::iterator after = i;
        ++after;
        if ( after != m.end() ) {
            hint = after;
            higher = (*after).first;
        }
        else higher = (*i).first + 1;  // arbitrarily higher.

        // if ordering didn't change...
        if ( key < higher ) {
            ((pair<double,PyObject*>&) (*i)).first = key;
            return voiditer;
	}
    }

    // else key changed enough that reordering is necessary.
    double oldkey = (*i).first;
    PyObject *v = (*i).second;
    dmmap::iterator *jp = new dmmap::iterator(); //alloc before changing mmap
    if ( jp == NULL ) 
        throw MemoryError(); 
    dmmap::iterator j = m.insert(hint,dpair(key,v));
    if ((*j).second != v )
        throw KeyError();
    m.erase(i);
    *jp = j;
    return jp;
}


/**
 * Returns iterator pointing to the smallest key equal to or greater than the 
 * passed key.
 */
/*dmmap::iterator*/ void *mmap_lower_bound( /*dmmap*/ void *voidmmap, 
                                            double key ) 
{
    dmmap& m = *((dmmap*) voidmmap);
    dmmap::iterator *i = new dmmap::iterator(m.lower_bound(key));
    if ( i == NULL ) throw MemoryError();
    return i;
}

/**
 * Returns iterator pointing to one after the largest key equal to or greater
 * than the passed key.  This is in keeping with expressing ranges
 * as [x,y) where x <= y.
 */
/*dmmap::iterator*/ void *mmap_upper_bound( /*dmmap*/ void *voidmmap, 
                                            double key ) 
{
    dmmap& m = *((dmmap*) voidmmap);
    dmmap::iterator *i = new dmmap::iterator(m.upper_bound(key));
    if ( i == NULL ) throw MemoryError();
    return i;
}



