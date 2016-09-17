reset
set termoption dash

set output "fat_isp.pdf"
set terminal pdfcairo size 5, 2.6 font "Gill Sans,9" linewidth 2 rounded fontscale 1

set style line 80 lt -1 lc rgb "#808080"
set style line 81 lt 0  # dashed
set style line 81 lt rgb "#808080"
set grid back linestyle 81
set border 3 back linestyle 80

set style line 52 lc rgb "#636363" lt -1 lw 5
set style line 54 lc rgb "#cccccc" lt -1 lw 5
set style line 53 lc rgb "#969696" lt -1 lw 5

# red scale
set style line 1 lc rgb "#a50f15" lt -1 lw 5
set style line 2 lc rgb "#de2d26" lt -1 lw 5
set style line 3 lc rgb "#fb6a4a" lt -1 lw 5
set style line 4 lc rgb "#fc9272" lt -1 lw 5
set style line 5 lc rgb "#fcbba1" lt -1 lw 5

# blue scale
set style line 11 lc rgb "#08519c" lt -1 lw 5
set style line 12 lc rgb "#3182bd" lt -1 lw 5
set style line 13 lc rgb "#6baed6" lt -1 lw 5
set style line 14 lc rgb "#9ecae1" lt -1 lw 5
set style line 15 lc rgb "#c6dbef" lt -1 lw 5

# green scale
set style line 21 lc rgb "#006d2c" lt -1 lw 5
set style line 22 lc rgb "#31a354" lt -1 lw 5
set style line 23 lc rgb "#74c476" lt -1 lw 5
set style line 24 lc rgb "#a1d99b" lt -1 lw 5
set style line 25 lc rgb "#c7e9c0" lt -1 lw 5

# orange scale
set style line 31 lc rgb "#a63603" lt -1 lw 3
set style line 32 lc rgb "#e6550d" lt -1 lw 3
set style line 33 lc rgb "#fd8d3c" lt -1 lw 3
set style line 34 lc rgb "#fdae6b" lt -1 lw 3
set style line 35 lc rgb "#fdd0a2" lt -1 lw 3

# pink scale
set style line 41 lc rgb "#54278f" lt -1 lw 5
set style line 42 lc rgb "#756bb1" lt -1 lw 3
set style line 43 lc rgb "#9e9ac8" lt -1 lw 5
set style line 44 lc rgb "#bcbddc" lt -1 lw 3
set style line 45 lc rgb "#dadaeb" lt -1 lw 3

set logscale x
set xtics font ',6'
set ytics nomirror
set ytics .2 font ',6' offset .5
set yrange [0:1]

unset key

set multiplot layout 2,3

set tmargin at screen 0.88
set bmargin at screen 0.58

# row 1
# plot 1

set lmargin at screen .08
set rmargin at screen .28

unset label
set ylabel "(a) CDF" offset 3.5
unset key

set label 1 "AS 4755" at graph 0,1.1
plot "isp_3sizes/dat/acl_rt_fix_violation__per_rule_.dat" using 2:1 title "acl+lb+rt" with lp ls 11,\
     "isp_3sizes/dat/lb_rt_re-balance__per_rule_.dat" using 2:1 t "lb+rt" with lp ls 1,\
     "isp_3sizes/dat/acl_lb_rt_route_ins.dat" using 2:1 t "lb@t+rt" with lp ls 41

set format y ''; unset ylabel

# plot 2
set lmargin at screen 0.32
set rmargin at screen .52

set label 1 "AS 3356" at graph 0,1.1
plot "isp_3sizes/dat/acl_rt_fix_violation__per_rule_.dat" using 4:3 title "acl+lb+rt" with lp ls 11,\
     "isp_3sizes/dat/lb_rt_re-balance__per_rule_.dat" using 4:3 t "lb+rt" with lp ls 1,\
     "isp_3sizes/dat/acl_lb_rt_route_ins.dat" using 4:3 t "lb@t+rt" with lp ls 41


# plot 3
set lmargin at screen 0.56
set rmargin at screen .76

set label 1 "AS 7018" at graph 0,1.1
plot "isp_3sizes/dat/acl_rt_fix_violation__per_rule_.dat" using 6:5 title "acl+lb+rt" with lp ls 11,\
     "isp_3sizes/dat/lb_rt_re-balance__per_rule_.dat" using 6:5 t "lb+rt" with lp ls 1,\
     "isp_3sizes/dat/acl_lb_rt_route_ins.dat" using 6:5 t "lb@t+rt" with lp ls 41

# plot key
set lmargin at screen 0.8
set rmargin at screen 0.99

unset logscale x

unset ytics
set border 0
unset tics

set key vertical
set key samplen .2 spacing .8 font "Gill Sans,9"

set yrange [40:41]
set label 1 " " at graph 0,1.1
plot "isp_3sizes/dat/acl_rt_fix_violation__per_rule_.dat" using 2:1 title "acl+rt" with lp ls 11,\
     "isp_3sizes/dat/lb_rt_re-balance__per_rule_.dat" using 2:1 t "lb+rt" with lp ls 1,\
     "isp_3sizes/dat/acl_lb_rt_route_ins.dat" using 2:1 t "acl+lb+rt" with lp ls 41

