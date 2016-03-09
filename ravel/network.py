"""
Abstractions for the underlying network.

This package contains abstractions for the underlying network provider.
A network provider can be an emulator (eg, Mininet), a physical network,
or if testing only database operations in the CLI, no network at all.

This package also contains helper functions for interacting with the network,
and adding or removing flows from the command line.

Note: flow-related functions in this package are for user interaction (eg,
through a command line or script).  Flow modifications for the Ravel backend
(database) use the ravel.flow package.
"""

import os
import pickle
import re
import tempfile
import threading
import time
from functools import partial

import mininet.clean
from mininet.cli import CLI
from mininet.net import macColonHex, netParse, ipAdd
from mininet.net import Mininet
from mininet.node import RemoteController
import sysv_ipc

import ravel.messaging
from ravel.log import logger

def name2uid(db, host):
    """Convert a host's name to its u_hid (from Ravel's uhosts table).
       db: a RavelDb instance to query for the host id
       host: the name of the host (eg, h1)
       returns: the host's id from uhosts"""
    db.cursor.execute("SELECT u_hid FROM uhosts WHERE hid="
                   "(SELECT hid FROM hosts WHERE name='{0}');"
                   .format(host))
    result = db.cursor.fetchall()
    if len(result) == 0:
        logger.warning("unknown host %s", host)
        return None
    else:
        return result[0][0]

def dbid2name(db, nid):
    """Convert a node's name to its node id in Ravel's host or switch table.
       For hosts, nid should be hid from the hosts table
       db: a RavelDb instance to query for the node name
       nid: the node id
       returns: the node's name"""
    db.cursor.execute("SELECT name FROM nodes WHERE id={0}".format(nid))
    result = db.cursor.fetchall()
    if len(result) == 0:
        logger.warning("cannot find node with id %s", nid)
        return None
    if len(result) > 1:
        logger.error("multiple matches with nid %s", nid)
        return None
    else:
        return result[0][0]

def addFlow(db, h1, h2):
    """Add a flow to the database using host names
       db: a RavelDb instance to add the flow to
       h1: the host name of the source
       h2: the host name of the destination
       returns: the flow id on success, None on failure"""
    hid1 = name2uid(db, h1)
    hid2 = name2uid(db, h2)

    if hid1 is None or hid2 is None:
        return None

    try:
        db.cursor.execute("SELECT * FROM rtm;")
        fid = len(db.cursor.fetchall()) + 1
        db.cursor.execute("INSERT INTO rtm (fid, host1, host2) "
                       "VALUES ({0}, {1}, {2});"
                       .format(fid, hid1, hid2))
        db.cursor.execute ("UPDATE tm set FW = 0 where fid = {0};"
                           .format(fid, hid1, hid2))
        return fid
    except Exception, e:
        print e
        return None

def delFlowById(db, fid):
    """Delete a flow from the database using the flow's id
       db: a RavelDb instance to remove the flow from
       fid: the flow id of the flow to be removed
       returns: the flow id on success, None on failure"""
    try:
        # does the flow exist?
        db.cursor.execute("SELECT fid FROM rtm WHERE fid={0}".format(fid))
        if len(db.cursor.fetchall()) == 0:
            logger.warning("no flow installed with fid %s", fid)
            return None

        db.cursor.execute("DELETE FROM rtm WHERE fid={0}".format(fid))
        return fid
    except Exception, e:
        print e
        return None

def delFlowByHostname(db, h1, h2):
    """Delete a flow from the database using host names.  This will remove
       all flows that match the source and destination names.  To delete a
       specific flow, use delFlowById.
       db: a RavelDb instance to remove the flow from
       h1: the host name of the source
       h2: the host name of the destination
       returns: a list of matching and removed flow ids on success,
       None on failure"""
    # convert to fid, so we can report which fid is removed
    hid1 = name2uid(db, h1)
    hid2 = name2uid(db, h2)

    if hid1 is None or hid2 is None:
        return None

    db.cursor.execute("SELECT fid FROM rtm WHERE host1={0} and host2={1};"
                      .format(hid1, hid2))

    result = db.cursor.fetchall()
    if len(result) == 0:
        logger.warning("no flow installed for hosts {0},{1}".format(h1, h2))
        return None

    fids = [res[0] for res in result]
    for fid in fids:
        delFlowById(db, fid)

    return fids

