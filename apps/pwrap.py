import os
import sys

from ravel.util import Config
from ravel.app import AppConsole

def updatePath():
    path = ""
    if 'PYTHONPATH' in os.environ:
        path = os.environ['PYTHONPATH']

    sys.path = path.split(':') + sys.path
    cwd = os.path.dirname(os.path.abspath(__file__))

    # add pyretic wrapper, apps
    pyreticpath = os.path.normpath(os.path.join(cwd, "pyretic_apps"))
    sys.path.append(os.path.abspath(pyreticpath))

    # add pox
    sys.path.append(Config.PoxDir)

class PyreticConsole(AppConsole):
    def __init__(self, db, env, components):
        AppConsole.__init__(self, db, env, components)
        updatePath()
        # from simple_ui_firewall import firewall
        # self.fw = firewall()
        # self.fw.attach(self.pycallback)

        # import rewrite
        # policy = rewrite.main()
        # print policy

        import pyfw
        policy = pyfw.main()
        print policy

    def pycallback(self, obj):
        print "policy updated"
        print self.fw.policy

    def do_load(self, line):
        pass

    def do_echo(self, line):
        "Test command, echo arguments"
        print self.__class__.__name__, "says:", line


shortcut = "py"
description = "Pyretic runtime console"
console = PyreticConsole
