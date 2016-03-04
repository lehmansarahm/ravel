#!/usr/bin/env python

from itertools import tee, izip
from ravel.app import AppConsole, discoverComponents

routing = """
DROP TABLE IF EXISTS p_RT CASCADE;
CREATE UNLOGGED TABLE p_RT (
    counts    integer,
    status    text,
    PRIMARY key (counts)
);

CREATE TRIGGER run_RT_trigger
     AFTER INSERT ON p_RT
     FOR EACH ROW
   EXECUTE PROCEDURE spv_constraint1_fun();

CREATE OR REPLACE RULE run_RT AS
    ON INSERT TO p_RT
    WHERE (NEW.status = 'on')
    DO ALSO (
         UPDATE p_RT SET status = 'off' WHERE counts = NEW.counts;
         );
"""

ptable_template = """
DROP TABLE IF EXISTS p_{0} CASCADE;
CREATE UNLOGGED TABLE p_{0} (
       counts integer,
       status text,
       PRIMARY key (counts)
);
"""

runrule_template = """
CREATE OR REPLACE RULE run_{0} AS
    ON INSERT TO p_{0}
    WHERE (NEW.status = 'on')
    DO ALSO (
        DELETE FROM {1};
        UPDATE p_{0} SET status = 'off' WHERE counts = NEW.counts;
        );
"""

orderrule_template = """
CREATE OR REPLACE RULE {0}2{1} AS
    ON UPDATE TO p_{0}
    WHERE (NEW.status = 'off')
    DO ALSO
        INSERT INTO p_{1} values (NEW.counts, 'on');
"""

clock_template = """
CREATE OR REPLACE RULE {0}2Clock AS
    ON UPDATE TO p_{0}
    WHERE (NEW.status = 'off')
    DO ALSO
        INSERT INTO clock values (NEW.counts);
"""

def pairwise(iterable):
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)

class orchConsole(AppConsole):
    def __init__(self, db, env, components):
        self.ordering = None
        self.sql = None
        AppConsole.__init__(self, db, env, components)

    def do_run(self, line):
        "Execute the orchestration protocol"
        if self.ordering is None:
            print "Must first set ordering"
            return

        try:
            self.db.cursor.execute("SELECT MAX(counts) FROM clock;")
            count = self.db.cursor.fetchall()[0][0]
            hipri = self.ordering[-1]

            self.db.cursor.execute("INSERT INTO p_{0} VALUES ({1}, 'on');"
                                   .format(hipri, count))
        except Exception, e:
            print e

    def do_reset(self, line):
        "Remove orchestration protocol function"
        components = discoverComponents(self.sql)
        for component in components:
            component.drop(self.db)

    def default(self, line):
        ordering = line.split()
        for app in ordering:
            if app.lower() not in self.env.apps and \
               app.lower() not in ['routing', 'rt']:
                print "Unrecognized app", app
                return

        ordering = [x.upper() for x in ordering]

        # replace routing app name with rt 
        if "ROUTING" in ordering:
            ordering[ordering.index("ROUTING")] = "RT"

        sql = ""
        for app in [x for x in ordering if x != "RT"]:
            vtable = "{0}_violation".format(app)
            sql += ptable_template.format(app)
            sql += runrule_template.format(app, vtable)

        sql += routing

        for app1, app2 in pairwise(ordering):
            sql += orderrule_template.format(app1, app2)

        sql += clock_template.format(ordering[-1])

        self.ordering = ordering
        self.sql = sql

        try:
            self.db.cursor.execute(self.sql)
        except Exception, e:
            print e

shortcut = "oa"
description = "an automated orchestration protocol application"
console = orchConsole