class NetworkProvider(object):
    """Superclass for a network provider.  A network provider exposes the
       underlying topology to Ravel's database and CLI.  It also receives
       and handles changes to the topology that are made from the database
       (eg, a link is removed from the database)"""

    QueueId = 123456

    def __init__(self, queue_id):
        """queue_id: an integer id to be used for the database to communicate
           with the provider for updates to the topology inserted into the
           database"""
        self.receiver = ravel.messaging.MsgQueueReceiver(queue_id, self)

    def _on_update(self, msg):
        msg.consume(self)

    def addLink(self, msg):
        """Add a link to the topology
           msg: an AddLinkMessage object"""
        pass

    def removeLink(self, msg):
        """Remove a link from the topology
           msg: a RemoveLinkMessage object"""
        pass

    def addSwitch(self, msg):
        """Add a new switch to the topology
           msg: an AddSwitchMessage object"""
        pass

    def removeSwitch(self, msg):
        """Remove a switch from the topology
           msg: a RemoveSwitchMessage object"""
        pass

    def addHost(self, msg):
        """Add a new host to the topology
           msg: an AddHostMessage object"""
        pass

    def removeHost(self, msg):
        """Remove a host from the topology
           msg: a RemoveHostMessage object"""
        pass

    def start(self):
        "Start the network provider and any components in the network"
        self.receiver.start()

    def stop(self):
        "Stop the network provider and any components in the network"
        self.receiver.stop()

    def cli(self, cmd):
        """Pass commands to the network provider's CLI, if it has its own.
           Preferably, the behavior should follow the same pattern as Ravel's
           application sub-shells, which executes a command is one is given,
           otherwise loop in the CLI on an empty input
           cmd: the command run within the provider's CLI"""
        pass

class EmptyNetProvider(NetworkProvider):
    """A provider for an empty network.  Accepts a Mininet topology and
       assigns IP and MAC addresses to the nodes without starting Mininet."""

    def __init__(self, db, topo):
        """db: a RavelDb instance
           topo: a Mininet topology"""
        self.db = db
        self.topo = topo
        self.nodes = {}
        super(EmptyNetProvider, self).__init__(NetworkProvider.QueueId)

    def buildTopo(self):
        "Build a Mininet topology without starting Mininet"

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
                nums = re.findall(r"\d+", self.name)
                if nums:
                    dpid = hex(int(nums[0]))[2:]
                else:
                    raise Exception("Unable to device default DPID")

                return "0" * (self.dpidLen - len(dpid)) + dpid

        ipBase = "10.0.0.0/8"
        ipBaseNum, prefixLen = netParse(ipBase)
        nextIp = 1
        defaults = { "ip" : ipAdd(nextIp,
                                  ipBaseNum=ipBaseNum,
                                  prefixLen=prefixLen) +
                     "/%s" % prefixLen,
                     "mac" : macColonHex(nextIp)
                 }

        for host in self.topo.hosts():
            ip = ipAdd(nextIp,
                       ipBaseNum=ipBaseNum,
                       prefixLen=prefixLen)
            n = SkeletonNode(host, ip, macColonHex(nextIp))
            self.nodes[host] = n
            nextIp += 1

        for switch in self.topo.switches():
            s = SkeletonSwitch(switch, "127.0.0.1", macColonHex(nextIp))
            self.nodes[switch] = s
            nextIp += 1

    def getNodeByName(self, node):
        """Find a node by its name
           node: a node name
           returns: the node object"""
        if node in self.nodes:
            return self.nodes[node]
        return None

    def start(self):
        "Start the network provider"
        self.buildTopo()
        self.receiver.start()

    def stop(self):
        "Stop the network provider"
        self.receiver.stop()

    def cli(self, cmd):
        "EmptyNetProvider has no CLI, raises warning"
        logger.warning("no CLI available for db-only mode")

