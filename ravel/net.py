#!/usr/bin/env python
import os
import psycopg2
import socket
import sys
import time
import xmlrpclib
import sysv_ipc
import pickle
import json

PoxDir = "/home/croft1/src/pox"

import util

util.append_path(PoxDir)
from pox.lib.addresses import IPAddr
import pox.openflow.libopenflow_01 as of

ControllerPort = 6653
RpcAddress = "http://localhost:9000/"
QueueId = 123

OFPP_FLOOD = of.OFPP_FLOOD
OFPFC_ADD = of.OFPFC_ADD
OFPFC_DELETE = of.OFPFC_DELETE
OFPFC_DELETE_STRICT = of.OFPFC_DELETE_STRICT

class Context:
    Ocean = 0
    Mininet = 1

class Channel:
    Ovs = 0
    Rpc = 1
    Mq = 2
    MqProfile = 3
    MqUnopt = 4

CurrentContext = Context.Mininet
CurrentChannel = Channel.Mq

def channelFactory(channel):
    return channels[channel]()

def installFlow(flowid, sw, ip1, mac1, ip2, mac2, outport, revoutport):
    channel = channelFactory(CurrentChannel)
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

    channel.send(msg1)
    channel.send(msg2)
    channel.send(arp1)
    channel.send(arp2)

def removeFlow(flowid, sw, ip1, mac1, ip2, mac2, outport, revoutport):
    raise Exception('Not implemented')
    channel = channelFactory(CurrentChannel)

class ChannelBase(object):
    def send(self, msg):
        pass

class MqChannel(ChannelBase):
    def __init__(self):
        self.mq = sysv_ipc.MessageQueue(QueueId, mode=07777)

    def send(self, msg):
        p = json.dumps(msg.to_dict(msg.switch.dpid))
        self.mq.send(p)

class OvsChannel(ChannelBase):
    command = "/usr/bin/sudo /usr/bin/ovs-ofctl"
    subcmds = { OFPFC_ADD : "add-flow",
                OFPFC_DELETE : "del-flows",
                OFPFC_DELETE_STRICT : "--strict del-flows"
    }

    def __init__(self):
        pass

    def send(self, msg):
        subcmd = OvsChannel.subcmds[msg.command]

        # TODO: need to modify this for remote switches
        dest = msg.switch.name

        match = ""
        if msg.nw_src:
            match += "nw_src={0}".format(msg.nw_src)
        if msg.nw_dst:
            match += "nw_dst={0}".format(msg.nw_dst)
        if msg.dl_type:
            match += "dl_type={0}".format(msg.dl_type)

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

        cmd = "{0} {1} {2} {3}".format(OvsChannel.command,
                                       subcmd,
                                       dest,
                                       params)

        return os.system(cmd)

class RpcChannel(ChannelBase):
    def __init__(self):
        self.proxy = xmlrpclib.ServerProxy(RpcAddress, allow_none=True)

    def set_addr(addr):
        self.proxy = xmlrpclib.ServerProxy(addr, allow_none=True)

    def send(self, msg):
        self.proxy.sendFlowmod(msg.to_dict(msg.switch.dpid))

class Switch(object):
    def __init__(self, name, ip, dpid):
        self.name = name
        self.ip = ip
        self.dpid = dpid

class Match(object):
    def __init__(self, nw_src=None, nw_dst=None, dl_src=None, dl_dst=None, dl_type=None):
        self.nw_src = nw_src
        self.nw_dst = nw_dst
        self.dl_src = dl_src
        self.dl_dst = dl_dst
        self.dl_type = dl_type

    def to_dict(self):
        d = {}
        if self.nw_src:
            d['nw_src'] = self.nw_src
        if self.nw_dst:
            d['nw_dst'] = self.nw_dst
        if self.dl_src:
            d['dl_src'] = self.dl_src
        if self.dl_dst:
            d['dl_dst'] = self.dl_dst
        if self.dl_type:
            d['dl_type'] = self.dl_type
        return d

class OfMessage(object):
    def __init__(self, command=None, priority=1, switch=None,
                 match=None, actions=None):
        self.command = command
        self.priority = priority
        self.switch = switch
        self.match = match
        self.actions = actions
        if not actions:
            self.actions = []

    def to_dict(self, switch_prop):
        d = {}
        d['match'] = self.match.to_dict()
        d['command'] = self.command
        d['priority'] = self.priority
        d['switch'] = switch_prop
        d['actions'] = self.actions
        return d

channels = { Channel.Mq : MqChannel,
             Channel.Ovs : OvsChannel,
             Channel.Rpc : RpcChannel
         }
