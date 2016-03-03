#!/usr/bin/env python

import cmd
from ravel.app import AppConsole

class orchConsole(AppConsole):
    def do_echo(self, line):
        "kf (Kinetic Firewall) command, echo arguments"
        print self.__class__.__name__, "says:", line

    def do_list(self, line):
        "orchestration protocol for: Kinetic Firewall (kf), pga, merlin, and routing "
        print self.__class__.__name__, "orchestration enforces ordering:", "pga, kinetic firewall, routing"

    def do_run(self, line):
        "run protocol"
        try:
            self.cursor.execute ("select max (counts) from clock;")
            print "hello"

            # ct = self.cur.fetchall () [0]['max']
            ##########################################
            # make cursor a dict cursors?
            ##########################################
            
            ct = self.cursor.fetchall()[0][0]
            self.cursor.execute ("INSERT INTO p_PGA VALUES (" + str (ct+1) + ", 'on');")

        except Exception, e:
            print e

    def do_watch(self, line):            
        print self.__class__.__name__, "watch orchestrated applications"

        app_list = ["tm", "cf", "PGA_violation", "FW_violation"]

        for app_view in app_list:
            query = "'SELECT * FROM {0} {1}'".format(app_view, "")

            # watch_arg = 'echo {0}: {1}; psql -U{3} -d {0} -c {2}'.format(
            #     self.env.db.name, app_view, query, self.env.db.user)
            watch_arg = 'echo {0}: {1}; psql -U{3} -d {0} -c {2}'.format(
                "mininet", app_view, query, "mininet")

            ##########################################
            # AppConsole class needs access to env.db.name, make it part of the data?
            # AppConsole __init__ passes cursor explicitly to the data part, can we use inheritance instead?
            ##########################################
            
            watch = 'watch -c -n 2 --no-title "{0}"'.format(watch_arg)

            # self.env.mkterm('xterm -e ' + watch)
            ##########################################
            # need env ...
            ##########################################

        print "watch tm, cf, PGA_violation, FW_violation\n", "pending implementation: AppConsole needs access to env"

shortcut = "orch"
description = "an orchestration protocol application"
console = orchConsole
