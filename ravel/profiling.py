#!/usr/bin/env python

import pickle
import sysv_ipc
import threading
import time
from collections import OrderedDict

import ravel.messaging
from ravel.log import logger

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
    try:
        shm = sysv_ipc.SharedMemory(ProfileQueueId)
        return shm.read().strip('\0') == ProfileOn
    except sysv_ipc.ExistentialError, e:
        logger.warning("profile queue doesn't exist: %", e)
        return False

class PerfCounter(object):
    def __init__(self, name, time_ms=None):
        self.name = name
        self.start_time = None
        self.time_ms = time_ms
        if self.time_ms is not None:
            self.time_ms = round(float(time_ms), 3)

    def start(self):
        if is_profiled():
            self.start_time = time.time()

    def stop(self):
        if self.start_time is not None:
            self.time_ms = round((time.time() - self.start_time) * 1000, 3)
            self.report()

    def consume(self, consumer):
        consumer.handler(self)

    def report(self):
        try:
            mq = sysv_ipc.MessageQueue(ProfileQueueId, mode=0777)
            mq.send(pickle.dumps(self))
        except Exception, e:
            print e

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "{0}:{1}".format(self.name, self.time_ms)

class ProfiledExecution(object):
    def __init__(self):
        self.counters = []
        self.receiver = ravel.messaging.MsgQueueReceiver(ProfileQueueId, self)

    def print_summary(self):
        if len(self.counters) == 0:
            print "No performance counters found"
            return

        agg = OrderedDict()
        summ = 0
        print "-" * 40
        for counter in self.counters:
            summ += counter.time_ms

            if counter.name not in agg.keys():
                agg[counter.name] = (1, counter.time_ms)
            else:
                count,ms =  agg[counter.name]
                agg[counter.name] = (count + 1, ms + counter.time_ms)

        for counter, tup in agg.iteritems():
            print "{0}({1}): {2}ms".format(counter, tup[0], tup[1])

        print "-" * 40
        print "Total: {0}ms".format(summ)

    def start(self):
        enable_profiling()
        self.receiver.start()

    def stop(self):
        self.receiver.stop()
        disable_profiling()

    def handler(self, obj):
        if obj is not None:
            self.counters.append(obj)
