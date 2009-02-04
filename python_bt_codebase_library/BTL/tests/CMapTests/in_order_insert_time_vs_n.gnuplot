
set output "in_order_insert_time_vs_n.eps"
set terminal postscript eps
set title "in-order insert time versus n"
set yrange [0:]

plot "cindexedmap_in_order_inserts_vs_n.txt", \
     "cmap_in_order_inserts_vs_n.txt", \
     "dict_in_order_inserts_vs_n.txt", \
     "pmap_in_order_inserts_vs_n.txt"

