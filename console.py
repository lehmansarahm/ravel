#!/usr/bin/env python
import cmd
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
    parser.add_option('--topo', '-t', type='string', default=None,
                      help='mininet topology argument')

    options, args = parser.parse_args()
    if args:
        parser.print_help()
        exit()

    if not options.topo:
        parser.error("No topology specified")

    return options

if __name__ == "__main__":
    opts = parseArgs()
    topo = mndeps.build(opts.topo)
    net = Mininet(topo)
    net.start()
    db = RavelDb(opts.db, opts.user)
    db.load_topo(topo, net)
    RavelConsole(net, db).cmdloop()
    net.stop()
