#!/bin/sh 
cd /home/ravel/ravel 
./ravel.py --clean 
./ravel.py --topo=single,3 --restore 
bashpeSchema.sql 
bash