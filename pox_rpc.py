#!/usr/bin/env python
#
# Script: poxxml.py
# Description:
#    Pox module with rpc server

import atexit
import pickle
import json
import posix_ipc
import sysv_ipc
import sys
import time
import threading
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer

import pox.openflow.libopenflow_01 as of
from pox.core import core
from pox.lib.recoco import *
from pox.lib.revent import *
from pox.lib.addresses import IPAddr, IPAddr6, EthAddr

from pox.lib.util import dpid_to_str
from pox.lib.util import str_to_dpid

log = core.getLogger()

class RavelPoxController(object):
    def __init__(self, log):
        self.log = log
        self.datapaths = {}
        self.flowstats = []

        self.timelast = None
        self.elapsed = None
        core.openflow.addListeners(self, priority=0)
        self.log.info("ravel: starting controller")

        def startup():
            self.log.info("registering hanlders")
            core.openflow_discovery.addListeners(self)

        core.call_when_ready(startup, ('openflow', 'openflow_discovery'))

    def _handle_ConnectionDown(self, event):
        self.log.info("ravel: dpid {0} removed".format(event.dpid))
        del self.datapaths[event.dpid]

    def _handle_ConnectionUp(self, event):
        self.log.info("ravel: dpid {0} online".format(event.dpid))
        self.datapaths[event.dpid] = event.connection
        self.log.info("----{0}".format(self.datapaths))

    def _handle_LinkEvent(self, event):
        if event.removed:
            self.log.info("Link down {0}".format(event.link))
        elif event.added:
            self.log.info("Link up {0}".format(event.link))

    def _handle_BarrierIn(self, event):
        self.log.debug("received barrier")
        if self.timelast is not None:
            self.elapsed = time.time() - self.timelast
            t = round(self.elapsed * 1000, 3)
            self.log.info("ravel: install time={0}ms".format(t))
            #f = open("/home/ravel/ravel/log.txt", "a")
            #f.write("switch -- {0}\n".format(t))
            #f.close()

    def _handle_FlowStatsReceived(self, event):
        self.log.info("ravel: flow stat received dpid={0}, len={1}".format(
            event.connection.dpid, len(event.stats)))
        for stat in event.stats:
            self.log.info("   flow: nw_src={0}, nw_dst={1}".format(
                stat.match.nw_src, stat.match.nw_dst))

    def mk_msg(self, command, priority, nw_src, nw_dst, outport):
        msg = of.ofp_flow_mod()
        msg.command = command
        msg.priority = priority
        msg.match = of.ofp_match()
        msg.match.nw_src = IPAddr(nw_src)
        msg.match.nw_dst = IPAddr(nw_dst)
        msg.match.dl_type = 0x0800
        msg.actions.append(of.ofp_action_output(port=outport))
        return msg

    def startTimer(self):
        self.timelast = time.time()

    def requestStats(self):
        self.flowstats = []
        for connection in core.openflow._connections.values():
            connection.send(of.ofp_stats_request(body=of.ofp_flow_stats_request()))

        self.log.debug("ravel: sent {0} flow stats requests".format(
            len(core.openflow._connections)))

        return True

    def send(self, dpid, msg):
        self.log.debug("ravel: flow mod dpid={0}".format(dpid))
        if dpid in self.datapaths:
            dp = self.datapaths[dpid]
            dp.send(msg)
        else:
            self.log.debug("dpid {0} not in datapath list".format(dpid))

    def sendBarrier(self, dpid):
        dpid = int(dpid)
        if dpid in self.datapaths:
            dp = self.datapaths[dpid]
            msg = of.ofp_barrier_request()
            dp.send(msg)
            self.log.debug("dpid {0} sent barrier".format(dpid))
        else:
            self.log.debug("dpid {0} not in datapath list".format(dpid))
        return True

    def removeFlow(self, dpid, priority, nw_src, nw_dst, outport):
        dpid = int(dpid)
        priority = int(priority)
        outport = int(outport)
        msg = self.mk_msg(of.OFPFC_DELETE_STRICT, priority, nw_src, nw_dst, outport)
        self.send(dpid, msg)
        return True

    def installFlow(self, dpid, priority, nw_src, nw_dst, outport):
        dpid = int(dpid)
        priority = int(priority)
        outport = int(outport)
        msg = self.mk_msg(of.OFPFC_ADD, priority, nw_src, nw_dst, outport)
        self.send(dpid, msg)
        return True

    def removeBidirectional(self, dpid, priority, nw_src, nw_dst, outport1, outport2):
        dpid = int(dpid)
        priority = int(priority)
        outport1 = int(outport1)
        outport2 = int(outport2)
        msg1 = self.mk_msg(of.OFPFC_DELETE_STRICT, priority, nw_src, nw_dst, outport1)
        msg2 = self.mk_msg(of.OFPFC_DELETE_STRICT, priority, nw_dst, nw_src, outport2)
        self.timelast = time.time()
        self.send(dpid, msg1)
        self.send(dpid, msg2)
        self.sendBarrier(dpid)

    def installBidirectional(self, dpid, priority, nw_src, nw_dst, outport1, outport2):
        dpid = int(dpid)
        priority = int(priority)
        outport1 = int(outport1)
        outport2 = int(outport2)
        msg1 = self.mk_msg(of.OFPFC_ADD, priority, nw_src, nw_dst, outport1)
        msg2 = self.mk_msg(of.OFPFC_ADD, priority, nw_dst, nw_src, outport2)
        self.timelast = time.time()
        self.send(dpid, msg1)
        self.send(dpid, msg2)
        self.sendBarrier(dpid)

