"""
A command-line interface for Ravel.

Ravel's CLI provides a user-friendly way to interact the backend
PostgreSQL database and Mininet.
"""
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
from ravel.network import name2dbid, addFlow, delFlowById, delFlowByHostname
from ravel.of import PoxInstance
from ravel.util import Config, resource_file

class RavelConsole(cmd.Cmd):
    "Command line interface for Ravel."

    prompt = "ravel> "
    doc_header = "Commands (type help <topic>):"

    def __init__(self, env):
        self.env = env
        self.intro = "RavelConsole: interactive console for Ravel.\n" \
                     "Configuration:\n" + self.env.pprint()

        cmd.Cmd.__init__(self)

    def default(self, line):
        "Check loaded applications before raising unknown command error"
        cmd = line.strip().split()[0]
        if cmd in self.env.loaded:
            self.env.loaded[cmd].cmd(line[len(cmd):])
        else:
            print '*** Unknown command: %s' % line

    def emptyline(self):
        "Don't repeat the last line when hitting return on empty line"
        return

    def do_addflow(self, line):
        """Add a flow between two hosts, using Mininet hostnames
           Usage: addflow [host1] [host2]"""
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
        "Placeholder for batch commands for testing"
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
        """Delete a flow between two hosts, using flow ID or Mininet hostnames"
           Usage: delflow [host1] [host2]
                  delflow [flow id]"""
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
        """Start one or more applications
           Usage: load [app1] [app2] ..."""
        apps = line.split()
        for app in apps:
            if app in self.env.apps:
                self.env.load_app(app)
            else:
                print "Unknown application", app

    def do_unload(self, line):
        """Stop one or more applications
           Usage: unload [app1] [app2] ..."""
        apps = line.split()
        for app in apps:
            if app in self.env.apps:
                self.env.unload_app(app)
            else:
                print "Unknown application", app

    def do_m(self, line):
        """Execute a command in Mininet
           Usage: m [mininet cmd]"""
        self.env.provider.cli(line)

    def do_p(self, line):
        """Execute a PostgreSQL statement
           Usage: p [SQL statement]"""
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
        """Launch an xterm window to watch database tables in real-time
           Usage: watch [table1(,max_rows)] [table2(,max_rows)] ...
           Example: watch hosts switches cf,5"""
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
        "List available commands with 'help' or detailed help with 'help cmd'"
        # extend to include loaded apps and their help methods
        tokens = arg.split()
        if len(tokens) > 0 and tokens[0] in self.env.loaded:
            app = self.env.apps[tokens[0]]
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
        "Complete loaded applications' names for load command"
        apps = self.env.apps.keys()
        if not text:
            completions = apps
        else:
            completions = [d for d in apps if d.startswith(text)]

        return completions

    def complete_unload(self, text, line, begidx, endidx):
        "Complete unloaded applications' names for unload command"
        apps = self.env.apps.loaded.keys()
        if not text:
            completions = apps
        else:
            completions = [d for d in apps if d.startswith(text)]

        return completions

def RavelCLI(opts):
    """Start a RavelConsole instance given a list of command line options
       opts: parsed OptionParser object"""
    if opts.custom:
        ravel.mndeps.custom(opts.custom)

    params = { 'topology' : opts.topo,
               'pox' : 'offline' if opts.noctl else 'running',
               'mininet' : 'running' if not opts.onlydb else 'offline',
               'database' : opts.db,
               'username' : opts.user,
               'app path' : Config.AppDirs
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

    if opts.noctl:
        controller = None
    else:
        controller = PoxInstance("poxapp")

    from ravel.network import MininetProvider, EmptyNetProvider
    if opts.onlydb:
        net = EmptyNetProvider(raveldb, topo)
    else:
        try:
            net = MininetProvider(raveldb, topo, controller)
        except Exception, e:
            if 'shut down the controller' in str(e):
                print "Mininet cannot start. If running without --remote " \
                    "flag, shut down existing controller first."
                return
            raise

    if net is None:
        print "Cannot start network"

    env = Environment(raveldb, net, Config.AppDirs, params)
    env.start()

    while True:
        try:
            RavelConsole(env).cmdloop()
            break
        except Exception, e:
            logger.warning("console crashed: %s", e)

    env.stop()