# row 2, plot 4

set grid back linestyle 81
set border 3 back linestyle 80
set tmargin at screen 0.4
set bmargin at screen 0.1

set logscale x
set xtics font ',6' offset 0

set ytics nomirror
set ytics .2 font ',6' offset .5
set yrange [0:1]
set format y '%g'

set lmargin at screen .08
set rmargin at screen .28

unset label
set ylabel "(b) CDF" offset 2.5
unset key

set label 1 "fattree k=16" at graph 0,1.1
plot "fattree/dat/rt_route_ins.dat" using 2:1 title "rt" with lp ls 53,\
     "fattree/dat/rt_tenant_route_ins.dat" using 2:1 title "rt@t" with lp ls 52,\
     "fattree/dat/acl_rt_fix_violation__per_rule_.dat" using 2:1 t "acl+rt" with lp ls 13,\
     "fattree/dat/acl_rt_tenant_fix_violation.dat" using 2:1 t "acl@t+rt" with lp ls 11,\
     "fattree/dat/lb_rt_re-balance__per_rule_.dat" using 2:1 t "lb+rt" with lp ls 3,\
     "fattree/dat/_lb_rt__tenant_re-balance.dat" using 2:1 t "lb@t+rt" with lp ls 1,\
     "fattree/dat/_acl_lb_rt__tenant_route_ins.dat" using 2:1 title "(acl+lb)@t+rt" with lp ls 41


set format y ''; unset ylabel

# plot 5
set lmargin at screen 0.32
set rmargin at screen .52

set label 1 "fattree k=32" at graph 0,1.1
plot "fattree/dat/rt_route_ins.dat" using 4:3 title "rt" with lp ls 53,\
     "fattree/dat/rt_tenant_route_ins.dat" using 4:3 title "rt@t" with lp ls 52,\
     "fattree/dat/acl_rt_fix_violation__per_rule_.dat" using 4:3 t "acl+rt" with lp ls 13,\
     "fattree/dat/acl_rt_tenant_fix_violation.dat" using 4:3 t "acl@t+rt" with lp ls 11,\
     "fattree/dat/lb_rt_re-balance__per_rule_.dat" using 4:3 t "lb+rt" with lp ls 3,\
     "fattree/dat/_lb_rt__tenant_re-balance.dat" using 4:3 t "lb@t+rt" with lp ls 1,\
     "fattree/dat/_acl_lb_rt__tenant_route_ins.dat" using 4:3 title "(acl+lb)@t+rt" with lp ls 41


# plot 6
set lmargin at screen 0.56
set rmargin at screen .76

set label 1 "fattree k=64" at graph 0,1.1
plot "fattree/dat/rt_route_ins.dat" using 6:5 title "rt" with lp ls 53,\
     "fattree/dat/rt_tenant_route_ins.dat" using 6:5 title "rt@t" with lp ls 52,\
     "fattree/dat/acl_rt_fix_violation__per_rule_.dat" using 6:5 t "acl+rt" with lp ls 13,\
     "fattree/dat/acl_rt_tenant_fix_violation.dat" using 6:5 t "acl@t+rt" with lp ls 11,\
     "fattree/dat/lb_rt_re-balance__per_rule_.dat" using 6:5 t "lb+rt" with lp ls 3,\
     "fattree/dat/_lb_rt__tenant_re-balance.dat" using 6:5 t "lb@t+rt" with lp ls 1,\
     "fattree/dat/_acl_lb_rt__tenant_route_ins.dat" using 6:5 title "(acl+lb)@t+rt" with lp ls 41

# plot key      # "acl_lb_rt_route_ins.dat" using 6:5 title "rt@t" with lp ls 43,\

set lmargin at screen 0.8
set rmargin at screen 0.99

set tmargin at screen 0.5
set bmargin at screen 0.0

unset logscale x

unset ytics
set border 0
unset tics

set key vertical
set key samplen .2 spacing .8 font "Gill Sans,9"
set key width -2

set yrange [40:41]
set label 1 " " at graph 0,1.2
plot "fattree/dat/rt_route_ins.dat" using 2:1 title "rt" with lp ls 53,\
     "fattree/dat/rt_tenant_route_ins.dat" using 2:1 title "rt@t" with lp ls 52,\
     "fattree/dat/acl_rt_fix_violation__per_rule_.dat" using 2:1 t "acl+rt" with lp ls 13,\
     "fattree/dat/acl_rt_tenant_fix_violation.dat" using 2:1 t "acl@t+rt" with lp ls 11,\
     "fattree/dat/lb_rt_re-balance__per_rule_.dat" using 2:1 t "lb+rt" with lp ls 3,\
     "fattree/dat/_lb_rt__tenant_re-balance.dat" using 2:1 t "lb@t+rt" with lp ls 1,\
     "fattree/dat/_acl_lb_rt__tenant_route_ins.dat" using 2:1 title "(acl+lb)@t+rt" with lp ls 41
