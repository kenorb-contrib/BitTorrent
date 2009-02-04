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
#include <list>
#include "cmap_swig.h"
#include <iostream>

using namespace std;

typedef map<double, PyObject*> dmap;
typedef map<double, double> ddmap;  //DEBUG
typedef pair<const double, PyObject*> dpair;
typedef pair<const double, double> ddpair; //DEBUG


/*dmap*/ void *map_constructor() {
  return new dmap();
}

//void *map_constructor_double() {
//    return new ddmap();
//}

void map_delete( void *voidmap ) {
    dmap& m = *((dmap*) voidmap);
    dmap *mp = (dmap*) voidmap;
  
    // decrement the referencde to every object in the map.
    dmap::iterator i;
    for ( i = m.begin(); i != m.end(); ++i ) 
        Py_DECREF((*i).second);
  
    delete mp;
}


/*dmap::iterator*/ void *map_begin( void *voidmap ) {
    dmap& m = *((dmap*) voidmap);
    dmap::iterator *i = new dmap::iterator(m.begin());
    if ( i == NULL ) throw MemoryError();
    return i;
}

/*dmap::iterator*/ void *map_end( void *voidmap ) {
    dmap& m = *((dmap*) voidmap);
    dmap::iterator *i = new dmap::iterator(m.end());
    if ( i == NULL ) throw MemoryError();
    return i;
}

bool map_iter_at_end( void *voidmap, void *iter ) {
    dmap& m = *((dmap*) voidmap);
    dmap::iterator& i = *((dmap::iterator*) iter );
    return i == m.end();
}

bool map_iter_at_begin( void *voidmap, void *iter ) {
    dmap& m = *((dmap*) voidmap);
    dmap::iterator& i = *((dmap::iterator*) iter );
    return i == m.begin();
}


int map_size( void *voidmap ) {
    dmap& m = *((dmap*) voidmap);
    return m.size();   
}

int map_size_double( void *voidmap ) {
    ddmap& m = *((ddmap*) voidmap);
    return m.size();    
}


PyObject *map_find( void *voidmap, double k ) {
    dmap& m = *((dmap*) voidmap);
    dmap::iterator i = m.find(k);

    if ( i == m.end()) throw KeyError();
    PyObject *v = (PyObject*) ((*i).second);
    Py_INCREF(v);
    return v;
}

/*dmap::iterator*/ void *map_find_iter( void *voidmap, double k ) {
    dmap& m = *((dmap*) voidmap);
    dmap::iterator *i = new dmap::iterator(m.find(k));
    if ( i == NULL ) throw MemoryError();
    return i;
}

/*ddmap::iterator*/ void *map_find_iter_double( void *voidmap, double k ) {
    ddmap& m = *((ddmap*) voidmap);
    ddmap::iterator *i = new ddmap::iterator(m.find(k));
    if ( i == NULL ) throw MemoryError();
    return i;
}

void map_set( /*dmap*/ void *voidmap, double k, PyObject *v ) {
    dmap& m = *((dmap*) voidmap);
    pair<dmap::iterator,bool> p = m.insert(dpair(k,v));
    dmap::iterator i = p.first;
    if ( p.second == false ) {  // if failed to insert because already in map.
	Py_DECREF( (*i).second ); // release reference to old value.
        (*i).second = v;          // force entry to reference new value.
    }
    Py_INCREF(v);
}


/**
 * inserts the passed key-value pair into the map.  
 *
 * Raises a KeyError exception if the key is already in the map and has
 * a different value than passed.
 */
void map_insert( /*dmap*/ void *voidmap, double k, PyObject *v ) {
    dmap& m = *((dmap*) voidmap);
    pair<dmap::iterator,bool> p = m.insert(dpair(k,v));
    dmap::iterator i = p.first;
    if ( (*i).second != v ) throw KeyError();
    Py_INCREF(v);  // Is this causing a memory leak?
}

//void map_insert_double( /*dmap*/ void *voidmap, double k, double v ) {
//    ddmap& m = *((ddmap*) voidmap);
//    pair<ddmap::iterator,bool> p = m.insert(ddpair(k,v));
//    ddmap::iterator i = p.first;
//    if ( (*i).second != v ) throw KeyError();
//}

/**
 * inserts the passed key-value pair into the map.
 * 
 * If the key is already in the map, returns without modifying the map
 * and returns an iterator pointing to the existing key-value pair.  This
 * function does not throw a KeyError.
 */
