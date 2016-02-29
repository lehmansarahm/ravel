#!/usr/bin/env python

import cmd
from ravel.env import AppConsole

class SampleConsole(AppConsole):
    def do_echo(self, line):
        "Test command, echo arguments"
        print self.__class__.__name__, "says:", line

    def do_sql(self, line):
        "Execute a sql statement"
        self.cursor.execute(line)

shortcut = "sp"
description = "a sample application"
console = SampleConsole
