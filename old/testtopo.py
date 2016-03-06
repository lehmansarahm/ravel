#!/usr/bin/env python

from mininet.topo import Topo

class TestTopo(Topo):
    def build(self, n=5):
        switch = self.addSwitch('s1')
        for h in range(n):
            host = self.addHost('h%s' % (h + 1))
            self.addLink(host, switch)

topos = { 'testtopo': ( lambda: TestTopo() ) }
