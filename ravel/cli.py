#!/usr/bin/env python

import cmd
import getpass
import os
import psycopg2
import sys
import tabulate
import time
from functools import partial

import ravel.mndeps
import ravel.profiling
from ravel.db import RavelDb, BASE_SQL
from ravel.env import Environment
from ravel.log import logger
from ravel.util import resource_file

# TODO: move to config
APP_DIR = resource_file("apps")

# TODO: move into net-type module, different from net triggers
def name2dbid(db, host):
    db.cursor.execute("SELECT u_hid FROM uhosts WHERE hid="
                   "(SELECT hid FROM hosts WHERE name='{0}');"
                   .format(host))
    result = db.cursor.fetchall()
    if len(result) == 0:
        logger.warning("unknown host %s", host)
        return None
    else:
        return result[0][0]

def addFlow(db, h1, h2):
    hid1 = name2dbid(db, h1)
    hid2 = name2dbid(db, h2)

    if hid1 is None or hid2 is None:
        return None

    try:
        db.cursor.execute("SELECT * FROM rtm;")
        fid = len(db.cursor.fetchall()) + 1
        db.cursor.execute("INSERT INTO rtm (fid, host1, host2) "
                       "VALUES ({0}, {1}, {2});"
                       .format(fid, hid1, hid2))
        db.cursor.execute ("UPDATE tm set FW = 0 where fid = {0};"
                           .format(fid, hid1, hid2))
        return fid
    except Exception, e:
        print e
        return None

def delFlowById(db, fid):
    try:
        # does the flow exist?
        db.cursor.execute("SELECT fid FROM rtm WHERE fid={0}".format(fid))
        if len(db.cursor.fetchall()) == 0:
            logger.warning("no flow installed with fid %s", fid)
            return None

        db.cursor.execute("DELETE FROM rtm WHERE fid={0}".format(fid))
        return fid
    except Exception, e:
        print e
        return None

def delFlowByHostname(db, h1, h2):
    # convert to fid, so we can report which fid is removed
    hid1 = name2dbid(db, h1)
    hid2 = name2dbid(db, h2)

    if hid1 is None or hid2 is None:
        return None

    db.cursor.execute("SELECT fid FROM rtm WHERE host1={0} and host2={1};"
                      .format(hid1, hid2))

    result = db.cursor.fetchall()
    if len(result) == 0:
        logger.warning("no flow installed for hosts {0},{1}".format(h1, h2))
        return None

    return delFlowById(db, result[0][0])

