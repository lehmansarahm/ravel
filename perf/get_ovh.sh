#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cp /tmp/*.dat $DIR/plot/optimization/dat/
cp /tmp/*.plt $DIR/plot/optimization/dat/
cp /tmp/*.pdf $DIR/plot/optimization/
