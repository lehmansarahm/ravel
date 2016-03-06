#!/usr/bin/env python

import os
import subprocess

import ravel.db
import ravel.util
from ravel.app import Application
from ravel.log import logger

class Environment(object):
    def __init__(self, db, provider, appdirs, params, enable_flows):
        self.db = db
        self.appdirs = appdirs
        self.apps = {}
        self.loaded = {}
        self.xterms = []
        self.xterm_files = []
        self.params = params
        self.enable_flows = enable_flows
        self.provider = provider
        self.discover()

    def start(self):
        self.provider.start()

        # only load topo if connecting to a clean db
        if self.db.cleaned:
            self.db.load_topo(self.provider)
        else:
            logger.debug("connecting to existing db, skipping load_topo()")

        # TODO: eventually we will only run mininet as remote, so remove this
        if self.enable_flows:
            ravel.util.update_trigger_path(ravel.db.FLOW_SQL,
                                           ravel.util.resource_file())
            self.db.load_schema(ravel.db.FLOW_SQL)

        # delay loading of topo triggers until after db is loaded
        # we only want to catch updates
        ravel.util.update_trigger_path(ravel.db.TOPO_SQL,
                                       ravel.util.resource_file())

        self.db.load_schema(ravel.db.TOPO_SQL)

    def stop(self):
        self.provider.stop()
        if len(self.xterms) > 0:
            logger.debug("waiting for xterms")

        for t in self.xterms:
            t.wait()

        # delete xterm temp files
        for f in self.xterm_files:
            os.unlink(f)

    def mkterm(self, cmds, cmdfile=None):
        p = subprocess.Popen(cmds,
                             shell=True,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE)

        self.xterms.append(p)
        if cmdfile is not None:
            self.xterm_files.append(cmdfile)

    def unload_app(self, appname):
        app = self.apps[appname]
        app.unload(self.db)

        if app.name in self.loaded:
            del self.loaded[app.name]

        if app.shortcut is not None and app.shortcut in self.loaded:
            del self.loaded[app.shortcut]

    def load_app(self, appname):
        if appname in self.loaded:
            return

        # look for newly-added applications
        self.discover()

        if appname in self.apps:
            app = self.apps[appname]
            app.load(self.db)
            if app.is_loadable():
                self.loaded[app.name] = app
                if app.shortcut is not None:
                    self.loaded[app.shortcut] = app

    def discover(self):
        new = []

        for d in self.appdirs:
            for f in os.listdir(d):
                if f.endswith(".py") or f.endswith(".sql"):
                    name = os.path.splitext(f)[0]
                    path = os.path.join(d, f)
                    if name not in self.apps:
                        self.apps[name] = Application(name)
                        new.append(name)
                    self.apps[name].link(path)

        for name in new:
            self.apps[name].init(self.db, self)

    def pprint(self):
        out = ""
        pad = max([len(k) for k in self.params.keys()]) + 2
        for k,v in self.params.iteritems():
            key = "{0}:".format(k).ljust(pad, ' ')
            out += "  {0} {1}\n".format(key, v)
        return out
