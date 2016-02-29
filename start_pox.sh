#!/bin/bash

eval $(grep "^PoxDir=" ravel.cfg)

CWD="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PYTHONPATH=.:$CWD

${PoxDir}/pox.py log.level --DEBUG openflow.of_01 --port=6633 poxapp

