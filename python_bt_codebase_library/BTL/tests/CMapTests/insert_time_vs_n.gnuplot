
set terminal postscript eps
set output "insert_time_vs_n.eps"

set yrange [0:]
set title "time for n inserts"

plot "dict_random_inserts_vs_n.txt", \
     "cmap_random_inserts_vs_n.txt", \
     "pmap_random_inserts_vs_n.txt", \
     "cindexedmap_random_inserts_vs_n.txt"

#pause -1


