#!/usr/bin/env python

import pickle
import threading
import time
import xmlrpclib
import sysv_ipc
from SimpleXMLRPCServer import SimpleXMLRPCServer

from ravel.log import logger
from ravel.of import OFPP_FLOOD, OFPFC_ADD, OFPFC_DELETE, OFPFC_DELETE_STRICT
from ravel.perf import PerfCounter

class Publisher(object):
    def __init__(self, proto):
        self.proto = proto
        self.proto.init_pub()

    def send(self, msg):
        p = pickle.dumps(msg)
        pc = PerfCounter(self.proto.name + "_send")
        pc.start()
        self.proto.send(p)
        pc.stop()

class Subscriber(object):
    def __init__(self, proto):
        self.proto = proto
        self.proto.init_sub()
        self.running = False

    def start(self, event=None):
        self.running = True
        self.t = threading.Thread(target=self._do)
        self.t.start()

    def _do(self):
        while self.running:
            msg = self.proto.receive()
            obj = pickle.loads(msg)
            if obj is not None:
                obj.consume(self.proto.consumer_obj)

    def stop(self, event=None):
        self.running = False
        self.proto.shutdown()

class PubsubProtocol(object):
    def init_sub(self):
        pass

    def init_pub(self):
        pass

    def send(self, msg):
        pass

    def receive(self):
        pass

    def shutdown(self):
        pass

class MsgQueueProtocol(PubsubProtocol):
    def __init__(self, queue_id, consumer_obj=None):
        self.name = "mq"
        self.queue_id = queue_id
        self.consumer_obj = consumer_obj

    def init_pub(self):
        # clear message queue
        self.mq = sysv_ipc.MessageQueue(self.queue_id,
                                        sysv_ipc.IPC_CREAT,
                                        mode=0777)
#        mq.remove()
#        self.mq = sysv_ipc.MessageQueue(self.queue_id,
#                                        sysv_ipc.IPC_CREAT,
#                                        mode=0777)

    def init_sub(self):
        try:
            self.mq = sysv_ipc.MessageQueue(self.queue_id, mode=0777)
        except sysv_ipc.ExistentialError, e:
            logger.warning("network provider queue doesn't exist, creating")
            self.mq = sysv_ipc.MessageQueue(self.queue_id,
                                            sysv_ipc.IPC_CREAT,
                                            mode=0777)

    def shutdown(self):
        self.mq.send(pickle.dumps(None))

    def send(self, msg):
        self.mq.send(msg)

    def receive(self):
        s,_ = self.mq.receive()
        return s.decode()

    def reset(self):
        self.mq.remove()
        self.mq = sysv_ipc.MessageQueue(self.queue_id,
                                        sysv_ipc.IPC_CREAT,
                                        mode=0777)

class RpcProtocol(PubsubProtocol):
    def __init__(self, host, port, consumer_obj=None):
        self.name = "rpc"
        self.host = host
        self.port = port
        self.addr = "http://{0}:{1}".format(self.host, self.port)
        self.consumer_obj = consumer_obj

    def init_pub(self):
        self.client = xmlrpclib.ServerProxy(self.addr, allow_none=True)

    def init_sub(self):
        self.server = SimpleXMLRPCServer((self.host, self.port),
                                         logRequests=False,
                                         allow_none=True)
        self.server.register_function(self._proxy_receive)

    def _proxy_receive(self, msg):
        print "yo"
        self.msg = msg

    def receive(self):
        self.server.handle_request()
        return self.msg

    def send(self, msg):
        self.client._proxy_receive(msg)

    def shutdown(self):
        proxy = xmlrpclib.ServerProxy(self.addr, allow_none=True)
        proxy._proxy_receive(pickle.dumps(None))

class OvsProtocol(PubsubProtocol):
    def __init__(self):
        pass

    command = "/usr/bin/sudo /usr/bin/ovs-ofctl"
    subcmds = { OFPFC_ADD : "add-flow",
                OFPFC_DELETE : "del-flows",
                OFPFC_DELETE_STRICT : "--strict del-flows"
    }

    def send(self, msg):
        # TODO: this is pretty ugly
        msg = pickle.loads(msg)

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
