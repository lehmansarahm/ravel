#!/usr/bin/env python

OFPC_FLOW_STATS = 1
OFPC_TABLE_STATS = 2
OFPC_PORT_STATS = 4

OFPFC_ADD = 0
OFPFC_MODIFY = 1
OFPFC_MODIFY_STRICT = 2
OFPFC_DELETE = 3
OFPFC_DELETE_STRICT = 4

OFPP_MAX = 65280
OFPP_IN_PORT = 65528
OFPP_TABLE = 65529
OFPP_NORMA = 65530
OFPP_FLOOD = 65531
OFPP_ALL = 65532
OFPP_CONTROLLER = 65533
OFPP_LOCAL = 65534
OFPP_NONE = 65535

class OfManager(object):
    def __init__(self):
        self.receiver = []

    def registerReceiver(self, receiver):
        self.receiver.append(receiver)

    def stop(self):
        for receiver in self.receiver:
            receiver.stop()

    def isRunning(self):
        pass

    def sendBarrier(self, dpid):
        pass

    def sendFlowmod(self, msg):
        pass

    def requestStats(self):
        pass
