#!/usr/bin/env python

import os
import pickle
import sys
import threading
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer

import sysv_ipc
from mininet.net import macColonHex, netParse, ipAdd

import util
from ravel.log import logger
from ravel.profiling import PerfCounter
from ravel.util import Config, Connection, MsgQueueReceiver

util.append_path(Config.PoxDir)
import pox.openflow.libopenflow_01 as of

OFPP_FLOOD = of.OFPP_FLOOD
OFPFC_ADD = of.OFPFC_ADD
OFPFC_DELETE = of.OFPFC_DELETE
OFPFC_DELETE_STRICT = of.OFPFC_DELETE_STRICT

RpcAddress = "http://{0}:{1}".format(Config.RpcHost, Config.RpcPort)
MininetQueueId = 5555

# TODO: move into net-type module, different from net triggers
def dbid2name(db, nid):
    cursor = db.connect().cursor()
    cursor.execute("SELECT name FROM nodes WHERE id={0}".format(nid))
    result = cursor.fetchall()
    if len(result) == 0:
        logger.warning("cannot find node with id %s", nid)
    else:
        return result[0][0]

class MininetAdapter(object):
    def __init__(self, db, net):
        self.db = db
        self.net = net
        from util import MsgQueueReceiver
        from net import MininetQueueId
        self.server = MsgQueueReceiver(MininetQueueId,
                                       None,
                                       self.handler,
                                       self.can_continue,
                                       logger)

    def can_continue(self):
        return self.running

    def start(self):
        self.running = True
        self.server.start()

    def stop(self):
        self.running = False
        self.server.shutdown()

    def handler(self, msg):
        if msg is not None:
            msg.update(self.db, self.net)

class AddSwitchMessage(object):
    def __init__(self, sid, name, dpid, ip, mac):
        self.sid = sid
        self.name = name
        self.dpid = dpid
        self.ip = ip
        self.mac = mac

    def update(self, db, net):
        default = {}
        if self.dpid is not None:
            default['dpid'] = str(self.dpid)

        if self.name is None:
            self.name = 's' + str(self.sid)
            cursor = db.connect().cursor()
            cursor.execute("UPDATE switches SET name='{0}' WHERE sid={1}"
                       .format(self.name, self.sid))

        net.addSwitch(self.name, listenPort=6633, **default)

        if self.dpid is None:
            self.dpid = net.get(self.name).dpid
            cursor = db.connect().cursor()
            cursor.execute("UPDATE switches SET dpid='{0}' WHERE sid={1}"
                       .format(self.dpid, self.sid))

        sw = net.get(self.name)
        sw.start(net.controllers)
        net.topo.addSwitch(self.name)

class RemoveSwitchMessage(object):
    def __init__(self, sid, name):
        self.sid = sid
        self.name = name

    def update(self, db, net):
        swobj = net.get(self.name)
        for intf in net.get(self.name).intfNames():
            swobj.detach(intf)
            del swobj.nameToIntf[intf]
            del swobj.intfs[swport]
        net.topo.g.node.pop(self.name, None)
        net.switches = [s for s in net.switches if s.name != self.name]
        del net.nameToNode[self.name]

class AddHostMessage(object):
    def __init__(self, hid, name, ip, mac):
        self.hid = hid
        self.name = name
        self.ip = ip
        self.mac = mac

    def update(self, db, net):
        if self.name is None:
            self.name = 'h' + str(self.hid)
            cursor = db.connect().cursor()
            cursor.execute("UPDATE hosts SET name='{0}' WHERE hid={1}"
                       .format(self.name, self.hid))

        net.addHost(self.name)
        host = net.get(self.name)
        net.topo.addHost(self.name)

        # delay setting ip/mac until link is added
        if self.ip is None:
            # TODO: reference mndeps
            ipBase = '10.0.0.0/8'
            ipBaseNum, prefixLen = netParse(ipBase)
            nextIp = len(net.hosts) + 1
            self.ip = ipAdd(nextIp, ipBaseNum=ipBaseNum, prefixLen=prefixLen)

            cursor = db.connect().cursor()
            cursor.execute("UPDATE hosts SET ip='{0}' WHERE hid={1}"
                       .format(self.ip, self.hid))

        if self.mac is None:
            self.mac = macColonHex(nextIp)
            cursor = db.connect().cursor()
            cursor.execute("UPDATE hosts SET mac='{0}' WHERE hid={1}"
                           .format(self.mac, self.hid))

