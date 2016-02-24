#!/usr/bin/env python

import os
import pickle
import sys
import threading
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer

import sysv_ipc

import util
from ravel.util import Config, Connection
util.append_path(Config.PoxDir)
import pox.openflow.libopenflow_01 as of

OFPP_FLOOD = of.OFPP_FLOOD
OFPFC_ADD = of.OFPFC_ADD
OFPFC_DELETE = of.OFPFC_DELETE
OFPFC_DELETE_STRICT = of.OFPFC_DELETE_STRICT

RpcAddress = "http://{0}:{1}".format(Config.RpcHost, Config.RpcPort)

def connectionFactory(conn):
    return connections[conn]()

def installFlow(flowid, sw, ip1, mac1, ip2, mac2, outport, revoutport):
    conn = connectionFactory(Config.Connection)
    msg1 = OfMessage(command=OFPFC_ADD,
                     priority=10,
                     switch=sw,
                     match=Match(nw_src=ip1, nw_dst=ip2, dl_type=0x0800),
                     actions=[outport])

    msg2 = OfMessage(command=OFPFC_ADD,
                     priority=10,
                     switch=sw,
                     match=Match(nw_src=ip2, nw_dst=ip1, dl_type=0x0800),
                     actions=[revoutport])

    arp1 = OfMessage(command=OFPFC_ADD,
                     priority=1,
                     switch=sw,
                     match=Match(dl_src=mac1, dl_type=0x0806),
                     actions=[OFPP_FLOOD])

    arp2 = OfMessage(command=OFPFC_ADD,
                     priority=1,
                     switch=sw,
                     match=Match(dl_src=mac2, dl_type=0x0806),
                     actions=[OFPP_FLOOD])

    conn.send(msg1)
    conn.send(msg2)
    conn.send(arp1)
    conn.send(arp2)

    print arp1
    print arp2


def removeFlow(flowid, sw, ip1, mac1, ip2, mac2, outport, revoutport):

    conn = connectionFactory(Config.Connection)
    msg1 = OfMessage(command=OFPFC_DELETE_STRICT,
                     priority=10,
                     switch=sw,
                     match=Match(nw_src=ip1, nw_dst=ip2, dl_type=0x0800),
                     actions=[outport])

    msg2 = OfMessage(command=OFPFC_DELETE_STRICT,
                     priority=10,
                     switch=sw,
                     match=Match(nw_src=ip2, nw_dst=ip1, dl_type=0x0800),
                     actions=[revoutport])

    arp1 = OfMessage(command=OFPFC_DELETE_STRICT,
                     priority=1,
                     switch=sw,
                     match=Match(dl_src=mac1, dl_type=0x0806),
                     actions=[OFPP_FLOOD])

    arp2 = OfMessage(command=OFPFC_DELETE_STRICT,
                     priority=1,
                     switch=sw,
                     match=Match(dl_src=mac2, dl_type=0x0806),
                     actions=[OFPP_FLOOD])

    conn.send(msg1)
    conn.send(msg2)
    conn.send(arp1)
    conn.send(arp2)

    print flowid, sw, ip1, mac1, ip2, mac2, outport, revoutport
    print arp1
    print arp2

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

    def run(self):
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

        mq = sysv_ipc.MessageQueue(Config.QueueId, sysv_ipc.IPC_CREAT,
                                   mode=0777)
        mq.remove()

        self.mq = sysv_ipc.MessageQueue(Config.QueueId, sysv_ipc.IPC_CREAT,
                                        mode=0777)

        t = threading.Thread(target=self.run)
        t.start()

    def shutdown(self, event=None):
        # send an empty message to pop out of while loop
        self.mq.send(pickle.dumps(OfMessage()))

    def run(self):
        while self.ctrl.isRunning():
            self.log.debug("mq_server: waiting for message")
            s,_ = self.mq.receive()
            p = s.decode()
            obj = pickle.loads(p)
            self.log.debug("mq_server: received {0}".format(len(p)))
            if obj is not None and obj.command is not None:
                self.ctrl.sendFlowmod(obj)

        self.log.debug("mq_server: done")

class AdapterConnection(object):
    def send(self, msg):
        pass

class MsgQueueConnection(AdapterConnection):
    def __init__(self):
        self.mq = sysv_ipc.MessageQueue(Config.QueueId, mode=07777)

    def send(self, msg):
        p = pickle.dumps(msg)
        self.mq.send(p)

class RpcConnection(AdapterConnection):
    def __init__(self, addr=RpcAddress):
        self.proxy = xmlrpclib.ServerProxy(addr, allow_none=True)

    def send(self, msg):
        p = pickle.dumps(msg)
        self.proxy.sendFlowmod(p)

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

        match = ""
        if msg.match.nw_src is not None:
            match += "nw_src={0}".format(msg.match.nw_src)
        if msg.match.nw_dst is not None:
            match += "nw_dst={0}".format(msg.match.nw_dst)
        if msg.match.dl_type is not None:
            match += "dl_type={0}".format(msg.match.dl_type)

        # remove trailing comma, don't know if we need it yet
        match = match[:-1]

        match = "priority={0}".format(msg.priority) + match
        action = ""
        if msg.command == OFPFC_ADD:
            action = "action=output:" + \
                     ",".join([str(a) for a in msg.actions])

        params = ""
        if len(match) > 1 and len(action) > 1:
            params = "{0},{1}".format(match, action)

        cmd = "{0} {1} {2} {3}".format(OvsConnection.command,
                                       subcmd,
                                       dest,
                                       params)

        return os.system(cmd)

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

connections = { Connection.Mq : MsgQueueConnection,
                Connection.Ovs : OvsConnection,
                Connection.Rpc : RpcConnection
         }
