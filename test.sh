#!/bin/bash

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

mkdir -p riblogs
mkdir -p tmp.riblogs
mkdir -p riblogs/fattree4 riblogs/fattree8 riblogs/fattree16 riblogs/fattree32 riblogs/fattree64

# if .out files exists
if ls *.out 1> /dev/null 2>&1; then
    mv *.out tmp.riblogs
fi

# # service postgresql restart
# echo -e "\n============================================="
# date
# echo "*** FATTREE, 4"
# ./perf/fattree.py 4
# ./ravel.py --topo=fattree,4 --custom=topo/fattree.py --onlydb --script=sample.sh --exit --reconnect
# mv *.out riblogs/fattree4

# # service postgresql restart
# echo -e "\n============================================="
# date
# echo "*** FATTREE, 8"
# ./perf/fattree.py 8
# ./ravel.py --topo=fattree,8 --custom=topo/fattree.py --onlydb --script=sample.sh --exit --reconnect
# mv *.out riblogs/fattree8

# service postgresql restart
echo -e "\n============================================="
date
echo "*** FATTREE, 16"
./perf/fattree.py 16
./ravel.py --topo=fattree,16 --custom=topo/fattree.py --onlydb --script=sample.sh --exit --reconnect
mv *.out riblogs/fattree16

# service postgresql restart
# echo -e "\n============================================="
# date
# echo "*** FATTREE, 24"
# ./perf/fattree.py 24
# ./ravel.py --topo=fattree,24 --custom=topo/fattree.py --onlydb --script=sample.sh --exit --reconnect
# mv *.out riblogs/fattree24

#service postgresql restart
echo -e "\n============================================="
date
echo "*** FATTREE, 32"
./perf/fattree.py 32
./ravel.py --topo=fattree,32 --custom=topo/fattree.py --onlydb --script=sample.sh --exit --reconnect
mv *.out riblogs/fattree32

# service postgresql restart
# echo -e "\n============================================="
# date
# echo "*** FATTREE, 64"
# ./perf/fattree.py 32
# ./ravel.py --topo=fattree,64 --custom=topo/fattree.py --onlydb --script=sample.sh --exit --reconnect
# mv *.out riblogs/fattree64

date