class RemoveHostMessage(object):
    def __init__(self, hid, name):
        self.hid = hid
        self.name = name

    def update(self, db, net):
        # find adjacent switch(es)
        sw = [intf.link.intf2.node.name for
              intf in net.get(self.name).intfList() if
              net.topo.isSwitch(intf.link.intf2.node.name)]

        net.get(self.name).terminate()
        net.topo.g.node.pop(self.name, None)
        net.hosts = [h for h in net.hosts if h.name != self.name]
        del net.nameToNode[self.name]

        if len(sw) == 0:
            logger.debug("deleting host connected to 0 switches")
            return
        elif len(sw) > 1:
            raise Exception("cannot support hosts connected to %s switches",
                            len(sw))

        swname = str(sw[0])
        swobj = net.get(swname)
        swport = net.topo.port(swname, self.name)[0]
        intf = str(swobj.intfList()[swport])
        swobj.detach(intf)
        del swobj.nameToIntf[intf]
        del swobj.intfs[swport]

class AddLinkMessage(object):
    def __init__(self, node1, node2, isHost, isActive):
        self.node1 = node1
        self.node2 = node2
        self.isHost = isHost
        self.isActive = isActive

    def _create(self, db, net, hid, name):
        if net.topo.isSwitch(name):
            intf = net.get(name).intfNames()[-1]
            net.get(name).attach(intf)
        else:
            cursor = db.connect().cursor()
            cursor.execute("SELECT ip, mac FROM hosts WHERE hid={0}"
                           .format(hid))
            results = cursor.fetchall()
            ip = results[0][0]
            mac = results[0][1]
            net.get(name).setIP(ip)
            net.get(name).setMAC(mac)

    def update(self, db, net):
        name1 = dbid2name(db, self.node1)
        name2 = dbid2name(db, self.node2)
        net.addLink(name1, name2)
        net.topo.addLink(name1, name2)
        self._create(db, net, self.node1, name1)
        self._create(db, net, self.node2, name2)

        # don't forget to update port mapping
        isHost = 1
        if net.topo.isSwitch(name1) and net.topo.isSwitch(name2):
            isHost = 0

        port1, port2 = net.topo.port(name1, name2)
        cursor = db.connect().cursor()
        cursor.execute("INSERT INTO PORTS (sid, nid, port) "
                       "VALUES ({0}, {1}, {2}), ({1}, {0}, {3});"
                       .format(self.node1, self.node2,
                               port1, port2))

class RemoveLinkMessage(object):
    def __init__(self, node1, node2):
        self.node1 = node1
        self.node2 = node2

    def _destroy(self, db, net, hid, name, port):
        # detach switch, remove interfaces
        # similar to remove host, switch but keeping the node
        obj = net.get(name)
        intf = obj.intfNames()[port]

        if net.topo.isSwitch(name):
            obj.detach(intf)

        del obj.nameToIntf[intf]
        del obj.intfs[port]

    def update(self, db, net):
        name1 = dbid2name(db, self.node1)
        name2 = dbid2name(db, self.node2)
        port1, port2 = net.topo.port(name1, name2)

        self._destroy(db, net, self.node1, name1, port1)
        self._destroy(db, net, self.node2, name2, port2)

def addLink(sid, nid, isHost, isActive):
    msg = AddLinkMessage(sid, nid, isHost, isActive)
    conn = MsgQueueConnection(MininetQueueId)
    conn.send(msg)

def removeLink(sid, nid):
    msg = RemoveLinkMessage(sid, nid)
    conn = MsgQueueConnection(MininetQueueId)
    conn.send(msg)

def addHost(hid, name, ip, mac):
    msg = AddHostMessage(hid, name, ip, mac)
    conn = MsgQueueConnection(MininetQueueId)
    conn.send(msg)

def removeHost(hid, name):
    msg = RemoveHostMessage(hid, name)
    conn = MsgQueueConnection(MininetQueueId)
    conn.send(msg)

def addSwitch(sid, name, dpid, ip, mac):
    msg = AddSwitchMessage(sid, name, dpid, ip, mac)
    conn = MsgQueueConnection(MininetQueueId)
    conn.send(msg)

