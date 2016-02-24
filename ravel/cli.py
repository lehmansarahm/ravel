#!/usr/bin/env python

import cmd
import getpass
import os
import psycopg2
import sys
import tabulate
import tempfile
from functools import partial

from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import RemoteController

import mndeps
import db
import util
from env import Environment, Application, Emptynet
from log import logger

BASE_SQL = util.libpath("ravel/sql/primitive.sql")
FLOW_SQL = util.libpath("ravel/sql/flows.sql")

# TODO: move to config
APP_DIR = util.libpath("apps")

# TODO: move into net-type module, different from net triggers
def name2dbid(db, host):
    cursor = db.connect().cursor()
    cursor.execute("SELECT u_hid FROM uhosts WHERE hid="
                   "(SELECT hid FROM hosts WHERE name='{0}');"
                   .format(host))
    result = cursor.fetchall()
    if len(result) == 0:
        logger.warning("Unknown host %s", host)
        return None
    else:
        return result[0][0]

def addFlow(db, h1, h2):
    hid1 = name2dbid(db, h1)
    hid2 = name2dbid(db, h2)

    if hid1 is None or hid2 is None:
        return None

    cursor = db.connect().cursor()
    cursor.execute("SELECT * FROM rtm;")
    fid = len(cursor.fetchall()) + 1
    cursor.execute("INSERT INTO rtm (fid, host1, host2) "
                   "VALUES ({0}, {1}, {2});"
                   .format(fid, hid1, hid2))

    return fid

def delFlowById(db, fid):
    cursor = db.connect().cursor()

    # does the flow exist?
    cursor.execute("SELECT fid FROM rtm WHERE fid={0}".format(fid))
    if len(cursor.fetchall()) == 0:
        logger.warning("No flow installed with fid %s", fid)
        return None

    cursor.execute("DELETE FROM rtm WHERE fid={0}".format(fid))
    return fid

def delFlowByHostname(db, h1, h2):
    # convert to fid, so we can report which fid is removed
    hid1 = name2dbid(db, h1)
    hid2 = name2dbid(db, h2)

    if hid1 is None or hid2 is None:
        return None

    cursor = db.connect().cursor()
    cursor.execute("SELECT fid FROM rtm WHERE host1={0} and host2={1};"
                   .format(hid1, hid2))

    result = cursor.fetchall()
    if len(result) == 0:
        logger.warning("No flow installed for hosts {0},{1}".format(h1, h2))
        return None

    return delFlowById(db, result[0][0])

class RavelConsole(cmd.Cmd):
    prompt = "ravel> "
    intro = "RavelConsole: interactive console for Ravel."
    doc_header = "Commands (type help <topic>):"

    def __init__(self, env):
        self.env = env
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

        fid = addFlow(self.env.db, args[0], args[1])
        if fid is not None:
            print "Success: installed flow with fid", fid
        else:
            print "Failure: flow not installed"

    def do_delflow(self, line):
        args = line.split()

        if len(args) == 1:
            fid = delFlowById(self.env.db, args[0])
        elif len(args) == 2:
            fid = delFlowByHostname(self.env.db, args[0], args[1])
        else:
            print "Invalid syntax"
            return

        if fid is not None:
            print "Success: removed flow with fid", fid
        else:
            print "Failure: flow not removed"

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

    def do_unload(self, line):
        apps = line.split()
        for app in apps:
            if app in self.env.apps:
                self.env.unload_app(app)
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

    def do_watch(self, line):
        if not line:
            return

        args = line.split()
        if len(args) == 0 or len(args) > 2:
            print "Invalid syntax"
            return

        limit = ""
        if len(args) == 2:
            limit = "LIMIT {0}".format(args[1])

        query = "'SELECT * FROM {0} {1}'".format(args[0], limit)
        watch_arg = 'echo {0}: {1}; psql -U{3} -d {0} -c {2}'.format(
            self.env.db.name, args[0], query, self.env.db.user)
        watch = 'watch -c -n 2 --no-title "{0}"'.format(watch_arg)
        self.env.mkterm('xterm -e ' + watch)

    def do_EOF(self, line):
        "Quit Ravel console"
        sys.stdout.write('\n')
        return True

    def do_exit(self, line):
        "Quit Ravel console"
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
        print"         delflow [flow id]"
        print "-- remove flow between host1 and host2 (mininet names)."
        print "   specify src, dst or flow id"

    def help_load(self):
        print "syntax: load [application]"
        print "-- start an application"

    def help_m(self):
        print "syntax: m [mininet cmd]"
        print "-- run mininet command"

    def help_p(self):
        print "syntax: p [sql statement]"
        print "-- execute PostgreSQL statement"

    def help_watch(self):
        print "syntax: watch [table] [optional: max_rows]"
        print "-- launch another terminal to watch db table in real-time"

def RavelCLI(opts):
    if opts.custom:
        mndeps.custom(opts.custom)

    topo = mndeps.build(opts.topo)
    if opts.onlydb:
        net = Emptynet(topo)
    elif opts.remote:
        net = Mininet(topo,
                      controller=partial(RemoteController, ip='127.0.0.1'))
    else:
        net = Mininet(topo)

    passwd = None
    if opts.password:
        passwd = getpass.getpass("Enter password: ")

    raveldb = db.RavelDb(opts.db, opts.user, BASE_SQL, passwd)

    if opts.remote:
        util.update_trigger_path(FLOW_SQL, util.libpath())
        raveldb.load_schema(FLOW_SQL)

    env = Environment(raveldb, net, [APP_DIR])
    env.start()

    while True:
        try:
            RavelConsole(env).cmdloop()
            break
        except Exception, e:
            logger.warning("console crashed: %s", e)

    env.stop()
