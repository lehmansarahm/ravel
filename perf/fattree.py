#!/usr/bin/env python

import sys
import os
from mininet.topo import Topo

class FattreeTopo(Topo):
    def __init__(self, k=4):
        super(FattreeTopo, self).__init__()
        self.size = int(k)
        self.name = "fattree{0}".format(k)
        Topo.__init__(self)
        self._build()

    def _build(self):
        cores = (self.size/2)**2
        aggs = (self.size/2) * self.size
        edges = (self.size/2) * self.size
        hosts = (self.size/2)**2 * self.size

        switches = {}

        for pod in range(0, self.size):
            agg_offset = cores + self.size/2 * pod
            edge_offset = cores + aggs + self.size/2 * pod
            host_offset = cores + aggs + edges + (self.size/2)**2 * pod

            for agg in range(0, self.size/2):
                core_offset = agg * self.size/2
                aggname = "s{0}".format(agg_offset + agg)
                agg_sw = self.addSwitch(aggname)
                switches[aggname] = agg_sw

                # connect core and aggregate switches
                for core in range(0, self.size/2):
                    corename = "s{0}".format(core_offset + core)
                    core_sw = self.addSwitch(corename)
                    switches[corename] = core_sw
                    self.addLink(agg_sw, core_sw)

                # connect aggregate and edge switches
                for edge in range(0, self.size/2):
                    edgename = "s{0}".format(edge_offset + edge)
                    edge_sw = self.addSwitch(edgename)
                    switches[edgename] = edge_sw
                    self.addLink(agg_sw, edge_sw)

            # connect edge switches with hosts
            for edge in range(0, self.size/2):
                edgename = "s{0}".format(edge_offset + edge)
                edge_sw = switches[edgename]

                for h in range(0, self.size/2):
                    hostname = "h{0}".format(host_offset + self.size/2 * edge + h)
                    hostobj = self.addHost(hostname)
                    self.addLink(edge_sw, hostobj)

topos = { 'fattree' : FattreeTopo }

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        sys.exit(0)

    k = int(sys.argv[1])
    topo = FattreeTopo(k)

    # add ravel to path
    path = ""
    if 'PYTHONPATH' in os.environ:
        path = os.environ['PYTHONPATH']

    sys.path = path.split(':') + sys.path
    cwd = os.path.dirname(os.path.abspath(__file__))
    raveldir = os.path.normpath(os.path.join(cwd, ".."))
    sys.path.append(os.path.abspath(raveldir))

    from ravel.db import RavelDb, BASE_SQL

    db = RavelDb("mininet", "mininet", BASE_SQL)
    db.cursor.execute("DELETE FROM switches; DELETE FROM hosts; DELETE FROM tp;")
    nodecount = 0
    nodemap = {}
    hosts = []
    for sw in topo.switches():
        db.cursor.execute("INSERT INTO SWITCHES(sid, name) VALUES({0}, '{1}');"
                          .format(nodecount, sw))
        nodemap[sw] = nodecount
        nodecount += 1

    for host in topo.hosts():
        db.cursor.execute("INSERT INTO hosts(hid, name) VALUES({0}, '{1}');"
                          .format(nodecount, host))
        nodemap[host] = nodecount
        hosts.append(host)
        nodecount += 1

    for edge1, edge2 in topo.links():
        sid = nodemap[edge1]
        nid = nodemap[edge2]
        if edge1 in hosts or edge2 in hosts:
            ishost = 1
        else:
            ishost = 0

        if hasattr(topo, "bidirectional") and not topo.bidirectional:
            db.cursor.execute("INSERT INTO tp(sid, nid, ishost, isactive) "
                              "VALUES({0}, {1}, {2}, 1);"
                              .format(sid, nid, ishost))
        else:
            db.cursor.execute("INSERT INTO tp(sid, nid, ishost, isactive) "
                              "VALUES({0}, {1}, {2}, 1),({1}, {0}, {2}, 1);"
                              .format(sid, nid, ishost))
