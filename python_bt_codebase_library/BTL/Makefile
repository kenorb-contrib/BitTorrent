# The contents of this file are subject to the Python Software Foundation
# License Version 2.3 (the License).  You may not copy or use this file, in
# either source code or executable form, except in compliance with the License.
# You may obtain a copy of the License at http://www.python.org/license.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

INCLUDES = -I/usr/include/python2.4

#CFLAGS = 
CFLAGS = -fpic 

all: _cmap_swig.so _cmultimap_swig.so #performance_test 

performance_test: tests/graphs.ps

tests/graphs.ps: tests/graphs.tex tests/search_time_vs_n.gnuplot \
		 tests/insert_time_vs_n.gnuplot \
		 tests/cross_index_search_time_vs_n.gnuplot \
		 tests/cross_wo_dict_vs_n.gnuplot \
		 cmap_swig.cxx CMap.py tests/performance_test.py \
		 tests/cindexedmap_5000_cross_index_searches_vs_n.txt \
		 tests/cindexedmap_5000_searches_vs_n.txt \
		 tests/cindexedmap_in_order_inserts_vs_n.txt \
		 tests/cindexedmap_random_inserts_vs_n.txt \
		 tests/cmap_5000_cross_index_searches_vs_n.txt \
		 tests/cmap_5000_searches_vs_n.txt \
		 tests/cmap_in_order_inserts_vs_n.txt \
		 tests/cmap_random_inserts_vs_n.txt \
		 tests/dict_5000_cross_index_searches_vs_n.txt \
		 tests/dict_5000_searches_vs_n.txt \
		 tests/dict_in_order_inserts_vs_n.txt \
		 tests/dict_random_inserts_vs_n.txt \
		 tests/pmap_5000_cross_index_searches_vs_n.txt \
		 tests/pmap_5000_searches_vs_n.txt \
		 tests/pmap_in_order_inserts_vs_n.txt \
		 tests/pmap_random_inserts_vs_n.txt
	cd tests; gnuplot search_time_vs_n.gnuplot
	cd tests; gnuplot insert_time_vs_n.gnuplot
	cd tests; gnuplot cross_index_search_time_vs_n.gnuplot
	cd tests; gnuplot cross_wo_dict_vs_n.gnuplot 
	cd tests; gnuplot in_order_insert_time_vs_n.gnuplot
	cd tests; latex graphs.tex; dvips graphs -o

tests/cindexedmap_5000_cross_index_searches_vs_n.txt \
tests/cindexedmap_5000_searches_vs_n.txt \
tests/cindexedmap_in_order_inserts_vs_n.txt \
tests/cindexedmap_random_inserts_vs_n.txt \
tests/cmap_5000_cross_index_searches_vs_n.txt \
tests/cmap_5000_searches_vs_n.txt \
tests/cmap_in_order_inserts_vs_n.txt \
tests/cmap_random_inserts_vs_n.txt \
tests/dict_5000_cross_index_searches_vs_n.txt \
tests/dict_5000_searches_vs_n.txt \
tests/dict_in_order_inserts_vs_n.txt \
tests/dict_random_inserts_vs_n.txt \
tests/pmap_5000_cross_index_searches_vs_n.txt \
tests/pmap_5000_searches_vs_n.txt \
tests/pmap_in_order_inserts_vs_n.txt \
tests/pmap_random_inserts_vs_n.txt: tests/performance_test.py
	cd tests; python performance_test.py

cmap_swig_wrap.cxx: cmap_swig.o cmap_swig.cxx cmap_swig.i
	swig -c++ -python -module cmap_swig cmap_swig.i

cmap_swig_wrap.o: cmap_swig_wrap.cxx
	g++ -c $(CFLAGS) $(INCLUDES) cmap_swig_wrap.cxx

_cmap_swig.so: cmap_swig.o cmap_swig_wrap.o
	g++ -shared $(INCLUDES) cmap_swig_wrap.o cmap_swig.o -o _cmap_swig.so

cmap_swig.o:  cmap_swig.cxx
	g++ -c $(CFLAGS) $(INCLUDES) cmap_swig.cxx

cmultimap_swig_wrap.o: cmultimap_swig_wrap.cxx
	g++ -c $(CFLAGS) $(INCLUDES) cmultimap_swig_wrap.cxx

cmultimap_swig_wrap.cxx: cmultimap_swig.o cmultimap_swig.cxx cmultimap_swig.i 
	swig -c++ -python -module cmultimap_swig cmultimap_swig.i

_cmultimap_swig.so: cmultimap_swig.o cmultimap_swig_wrap.o
	g++ -shared $(INCLUDES) cmultimap_swig_wrap.o cmultimap_swig.o -o _cmultimap_swig.so

cmultimap_swig.o:  cmultimap_swig.cxx
	g++ -c $(CFLAGS) $(INCLUDES) cmultimap_swig.cxx



