
set output "cross_wo_dict_vs_n.eps"
set terminal postscript eps
set title "cross-index search time versus n"
set yrange [0:]

#    "list_5000_searches_vs_n.txt", \
#    "map_5000_searches_vs_n.txt", \
#    "fast_map_5000_searches_vs_n.txt", \

plot "cindexedmap_5000_cross_index_searches_vs_n.txt", \
     "pmap_5000_cross_index_searches_vs_n.txt"

