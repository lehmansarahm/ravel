import os
from mininet.topo import Topo

class IspTopo(Topo):
    def __init__(self, ispnum=1221, feeds=None, path=None):
        super(IspTopo, self).__init__()
        self.ispnum = int(ispnum)
        self.bidirectional = False

        if feeds is None:
            self.feeds = 0
            self.name = "isp{0}".format(ispnum)
        else:
            self.feeds = int(feeds)
            self.name = "isp{0}_{1}".format(ispnum, feeds)

        if path is None:
            self.path = os.path.dirname(os.path.realpath(__file__))
            self.path = os.path.join(self.path, "ISP_topo")

        Topo.__init__(self)
        self._build()

    def _build(self):
        edge_file = "{0}_edges.txt".format(self.ispnum)
        node_file = "{0}_nodes.txt".format(self.ispnum)

        nodes = []
        with open(os.path.join(self.path, node_file)) as node_fd:
            for line in node_fd.readlines():
                nodes.append(line.strip())

        edges = []
        with open(os.path.join(self.path, edge_file)) as edge_fd:
            for i, line in enumerate(edge_fd.readlines()):
                if self.feeds > 0 and i > self.feeds:
                    break

                tokens = line.split()
                edges.append((tokens[0], tokens[1]))

        switches = {}
        for node in nodes:
            node = int(node)

            swname = "s{0}".format(node)
            sw = self.addSwitch(swname)
            switches[swname] = sw

            hostname = "h{0}".format(node + len(self.hosts()) + 1)
            host = self.addHost(hostname)
            self.addLink(sw, host)

        for edge1, edge2 in edges:
            sw1 = "s{0}".format(edge1)
            sw2 = "s{0}".format(edge2)

            self.addLink(switches[sw1], switches[sw2])

topos = { 'isp' : IspTopo }
