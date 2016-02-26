#!/usr/bin/env python

import os
import pickle
import re
import tempfile
import threading
from functools import partial

import mininet.clean
from mininet.cli import CLI
from mininet.net import macColonHex, netParse, ipAdd
from mininet.net import Mininet
from mininet.node import RemoteController
import sysv_ipc

from ravel.log import logger
from ravel.pubsub import Subscriber, MsgQueueProtocol

# TODO: move to provider?
def dbid2name(db, nid):
    cursor = db.connect().cursor()
    cursor.execute("SELECT name FROM nodes WHERE id={0}".format(nid))
    result = cursor.fetchall()
    if len(result) == 0:
        logger.warning("cannot find node with id %s", nid)
    else:
        return result[0][0]

class NetworkProvider(object):
    QueueId = 123456

    def __init__(self, subscriber_queue):
        self.subscriber = Subscriber(MsgQueueProtocol(subscriber_queue, self))

    def _on_update(self, msg):
        msg.consume(self)

    def addLink(self, msg):
        pass

    def removeLink(self, msg):
        pass

    def addSwitch(self, msg):
        pass

    def removeSwitch(self, msg):
        pass

    def addHost(self, msg):
        pass

    def removeHost(self, msg):
        pass

    def start(self):
        self.subscriber.start()

    def stop(self):
        self.subscriber.stop()

    def cli(self, cmd):
        pass

class EmptyNetProvider(NetworkProvider):
    def __init__(self, db, topo):
        self.db = db
        self.topo = topo
        self.nodes = {}
        super(EmptyNetProvider, self).__init__(NetworkProvider.QueueId)

    def buildTopo(self):
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

        for host in self.topo.hosts():
            ip = ipAdd(nextIp,
                       ipBaseNum=ipBaseNum,
                       prefixLen=prefixLen)
            n = SkeletonNode(host, ip, macColonHex(nextIp))
            self.nodes[host] = n
            nextIp += 1

        for switch in self.topo.switches():
            s = SkeletonSwitch(switch, '127.0.0.1', macColonHex(nextIp))
            self.nodes[switch] = s
            nextIp += 1

    def getNodeByName(self, node):
        if node in self.nodes:
            return self.nodes[node]
        return None

    def start(self):
        self.buildTopo()
        self.subscriber.start()

    def stop(self):
        self.subscriber.stop()

    def cli(self, cmd):
        logger.warning("no CLI available for db-only mode")

