reset
set termoption dash

set style line 80 lt -1 lc rgb "#808080"
set style line 81 lt 0  # dashed
set style line 81 lt rgb "#808080"
set grid back linestyle 81
set border 3 back linestyle 80

set style data histogram
#set style histogram cluster gap 1
set style histogram errorbars gap 1 lw 1
set style fill solid border -1
set boxwidth 0.9

set output 'barplot.pdf'
set terminal pdfcairo size 4.7, 2 font "Gill Sans, 8" linewidth 2 rounded fontscale 1

set multiplot
unset xtics
set ytics font ',6' offset 0.5
set xtics font ',6'

unset key

top=0.85
bot=0.25

set ylabel "time (ms)" offset 2.2,0

# ovs plot
set tmargin at screen top
set bmargin at screen bot
set lmargin at screen 0.10
set rmargin at screen 0.30
set auto x
set yrange[0:*]
set ytics 10
unset xlabel
#set xlabel "path length (hops)" font "Gill Sans, 8" offset 1,0.4
set label "fattree,8" font "Gill Sans, 8" at graph 0.18,1.125
plot 'bar_ovs.dat' using 2:3:4:xtic(1) title col lc rgb "#92c5de", \
     '' using 5:6:7:xtic(1) title col lc rgb "#ca0020"


unset ylabel
unset xlabel
unset label

# rpc plot
set tmargin at screen top
set bmargin at screen bot
set lmargin at screen 0.33
set rmargin at screen 0.53
set auto x
set yrange[0:6]
set ytics 1
set label "fattree,16" font "Gill Sans, 8" at graph 0.35,1.125
plot 'bar_rpc.dat' using 2:3:4:xtic(1) title col lc rgb "#92c5de", \
     '' using 5:6:7:xtic(1) title col lc rgb "#ca0020"

unset label

# rpc plot
set tmargin at screen top
set bmargin at screen bot
set lmargin at screen 0.56
set rmargin at screen 0.76
set auto x
set yrange[0:6]
set ytics 1
set label "fattree,32" font "Gill Sans, 8" at graph -0.2,1.125
plot 'bar_mqunopt.dat' using 2:3:4:xtic(1) title col lc rgb "#92c5de", \
     '' using 5:6:7:xtic(1) title col lc rgb "#ca0020"

unset label

# mq plot
set tmargin at screen top 
set bmargin at screen bot
set lmargin at screen 0.79
set rmargin at screen 0.99
set auto x
set yrange[0:6]
set ytics 1
set label "fattree,64" font "Gill Sans, 8" at graph 0.39,1.125
plot 'bar_mq.dat' using 2:3:4:xtic(1) title col lc rgb "#92c5de", \
     '' using 5:6:7:xtic(1) title col lc rgb "#ca0020"


# key
set tmargin at screen 0.13
set bmargin at screen 0
set lmargin at screen 0.0
set rmargin at screen 1

unset label
unset ytics
unset tics
unset xlabel
unset ylabel
set border 0

set key horiz
set key samplen 1 spacing 0.75 font "Gill Sans,8" maxcols 2
set yrange [0:1]
set style data histograms

plot NaN t "baseline" w boxes lc rgb "#92c5de", \
     NaN t "orchestration" w boxes lc rgb "#ca0020", \
     NaN t "pytrigger" w boxes lc rgv "#f4a583", \
     NaN t "column cnst" w boxes lc rgv "#0571b0"
