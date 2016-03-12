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

    # Part 1
    def testStartup(self):
        cmd = "python {0} ".format(resource_file("ravel.py"))
        p = pexpect.spawn(cmd + "--help")
        p.expect("Usage")
        p.sendeof()

        p = pexpect.spawn(cmd + "--topo=single,2")
        p.expect("ravel>")
        p.sendline("exit")
        p.sendeof()

        p = pexpect.spawn(cmd + "--topo=single,2 --onlydb")
        p.expect("ravel>")
        p.sendline("exit")
        p.sendeof()

        p = pexpect.spawn(cmd + "--topo=single,2 --verbosity=debug")
        p.expect("DEBUG")
        p.sendline("exit")
        p.sendeof()

    # Part 2
    def testCommands(self):
        p = pexpect.spawn(self.ravelCmd)
        p.expect("ravel>")
        p.sendline("help")
        p.expect("Commands")

        p.sendline("p SELECT * FROM hosts;")
        p.expect("hid")
        
        p.sendline("addflow h1 h2")
        p.expect("Success")
        p.sendline("m h1 ping -c 1 h2")
        p.expect("0% packet loss")

        p.sendline("m")
        p.expect("mininet>")
        p.sendline("h1 ping -c 1 h2")
        p.expect("0% packet loss")
        p.sendline("exit")
        p.expect("ravel>")
        p.sendline("delflow h1 h2")

        p.sendline("addflow h1 h2")
        p.expect("Success")
        p.sendline("p SELECT COUNT(*) FROM rtm;")
        p.expect("1")
        p.sendline("delflow h1 h2")
        p.expect("Success")

        p.sendline("time addflow h1 h2")
        p.expect("Time:")
        p.sendline("delflow h1 h2")

        p.sendline("profile addflow h1 h2")
        p.expect("db_select")

        p.sendline("exit")
        p.sendeof()

    # Part 3
    def testApps(self):
        p = pexpect.spawn(self.ravelCmd)
        p.expect("ravel>")
        p.sendline("apps")
        p.expect("offline")
        p.sendline("load sample pga")

        p.sendline("sample")
        p.expect("sample>")
        p.sendline("exit")
        p.expect("ravel>")

        p.sendline("unload sample pga")
        p.sendline("sample")
        p.expect("Unknown command")
        
        p.sendline("load sample")
        p.sendline("sample echo Hello World")
        p.expect("SampleConsole says: Hello World")

        p.sendline("sample")
        p.expect("sample>")
        p.sendline("echo Hello World")
        p.expect("SampleConsole says: Hello World")
        p.sendline("exit")
        p.expect("ravel>")

        p.sendline("sample")
        p.sendline("help echo")
        p.expect("echo arguments")
        p.sendline("exit")

        p.sendline("help sample echo")
        p.expect("echo arguments")

        p.sendline("help sample")
        p.expect("sample commands")
        p.sendline("exit")
        p.sendeof()

    def tearDown(self):
        # kill pox if it's still running
        os.system("sudo killall -9 python2.7 > /dev/null 2>&1")

if __name__ == "__main__":
    unittest.main()
