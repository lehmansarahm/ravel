#!/usr/bin/env python

import os
import pickle
import threading
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer

import sysv_ipc
from mininet.net import macColonHex, netParse, ipAdd

from ravel.log import logger
from ravel.util import Config, append_path
from ravel.profiling import PerfCounter
from ravel.proto import MsgQueueSubscriber, ConnectionType

append_path(Config.PoxDir)
import pox.openflow.libopenflow_01 as of

OFPP_FLOOD = of.OFPP_FLOOD
OFPFC_ADD = of.OFPFC_ADD
OFPFC_DELETE = of.OFPFC_DELETE
OFPFC_DELETE_STRICT = of.OFPFC_DELETE_STRICT

RpcAddress = "http://{0}:{1}".format(Config.RpcHost, Config.RpcPort)

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
        self.subscribers = []

    def registerSubscriber(self, subscriber):
        self.subscribers.append(subscriber)

    def shutdown(self):
        for subscriber in self.subscribers:
            subscriber.shutdown()

    def isRunning(self):
        pass

    def sendBarrier(self, dpid):
        pass

    def sendFlowmod(self, msg):
        pass

    def requestStats(self):
        pass

class OfManagerSubscriber(object):
    def __init__(self, ctrl, log):
        self.ctrl = ctrl
        self.log = log
        self.running = False

    def shutdown(self, event):
        pass

class OfRpcSubscriber(OfManagerSubscriber):
    def __init__(self, ctrl, log):
        super(OfRpcSubscriber, self).__init__(ctrl, log)
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

class OfMsgQueueSubscriber(OfManagerSubscriber):
    def __init__(self, ctrl, log):
        self.ctrl = ctrl
        self.log = log
        super(OfMsgQueueSubscriber, self).__init__(ctrl, log)
        self.subscriber = MsgQueueSubscriber(Config.QueueId,
                                             self.msg_handler)
        self.subscriber.start()

    def shutdown(self, event=None):
        self.subscriber.stop()

    def msg_handler(self, msg):
        if isinstance(msg, BarrierMessage):
            self.ctrl.sendBarrier(msg.dpid)
        elif isinstance(msg, OfMessage) and msg.command is not None:
            self.ctrl.sendFlowmod(msg)
        else:
            self.log.debug("unexpected object {0}".format(msg))

class OfManagerPublisher(object):
    def send(self, msg):
        pass

    def sendBarrier(self, msg):
        pass

class OfMsgQueuePublisher(OfManagerPublisher):
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

class OfRpcPublisher(OfManagerPublisher):
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

class OfOvsPublisher(OfManagerPublisher):
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

connections = { ConnectionType.Mq : OfMsgQueuePublisher,
                ConnectionType.Ovs : OfOvsPublisher,
                ConnectionType.Rpc : OfRpcPublisher
         }
