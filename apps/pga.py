#!/usr/bin/env python

from ravel.app import AppConsole

class pgaConsole(AppConsole):
    def do_echo(self, line):
        "kf (Kinetic Firewall) command, echo arguments"
        print self.__class__.__name__, "says:", line

    def do_list(self, line):
        "pga (service chain): list tables and views"
        print self.__class__.__name__, "tables (t) and views (v):", "\n\t PGA_policy (t)\n\t PGA_group (t)\n\t PGA (v)\n\t PGA_violation (v)"

shortcut = "pga"
description = "a PGA (service chain) application"
console = pgaConsole
