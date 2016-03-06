#!/usr/bin/env python

import os
import signal
import subprocess
import sys

import ravel.util
from ravel.log import logger

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

class PoxInstance(object):
    def __init__(self, app):
        self.app = app
        self.proc = None

    def start(self, cargs=None):
        pox = os.path.join(ravel.util.Config.PoxDir, "pox.py")
        if cargs is None:
            cargs = ["log.level",
                     "--DEBUG",
                     "openflow.of_01",
                     "--port=6633",
                     self.app]

        ravel.util.append_path(ravel.util.resource_file())
        env = os.environ.copy()
        env['PYTHONPATH'] = ":".join(sys.path)
        logger.debug("pox with params: %s", " ".join(cargs))
        self.proc = subprocess.Popen([pox] + cargs,
                                     env=env,
                                     stdout=open("/tmp/pox.log", "wb"),
                                     stderr=open("/tmp/pox.err", "wb"))

    def stop(self):
        if self.proc is not None:
            os.kill(self.proc.pid, signal.SIGINT)
