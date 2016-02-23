#!/bin/bash

CWD="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
POXPATH=~/src/pox

export PYTHONPATH=.:$CWD
${POXPATH}/pox.py log.level --DEBUG openflow.of_01 --port=6633 poxapp

