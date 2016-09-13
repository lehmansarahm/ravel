#!/bin/bash

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR/..

set -e

# service postgresql restart
echo "\n============================================="
date
echo "FATTREE, 4"
./ravel.py --topo=fattree,4 --custom=topo/fattree.py --onlydb --script=./eval/ribtest.rv --exit

# service postgresql restart
# echo "\n============================================="
# date
# echo "FATTREE, 8"
# ./ravel.py --topo=fattree,8 --custom=topo/fattree.py --onlydb --script=./eval/ribtest.rv --exit

# service postgresql restart
# echo "\n============================================="
# date
# echo "FATTREE, 16"
# ./ravel.py --topo=fattree,16 --custom=topo/fattree.py --onlydb --script=./eval/ribtest.rv --exit

# service postgresql restart
# echo "\n============================================="
# date
# echo "FATTREE, 24"
# ./ravel.py --topo=fattree,24 --custom=topo/fattree.py --onlydb --script=./eval/ribtest.rv --exit

# service postgresql restart
# echo "\n============================================="
# date
# echo "FATTREE, 32"
# ./ravel.py --topo=fattree,32 --custom=topo/fattree.py --onlydb --script=./eval/ribtest.rv --exit

# service postgresql restart
# echo "\n============================================="
# date
# echo "FATTREE, 64"
# ./ravel.py --topo=fattree,64 --custom=topo/fattree.py --onlydb --script=./eval/ribtest.rv --exit

date
