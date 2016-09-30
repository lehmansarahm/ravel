reset
set termoption dash
set style line 80 lt -1 lc rgb "#808080"
set style line 81 lt 0  # dashed
set style line 81 lt rgb "#808080"
set grid back linestyle 81
set border 3 back linestyle 80
set style line 3 lt 1 lc rgb "#a50f15" lw 5 pt 0
set style line 2 lt 1 lc rgb "#fb6a4a" lw 5 pt 0
set style line 1 lt 1 lc rgb "#fcbba1" lw 5 pt 0
set style line 4 lt 1 lc rgb "#8B008B" lw 5 pt 0
set style line 13 lt 1 lc rgb "#08519c" lw 5 pt 0 
set style line 12 lt 1 lc rgb "#6baed6" lw 5 pt 0
set style line 11 lt 1 lc rgb "#c6dbef" lw 5 pt 0
set style line 14 lt 1 lc rgb "#F25900" lw 5 pt 0
set key top left

set logscale x
set xtics font ',6'
set ytics nomirror
set ytics .2 font ',6' offset .5

set output "SOSR16.pdf"
set terminal pdfcairo size 5,1.5 font "Gill Sans,9" linewidth 2 rounded fontscale 1
set yrange [0:1]
set logscale x

set multiplot layout 1,5

# plot query

set lmargin at screen 0.1
set rmargin at screen 0.3
set tmargin at screen .8
unset key
set ylabel "probability" offset 3
set label 1 "(a) query" at graph 0,1.2
plot "max.dat" using 2:1 title "10view" with lp ls 1, '' using 4:3 title "100view" with lp ls 2, '' using 6:5 title "1000view" with lp ls 3, '' using 8:7 title "10table" with lp ls 11, '' using 10:9 title "100table" with lp ls 12, '' using 12:11 title "1000table" with lp ls 13

# plot key
set lmargin at screen 0.31
set rmargin at screen 0.35
set tmargin at screen 0.95
set bmargin at screen 0.0

unset logscale x

unset ytics
set border 0
unset tics

set key vertical
set key samplen .2 spacing .9 font "Gill Sans,9"
set key width -2

set yrange [40:41]
unset xlabel
unset ylabel
set label 1 " " at graph 0,1.2
plot "max.dat" using 2:1 title "10,v" with lp ls 1, '' using 4:3 title "100,v" with lp ls 2, '' using 6:5 title "1000,v" with lp ls 3, '' using 8:7 title "10,o" with lp ls 11, '' using 10:9 title "100,o" with lp ls 12, '' using 12:11 title "1000,o" with lp ls 13


# overhead plots
# plot 1

set grid back linestyle 81
set border 3 back linestyle 80

set yrange [0:1]

set lmargin at screen 0.50
set rmargin at screen 0.65

set tmargin at screen .8
unset bmargin
unset key
set logscale x

set xtics font ',6'
set ytics nomirror
set ytics .2 font ',6' offset .5

# set xlabel "update lbtb"
unset ylabel
# unset ytics
set label 1 "(b)rm" at graph 0,1.2

plot "ovh.dat" using 2:1 title "fattree4del" with lp ls 1, '' using 4:3 title "fattree8del" with lp ls 2, '' using 6:5 title "fattree16del" with lp ls 3, '' using 8:7 title "fattree32del" with lp ls 11, '' using 10:9 title "fattree64del" with lp ls 12, '' using 12:11 title "fattree4ins" with lp ls 13

# plot "ovh1.dat" using 2:1 title "fattree4del" with lp ls 1, '' using 4:3 title "fattree8del" with lp ls 2, '' using 6:5 title "fattree16del" with lp ls 3, '' using 8:7 title "fattree4ins" with lp ls 11, '' using 10:9 title "fattree8ins" with lp ls 12, '' using 12:11 title "fattree16ins" with lp ls 13

# plot 2

unset ylabel
unset ytics
set lmargin at screen 0.7
set rmargin at screen 0.85
set tmargin at screen .8
unset key
# set xlabel "update utm"
set label 1 "(c)lb_tb" at graph 0,1.2
plot "ovh2.dat" using 2:1 title "fattree4del" with lp ls 1, '' using 4:3 title "fattree8del" with lp ls 2, '' using 6:5 title "fattree16del" with lp ls 3, '' using 8:7 title "fattree4ins" with lp ls 11, '' using 10:9 title "fattree8ins" with lp ls 12, '' using 12:11 title "fattree16ins" with lp ls 13


# plot key
set lmargin at screen 0.85
set rmargin at screen 0.99
set tmargin at screen 0.95
set bmargin at screen 0.0

unset logscale x

unset ytics
set border 0
unset tics

set key vertical
set key samplen .2 spacing .9 font "Gill Sans,9"
set key width -2

set yrange [40:41]
unset xlabel
unset ylabel
set label 1 " " at graph 0,1.2
plot "ovh2.dat" using 2:1 title "f16,del" with lp ls 1, '' using 4:3 title "f32,del" with lp ls 2, '' using 6:5 title "f64,del" with lp ls 3, '' using 8:7 title "f16,ins" with lp ls 11, '' using 10:9 title "f32,ins" with lp ls 12, '' using 12:11 title "f64,ins" with lp ls 13
