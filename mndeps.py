#!/usr/bin/env python

# XXX: newer mininet version also has MinimalTopo
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

def build(opts):
    return buildTopo(TOPOS, opts)
