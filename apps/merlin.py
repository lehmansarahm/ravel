#!/usr/bin/env python

import cmd
from ravel.app import AppConsole

class merlinConsole(AppConsole):
    def do_echo(self, line):
        "kf (Kinetic Firewall) command, echo arguments"
        print self.__class__.__name__, "says:", line

    def do_list(self, line):
        "merlin (Resource provisioning): list tables and views"
        print self.__class__.__name__, "tables (t) and views (v):", "\n\t MERLIN_policy (t)\n\t MERLIN_violation (v)"

shortcut = "merlin"
description = "a merlin (resource provisioning) application"
console = merlinConsole
