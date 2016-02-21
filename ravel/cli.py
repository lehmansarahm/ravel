#!/usr/bin/env python

import cmd
import getpass
import os
import psycopg2
import sys
import tabulate
import tempfile

from mininet.cli import CLI
from mininet.net import Mininet

import mndeps
import db
from env import Environment, Application
from log import logger

#TODO: better reference
BASE_SQL="ravel/sql/primitive.sql"
APP_DIR="./apps"

class Flow(object):
    def __init__(self, db, h1, h2):
        self.db = db
        self.h1 = self._dbid(h1)
        self.h2 = self._dbid(h2)

    def _dbid(self, host):
        cursor = self.db.connect().cursor()
        cursor.execute("SELECT id FROM nodes WHERE name='{0}';"
                       .format(host))
        result = cursor.fetchall()
        if len(result) == 0:
            print "Unknown host", host
            return None
        else:
            return result[0][0]

    def insert(self):
        if not self.h1 or not self.h2:
            return

        cursor = self.db.connect().cursor()
        cursor.execute("SELECT * FROM utm;")
        fid = len(cursor.fetchall()) + 1
        cursor.execute("INSERT INTO utm (fid, host1, host2) "
                       "VALUES ({0}, {1}, {2});"
                       .format(fid, self.h1, self.h2))

    def remove(self):
        if not self.h1 or not self.h2:
            return

        cursor = self.db.connect().cursor()
        cursor.execute("DELETE FROM utm WHERE host1={0} and host2={1};"
                       .format(self.h1, self.h2))

class RavelConsole(cmd.Cmd):
    prompt = "ravel> "
    intro = "RavelConsole: interactive console for Ravel."
    doc_header = "Commands (type help <topic>):"

    def __init__(self, env):
        self.env = env
        self.env.start()
        cmd.Cmd.__init__(self)

    def default(self, line):
        cmd = line.split()[0]
        if cmd in self.env.loaded:
            self.env.loaded[cmd].cmd(line[len(cmd):])
        else:
            print '*** Unknown command: %s' % line

    def do_addflow(self, line):
        args = line.split()
        if len(args) != 2:
            print "Invalid syntax"
            return

        Flow(self.env.db, args[0], args[1]).insert()

    def do_delflow(self, line):
        args = line.split()
        if len(args) != 2:
            print "Invalid syntax"
            return

        Flow(self.env.db, args[0], args[1]).remove()

    def do_apps(self, line):
        "List available applications"
        for app in self.env.apps.values():
            shortcut = ""
            description = ""
            if app.shortcut:
                shortcut = " ({0})".format(app.shortcut)
            if app.description:
                description = ": {0}".format(app.description)

            print "  {0}{1}{2}".format(app.name, shortcut, description)

    def do_load(self, line):
        apps = line.split()
        for app in apps:
            if app in self.env.apps:
                self.env.load_app(app)
            else:
                print "Unknown application", app

    def do_m(self, line):
        if not line:
            CLI(self.env.net)
        else:
            temp = tempfile.NamedTemporaryFile(delete=False)
            temp.write(line)
            temp.close()
            CLI(self.env.net, script=temp.name)
            os.unlink(temp.name)

    def do_p(self, line):
        cursor = self.env.db.connect().cursor()
        try:
            cursor.execute(line)
        except psycopg2.ProgrammingError, e:
            print e
            return

        try:
            names = [row[0] for row in cursor.description]
            data = cursor.fetchall()
            print tabulate.tabulate(data, headers=names)
        except psycopg2.ProgrammingError:
            pass
        except TypeError, e:
            print e

    def do_reinit(self, line):
        "Reinitialize the database, deleting all data except topology"
        self.env.db.truncate()

    def do_EOF(self, line):
        "Quit Ravel console"
        sys.stdout.write('\n')
        self.env.stop()
        return True

    def do_exit(self, line):
        "Quit Ravel console"
        self.env.stop()
        return True

    def complete_load(self, text, line, begidx, endidx):
        apps = self.env.apps.keys()
        if not text:
            completions = apps
        else:
            completions = [d for d in apps if d.startswith(text)]

        return completions

    def help_addflow(self):
        print "syntax: addflow [node1] [host2]"
        print "-- add flow between host1 and host2 (mininet names)"

    def help_delflow(self):
        print "syntax: delflow [node1] [host2]"
        print "-- remove flow between host1 and host2 (mininet names)"

    def help_load(self):
        print "syntax: load [application]"
        print "-- start an application"

    def help_m(self):
        print "syntax: m [mininet cmd]"
        print "-- run mininet command"

    def help_p(self):
        print "syntax: p [sql statement]"
        print "-- execute PostgreSQL statement"

def RavelCLI(opts):
    if opts.custom:
        mndeps.custom(opts.custom)

    topo = mndeps.build(opts.topo)
    net = Mininet(topo)

    passwd = None
    if opts.password:
        passwd = getpass.getpass("Enter password: ")

    raveldb = db.RavelDb(opts.db, opts.user, BASE_SQL, passwd)
    env = Environment(raveldb, net, [APP_DIR])
    RavelConsole(env).cmdloop()
