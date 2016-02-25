#!/usr/bin/env python

import pickle
import threading

import sysv_ipc

from ravel.log import logger

class ConnectionType:
    Ovs = 0
    Rpc = 1
    Mq = 2
    Name = { "ovs" : Ovs,
             "rpc" : Rpc,
             "mq" : Mq
         }

class MsgQueuePublisher(object):
    def __init__(self, queue_id):
        self.mq = sysv_ipc.MessageQueue(queue_id, mode=0777)

    def send(self, msg):
        p = pickle.dumps(msg)
        self.mq.send(p)

class MsgQueueSubscriber(object):
    def __init__(self, queue_id, msg_cb):
        self.msg_cb = msg_cb
        self.mq = self._create_queue(queue_id)
        self.running = False

    def _create_queue(self, qid):
        mq = sysv_ipc.MessageQueue(qid, sysv_ipc.IPC_CREAT, mode=0777)
        mq.remove()
        mq = sysv_ipc.MessageQueue(qid, sysv_ipc.IPC_CREAT, mode=0777)
        return mq

    def can_continue(self):
        return self.running

    def start(self):
        self.running = True
        t = threading.Thread(target=self._do)
        t.start()

    def stop(self):
        self.running = False
        self.mq.send(pickle.dumps(None))

    def _do(self):
        while self.running:
            logger.debug("mq_subscriber: waiting for message")
            try:
                s,_ = self.mq.receive()
                p = s.decode()
                obj = pickle.loads(p)
                if obj is not None:
                    self.msg_cb(obj)
            except sysv_ipc.ExistentialError, e:
                logger.warning(e)

        logger.debug("mq_subsriber: done")
