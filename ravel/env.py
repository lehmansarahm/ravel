#!/usr/bin/env python

import importlib
import os
import subprocess

import mininet.clean

from log import logger, LEVELS
import util

class Application(object):
    def __init__(self, name):
        self.name = name
        self.shortcut = ""
        self.description = ""
        self.pyfile = None
        self.sqlfile = None
        self.module = None

    def link(self, filename):
        if filename.endswith(".py"):
            self.pyfile = filename
        elif filename.endswith(".sql"):
            self.sqlfile = filename

    def is_loadable(self):
        return self.module is not None

    def init(self):
        if not self.pyfile:
            return

        # if needed, add path
        filepath = os.path.dirname(self.pyfile)
        util.append_path(filepath)

        try:
            self.module = importlib.import_module(self.name)
        except BaseException, e:
            errstr = "{0}: {1}".format(type(e).__name__, str(e))
            print errstr

        try:
            self.shortcut = self.module.shortcut
            self.description = self.module.description
        except BaseException:
            pass

    def cmd(self, line):
        if self.module:
            self.module.console.onecmd(line)

class Environment(object):
    def __init__(self, db, net, appdirs):
        self.db = db
        self.net = net
        self.appdirs = appdirs
        self.apps = {}
        self.loaded = {}
        self.discover()
        self.xterms = []

    def start(self):
        self.net.start()
        self.db.load_topo(self.net)

    def stop(self):
        self.net.stop()
        logger.debug("cleaning up mininet")
        mininet.clean.cleanup()

        if len(self.xterms) > 0:
            logger.debug("waiting for xterms")

        for t in self.xterms:
            t.wait()

    def mkterm(self, cmds):
        p = subprocess.Popen(cmds,
                             shell=True,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE)
        self.xterms.append(p)

    def load_app(self, appname):
        if appname in self.loaded:
            return

        # for newly-added applications
        self.discover()

        if appname in self.apps:
            app = self.apps[appname]
            if app.is_loadable():
                self.loaded[app.name] = app
                self.loaded[app.shortcut] = app

    def discover(self):
        for d in self.appdirs:
            for f in os.listdir(d):
                if f.endswith(".py"): # or sql
                    name = os.path.splitext(f)[0]
                    path = os.path.join(d, f)
                    if name not in self.apps:
                        self.apps[name] = Application(name)
                    self.apps[name].link(path)

        for app in self.apps.values():
            app.init()