def removeSwitch(sid, name):
    msg = RemoveSwitchMessage(sid, name)
    conn = MsgQueueConnection(MininetQueueId)
    conn.send(msg)

def connectionFactory(conn):
    return connections[conn]()

def _send_msg(command, flow_id, sw, ip1, mac1, ip2, mac2, outport, revoutport):
    pc = PerfCounter('msg_create')
    pc.start()

    conn = connectionFactory(Config.Connection)
    msg1 = OfMessage(command=command,
                     priority=10,
                     switch=sw,
                     match=Match(nw_src=ip1, nw_dst=ip2, dl_type=0x0800),
                     actions=[outport])

    msg2 = OfMessage(command=command,
                     priority=10,
                     switch=sw,
                     match=Match(nw_src=ip2, nw_dst=ip1, dl_type=0x0800),
                     actions=[revoutport])

    arp1 = OfMessage(command=command,
                     priority=1,
                     switch=sw,
                     match=Match(dl_src=mac1, dl_type=0x0806),
                     actions=[OFPP_FLOOD])

    arp2 = OfMessage(command=command,
                     priority=1,
                     switch=sw,
                     match=Match(dl_src=mac2, dl_type=0x0806),
                     actions=[OFPP_FLOOD])

    pc.stop()
    conn.send(msg1)
    conn.send(msg2)
    conn.send(arp1)
    conn.send(arp2)
    conn.sendBarrier(BarrierMessage(sw.dpid))

def installFlow(flowid, sw, ip1, mac1, ip2, mac2, outport, revoutport):
    _send_msg(OFPFC_ADD,
              flowid, sw, ip1, mac1, ip2, mac2, outport, revoutport)

def removeFlow(flowid, sw, ip1, mac1, ip2, mac2, outport, revoutport):
    _send_msg(OFPFC_DELETE_STRICT,
              flowid, sw, ip1, mac1, ip2, mac2, outport, revoutport)

class OfManager(object):
    def __init__(self):
        self.adapters = []

    def registerAdapter(self, adapter):
        self.adapters.append(adapter)

    def shutdown(self):
        for adapter in self.adapters:
            adapter.shutdown()

    def isRunning(self):
        pass

    def sendBarrier(self, dpid):
        pass

    def sendFlowmod(self, msg):
        pass

    def requestStats(self):
        pass

class OfManagerAdapter(object):
    def __init__(self, ctrl, log):
        self.ctrl = ctrl
        self.log = log
        self.running = False

    def shutdown(self, event):
        pass

class RpcAdapter(OfManagerAdapter):
    def __init__(self, ctrl, log):
        super(RpcAdapter, self).__init__(ctrl, log)
        self.log.info("rpc_server: starting")
        self.server = SimpleXMLRPCServer((Config.RpcHost, Config.RpcPort),
                                         logRequests=False,
                                         allow_none=True)
        self.server.register_function(self.ctrl.requestStats)
        self.server.register_function(self.ctrl.sendBarrier)
        self.server.register_function(self.echo)
        self.server.register_function(self.sendFlowmod)
        self.t = threading.Thread(target=self.run)
        self.t.start()

    def sendFlowmod(self, obj):
        msg = pickle.loads(obj)
        self.ctrl.sendFlowmod(msg)

    def echo(self, string=None):
        # for testing
        self.log.debug("rpc_server: echo()")
        if string is not None:
            self.log.info(string)
        return True

    def run(self):
        while self.ctrl.isRunning():
            self.log.debug("rpc_server: waiting for request")
            self.server.handle_request()
        self.log.debug("rpc_server: done")

    def handle_GoingDown(self, event):
        self.shutdown()

    def shutdown(self, event=None):
        # send rpc request to trigger handle request and end loop
        self.log.info("rpc_server: stopping")
        proxy = xmlrpclib.ServerProxy(RpcAddress, allow_none=True)
        proxy.echo(None)

class MsgQueueAdapter(OfManagerAdapter):
    def __init__(self, ctrl, log):
        super(MsgQueueAdapter, self).__init__(ctrl, log)
        self.log.info("mq_server: starting")
        self.server = MsgQueueReceiver(Config.QueueId,
                                       OfMessage(),
                                       self.msg_handler,
                                       self.ctrl.isRunning,
                                       self.log)
        self.server.start()

    def shutdown(self, event=None):
        self.server.shutdown()

    def msg_handler(self, msg):
        if isinstance(msg, BarrierMessage):
            self.ctrl.sendBarrier(msg.dpid)
        elif isinstance(msg, OfMessage) and msg.command is not None:
            self.ctrl.sendFlowmod(msg)
        else:
            self.log.debug("unexpected object {0}".format(msg))

