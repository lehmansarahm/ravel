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
    def __init__(self, db, net):
        self.db = db
        self.net = net
        self.apps = {}
        self.loaded = {}

    def start(self):
        self.net.start()
        self.load_topo(self.net.topo, self.net)
        pass

    def stop(self):
        pass

    def load_app(self, appname):
        if appname in self.apps:
            app = self.apps[appname]
            if app.start():
                self.loaded[app.name] = app
                self.loaded[app.shortcut] = app

    def find_apps(self, dirs):
        for d in dirs:
            for f in os.listdir(d):
                if f.endswith(".py"): # or sql
                    name = os.path.splitext(f)[0]
                    path = os.path.join(d, f)
                    if name not in self.apps:
                        self.apps[name] = Application(name)
                    self.apps[name].link(path)

class RavelConsole(cmd.Cmd):
    prompt = "ravel> "
    intro = "RavelConsole: interactive console for Ravel."
    doc_header = "Commands (type help <topic>):"

    def __init__(self, mnet, db):
        self.mnet = mnet
        self.db = db
        cmd.Cmd.__init__(self)

    def do_m(self, line):
        if not line:
            CLI(self.mnet)
        else:
            temp = tempfile.NamedTemporaryFile(delete=False)
            temp.write(line)
            temp.close()
            CLI(self.mnet, script=temp.name)
            os.unlink(temp.name)

    def do_p(self, line):
        cursor = self.db.connect().cursor()
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

    def help_m(self):
        print "syntax: m [mininet cmd]"
        print "-- run mininet command"

    def help_p(self):
        print "syntax: p [sql statement]"
        print "-- execute PostgreSQL statement"

    def do_EOF(self, line):
        "Quit Ravel console"
        sys.stdout.write('\n')
        return True

    def do_exit(self, line):
        "Quit Ravel console"
        return True

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
#    env = Environment(None, None)
#    env.find_apps(["./apps"])
#    env.load_app("routing")

#    env.apps["routing"].cmd("blah")
#
#    sys.exit(0)

    opts = parseArgs()
    if opts.custom:
        mndeps.custom(opts.custom)

    topo = mndeps.build(opts.topo)
    net = Mininet(topo)
    net.start()
    db = RavelDb(opts.db, opts.user)
    db.load_topo(net)
    RavelConsole(net, db).cmdloop()
    net.stop()
