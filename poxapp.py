#!/usr/bin/env python

import pox.openflow.libopenflow_01 as of
from pox.core import core
from pox.lib.recoco import *
from pox.lib.revent import *
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.util import dpid_to_str
from pox.lib.util import str_to_dpid

from ravel.util import Config
from ravel.profiling import PerfCounter
from ravel.pubsub import Subscriber, MsgQueueProtocol, RpcProtocol
from ravel.of import OfManager

log = core.getLogger()

class PoxManager(OfManager):
    def __init__(self, log):
        super(PoxManager, self).__init__()
        self.log = log
        self.datapaths = {}
        self.flowstats = []
        self.perfcounter = PerfCounter('sw_delay')

        core.openflow.addListeners(self, priority=0)
        self.log.info("ravel: starting pox manager")

        def startup():
            self.log.info("registering handlers")
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
        self.perfcounter.stop()
        self.log.debug("received barrier")

    def _handle_FlowStatsReceived(self, event):
        self.log.info("ravel: flow stat received dpid={0}, len={1}".format(
            event.connection.dpid, len(event.stats)))
        for stat in event.stats:
            self.log.info("   flow: nw_src={0}, nw_dst={1}".format(
                stat.match.nw_src, stat.match.nw_dst))

    def requestStats(self):
        self.flowstats = []
        for connection in core.openflow._connections.values():
            connection.send(of.ofp_stats_request(body=of.ofp_flow_stats_request()))

        self.log.debug("ravel: sent {0} flow stats requests".format(
            len(core.openflow._connections)))

        return True

    def sendBarrier(self, dpid):
        dpid = int(dpid)
        if dpid in self.datapaths:
            dp = self.datapaths[dpid]
            msg = of.ofp_barrier_request()
            dp.send(msg)
            self.perfcounter.start()
            self.log.debug("dpid {0} sent barrier".format(dpid))
        else:
            self.log.debug("dpid {0} not in datapath list".format(dpid))
        return True

    def registerSubscriber(self, subscriber):
        self.log.info("registering adapter")
        self.subscribers.append(subscriber)
        subscriber.start()
        core.addListener(pox.core.GoingDownEvent, subscriber.stop)

    def isRunning(self):
        return core.running

    def mk_msg(self, flow):
        msg = of.ofp_flow_mod()
        msg.command = int(flow.command)
        msg.priority = int(flow.priority)
        msg.match = of.ofp_match()
        if flow.match.dl_type is not None:
            msg.match.dl_type = int(flow.match.dl_type)
        if flow.match.nw_src is not None:
            msg.match.nw_src = IPAddr(flow.match.nw_src)
        if flow.match.nw_dst is not None:
            msg.match.nw_dst = IPAddr(flow.match.nw_dst)
        if flow.match.dl_src is not None:
            msg.match.dl_src = EthAddr(flow.match.dl_src)
        if flow.match.dl_dst is not None:
            msg.match.dl_dst = EthAddr(flow.match.dl_dst)
        for outport in flow.actions:
            msg.actions.append(of.ofp_action_output(port=int(outport)))
        return msg

    def send(self, dpid, msg):
        self.log.debug("ravel: flow mod dpid={0}".format(dpid))
        if dpid in self.datapaths:
            dp = self.datapaths[dpid]
            dp.send(msg)
        else:
            self.log.debug("dpid {0} not in datapath list".format(dpid))

    def sendFlowmod(self, flow):
        dpid = int(flow.switch.dpid)
        self.send(dpid, self.mk_msg(flow))

def launch():
    ctrl = PoxManager(log)
    mq = Subscriber(MsgQueueProtocol(Config.QueueId, ctrl))
    ctrl.registerSubscriber(mq)
    rpc = Subscriber(RpcProtocol(Config.RpcHost, Config.RpcPort, ctrl))
    ctrl.registerSubscriber(rpc)
    core.register("ravelcontroller", ctrl)
