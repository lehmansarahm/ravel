#!/usr/bin/env python

import importlib
import os
import re
import subprocess
import sys

import mininet.clean
import sqlparse
from sqlparse.tokens import Keyword

from log import logger, LEVELS
import util

class AppComponent(object):
    def __init__(self, name, typ):
        self.name = name
        self.typ = typ

    def __eq__(self, other):
        return (isinstance(other, self.__class__)) \
            and self.name == other.name and self.typ == other.typ

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "({1}:{0})".format(self.name, self.typ)

class Application(object):
    def __init__(self, name):
        self.name = name
        self.shortcut = None
        self.description = ""
        self.pyfile = None
        self.sqlfile = None
        self.module = None
        self.components = []

    def link(self, filename):
        if filename.endswith(".py"):
            self.pyfile = filename
        elif filename.endswith(".sql"):
            self.sqlfile = filename

    def is_loadable(self):
        return self.module is not None

    def load(self, db):
        cursor = db.connect().cursor()
        # TODO: error handle
        with open(self.sqlfile) as f:
            cursor.execute(f.read())

    def unload(self, db):
        cursor = db.connect().cursor()
        for component in self.components:
            cascade = ""
            if component.typ.lower() in ['table', 'view']:
                cascade = "CASCADE"
            cmd = "DROP {0} IF EXISTS {1} {2};".format(component.typ,
                                                       component.name,
                                                       cascade)
            cursor.execute(cmd)

    def init(self):
        if not self.pyfile:
            return

        # if needed, add path
        filepath = os.path.dirname(self.pyfile)
        util.append_path(filepath)

        try:
            self.module = importlib.import_module(self.name)

            # check if quit/EOF implemented
            if not "do_exit" in dir(self.module.console):
                self.module.console.do_exit = self._default_exit

            if not "do_EOF" in dir(self.module.console):
                self.module.console.do_EOF = self._default_EOF

            # force module prompt to app name
            self.module.console.prompt = self.name + "> "
        except BaseException, e:
            errstr = "{0}: {1}".format(type(e).__name__, str(e))
            print errstr

        try:
            self.shortcut = self.module.shortcut
            self.description = self.module.description
        except BaseException:
            pass

        # discover sql components (tables, views, functions)
        f = open(self.sqlfile)
        parsed = sqlparse.parse(f.read())
        f.close()

        obj_types = ["table", "view", "function"]
        for statement in parsed:
            for token in statement.tokens:
                typ = str(token)
                name = None

                if token.match(Keyword, "|".join(obj_types), regex=True):
                    name = str(statement.get_name())

                # sqlparse may parse postgres functions wrong, so use regex
                if token.match(Keyword, "function"):
                    m = re.search(r'(create|drop).* function.*? (\w+)(\(.*\))',
                                  str(statement),
                                  re.IGNORECASE)
                    if m:
                        name = m.group(2) + m.group(3)

                if name is not None:
                    component = AppComponent(name, typ)
                    if component not in self.components:
                        self.components.append(component)

    def cmd(self, line):
        if self.module:
            if line:
                self.module.console.onecmd(line)
            else:
                self.module.console.cmdloop()

    def _default_exit(self, line):
        return True

    def _default_EOF(self, line):
        sys.stdout.write('\n')
        return True

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
        for d in self.appdirs:
            for f in os.listdir(d):
                if f.endswith(".py") or f.endswith(".sql"):
                    name = os.path.splitext(f)[0]
                    path = os.path.join(d, f)
                    if name not in self.apps:
                        self.apps[name] = Application(name)
                    self.apps[name].link(path)

        for app in self.apps.values():
            app.init()
