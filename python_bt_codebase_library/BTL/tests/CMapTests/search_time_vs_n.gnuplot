

set title "search time versus n"
set yrange [0:]

set output "search_time_vs_n.eps"
set terminal postscript eps

#     "list_5000_searches_vs_n.txt", \
#    "map_5000_searches_vs_n.txt", \
#    "fast_map_5000_searches_vs_n.txt", \
#

plot "dict_5000_searches_vs_n.txt", \
     "cmap_5000_searches_vs_n.txt", \
     "cindexedmap_5000_searches_vs_n.txt", \
     "pmap_5000_searches_vs_n.txt"


#pause -1


