#!/usr/bin/env python
import cmd
import importlib
import os
import psycopg2
import pprint
import re
import sys
import tabulate
import tempfile
from optparse import OptionParser

from mininet.topo import Topo
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.log import setLogLevel

import mndeps
from db import RavelDb

DB='mininet'
DBUSER='mininet'
BASE_SQL="primitive.sql"

def append_path(path):
    if 'PYTHONPATH' not in os.environ:
        os.environ['PYTHONPATH'] = ""

    sys.path = os.environ['PYTHONPATH'].split(':') + sys.path

    if path is None or path == "":
        path = "."

    if path not in sys.path:
        sys.path.append(path)

class Application(object):
    def __init__(self, name):
        self.name = name
        self.shortcut = None
        self.pyfile = None
        self.sqlfile = None
        self.module = None

    def link(self, filename):
        if filename.endswith(".py"):
            self.pyfile = filename
        elif filename.endswith(".sql"):
            self.sqlfile = filename

    def start(self):
        if not self.pyfile:
            return

        # if needed, add path
        filepath = os.path.dirname(self.pyfile)
        append_path(filepath)

        try:
            self.module = importlib.import_module(self.name)
            self.shortcut = self.module.shortcut
        except BaseException, e:
            errstr = "{0}: {1}".format(type(e).__name__, str(e))
            print errstr
            return False

        return True

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
        self.find_apps()

    def start(self):
        self.net.start()
        self.db.load_topo(self.net)

    def stop(self):
        self.net.stop()

    def load_app(self, appname):
        if appname in self.loaded:
            return

        if appname in self.apps:
            app = self.apps[appname]
            if app.start():
                self.loaded[app.name] = app
                self.loaded[app.shortcut] = app

    def find_apps(self):
        for d in self.appdirs:
            for f in os.listdir(d):
                if f.endswith(".py"): # or sql
                    name = os.path.splitext(f)[0]
                    path = os.path.join(d, f)
                    if name not in self.apps:
                        self.apps[name] = Application(name)
                    self.apps[name].link(path)

class Flow(object):
    def __init__(self, db, h1, h2):
        self.db = db
        self.h1 = self._dbid(h1)
        self.h2 = self._dbid(h2)

    def _dbid(self, host):
        cursor = self.db.connect().cursor()
        cursor.execute("SELECT sid FROM "
                       "(SELECT sid, name FROM switches UNION "
                       "SELECT hid, name FROM hosts) as N "
                       "WHERE N.name='{0}';".format(host))

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
        print "\n".join(["   {0}".format(app) for app in self.env.apps.keys()])

    def do_load(self, line):
        apps = line.split()
        for app in apps:
            if app in self.env.apps:
                self.env.load_app(app)
            else:
                print "Unknown application", app

    def do_m(self, line):
        if not line:
            CLI(self.mnet)
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

        try:
            names = [row[0] for row in cursor.description]
            data = cursor.fetchall()
            print tabulate.tabulate(data, headers=names)
        except psycopg2.ProgrammingError:
            pass

    def do_EOF(self, line):
        "Quit Ravel console"
        sys.stdout.write('\n')
        self.env.stop()
        return True

    def do_exit(self, line):
        "Quit Ravel console"
        self.env.stop()
        return True

    def help_load(self):
        print "syntax: load [application]"
        print "-- start an application"

    def help_m(self):
        print "syntax: m [mininet cmd]"
        print "-- run mininet command"

    def help_p(self):
        print "syntax: p [sql statement]"
        print "-- execute PostgreSQL statement"

def parseArgs():
    desc = ( "Ravel console." )
    usage = ( '%prog [options]\n'
              '(type %prog -h for details)' )

    parser = OptionParser(description=desc, usage=usage)
    parser.add_option('--user', '-u', type='string', default=DBUSER,
                      help='postgresql username (default: %s)' % DBUSER)
    parser.add_option('--db', '-d', type='string', default=DB,
                      help='postgresql username (default: %s)' % DB)
    parser.add_option("--custom", type='string', default=None,
                     help='mininet: read custom classes or params from py file(s)')
    parser.add_option('--topo', '-t', type='string', default=None,
                      help='mininet: topology argument')

    options, args = parser.parse_args()
    if args:
        parser.print_help()
        exit()

    if not options.topo:
        parser.error("No topology specified")

    return options

if __name__ == "__main__":
    opts = parseArgs()
    if opts.custom:
        mndeps.custom(opts.custom)

    topo = mndeps.build(opts.topo)
    net = Mininet(topo)
    db = RavelDb(opts.db, opts.user, BASE_SQL)
    env = Environment(db, net, ["./apps"])

    RavelConsole(env).cmdloop()
