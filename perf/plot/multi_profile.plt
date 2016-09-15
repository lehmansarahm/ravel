reset
set termoption dash
set style line 80 lt -1 lc rgb "#808080"
set style line 81 lt 0  # dashed
set style line 81 lt rgb "#808080"
set grid back linestyle 81
set border 3 back linestyle 80

set style data histograms
set style histogram rowstacked
set boxwidth .9 relative
set style fill solid 0.85 border
# set style fill solid 1.0 # border -1
set datafile separator "|"

set output "plot/multi_profile.pdf"
set terminal pdfcairo size 10, 1.8 font "Gill Sans,9" linewidth 2 rounded fontscale 1

unset xtics
unset xlabel
set ytics nomirror

unset key

set tmargin at screen 0.85
set lmargin at screen 0.03
set rmargin at screen .13
set bmargin at screen 0.15

set multiplot layout 2,9

set tmargin at screen 0.9
set bmargin at screen 0.67

# plot 1
set yrange [0:5]
set ytics 2 font ',6' offset .5
set ylabel "deletion" offset 2 # font ',8'

set label 1 "fattree, 16" at graph 0,1.2 # font ',8'
plot 'plot/dat/profile_fattree_16_rtd.dat' using 2 lc rgb "#0571b0", '' using 4 lc rgb "#f4a582"
set format y ''; unset ylabel

# plot 2
set lmargin at screen 0.13
set rmargin at screen .23

set label 1 "fattree, 32" at graph 0,1.2 # font ',8'
plot 'plot/dat/profile_fattree_32_rtd.dat' using 2 lc rgb "#0571b0", '' using 4 lc rgb "#f4a582"

# plot 3
set lmargin at screen 0.23
set rmargin at screen .33

set label 1 'fattree, 64' at graph 0,1.2 # font ',8'
plot 'plot/dat/profile_fattree_64_rtd.dat' using 2 lc rgb "#0571b0", '' using 4 lc rgb "#f4a582"

# plot 4
set lmargin at screen 0.36
set rmargin at screen .46

set yrange [0:5]
set ytics font ',6' offset .5
set format y "%g"

set label 1 'AS2914,30' at graph 0,1.2
plot "plot/dat/profile_isp_2914_30_rtd.dat" using 2 lc rgb "#0571b0", '' using 4 lc rgb "#f4a582"

set format y ''; unset ylabel

# plot 5

set lmargin at screen 0.46
set rmargin at screen .56

set label 1 'AS2914,300' at graph 0,1.2
plot "plot/dat/profile_isp_2914_300_rtd.dat" using 2 lc rgb "#0571b0", '' using 4 lc rgb "#f4a582"

# plot 6

set lmargin at screen .56
set rmargin at screen 0.66
set label 1 'AS2914,3000' at graph 0,1.2
plot "plot/dat/profile_isp_2914_3000_rtd.dat" using 2 lc rgb "#0571b0", '' using 4 lc rgb "#f4a582"

# plot 7
set yrange [0:5]
set format y "%g"
set ytics font ',6' offset .5

set lmargin at screen 0.69
set rmargin at screen .79
set label 1 'AS 4755' at graph 0,1.2
plot "plot/dat/profile_isp_4755_rtd.dat" using 2 lc rgb "#0571b0", '' using 4 lc rgb "#f4a582"

set format y ''; unset ylabel

# plot 8

set lmargin at screen 0.79
set rmargin at screen .89
set label 1 'AS 3356' at graph 0,1.2
plot "plot/dat/profile_isp_3356_rtd.dat" using 2 lc rgb "#0571b0", '' using 4 lc rgb "#f4a582"


# plot 9

set lmargin at screen 0.89
set rmargin at screen .99
set label 1 "AS 7018" at graph 0,1.2
plot "plot/dat/profile_isp_7018_rtd.dat" using 2 lc rgb "#0571b0", '' using 4 lc rgb "#f4a582"

# plot key
# set tmargin at screen 0.18
# set lmargin at screen 0.0
# set rmargin at screen 1
# set bmargin at screen 0.05

# unset label
# unset ytics
# set border 0
# unset tics
# unset xlabel
# unset ylabel

# set key horiz
# set key samplen 1 spacing 1 font "Gill Sans,9"

# set yrange [0:1]
# set style data histograms
# plot 2 t 'lookup ports (lk)' lw 6 lc rgb "#0571b0", \
#      2 t 'write to table (wt)' lw 6 lc rgb "#f4a582", \
#      2 t 'trigger and/or rule (tr)' lw 6 lc rgb "#ca0020"

# set lmargin at screen 0.56
# set rmargin at screen .78

