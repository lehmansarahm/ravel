#!/usr/bin/env python

import os
import sys
from optparse import OptionParser

# add ravel to path
if 'PYTHONPATH' in os.environ:
    sys.path = os.environ['PYTHONPATH'].split(':') + sys.path
    raveldir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.abspath(raveldir))

from ravel.cli import RavelCLI
from ravel.log import LEVELS, logger
from ravel.util import Config

def optParser():
    desc = ( "Ravel console." )
    usage = ( '%prog [options]\n'
              '(type %prog -h for details)' )

    parser = OptionParser(description=desc, usage=usage)
    parser.add_option('--onlydb', '-o', action='store_true', default=False,
                      help='start without mininet')
    parser.add_option('--reconnect', '-c', action='store_true', default=False,
                      help='reconnect to existing database, skipping reinit.')
    parser.add_option('--remote', '-r', action='store_true', default=False,
                      help='start remote controller')
    parser.add_option('--db', '-d', type='string', default=Config.DbName,
                      help='postgresql username (default: %s)' % Config.DbName)
    parser.add_option('--user', '-u', type='string', default=Config.DbUser,
                      help='postgresql username (default: %s)' % Config.DbUser)
    parser.add_option('--password', '-p', action='store_true', default=False,
                      help='postgresql password')
    parser.add_option('--custom', type='string', default=None,
                     help='mininet: read custom classes or params from py file(s)')
    parser.add_option('--topo', '-t', type='string', default=None,
                      help='mininet: topology argument')
    parser.add_option('--verbosity', '-v',  type='choice',
                      choices=LEVELS.keys(), default='info',
                      help='|'.join(LEVELS.keys()))

    return parser

def parse(parser):
    options, args = parser.parse_args()
    if args:
        parser.print_help()
        sys.exit(0)

    if not options.topo:
        parser.error("No topology specified")

    if options.onlydb and options.remote:
        parser.error("Cannot start remote controller with no network. "
                     "Choose either --remote or --onlydb")

    logger.setLogLevel(options.verbosity)

    return options

if __name__ == "__main__":
    parser = optParser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    opts = parse(parser)
    RavelCLI(opts)