class MininetProvider(NetworkProvider):
    """A Mininet network provider.  Starts Mininet with a remote controller
       that should be running at 127.0.0.1"""

    def __init__(self, db, topo, controller):
        """db: a RavelDb instance
           topo: a Mininet topology
           controller: a controller to start along with Mininet"""
        self.db = db
        self.topo = topo
        self.controller = controller

        # need to start controller for before instantiating Mininet
        if self.controller is not None:
            self.controller.start()
            time.sleep(0.5)

        self.net = Mininet(topo,
                           controller=partial(RemoteController,
                                              ip="127.0.0.1"))

        super(MininetProvider, self).__init__(NetworkProvider.QueueId)

    def _mkLinkIntf(self, hid, name):
        if self.net.topo.isSwitch(name):
            intf = self.net.get(name).intfNames()[-1]
            self.net.get(name).attach(intf)
        else:
            self.db.cursor.execute("SELECT ip, mac FROM hosts WHERE hid={0}"
                              .format(hid))
            results = self.db.cursor.fetchall()
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
        """Add a link to the Mininet topology
           msg: an AddLinkMessage object"""
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
        cursor = self.db.cursor
        cursor.execute("INSERT INTO PORTS (sid, nid, port) "
                       "VALUES ({0}, {1}, {2}), ({1}, {0}, {3});"
                       .format(msg.node1, msg.node2,
                               port1, port2))

    def removeLink(self, msg):
        """Remove a link from the Mininet topology
           msg: a RemoveLinkMessage object"""
        name1 = dbid2name(self.db, msg.node1)
        name2 = dbid2name(self.db, msg.node2)
        port1, port2 = self.net.topo.port(name1, name2)

        self._destroy(db, net, name1, port1)
        self._destroy(db, net, name2, port2)

    def addSwitch(self, msg):
        """Add a switch to the Mininet topology
           msg: an AddSwitchMessage object"""
        default = {}
        if msg.dpid is not None:
            default["dpid"] = str(msg.dpid)

        if msg.name is None:
            msg.name = "s" + str(msg.sid)
            cursor = self.db.cursor
            cursor.execute("UPDATE switches SET name='{0}' WHERE sid={1}"
                       .format(msg.name, msg.sid))

        self.net.addSwitch(msg.name, listenPort=6633, **default)

        if msg.dpid is None:
            msg.dpid = self.net.get(msg.name).dpid
            cursor = self.db.cursor
            cursor.execute("UPDATE switches SET dpid='{0}' WHERE sid={1}"
                       .format(msg.dpid, msg.sid))

        sw = self.net.get(msg.name)
        sw.start(self.net.controllers)
        self.net.topo.addSwitch(msg.name)

    def removeSwitch(self, msg):
        """Remove a switch from the Mininet topology
           msg: a RemoveSwitchMessage object"""
        swobj = self.net.get(msg.name)
        for swport, intf in enumerate(self.net.get(msg.name).intfNames()):
            swobj.detach(intf)
            del swobj.nameToIntf[intf]
            del swobj.intfs[swport]
        self.net.topo.g.node.pop(msg.name, None)
        self.net.switches = [s for s in self.net.switches if s.name != msg.name]
        del self.net.nameToNode[msg.name]

    def addHost(self, msg):
        """Add a host to the Mininet topology
           msg: an AddHostMessage object"""
        if msg.name is None:
            msg.name = "h" + str(msg.hid)
            cursor = self.db.cursor
            cursor.execute("UPDATE hosts SET name='{0}' WHERE hid={1}"
                       .format(msg.name, msg.hid))

        self.net.addHost(msg.name)
        host = self.net.get(msg.name)
        self.net.topo.addHost(msg.name)

        # delay setting ip/mac until link is added
        if msg.ip is None:
            ipBase = "10.0.0.0/8"
            ipBaseNum, prefixLen = netParse(ipBase)
            nextIp = len(self.net.hosts) + 1
            msg.ip = ipAdd(nextIp, ipBaseNum=ipBaseNum, prefixLen=prefixLen)

            cursor = self.db.cursor
            cursor.execute("UPDATE hosts SET ip='{0}' WHERE hid={1}"
                       .format(msg.ip, msg.hid))

        if msg.mac is None:
            msg.mac = macColonHex(nextIp)
            cursor = self.db.cursor
            cursor.execute("UPDATE hosts SET mac='{0}' WHERE hid={1}"
                           .format(msg.mac, msg.hid))

    def removeHost(self, msg):
        """Remove a host from the Mininet topology
           msg: a RemoveHostMessage object"""
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
        """Find a node by its name
           node: a node name
           returns: the node object"""
        return self.net.getNodeByName(node)

    def start(self):
        "Start the Mininet network"
        self.receiver.start()
        self.net.start()

    def stop(self):
        "Stop the Mininet network"
        self.receiver.stop()
        self.net.stop()
        if self.controller is not None:
            self.controller.stop()

        logger.debug("cleaning up mininet")
        mininet.clean.cleanup()

    def cli(self, cmd):
        """Pass commands to the Mininet CLI.  If an empty string or None is
           passed, starts the CLI in a loop
           cmd: the command to run within the Mininet CLI"""
        if not cmd:
            CLI(self.net)
        else:
            temp = tempfile.NamedTemporaryFile(delete=False)
            temp.write(cmd)
            temp.close()
            CLI(self.net, script=temp.name)
            os.unlink(temp.name)

