#!/usr/bin/env python

import ConfigParser
import os
import pickle
import re
import sys
import threading
import sysv_ipc
from sysv_ipc import ExistentialError

from log import logger

def libpath(path=None):
    install_path = os.path.dirname(os.path.abspath(__file__))
    install_path = os.path.normpath(
        os.path.join(install_path, ".."))

    if not path:
        return install_path

    return os.path.normpath(os.path.join(install_path, path))

def update_trigger_path(filename, path):
    if not os.path.isfile(filename):
        logger.warning("cannot find sql file %s", filename)
        return

    with open(filename, 'r') as f:
        lines = []
        content = f.read()

    newstr = "sys.path.append('{0}')".format(path)
    pattern = re.compile(r"sys.path.append\(\S+\)")
    content = re.sub(pattern, newstr, content)

    open(filename, 'w').write(content)

def append_path(path):
    if 'PYTHONPATH' not in os.environ:
        os.environ['PYTHONPATH'] = ""

    sys.path = os.environ['PYTHONPATH'].split(':') + sys.path

    if path is None or path == "":
        path = "."

    if path not in sys.path:
        sys.path.append(path)

class MsgQueueReceiver(object):
    def __init__(self, queue_id, stopmsg, msg_handler, continue_cb, log):
        self.stopmsg = stopmsg
        self.msg_handler = msg_handler
        self.continue_cb = continue_cb
        self.log = log
        mq = sysv_ipc.MessageQueue(queue_id, sysv_ipc.IPC_CREAT,
                                   mode=0777)
        mq.remove()

        self.mq = sysv_ipc.MessageQueue(queue_id, sysv_ipc.IPC_CREAT,
                                        mode=0777)

    def start(self):
        t = threading.Thread(target=self._run)
        t.start()

    def shutdown(self):
        self.mq.send(pickle.dumps(self.stopmsg))

    def _run(self):
        while self.continue_cb():
            self.log.debug("mq_server: waiting for message")
            try:
                s,_ = self.mq.receive()
                p = s.decode()
                obj = pickle.loads(p)
                self.log.debug("mq_server: received %s", len(p))
                self.msg_handler(obj)
            except ExistentialError, e:
                self.log.warning(e)

        self.log.debug("mq_server: done")

class Connection:
    Ovs = 0
    Rpc = 1
    Mq = 2
    Names = { "ovs" : Ovs,
              "rpc" : Rpc,
              "mq" : Mq
          }

class ConfigParameters(object):
    def __init__(self):
        self.RpcHost = None
        self.RpcPort = None
        self.QueueId = None
        self.Connection = None
        self.PoxDir = None
        self.read(libpath("ravel.cfg"))

    def read(self, cfg):
        parser = ConfigParser.SafeConfigParser()
        parser.read(cfg)

        if parser.has_option("of_manager", "poxdir"):
            self.PoxDir = parser.get("of_manager", "poxdir")

        if parser.has_option("of_manager", "connection"):
            name = parser.get("of_manager", "connection").lower()
            self.Connection = Connection.Names[name]

        if parser.has_option("rpc", "rpchost"):
            self.RpcHost = parser.get("rpc", "rpchost")
        if parser.has_option("rpc", "rpcport"):
            self.RpcPort = parser.getint("rpc", "rpcport")

        if parser.has_option("mq", "queueid"):
            self.QueueId = parser.getint("mq", "queueid")

Config = ConfigParameters()
