#!/usr/bin/env python

import os

# XXX: newer mininet version also has MinimalTopo, TorusTopo
from mininet.topo import ( SingleSwitchTopo, LinearTopo,
                           SingleSwitchReversedTopo )
from mininet.topolib import TreeTopo
from mininet.util import buildTopo
import psycopg2

TOPOS = { 'linear': LinearTopo,
          'reversed': SingleSwitchReversedTopo,
          'single': SingleSwitchTopo,
          'tree': TreeTopo
      }

def setCustom(name, value):
    if name in ('topos', 'switches', 'hosts', 'controllers'):
        param = name.upper()
        globals()[param].update(value)
    else:
        globals()[name] = value

def custom(value):
    files = []
    if os.path.isfile(value):
        files.append(value)
    else:
        files += value.split(',')

    for filename in files:
        customs = {}
        if os.path.isfile(filename):
            execfile(filename, customs, customs)
            for name, val in customs.iteritems():
                setCustom(name, value)
        else:
            print "Could not find custom file", filename

    print globals()

def build(opts):
    return buildTopo(TOPOS, opts)