class AddLinkMessage(ravel.messaging.ConsumableMessage):
    "A consumable message for adding a new link"

    def __init__(self, node1, node2, ishost, isactive):
        """node1: node to link together
           node2: node to link together
           ishost: false if both nodes are switches, true otherwise
           isactive: if the link should also be marked as active"""
        self.node1 = node1
        self.node2 = node2
        self.ishost = ishost
        self.isactive = isactive

    def consume(self, provider):
        """Consume the message
           provider: a NetworkProvider object to consume the message"""
        provider.addLink(self)

class RemoveLinkMessage(ravel.messaging.ConsumableMessage):
    "A consumable message for removing a link"

    def __init__(self, node1, node2):
        """node1: node connected to one end of the link
           node2: node connected to the other end of the link"""
        self.node1 = node1
        self.node2 = node2

    def consume(self, provider):
        """Consume the message
           provider: a NetworkProvider object to consume the message"""
        provider.removeLink(self)

class AddSwitchMessage(ravel.messaging.ConsumableMessage):
    "A consumable message for adding a switch"

    def __init__(self, sid, name, dpid, ip, mac):
        """sid: the id of the switch
           name: the name of the switch
           dpid: the datapath ID of the switch
           ip: the IP address of the switch
           mac: the MAC address of the switch"""
        self.sid = sid
        self.name = name
        self.dpid = dpid
        self.ip = ip
        self.mac = mac

    def consume(self, provider):
        """Consume the message
           provider: a NetworkProvider object to consume the message"""
        provider.addSwitch(self)

class RemoveSwitchMessage(ravel.messaging.ConsumableMessage):
    "A consumable message for removing a switch"

    def __init__(self, sid, name):
        """sid: the id of the switch
           name: the name of the switch"""
        self.sid = sid
        self.name = name

    def consume(self, provider):
        """Consume the message
           provider: a NetworkProvider object to consume the message"""
        provider.removeSwitch(self)

class AddHostMessage(ravel.messaging.ConsumableMessage):
    "A consumable message for adding a host"

    def __init__(self, hid, name, ip, mac):
        """hid: the id of the host
           name: the name of the host
           ip: the IP address of the host
           mac: the MAC address of the host"""
        self.hid = hid
        self.name = name
        self.ip = ip
        self.mac = mac

    def consume(self, provider):
        """Consume the message
           provider: a NetworkProvider object to consume the message"""
        provider.addHost(self)

class RemoveHostMessage(ravel.messaging.ConsumableMessage):
    "A consumable message for removing a host"
    def __init__(self, hid, name):
        """hid: the id of the host
           name: the name of the host"""
        self.hid = hid
        self.name = name

    def consume(self, provider):
        """Consume the message
           provider: a NetworkProvider object to consume the message"""
        provider.removeHost(self)