class AdapterConnection(object):
    def send(self, msg):
        pass

    def sendBarrier(self, msg):
        pass

class MsgQueueConnection(AdapterConnection):
    def __init__(self, queue_id=Config.QueueId):
        pc = PerfCounter('mq_conn')
        pc.start()
        self.mq = sysv_ipc.MessageQueue(queue_id, mode=07777)
        pc.stop()

    def send(self, msg):
        pc = PerfCounter('mq_send')
        pc.start()
        p = pickle.dumps(msg)
        self.mq.send(p)
        pc.stop()

    def sendBarrier(self, msg):
        self.mq.send(pickle.dumps(msg))

class RpcConnection(AdapterConnection):
    def __init__(self, addr=RpcAddress):
        pc = PerfCounter('rpc_conn')
        pc.start()
        self.proxy = xmlrpclib.ServerProxy(addr, allow_none=True)
        pc.stop()

    def send(self, msg):
        pc = PerfCounter('rpc_send')
        pc.start()
        p = pickle.dumps(msg)
        self.proxy.sendFlowmod(p)
        pc.stop()

    def sendBarrier(self, msg):
        self.proxy.sendBarrier(msg.dpid)

class OvsConnection(AdapterConnection):
    command = "/usr/bin/sudo /usr/bin/ovs-ofctl"
    subcmds = { OFPFC_ADD : "add-flow",
                OFPFC_DELETE : "del-flows",
                OFPFC_DELETE_STRICT : "--strict del-flows"
    }

    def __init__(self):
        pass

    def send(self, msg):
        subcmd = OvsConnection.subcmds[msg.command]

        # TODO: need to modify this for remote switches
        dest = msg.switch.name

        params = []
        if msg.match.nw_src is not None:
            params.append("nw_src={0}".format(msg.match.nw_src))
        if msg.match.nw_dst is not None:
            params.append("nw_dst={0}".format(msg.match.nw_dst))
        if msg.match.dl_src is not None:
            params.append("dl_src={0}".format(msg.match.dl_src))
        if msg.match.dl_dst is not None:
            params.append("dl_dst={0}".format(msg.match.dl_dst))
        if msg.match.dl_type is not None:
            params.append("dl_type={0}".format(msg.match.dl_type))

        params.append("priority={0}".format(msg.priority))
        actions = ["flood" if a == OFPP_FLOOD else str(a) for a in msg.actions]

        if msg.command == OFPFC_ADD:
            params.append("action=output:" + ",".join(actions))

        paramstr = ",".join(params)
        cmd = "{0} {1} {2} {3}".format(OvsConnection.command,
                                       subcmd,
                                       dest,
                                       paramstr)

        ret = os.system(cmd)
        print ret, cmd
        return ret

class Switch(object):
    def __init__(self, name, ip, dpid):
        self.name = name
        self.ip = ip
        self.dpid = dpid

    def __repr__(self):
        return str(self)

    def __str__(self):
        return str(self.dpid)

class Match(object):
    def __init__(self, nw_src=None, nw_dst=None,
                 dl_src=None, dl_dst=None, dl_type=None):
        self.nw_src = nw_src
        self.nw_dst = nw_dst
        self.dl_src = dl_src
        self.dl_dst = dl_dst
        self.dl_type = dl_type

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "[{0},{1},{2},{3},{4}]".format(self.nw_src,
                                              self.nw_dst,
                                              self.dl_src,
                                              self.dl_dst,
                                              self.dl_type)
class OfMessage(object):
    def __init__(self, command=None, priority=1, switch=None,
                 match=None, actions=None):
        self.command = command
        self.priority = priority
        self.switch = switch
        self.match = match
        self.actions = actions
        if actions is None:
            self.actions = []

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "{0}: {1} {2}".format(self.command,
                                     self.switch,
                                     self.match)

class BarrierMessage(object):
    def __init__(self, dpid):
        self.dpid = dpid

connections = { Connection.Mq : MsgQueueConnection,
                Connection.Ovs : OvsConnection,
                Connection.Rpc : RpcConnection
         }
