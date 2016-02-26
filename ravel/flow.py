#!/usr/bin/env python

import os
import pickle
import threading
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer

import sysv_ipc
from mininet.net import macColonHex, netParse, ipAdd

from ravel.log import logger
from ravel.of import OFPP_FLOOD, OFPFC_ADD, OFPFC_DELETE, OFPFC_DELETE_STRICT
from ravel.profiling import PerfCounter
from ravel.pubsub import Publisher, MsgQueueProtocol, RpcProtocol, OvsProtocol
from ravel.util import Config, append_path, ConnectionType

protos = { ConnectionType.Mq : MsgQueueProtocol(Config.QueueId, None),
           ConnectionType.Rpc : RpcProtocol(Config.RpcHost, Config.RpcPort, None),
           ConnectionType.Ovs : OvsProtocol()
       }

def connectionFactory(conn):
    proto = protos[conn]
    return Publisher(proto)

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
    conn.send(BarrierMessage(sw.dpid))

def installFlow(flowid, sw, ip1, mac1, ip2, mac2, outport, revoutport):
    _send_msg(OFPFC_ADD,
              flowid, sw, ip1, mac1, ip2, mac2, outport, revoutport)

def removeFlow(flowid, sw, ip1, mac1, ip2, mac2, outport, revoutport):
    _send_msg(OFPFC_DELETE_STRICT,
              flowid, sw, ip1, mac1, ip2, mac2, outport, revoutport)

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

    def consume(self, consumer):
        consumer.sendFlowmod(self)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "{0}: {1} {2}".format(self.command,
                                     self.switch,
                                     self.match)

class BarrierMessage(object):
    def __init__(self, dpid):
        self.dpid = dpid

    def consume(self, consumer):
        consumer.sendBarrier(self.dpid)