/*dmap::iterator*/ void *map_insert_iter( /*dmap*/ void *voidmap, double k, 
                                          PyObject *v ) 
{
    dmap& m = *((dmap*) voidmap);
    dmap::iterator *i = new dmap::iterator(); // malloc before modifying map.
    if ( i == NULL ) throw MemoryError();

    pair<dmap::iterator,bool> p = m.insert(dpair(k,v));
    if ( p.second ) Py_INCREF(v);
    *i = p.first;

    return i;
}

void map_erase( void *voidmap, double key ) {
    dmap& m = *((dmap*) voidmap);
    dmap::iterator i = m.find(key);
    if ( i == m.end() ) throw KeyError();
    PyObject *v = (*i).second;
    m.erase(i);
    Py_DECREF(v);
}

void map_iter_erase( /*dmap*/ void *voidmap, 
                     /*dmap::iterator*/ void *voiditer ) 
{
    dmap& m = *((dmap*) voidmap);
    dmap::iterator& i = *((dmap::iterator*) voiditer );
    PyObject *v = (*i).second;
    m.erase(i);
    Py_DECREF(v);  // this stops the memory leak.
}

//void map_iter_erase_double( /*ddmap*/ void *voidmap,
//                            /*ddmap::iterator*/ void *voiditer ) 
//{
//    ddmap& m = *((ddmap*) voidmap);
//    ddmap::iterator& i = *((ddmap::iterator*) voiditer );
//    m.erase(i);
//}

/**
 * Inserts the object with the hint that it should be appended to the end.
 * 
 * Takes O(log n) time.
 *
 * Raises KeyError if the key with a different value is already in the map.
 */
void map_append( /*dmap*/ void *voidmap, double k, PyObject *v ) {
    dmap& m = *((dmap*) voidmap);
    dmap::iterator i = m.insert(m.end(),dpair(k,v));
    if ( (*i).second != v ) throw KeyError();
    Py_INCREF(v);
}

/**
 * Inserts the object with the hint that it should be appended to the end.
 * 
 * Takes O(log n) time.
 *
 * Differs from map_append in that this returns an iterator pointing
 * to the location where the key-value pair was inserted or where it should
 * be inserted.  This does not raise a KeyError.  map_append also avoids
 * the overhead of dynamically allocating an iterator to return.
 */
/*dmap::iterator*/ void *map_append_iter( /*dmap*/ void *voidmap, double k, 
                                          PyObject *v ) 
{
    dmap& m = *((dmap*) voidmap);
    dmap::iterator *ip = new dmap::iterator(); //alloc before changing the map.
    if ( ip == NULL ) throw MemoryError(); 

    dmap::iterator i = m.insert(m.end(), dpair(k,v));
    if ( (*i).first == k ) Py_INCREF(v);
    *ip = i;
    return ip;
}

void iter_delete( /*dmap::iterator*/ void *voiditer ) {
    dmap::iterator *i = (dmap::iterator*) voiditer;
    delete i;
}

//void iter_delete_double( /*ddmap::iterator*/ void *voiditer ) {
//    ddmap::iterator *i = (ddmap::iterator*) voiditer;
//    delete i;
//}

int iter_cmp( /*dmap*/ void *voidmap, /*dmap::iterator*/ void *viter1, 
              /*dmap::iterator*/ void *viter2 ) {
    dmap& m = *((dmap*) voidmap);
    dmap::iterator& i1 = *((dmap::iterator*) viter1 );
    dmap::iterator& i2 = *((dmap::iterator*) viter2 );
    if ( i1 == i2 ) return 0;
    if ( i1 == m.end() && i2 != m.end() ) return 1;
    if ( i1 != m.end() && i2 == m.end() ) return -1;
    if ( (*i1).first < (*i2).first ) return -1;
    if ( (*i1).first > (*i2).first ) return 1;
    return 0;
}

void *iter_copy( /*dmap::iterator*/ void *voiditer ) {
    dmap::iterator& i = *((dmap::iterator*) voiditer );
    dmap::iterator *newi = new dmap::iterator(i);
    return newi; 
}

void iter_assign( /*dmap::iterator*/ void *voiditer1,
                  /*dmap::iterator*/ void *voiditer2 ) {
    dmap::iterator& i1 = *((dmap::iterator*) voiditer1 );
    dmap::iterator& i2 = *((dmap::iterator*) voiditer2 );
    i1 = i2;
}