# row 2

set grid back linestyle 81
set border 3 back linestyle 80
set tmargin at screen 0.6
set bmargin at screen 0.13

# set ytics nomirror
# set ytics .2 font ',6' offset .5
# set yrange [0:1]
# set format y '%g'

# plot 1

set lmargin at screen 0.03
set rmargin at screen .13

unset label
set yrange [0:30]
set ylabel "insertion" offset 2

unset xtics
set ytics nomirror
set ytics 5 font ',6' offset .5
set format y "%g"

unset key

# set label 1 "fattree, 16" at graph 0,1.1
plot 'plot/dat/profile_fattree_16_rti.dat' using 2 lc rgb "#92c5de", '' using 4 lc rgb "#0571b0", '' using 6 lc rgb "#f4a582"

set format y ''; unset ylabel

# plot 2
set lmargin at screen 0.13
set rmargin at screen .23

unset ylabel
set ytics 5 font ',6' offset .5

# set label 1 "fattree, 32" at graph 0,1.1
plot 'plot/dat/profile_fattree_32_rti.dat' using 2 lc rgb "#92c5de", '' using 4 lc rgb "#0571b0", '' using 6 lc rgb "#f4a582"


# plot 3
set lmargin at screen 0.23
set rmargin at screen .33

set ytics 5 font ',6' offset .5

# set label 1 'fattree, 64' at graph 0,1.1
plot 'plot/dat/profile_fattree_64_rti.dat' using 2 lc rgb "#92c5de", '' using 4 lc rgb "#0571b0", '' using 6 lc rgb "#f4a582"

# plot 4
set lmargin at screen 0.36
set rmargin at screen .46

set yrange [0:10]
set ytics 2 font ',6' offset .5
set format y "%g"

# set label 1 'AS2914,30' at graph 0,1.1
plot "plot/dat/profile_isp_2914_30_rti.dat" using 2 lc rgb "#92c5de", '' using 4 lc rgb "#0571b0", '' using 6 lc rgb "#f4a582"

set format y ''; unset ylabel

# plot 5

set lmargin at screen 0.46
set rmargin at screen .56

# set label 1 'AS2914,300' at graph 0,1.1
plot "plot/dat/profile_isp_2914_300_rti.dat" using 2 lc rgb "#92c5de", '' using 4 lc rgb "#0571b0", '' using 6 lc rgb "#f4a582"

# plot 6

set lmargin at screen .56
set rmargin at screen 0.66
# set label 1 'AS2914,3000' at graph 0,1.1
plot "plot/dat/profile_isp_2914_3000_rti.dat" using 2 lc rgb "#92c5de", '' using 4 lc rgb "#0571b0", '' using 6 lc rgb "#f4a582"

# plot 7
set yrange [0:10]
set format y "%g"
set ytics 2 font ',6' offset .5

set lmargin at screen 0.69
set rmargin at screen .79
# set label 1 'AS 4755' at graph 0,1.1 # font ',8'
plot "plot/dat/profile_isp_4755_rti.dat" using 2 lc rgb "#92c5de", '' using 4 lc rgb "#0571b0", '' using 6 lc rgb "#f4a582"

set format y ''; unset ylabel

# plot 8

set lmargin at screen 0.79
set rmargin at screen .89
# set label 1 'AS 3356' at graph 0,1.1 # font ',8'
plot "plot/dat/profile_isp_3356_rti.dat" using 2 lc rgb "#92c5de", '' using 4 lc rgb "#0571b0", '' using 6 lc rgb "#f4a582"


# plot 9

set lmargin at screen 0.89
set rmargin at screen .99
# set label 1 "AS 7018" at graph 0,1.1 # font ',8'
plot "plot/dat/profile_isp_7018_rti.dat" using 2 lc rgb "#92c5de", '' using 4 lc rgb "#0571b0", '' using 6 lc rgb "#f4a582"

# plot key
set lmargin at screen 0.0
set rmargin at screen 1

set tmargin at screen 0.17
set bmargin at screen 0.0

unset label
unset ytics
set border 0
unset tics
unset xlabel
unset ylabel

set key horiz
set key samplen 1 spacing 1 font "Gill Sans,9"

set yrange [0:1]
set style data histograms
#plot 2 t 'pgr_routing (rt)' lw 6 lc rgb "#92c5de", \
#     2 t 'lookup ports (lk)' lw 6 lc rgb "#0571b0", \
#     2 t 'write to table (wt)' lw 6 lc rgb "#f4a582", \
#     2 t 'trigger and/or rule (tr)' lw 6 lc rgb "#ca0020"

