#!/usr/bin/env python

import os
import pexpect
import sys
import time
import unittest
from runner import addRavelPath

addRavelPath()

from ravel.cli import RavelConsole, APP_DIR
from ravel.db import RavelDb, BASE_SQL
from ravel.env import Environment
from ravel.log import logger, LEVELS
from ravel.mndeps import build
from ravel.network import MininetProvider
from ravel.of import PoxInstance
from ravel.util import Config, resource_file

class testCommands(unittest.TestCase):
    ravelCmd = "python {0} --topo single,3".format(resource_file("ravel.py"))

    def testStartupOptions(self):
        cmd = "python {0} ".format(resource_file("ravel.py"))
        p = pexpect.spawn(cmd + "--help")
        p.expect("Usage")
        p.sendeof()

        p = pexpect.spawn(cmd + "--topo=single,3")
        p.expect("ravel>")
        p.sendeof()

        p = pexpect.spawn(cmd + "--topo=single,3 --onlydb")
        p.expect("ravel>")
        p.sendline("m")
        p.expect("no CLI available")
        p.sendline("exit")
        p.sendeof()

        p = pexpect.spawn(cmd + "--topo single,3 --noctl")
        p.expect("Unable to contact the remote controller")
        p.expect("ravel>")
        p.sendline("exit")
        p.sendeof()
        
    def testFlows(self):
        p = pexpect.spawn(self.ravelCmd)
        p.expect("ravel>")
        p.sendline("addflow h1 h2")
        p.expect("Success")
        p.sendline("m dpctl dump-flows")
        p.expect("cookie", timeout=10)
        p.sendline("addflow h1 h4")
        p.expect("Failure")
        p.sendline("profile addflow h1 h3")
        p.expect("db_select", timeout=10)
        p.sendline("exit")     
        p.expect(pexpect.EOF)

    def testApps(self):
        p = pexpect.spawn(self.ravelCmd)
        env = Environment(None, None, [APP_DIR], {'db': 'ravel'})
        env.discover()
        apps = [a for a in env.apps if a != "orch"]
        for app in apps:
            p.sendline(app)
            p.expect("Unknown command")
            p.sendline("load {0}".format(app))
            p.sendline("{0}".format(app))
            p.expect(app + ">")
            p.sendline("exit")
            p.expect("ravel>")
            p.sendline("unload " + app)
            p.sendline("" + app)
            p.expect("Unknown command")
        p.sendline("exit")
        p.expect(pexpect.EOF)

    def testCommands(self):
        p = pexpect.spawn(self.ravelCmd)
        p.expect("ravel>")
        p.sendline("exit")
        p.expect(pexpect.EOF)

    def tearDown(self):
        # kill pox if it's still running
        os.system("sudo killall -9 python2.7 > /dev/null 2>&1")

if __name__ == "__main__":
    unittest.main()
