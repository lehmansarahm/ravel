#!/bin/bash

CWD="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PYTHONPATH=.:$CWD
#~/src/pox/pox.py log.level --DEBUG openflow.of_01 --port=6633 pox_rpc
~/src/pox/pox.py log.level --DEBUG openflow.of_01 --port=6633 poxapp

