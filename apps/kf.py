#!/usr/bin/env python

import cmd
from ravel.app import AppConsole

class kfConsole(AppConsole):
    def do_echo(self, line):
        "kf (Kinetic Firewall) command, echo arguments"
        print self.__class__.__name__, "says:", line

    def do_list(self, line):
        "kf (Kinetic Firewall): list tables and views"
        print self.__class__.__name__, "tables (t) and views (v):", "\n\t FW_policy_acl (t)\n\t FW_policy_user (t)\n\t FW_violation (v)"

shortcut = "kf"
description = "a kinetic (firewall) application"
console = kfConsole
