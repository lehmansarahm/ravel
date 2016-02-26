#!/usr/bin/env python

from ravel.util import Config, append_path

append_path(Config.PoxDir)
import pox.openflow.libopenflow_01 as of

OFPP_FLOOD = of.OFPP_FLOOD
OFPFC_ADD = of.OFPFC_ADD
OFPFC_DELETE = of.OFPFC_DELETE
OFPFC_DELETE_STRICT = of.OFPFC_DELETE_STRICT

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
