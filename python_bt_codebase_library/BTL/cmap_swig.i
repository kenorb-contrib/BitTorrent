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

//
//
// NOTE: This is NOT a generated file!!!!!! NOT NOT NOT NOT.  Do not delete
// the .i file and expect make to work.
//
//

%{
#include "cmap_swig.h"
//#include <iostream>  // DEBUG
//using namespace std; // DEBUG
%}


%exception {
  try {
     $action    
  }
  catch (MemoryError& e) {
    PyErr_SetString(PyExc_MemoryError,"Not enough memory");
    return NULL; // wrapper returns PyObject* even when C++ return is void.
  }
  catch (KeyError& e ) {
    PyErr_SetString(PyExc_KeyError,"Key not found." );
    return NULL; // wrapper returns PyObject* even when C++ return is void.
  }
}

extern /*dmap*/ void *map_constructor();

extern /*dmap::iterator*/ void *map_begin( void *voidmap );

extern /*dmap::iterator*/ void *map_end( void *voidmap );

extern bool map_iter_at_end( void *voidmap, void *voiditer );

extern bool map_iter_at_begin( void *voidmap, void *voiditer );

extern int map_size( void *voidmap );

extern PyObject *map_find( void *voidmap, double k );

extern /*dmap::iterator*/ void *map_find_iter( void *voidmap, double k );


extern /*dmap::iterator*/ void *map_insert_iter( /*dmap*/ void *voidmap, 
                                                 double k, PyObject *v );

extern void map_delete( void *voidmap );

extern void map_set( /*dmap*/ void *voidmap, double k, PyObject *v );

extern void map_erase( void *voidmap, double k );

extern void map_iter_erase( /*dmap*/ void *voidmap, 
                            /*dmap::iterator*/ void *voiditer );

extern void iter_delete( /*dmap::iterator*/ void *voiditer );

extern int iter_cmp( /*dmap*/ void *voidmap, 
                     /*dmap::iterator*/ void *voiditer1, 
                     /*dmap::iterator*/ void *voiditer2 );

extern void iter_assign( /* dmap::iterator*/ void *voiditer1,
                         /* dmap::iterator*/ void *voiditer2 );

extern void iter_incr( /* dmap::iterator*/ void *voiditer );

extern void iter_decr( /*dmap::iterator*/ void *voiditer );

extern PyObject *iter_value( /* dmap::iterator*/ void *voiditer );

extern double iter_key( /*dmap::iterator*/ void *voiditer );

extern void iter_set( /*dmap::iterator*/ void *voiditer, PyObject *value );

extern /*dmap::iterator*/ void *iter_copy( /*dmap::iterator*/ void *voiditer );

extern /*dmap::iterator*/ void *map_append_iter( /*dmap*/ void *voidmap, 
                                                 double k, PyObject *v );

extern /*dmap::iterator*/ void *map_lower_bound( /*dmap*/ void *voidmap, 
                                                 double key );

extern /*dmap::iterator*/ void *map_upper_bound( /*dmap*/ void *voidmap, 
                                                 double key );

%exception;

%exception {
  try {
     $action    
  }
  catch (MemoryError& e) {
    PyErr_SetString(PyExc_MemoryError,"Not enough memory");
    return NULL; // wrapper returns PyObject* even when C++ return is void.
  }
  catch (KeyError& e ) {
    PyErr_SetString(PyExc_KeyError,"Key is already in the map." );
    return NULL; // wrapper returns PyObject* even when C++ return is void.
  }
}

extern void map_insert( /*dmap*/ void *voidmap, double k, PyObject *v );


extern void map_append( /*dmap*/ void *voidmap, double k, PyObject *v );

extern void map_iter_update_key( /*dmap*/ void *voidmap, 
                                  /*dmap::iterator*/ void *voiditer, double k);

extern /*dmap::iterator*/ void *map_iter_update_key_iter( 
                                 /*dmap*/ void *voidmap, 
                                 /*dmap::iterator*/ void *voiditer, double k );


// DEBUG
//extern void *map_constructor_double();
//extern /*ddmap::iterator*/ void *map_find_iter_double(void *voidmap, double k);
//extern void map_insert_double(void *voidmap, double k, double v);
//extern void map_iter_erase_double(void *voidmap, void *voiditer);
//extern void iter_delete_double(void *voiditer);
//extern int map_size_double( void *voidmap );

%exception;