class MininetProvider(NetworkProvider):
    def __init__(self, db, topo, remote=True):
        self.db = db
        self.topo = topo

        if remote:
            self.net = Mininet(topo,
                               controller=partial(RemoteController,
                                                  ip='127.0.0.1'))
        else:
            self.net = Mininet(topo)

        super(MininetProvider, self).__init__(NetworkProvider.QueueId)

    def _mkLinkIntf(self, hid, name):
        if self.net.topo.isSwitch(name):
            intf = self.net.get(name).intfNames()[-1]
            self.net.get(name).attach(intf)
        else:
            cursor = self.db.connect().cursor()
            cursor.execute("SELECT ip, mac FROM hosts WHERE hid={0}"
                           .format(hid))
            results = cursor.fetchall()
            ip = results[0][0]
            mac = results[0][1]
            self.net.get(name).setIP(ip)
            self.net.get(name).setMAC(mac)

    def _destroyLinkIntf(self, name, port):
        # detach switch, remove interfaces
        # similar to remove host, switch but keeping the node
        obj = net.get(name)
        intf = obj.intfNames()[port]

        if self.net.topo.isSwitch(name):
            obj.detach(intf)

        del obj.nameToIntf[intf]
        del obj.intfs[port]

    def addLink(self, msg):
        name1 = dbid2name(self.db, msg.node1)
        name2 = dbid2name(self.db, msg.node2)
        self.net.addLink(name1, name2)
        self.net.topo.addLink(name1, name2)
        self._mkLinkIntf(msg.node1, name1)
        self._mkLinkIntf(msg.node2, name2)

        # don't forget to update port mapping
        isHost = 1
        if self.net.topo.isSwitch(name1) and self.net.topo.isSwitch(name2):
            isHost = 0

        port1, port2 = self.net.topo.port(name1, name2)
        cursor = self.db.connect().cursor()
        cursor.execute("INSERT INTO PORTS (sid, nid, port) "
                       "VALUES ({0}, {1}, {2}), ({1}, {0}, {3});"
                       .format(msg.node1, msg.node2,
                               port1, port2))

    def removeLink(self, msg):
        name1 = dbid2name(self.db, msg.node1)
        name2 = dbid2name(self.db, msg.node2)
        port1, port2 = self.net.topo.port(name1, name2)

        self._destroy(db, net, name1, port1)
        self._destroy(db, net, name2, port2)

    def addSwitch(self, msg):
        default = {}
        if msg.dpid is not None:
            default['dpid'] = str(msg.dpid)

        if msg.name is None:
            msg.name = 's' + str(msg.sid)
            cursor = self.db.connect().cursor()
            cursor.execute("UPDATE switches SET name='{0}' WHERE sid={1}"
                       .format(msg.name, msg.sid))

        self.net.addSwitch(msg.name, listenPort=6633, **default)

        if msg.dpid is None:
            msg.dpid = self.net.get(msg.name).dpid
            cursor = self.db.connect().cursor()
            cursor.execute("UPDATE switches SET dpid='{0}' WHERE sid={1}"
                       .format(msg.dpid, msg.sid))

        sw = self.net.get(msg.name)
        sw.start(self.net.controllers)
        self.net.topo.addSwitch(msg.name)

    def removeSwitch(self, msg):
        swobj = self.net.get(msg.name)
        for swport, intf in enumerate(self.net.get(msg.name).intfNames()):
            swobj.detach(intf)
            del swobj.nameToIntf[intf]
            del swobj.intfs[swport]
        self.net.topo.g.node.pop(msg.name, None)
        self.net.switches = [s for s in self.net.switches if s.name != msg.name]
        del self.net.nameToNode[msg.name]

    def addHost(self, msg):
        if msg.name is None:
            msg.name = 'h' + str(msg.hid)
            cursor = self.db.connect().cursor()
            cursor.execute("UPDATE hosts SET name='{0}' WHERE hid={1}"
                       .format(msg.name, msg.hid))

        self.net.addHost(msg.name)
        host = self.net.get(msg.name)
        self.net.topo.addHost(msg.name)

        # delay setting ip/mac until link is added
        if msg.ip is None:
            # TODO: reference mndeps
            ipBase = '10.0.0.0/8'
            ipBaseNum, prefixLen = netParse(ipBase)
            nextIp = len(self.net.hosts) + 1
            msg.ip = ipAdd(nextIp, ipBaseNum=ipBaseNum, prefixLen=prefixLen)

            cursor = self.db.connect().cursor()
            cursor.execute("UPDATE hosts SET ip='{0}' WHERE hid={1}"
                       .format(msg.ip, msg.hid))

        if msg.mac is None:
            msg.mac = macColonHex(nextIp)
            cursor = self.db.connect().cursor()
            cursor.execute("UPDATE hosts SET mac='{0}' WHERE hid={1}"
                           .format(msg.mac, msg.hid))

    def removeHost(self, msg):
        # find adjacent switch(es)
        sw = [intf.link.intf2.node.name for
              intf in self.net.get(msg.name).intfList() if
              self.net.topo.isSwitch(intf.link.intf2.node.name)]

        self.net.get(msg.name).terminate()
        self.net.topo.g.node.pop(msg.name, None)
        self.net.hosts = [h for h in self.net.hosts if h.name != msg.name]
        del self.net.nameToNode[msg.name]

        if len(sw) == 0:
            logger.debug("deleting host connected to 0 switches")
            return
        elif len(sw) > 1:
            raise Exception("cannot support hosts connected to %s switches",
                            len(sw))

        swname = str(sw[0])
        swobj = self.net.get(swname)
        swport = self.net.topo.port(swname, msg.name)[0]
        intf = str(swobj.intfList()[swport])
        swobj.detach(intf)
        del swobj.nameToIntf[intf]
        del swobj.intfs[swport]

    def getNodeByName(self, node):
        return self.net.getNodeByName(node)

    def start(self):
        self.subscriber.start()
        self.net.start()

    def stop(self):
        self.subscriber.stop()
        self.net.stop()
        logger.debug("cleaning up mininet")
        mininet.clean.cleanup()

    def cli(self, cmd):
        if not cmd:
            CLI(self.net)
        else:
            temp = tempfile.NamedTemporaryFile(delete=False)
            temp.write(cmd)
            temp.close()
            CLI(self.net, script=temp.name)
            os.unlink(temp.name)

class TopoModMessage(object):
    def consume(self, provider):
        pass

class AddLinkMessage(TopoModMessage):
    def __init__(self, node1, node2, ishost, isactive):
        self.node1 = node1
        self.node2 = node2
        self.ishost = ishost
        self.isactive = isactive

    def consume(self, provider):
        provider.addLink(self)

class RemoveLinkMessage(TopoModMessage):
    def __init__(self, node1, node2):
        self.node1 = node1
        self.node2 = node2

    def consume(self, provider):
        provider.removeLink(self)

class AddSwitchMessage(TopoModMessage):
    def __init__(self, sid, name, dpid, ip, mac):
        self.sid = sid
        self.name = name
        self.dpid = dpid
        self.ip = ip
        self.mac = mac

    def consume(self, provider):
        provider.addSwitch(self)

class RemoveSwitchMessage(TopoModMessage):
    def __init__(self, sid, name):
        self.sid = sid
        self.name = name

    def consume(self, provider):
        provider.removeSwitch(self)

class AddHostMessage(TopoModMessage):
    def __init__(self, hid, name, ip, mac):
        self.hid = hid
        self.name = name
        self.ip = ip
        self.mac = mac

    def consume(self, provider):
        provider.addHost(self)

class RemoveHostMessage(TopoModMessage):
    def __init__(self, hid, name):
        self.hid = hid
        self.name = name

    def consume(self, provider):
        provider.removeHost(self)
