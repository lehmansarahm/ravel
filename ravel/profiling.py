#!/usr/bin/env python

import json
import sysv_ipc
import threading
import time
from collections import OrderedDict

from log import logger

ProfileQueueId = 99999
ProfileOff = "1"
ProfileOn = "2"

def enable_profiling():
    shm = sysv_ipc.SharedMemory(ProfileQueueId,
                                flags=sysv_ipc.IPC_CREAT,
                                mode=0777,
                                size=sysv_ipc.PAGE_SIZE,
                                init_character=' ')
    shm.write(str(ProfileOn))
    shm.detach()

def disable_profiling():
    shm = sysv_ipc.SharedMemory(ProfileQueueId,
                                flags=sysv_ipc.IPC_CREAT,
                                mode=07777,
                                size=sysv_ipc.PAGE_SIZE,
                                init_character=' ')
    shm.write(str(ProfileOff))
    shm.detach()

def is_profiled():
    shm = sysv_ipc.SharedMemory(ProfileQueueId)
    return shm.read().strip('\0') == ProfileOn

class PerfCounter(object):
    def __init__(self, name, time_ms=None):
        self.name = name
        self.time_ms = time_ms
        self.start_time = None

    def start(self):
        if is_profiled():
            self.start_time = time.time()

    def stop(self):
        if self.start_time is not None:
            self.time_ms = round((time.time() - self.start_time) * 1000, 3)
        self.report()

    def report(self):
        try:
            mq = sysv_ipc.MessageQueue(ProfileQueueId, mode=0777)
            mq.send(self.to_json())
        except Exception, e:
            print e

    def to_json(self):
        return json.dumps((self.name, self.time_ms))

    @classmethod
    def from_json(cls, obj):
        (name, time_ms) = json.loads(obj)
        return PerfCounter(name, time_ms)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "{0}:{1}".format(self.name, self.time_ms)

class ProfiledExecution(object):
    def __init__(self):
        self.counters = []
        # clear existing messages
        mq = sysv_ipc.MessageQueue(ProfileQueueId, sysv_ipc.IPC_CREAT,
                                   mode=0777)
        mq.remove()

        self.mq = sysv_ipc.MessageQueue(ProfileQueueId, sysv_ipc.IPC_CREAT,
                                        mode=0777)

    def print_summary(self):
        agg = OrderedDict()
        summ = 0
        for counter in self.counters:
            summ += counter.time_ms

            if counter.name not in agg.keys():
                agg[counter.name] = (1, counter.time_ms)
            else:
                count,ms =  agg[counter.name]
                agg[counter.name] = (count + 1, ms + counter.time_ms)

        for counter, tup in agg.iteritems():
            print "{0}({1}): {2}ms".format(counter, tup[0], tup[1])
        print "Total: {0}ms".format(summ)

    def stop(self):
        self.running = False
        self.mq.send(json.dumps(None))
        disable_profiling()

    def start(self):
        enable_profiling()
        self.running = True
        t = threading.Thread(target=self.run)
        t.start()

    def run(self):
        logger.debug("starting profile mq server")
        while self.running:
            try:
                s,_ = self.mq.receive()
                p = s.decode()
                if p is not None and p != "null":
                    counter = PerfCounter.from_json(p)
                    self.counters.append(counter)
            except ExistentialError, e:
                logger.debug(e)
