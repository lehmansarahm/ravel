#!/usr/bin/env python

import cmd

class SampleConsole(cmd.Cmd):
    def do_echo(self, line):
        "Test command, echo arguments"
        print self.__class__.__name__, "says:", line

shortcut = "sp"
console = SampleConsole()
