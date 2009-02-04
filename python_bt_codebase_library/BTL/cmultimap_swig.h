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
#ifndef CMULTIMAP_H
#define CMULTIMAP_H

// This whole header file should not be necesary. In my environment,
// swig includes these declarations in the generated cmultimap_swig_wrap.cxx file.
// --Dave
#include "Python.h"

extern /*dmmap*/ void *mmap_constructor();

extern /*dmmap::iterator*/ void *mmap_begin( void *voidmmap );

extern /*dmmap::iterator*/ void *mmap_end( void *voidmmap );

extern bool mmap_iiter_at_end( void *voidmmap, void *voiditer );

extern bool mmap_iiter_at_begin( void *voidmmap, void *voiditer );

extern int mmap_size( void *voidmmap );

extern PyObject *mmap_find( void *voidmmap, double k );

extern /*dmmap::iterator*/ void *mmap_find_iiter( void *voidmmap, double k );


extern /*dmmap::iterator*/ void *mmap_insert_iiter( /*dmmap*/ void *voidmmap, 
                                                 double k, PyObject *v );

extern void mmap_delete( void *voidmmap );

// Does not apply to multimaps.
//extern void mmap_set( /*dmmap*/ void *voidmmap, double k, PyObject *v );

// dangerous.  Use mmap_iter_erase and invalidate iterators pointing to each
// erase item.
//extern void mmap_erase( void *voidmmap, double k );

extern void mmap_iiter_erase( /*dmmap*/ void *voidmmap, 
                            /*dmmap::iterator*/ void *voiditer );

extern void iiter_assign( /*dmmap::iterator*/ void *voiditer1,
                          /*dmmap::iterator*/ void *voiditer2 );

extern void iiter_delete( /*dmmap::iterator*/ void *voiditer );

extern int iiter_cmp( /*dmmap*/ void *voidmmap, 
                     /*dmmap::iterator*/ void *voiditer1, 
                     /*dmmap::iterator*/ void *voiditer2 );


extern void iiter_incr( /* dmmap::iterator*/ void *voiditer );

extern void iiter_decr( /*dmmap::iterator*/ void *voiditer );

extern PyObject *iiter_value( /* dmmap::iterator*/ void *voiditer );

extern double iiter_key( /*dmmap::iterator*/ void *voiditer );

extern void iiter_set( /*dmmap::iterator*/ void *voiditer, PyObject *value );

extern /*dmmap::iterator*/ void *iiter_copy( /*dmmap::iterator*/ void *voiditer );

extern /*dmmap::iterator*/ void *mmap_append_iiter( /*dmmap*/ void *voidmmap, 
                                                 double k, PyObject *v );

extern /*dmmap::iterator*/ void *mmap_lower_bound( /*dmmap*/ void *voidmmap, 
                                                 double key );

extern /*dmmap::iterator*/ void *mmap_upper_bound( /*dmmap*/ void *voidmmap, 
                                                 double key );
extern void mmap_insert( /*dmmap*/ void *voidmmap, double k, PyObject *v );


extern void mmap_append( /*dmmap*/ void *voidmmap, double k, PyObject *v );

extern void mmap_iiter_update_key( /*dmmap*/ void *voidmmap, 
                                  /*dmmap::iterator*/ void *voiditer, double k);

extern /*dmmap::iterator*/ void *mmap_iiter_update_key_iiter( 
                                 /*dmmap*/ void *voidmmap, 
                                 /*dmmap::iterator*/ void *voiditer, double k );
#endif