class RpcAdapter():
    def __init__(self, ctrl, log):
        self.ctrl = ctrl
        self.log = log
        self.log.info("rpc_server: starting")
        self.server = SimpleXMLRPCServer(("localhost", 9000),
                                         logRequests=False,
                                         allow_none=True)

        self.server.register_function(self.ctrl.send)
        self.server.register_function(self.ctrl.installFlow)
        self.server.register_function(self.ctrl.installBidirectional)
        self.server.register_function(self.ctrl.removeBidirectional)
        self.server.register_function(self.ctrl.removeFlow)
        self.server.register_function(self.ctrl.requestStats)
        self.server.register_function(self.ctrl.sendBarrier)
        self.server.register_function(self.echo)
        core.addListener(pox.core.GoingDownEvent, self.handle_GoingDown)

        self.t = threading.Thread(target=self.run)
        self.t.start()

    def echo(self, string=None):
        # for testing
        self.log.debug("rpc_server: echo()")
        if string is not None:
            self.log.info(string)
        return True

    def handle_GoingDown(self, event):
        self.shutdown()

    def shutdown(self):
        # send rpc request to trigger handle request and end loop
        self.log.info("rpc_server: stopping")
        proxy = xmlrpclib.ServerProxy("http://localhost:9000/", allow_none=True)
        proxy.echo(None)

    def run(self):
        while core.running:
            self.log.debug("rpc_server: waiting for request")
            self.server.handle_request()

class MsgQueueAdapter():
    def __init__(self, ctrl, log):
        self.ctrl = ctrl
        self.log = log
        self.log.info("mq_server: starting")

        # clear any existing messages
        mq = sysv_ipc.MessageQueue(123, sysv_ipc.IPC_CREAT,
                                   mode=0777)
        mq.remove()

        self.mq = sysv_ipc.MessageQueue(123, sysv_ipc.IPC_CREAT,
                                        mode=0777)

        core.addListener(pox.core.GoingDownEvent, self.shutdown)
        t = threading.Thread(target=self.run)
        t.start()

    def shutdown(self, event):
        # send an empty message to pop out of while loop
        self.mq.send(json.dumps([]))

    def run(self):
        while core.running:
            self.log.debug("mq_server: waiting for message")
            s,_ = self.mq.receive()
            t = time.time()
            p = s.decode()
            #obj = pickle.loads(p)
            obj = json.loads(p)
            self.log.debug("mq_server: received {0}".format(len(obj)))
            for flow in obj:
                if flow[0] == of.OFPFC_ADD:
                    self.ctrl.startTimer()
                    self.ctrl.installFlow(flow[1],
                                          flow[2],
                                          flow[3],
                                          flow[4],
                                          flow[5])
                elif flow[0] == of.OFPFC_DELETE_STRICT:
                    self.ctrl.startTimer()
                    self.ctrl.removeFlow(flow[1],
                                         flow[2],
                                         flow[3],
                                         flow[4],
                                         flow[5])

            t = time.time() - t
            if len(obj) > 0:
                dpid = obj[0][1]
                self.ctrl.sendBarrier(dpid)
                t = round(1000 * t, 3)
                #f = open("/home/ravel/ravel/log.txt", "a")
                #f.write("pox -- {0}\n".format(t))
                #f.close()

        self.log.debug("mq_server: **shutdown**")

def launch():
    ctrl = RavelPoxController(log)
    mq = MsgQueueAdapter(ctrl, log)
    rpc = RpcAdapter(ctrl, log)

    core.register("ravelcontroller", ctrl)

