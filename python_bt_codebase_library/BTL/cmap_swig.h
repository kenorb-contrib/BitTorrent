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
#ifndef CMAP_H
#define CMAP_H
#include <stdexcept>

// map out_of_range error to IndexError.
class KeyError {};
class MemoryError {};

// From here to the #endif is added to deal with potential problems on some
// swig versions.  In my environment, these declarations appear in the
// generated cmap_swig_wrap.cxx file.  --Dave
#include "Python.h"
extern void *map_constructor();
extern void map_delete(void *voidmap);
extern void *map_begin(void *voidmap);
extern void *map_end(void *voidmap);
extern bool map_iter_at_end(void *voidmap, void *iter);
extern bool map_iter_at_begin(void *voidmap, void *iter);
extern int map_size(void *voidmap);

extern PyObject *map_find(void *voidmap, double k);
extern void *map_find_iter(void *voidmap, double k);
extern void map_set(void *voidmap, double k, PyObject *v);
extern void map_insert(void *voidmap, double k, PyObject *v);
extern void *map_insert_iter(void *voidmap, double k, PyObject *v);
extern void map_erase(void *voidmap, double key);
extern void map_iter_erase(void *voidmap, void *voiditer);
extern void map_append(void *voidmap, double k, PyObject *v);
extern void *map_append_iter(void *voidmap, double k, PyObject *v);
extern void iter_delete(void *voiditer);
extern int iter_cmp(void *voidmap, void *viter1, void *viter2);
extern void *iter_copy(void *voiditer);
extern void iter_assign(void *voiditer1, void *voiditer2);
extern void iter_incr(void *voiditer);
extern void iter_decr(void *voiditer);
extern PyObject *iter_value(void *voiditer);
extern double iter_key(void *voiditer);
extern void iter_set(void *voiditer, PyObject *value);
extern void map_iter_update_key(void *voidmap, void *voiditer, double
key);
extern void *map_iter_update_key_iter(void *voidmap, void *voiditer,
double key);
extern void *map_lower_bound(void *voidmap, double key);
extern void *map_upper_bound(void *voidmap, double key);

// DEBUG
//extern void *map_constructor_double();
//extern void *map_find_iter_double(void *voidmap, double k);
//extern void map_insert_double(void *voidmap, double k, double v);
//extern void map_iter_erase_double(void *voidmap, void *voiditer);
//extern void iter_delete_double(void *voiditer);
// END DEBUG
#endif