class RavelConsole(cmd.Cmd):
    prompt = "ravel> "
    doc_header = "Commands (type help <topic>):"

    def __init__(self, env):
        self.env = env
        self.intro = "RavelConsole: interactive console for Ravel.\n" \
                     "Configuration:\n" + self.env.pprint()

        cmd.Cmd.__init__(self)

    def default(self, line):
        cmd = line.split()[0]
        if cmd in self.env.loaded:
            self.env.loaded[cmd].cmd(line[len(cmd):])
        else:
            print '*** Unknown command: %s' % line

    def emptyline(self):
        return

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

    def do_test(self, line):
        # placeholder for batch commands for testing
        cmds = ["p insert into switches (sid) values (5);",
                "p insert into hosts (hid) values (6);",
                "p insert into tp values (5, 6, 0, 1, 1);",
                "addflow h1 h2",
                "delflow h1 h2",
                "addflow h2 h9",
                "delflow h1 h9",
                "profile addflow h1 h2",
                "profile delflow h1 h2",
                "p delete from tp where sid=5 and nid=3;",
                "p delete from switches where sid=5;",
                "p delete from hosts where hid=6;",
        ]
        for c in cmds:
            print c
            self.onecmd(c)
            time.sleep(0.25)

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
        "List available applications and their status"
        for app in self.env.apps.values():
            shortcut = ""
            description = ""

            status = '\033[91m' + "[offline] " + '\033[0m'
            if app.name in self.env.loaded:
                status = '\033[92m' + "[online]  " + '\033[0m'
            if app.shortcut:
                shortcut = " ({0})".format(app.shortcut)
            if app.description:
                description = ": {0}".format(app.description)

            print "  {0} {1}{2}{3}".format(status, app.name,
                                           shortcut, description)

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
        self.env.provider.cli(line)

    def do_p(self, line):
        try:
            cursor = self.env.db.cursor
            cursor.execute(line)
        except psycopg2.ProgrammingError, e:
            print e
            return

        try:
            data = cursor.fetchall()
            if data is not None:
                names = [row[0] for row in cursor.description]
                print tabulate.tabulate(data, headers=names)
        except psycopg2.ProgrammingError:
            # no results, eg from an insert/delete
            pass
        except TypeError, e:
            print e

    def do_profile(self, line):
        "Run command and report detailed execution time"
        if line:
            pe = ravel.profiling.ProfiledExecution()
            pe.start()
            self.onecmd(line)

            # wait for straggling counters to report
            time.sleep(0.5)

            pe.stop()
            sys.stdout.write('\n')
            pe.print_summary()

    def do_reinit(self, line):
        "Reinitialize the database, deleting all data except topology"
        self.env.db.truncate()

    def do_stat(self, line):
        "Show running configuration, state"
        print self.env.pprint()

    def do_time(self, line):
        "Run command and report execution time"
        elapsed = time.time()
        if line:
            self.onecmd(line)
        elapsed = time.time() - elapsed
        print "\nTime: {0}ms".format(round(elapsed * 1000, 3))

    def do_watch(self, line):
        if not line:
            return

        args = line.split()
        if len(args) == 0:
            print "Invalid syntax"
            return

        cmd, cmdfile = ravel.app.mk_watchcmd(self.env.db, args)
        self.env.mkterm(cmd, cmdfile)

    def do_EOF(self, line):
        "Quit Ravel console"
        sys.stdout.write('\n')
        return True

    def do_exit(self, line):
        "Quit Ravel console"
        return True

    def do_help(self, arg):
        'List available commands with "help" or detailed help with "help cmd"'
        # extend help to include loaded apps and their help functions
        tokens = arg.split()
        appname = tokens[0]

        if appname in self.env.loaded:
            app = self.env.apps[appname]
            if len(tokens) <= 1:
                print app.description
                app.console.do_help("")
            else:
                app.console.do_help(" ".join(tokens[1:]))
        else:
            cmd.Cmd.do_help(self, arg)

    def completenames(self, text, *ignored):
        "Add loaded application names/shortcuts to cmd name completions"
        completions = cmd.Cmd.completenames(self, text, ignored)

        apps = self.env.loaded.keys()
        if not text:
            completions.extend(apps)
        else:
            completions.extend([d for d in apps if d.startswith(text)])

        return completions

    def complete_load(self, text, line, begidx, endidx):
        apps = self.env.apps.keys()
        if not text:
            completions = apps
        else:
            completions = [d for d in apps if d.startswith(text)]

        return completions

    def complete_unload(self, text, line, begidx, endidx):
        apps = self.env.apps.loaded.keys()
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
        print "syntax: load [app1] [app2] ..."
        print "-- start one or more applications"

    def help_unload(self):
        print "syntax: unload [app1] [app2] ..."
        print "-- stop one or more applications"

    def help_m(self):
        print "syntax: m [mininet cmd]"
        print "-- run mininet command"

    def help_p(self):
        print "syntax: p [sql statement]"
        print "-- execute PostgreSQL statement"

    def help_watch(self):
        print "syntax: watch [table1,max_rows(optional) table2,max_rows]"
        print "-- launch another terminal to watch db tables in real-time"
        print "-- example: watch hosts switches cf,5"

def RavelCLI(opts):
    if opts.custom:
        ravel.mndeps.custom(opts.custom)

    params = { 'topology' : opts.topo,
               'pox' : 'running' if opts.remote else 'offline',
               'mininet' : 'running' if not opts.onlydb else 'offline',
               'database' : opts.db,
               'username' : opts.user,
               'app path' : [APP_DIR]
           }

    topo = ravel.mndeps.build(opts.topo)
    if topo is None:
        print "Invalid mininet topology", opts.topo
        return

    passwd = None
    if opts.password:
        passwd = getpass.getpass("Enter password: ")

    raveldb = ravel.db.RavelDb(opts.db,
                               opts.user,
                               ravel.db.BASE_SQL,
                               passwd,
                               opts.reconnect)

    from ravel.network import MininetProvider, EmptyNetProvider
    if opts.onlydb:
        net = EmptyNetProvider(raveldb, topo)
    else:
        try:
            net = MininetProvider(raveldb, topo, opts.remote)
        except Exception, e:
            if not opts.remote and 'shut down the controller' in str(e):
                print "Mininet cannot start. If running without --remote " \
                    "flag, shut down existing controller first."
                return
            raise

    if net is None:
        print "Cannot start networ"

    env = Environment(raveldb, net, [APP_DIR], params, opts.remote)
    env.start()

    while True:
        try:
            RavelConsole(env).cmdloop()
            break
        except Exception, e:
            logger.warning("console crashed: %s", e)

    env.stop()
