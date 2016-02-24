#!/usr/bin/env python

import os
import re

# XXX: newer mininet version also has MinimalTopo, TorusTopo
from mininet.topo import (SingleSwitchTopo, LinearTopo,
                          SingleSwitchReversedTopo)
from mininet.topolib import TreeTopo
from mininet.util import buildTopo

from mininet.net import Mininet
from mininet.net import macColonHex, ipStr, ipParse, netParse, ipAdd
from mininet.node import (Node, Host, OVSKernelSwitch)


TOPOS = { 'linear': LinearTopo,
          'reversed': SingleSwitchReversedTopo,
          'single': SingleSwitchTopo,
          'tree': TreeTopo
      }

def setCustom(name, value):
    if name in ('topos', 'switches', 'hosts', 'controllers'):
        param = name.upper()
        globals()[param].update(value)
    elif name == 'validate':
        validate = value
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
                setCustom(name, val)
        else:
            print "Could not find custom file", filename

def build(opts):
    return buildTopo(TOPOS, opts)

def buildSkeletonTopo(topo, net):
    class SkeletonNode(object):
        def __init__(self, name, ip, mac):
            self.name = name
            self.ip = ip
            self.mac = mac

        def IP(self):
            return self.ip

        def MAC(self):
            return self.mac

    class SkeletonSwitch(SkeletonNode):
        dpidLen = 12

        def __init__(self, name, ip, mac):
            super(SkeletonSwitch, self).__init__(name, ip, mac)
            self.dpid = self.defaultDpid()

        def defaultDpid(self):
            nums = re.findall(r'\d+', self.name)
            if nums:
                dpid = hex(int(nums[0]))[2:]
            else:
                raise Exception("Unable to device default DPID")

            return '0' * (self.dpidLen - len(dpid)) + dpid

    ipBase = '10.0.0.0/8'
    ipBaseNum, prefixLen = netParse(ipBase)
    nextIp = 1
    defaults = { 'ip' : ipAdd(nextIp,
                              ipBaseNum=ipBaseNum,
                              prefixLen=prefixLen) +
                 '/%s' % prefixLen,
                 'mac' : macColonHex(nextIp)
             }

    for host in topo.hosts():
        ip = ipAdd(nextIp,
                   ipBaseNum=ipBaseNum,
                   prefixLen=prefixLen)
        n = SkeletonNode(host, ip, macColonHex(nextIp))
        net.nodes[host] = n
        nextIp += 1

    for switch in topo.switches():
        s = SkeletonSwitch(switch, '127.0.0.1', macColonHex(nextIp))
        net.nodes[switch] = s
        nextIp += 1