void iter_incr( /*dmap::iterator*/ void *voiditer ) {
    dmap::iterator& i = *((dmap::iterator*) voiditer );
    ++i;
}

void iter_decr( /*dmap::iterator*/ void *voiditer ) {
    dmap::iterator& i = *((dmap::iterator*) voiditer );
    --i;
}

PyObject *iter_value( /* dmap::iterator*/ void *voiditer ) {
    dmap::iterator& i = *((dmap::iterator*) voiditer );
    PyObject *v = (*i).second;
    Py_INCREF(v);
    return v;
}

double iter_key( /*dmap::iterator*/ void *voiditer ) {
    dmap::iterator& i = *((dmap::iterator*) voiditer );
    return (*i).first;
}

void iter_set( /*dmap::iterator*/ void *voiditer, PyObject *value ) {
    dmap::iterator& i = *((dmap::iterator*) voiditer );
    Py_DECREF((*i).second);
    (*i).second = value;
    Py_INCREF(value);
}

/**
 * same as map_iter_update_key_iter except this does not allocate and 
 * return an iterator when reordering occurs.
 * 
 * WARNING!! The passed iterator MUST be assumed to be invalid upon return.
 */
void map_iter_update_key( /*dmap*/ void *voidmap, 
                          /*dmap::iterator*/ void *voiditer, double key ) {
    dmap::iterator& i = *((dmap::iterator*) voiditer );
    dmap& m = *((dmap*) voidmap);
    double lower, higher;
    dmap::iterator hint = m.begin();

    // if no change then return.
    if ( key == (*i).first ) return;

    // if key changed so little that reordering does not change then 
    // just forcibly set the key. (HERE: Is forcibly setting the key 
    // dangerous?  It might upset some implementations of STL. Hmmmm....)
    if ( i != m.begin() ) {
	dmap::iterator before = i;
        --before;
        hint = before;
        lower = (*before).first;
    }
    else lower = (*i).first - 1;  // arbitrarily lower.d

    dmap::iterator after = i;
    ++after;
    if ( after != m.end() ) {
        hint = after;
        higher = (*after).first;
    }
    else higher = (*i).first + 1;  // arbitrarily higher.

    // if ordering didn't change...
    if ( lower < key && key < higher )
        ((pair<double,PyObject*>&) (*i)).first = key;

    // else key changed enough that reordering is necessary.
    else {
        double oldkey = (*i).first;
        PyObject *v = (*i).second;
	dmap::iterator j = m.insert(hint,dpair(key,v));
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
 * this throws a KeyError exception without changing the map.
 */
/*dmap::iterator*/ void *map_iter_update_key_iter( /*dmap*/ void *voidmap, 
                               /*dmap::iterator*/ void *voiditer, double key ) 
{
    dmap::iterator& i = *((dmap::iterator*) voiditer );
    dmap& m = *((dmap*) voidmap);
    double lower, higher;
    dmap::iterator hint = m.begin();

    // if no change then return.
    if ( key == (*i).first ) return voiditer;

    // if key changed so little that reordering does not change then 
    // just forcibly set the key. (HERE: Is forcibly setting the key 
    // dangerous?  It might upset some implementations of STL. Hmmmm....)
    if ( i != m.begin() ) {
	dmap::iterator before = i;
        --before;
        hint = before;
        lower = (*before).first;
    }
    else lower = (*i).first - 1;  // arbitrarily lower.

    if ( lower < key ) {
        dmap::iterator after = i;
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
    dmap::iterator *jp = new dmap::iterator(); //alloc before changing map
    if ( jp == NULL ) 
        throw MemoryError(); 
    dmap::iterator j = m.insert(hint,dpair(key,v));
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
/*dmap::iterator*/ void *map_lower_bound( /*dmap*/ void *voidmap, double key ) 
{
    dmap& m = *((dmap*) voidmap);
    dmap::iterator *i = new dmap::iterator(m.lower_bound(key));
    if ( i == NULL ) throw MemoryError();
    return i;
}

/**
 * Returns iterator pointing to one after the largest key equal to or greater
 * than the passed key.  This is in keeping with expressing ranges
 * as [x,y) where x <= y.
 */
/*dmap::iterator*/ void *map_upper_bound( /*dmap*/ void *voidmap, double key ) 
{
    dmap& m = *((dmap*) voidmap);
    dmap::iterator *i = new dmap::iterator(m.upper_bound(key));
    if ( i == NULL ) throw MemoryError();
    return i;
}



