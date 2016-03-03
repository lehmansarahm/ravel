#!/usr/bin/env python

import cmd
import importlib
import os
import re
import sys

import psycopg2
import sqlparse
from sqlparse.tokens import Keyword

import ravel.util
from ravel.log import logger

class SqlObjMatch(object):
    def __init__(self, typ, regex, group):
        self.typ = typ
        self.regex = regex
        if not isinstance(group, list):
            self.group = [group]
        else:
            self.group = group

    def match(self, stmt):
        m = re.search(self.regex, stmt, re.IGNORECASE)
        if m:
            name = ""
            for num in self.group:
                name += m.group(num)
            return name
        return None

sqlComponents = []
sqlComponents.append(SqlObjMatch(
    "view",
    r'(create|drop).* view( if exists)? (\w+)',
    3))
sqlComponents.append(SqlObjMatch(
    "function",
    r'(create|drop).* function.*? (\w+)(\(.*\))',
    [2,3]))
sqlComponents.append(SqlObjMatch(
    "table",
    r'(create|drop).* table( if exists)?( if not exists)? (\w+)',
    4))

def discoverComponents(sql):
    components = []
    parsed = sqlparse.parse(sql)
    for statement in parsed:
        for token in statement.tokens:
            name = None
            typ = None
            for comp in sqlComponents:
                if token.match(Keyword, comp.typ):
                    name = comp.match(str(statement))
                    typ = comp.typ

            if name is not None:
                component = AppComponent(name, typ)
                if component not in components:
                    components.append(component)

    return components

class AppConsole(cmd.Cmd):
    def __init__(self, cursor):
        self.cursor = cursor
        cmd.Cmd.__init__(self)

    def emptyline(self):
        return

    def do_EOF(self, line):
        "Quit application console"
        sys.stdout.write('\n')
        return True

    def do_exit(self, line):
        "Quit application console"
        return True

class AppComponent(object):
    def __init__(self, name, typ):
        self.name = name
        self.typ = typ

    def drop(self, db):
        try:
            cmd = "DROP {0} IF EXISTS {1} CASCADE;".format(self.typ, self.name)
            db.cursor.execute(cmd)
            logger.debug("removing component: %s", cmd)
        except Exception, e:
            logger.error("error removing component {0}: {1}"
                         .format(self.name, e))

    def __eq__(self, other):
        return (isinstance(other, self.__class__)) \
            and self.name == other.name and self.typ == other.typ

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "{1}:{0}".format(self.name, self.typ)

class Application(object):
    def __init__(self, name):
        self.name = name
        self.shortcut = None
        self.description = ""
        self.pyfile = None
        self.sqlfile = None
        self.module = None
        self.components = []
        self.console = None

    def link(self, filename):
        if filename.endswith(".py"):
            self.pyfile = filename
        elif filename.endswith(".sql"):
            self.sqlfile = filename

    def is_loadable(self):
        return self.module is not None

    def load(self, db):
        with open(self.sqlfile) as f:
            try:
                db.cursor.execute(f.read())
            except psycopg2.ProgrammingError, e:
                print "Error loading app {0}: {1}".format(self.name, e)

        logger.debug("loaded application %s", self.name)

    def unload(self, db):
        for component in self.components:
            component.drop(db)

        logger.debug("unloaded application %s", self.name)

    def init(self, db):
        if not self.pyfile:
            return

        # if needed, add path
        filepath = os.path.dirname(self.pyfile)
        ravel.util.append_path(filepath)

        try:
            self.module = importlib.import_module(self.name)
            self.console =  self.module.console(db.cursor)

            # force module prompt to app name
            self.console.prompt = self.name + "> "
        except BaseException, e:
            errstr = "{0}: {1}".format(type(e).__name__, str(e))
            print errstr

        try:
            self.shortcut = self.module.shortcut
            self.description = self.module.description
        except BaseException:
            pass

        # discover sql components (tables, views, functions)
        with open(self.sqlfile) as f:
            self.components = discoverComponents(f.read())

        logger.debug("discovered {0} components: {1}"
                     .format(self.name, self.components))

    def cmd(self, line):
        if self.console:
            if line:
                self.console.onecmd(line)
            else:
                self.console.cmdloop()

    def _default_exit(self, line):
        return True

    def _default_EOF(self, line):
        sys.stdout.write('\n')
        return True

