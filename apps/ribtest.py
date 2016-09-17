import os
import random
import sys
import time
import networkx

import orch
import routing

from ravel.app import AppConsole, discoverComponents
from ravel.log import logger
from ravel.util import resource_file
from ravel.messaging import clear_queue

#RIB_SIZE = 1000000
RIB_SIZE = 1000

def precompute_paths(db):
    db.cursor.execute("""
DROP TABLE IF EXISTS pre_paths CASCADE;
CREATE UNLOGGED TABLE pre_paths (
        src  integer,
        dst  integer,
        id   integer PRIMARY KEY,
        CONSTRAINT uniq_pairs UNIQUE(src,dst)
);
CREATE INDEX ON pre_paths(src, dst);

DROP TABLE IF EXISTS pre_cf CASCADE;
CREATE UNLOGGED TABLE pre_cf (
        id  integer REFERENCES pre_paths(id),
        pid integer,
        sid integer,
        nid integer
);
CREATE INDEX ON pre_cf(id);
""")

    db.cursor.execute("SELECT hid FROM hosts;")
    results = db.cursor.fetchall()
    nodes = [n[0] for n in results]

    db.cursor.execute("SELECT sid, nid FROM tp;")
    results = db.cursor.fetchall()
    edges = [(e[0], e[1]) for e in results]

    g = networkx.Graph()
    g.add_edges_from(edges)

    count = 0
    pre_paths = []
    pre_cf = []

    for src in nodes:
        for dst in nodes:
            if src == dst:
                continue

            if count > 1000000:
                break

            try:
                path = networkx.shortest_path(g, src, dst)
                count += 1
            except networkx.exception.NetworkXNoPath:
                continue

            path_edges = []

            # TODO: how to handle pathlen=2?
            for i in range(2, len(path)):
                path_edges.append((path[i-2], path[i-1], path[i]))

            pre_paths.append((count, src, dst))
            for row in path_edges:
                pre_cf.append((count, row[0], row[1], row[2]))

    print "Paths computed, inserting"
    open("pre_paths.sql", 'w').close()
    with open("pre_paths.sql", 'w') as f:
        f.write("INSERT INTO pre_paths(id, src, dst) VALUES {0};".format(
            ",".join("({0}, {1}, {2})".format(*t) for t in pre_paths)))

    open("pre_cf.sql", 'w').close()
    with open("pre_cf.sql", 'w') as f:
        f.write("INSERT INTO pre_cf(id, pid, sid, nid) VALUES {0};".format(
            ",".join("({0}, {1}, {2}, {3})".format(*t) for t in pre_cf)))

    pre_paths = []
    pre_cf = []
    db.cursor.execute(open("pre_paths.sql").read())
    db.cursor.execute(open("pre_cf.sql").read())
    os.remove("pre_paths.sql")
    os.remove("pre_cf.sql")

def cleanup_precomputed_paths(db):
    db.cursor.execute("DROP TABLE IF EXISTS pre_paths CASCADE;")
    db.cursor.execute("DROP TABLE IF EXISTS pre_cf CASCADE;")

def disable_orchestration(db):
    db.cursor.execute("""
DROP TABLE IF EXISTS p_routing CASCADE;
DROP TRIGGER IF EXISTS spv_constraint1 on p_spv;
DROP FUNCTION IF EXISTS spv_constraint2_fun() CASCADE;
CREATE OR REPLACE FUNCTION spv_constraint2_fun(f integer, s integer, d integer)
RETURNS integer
AS $$
rm = plpy.execute ("SELECT * FROM rm_delta;")
for t in rm:
    if t["isadd"] == 1:
        f = t["fid"]
        s = t["src"]
        d = t["dst"]
        pv = plpy.execute("SELECT array(SELECT id1 FROM pgr_dijkstra('SELECT 1 as id, sid as source, nid as target, 1.0::float8 as cost FROM tp WHERE isactive = 1'," +str (s) + "," + str (d)  + ",FALSE, FALSE))")[0]['array']

        l = len (pv)
        for i in range (l):
            if i + 2 < l:
                plpy.execute ("INSERT INTO cf (fid,pid,sid,nid) VALUES (" + str (f) + "," + str (pv[i]) + "," +str (pv[i+1]) +"," + str (pv[i+2])+  ");")

    elif t["isadd"] == 0:
        f = t["fid"]
        plpy.execute ("DELETE FROM cf WHERE fid =" +str (f) +";")

plpy.execute ("DELETE FROM rm_delta;")
return 0
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;

CREATE OR REPLACE RULE rm_ins AS
       ON INSERT TO rm
       DO ALSO (
           INSERT INTO rm_delta values (NEW.fid, NEW.src, NEW.dst, NEW.vol, 1);
           SELECT spv_constraint2_fun(NEW.fid, NEW.src, NEW.dst);
       );
""")

def reenable_orchestration(db):
    db.cursor.execute("""
DROP FUNCTION IF EXISTS spv_constraint2_fun() cascade;
CREATE TRIGGER spv_constraint1
       AFTER INSERT ON p_spv
       FOR EACH ROW
       EXECUTE PROCEDURE spv_constraint1_fun();
CREATE OR REPLACE RULE rm_ins AS
       ON INSERT TO rm
       DO ALSO
           INSERT INTO rm_delta values (NEW.fid, NEW.src, NEW.dst, NEW.vol, 1);
""")

class KernelTest(object):
    def __init__(self, db, env):
        self.db = db
        self.env = env
        self.macro_times = {}
        self.rule_counts = {}

    @property
    def name(self):
        return self.__class__.__name__

    def setup(self):
        pass

    def test_cdf(self, paths, trial=0):
        self.setup()
        hostnames = self.env.provider.cache_name
        self.env.maincli.onecmd("load routing")
        time.sleep(1)
        times = []
        elapsed = time.time()
        for src, dst in paths:
            micro = time.time()
            self.env.maincli.onecmd("routing addflow {0} {1}".format(src, dst))
            micro = time.time() - micro

            self.db.cursor.execute("SELECT fid FROM rm WHERE src={0} AND dst={1} LIMIT 1;"
                                   .format(hostnames[src], hostnames[dst]))
            fid = int(self.db.cursor.fetchall()[0][0])
            self.db.cursor.execute("SELECT COUNT(*) FROM cf WHERE fid={0};".format(fid))
            pathlen = int(self.db.cursor.fetchall()[0][0])
            if pathlen == 0 and src == dst:
                pathlen = 1
            times.append(micro * 1000 / pathlen)

        self.db.cursor.execute("SELECT COUNT(*) FROM cf;")
        fetch = self.db.cursor.fetchall()
        #print "    ", int(fetch[0][0])

        outfile = "{0}_times_{1}.out".format(self.name, trial)
        with open(outfile, 'w') as f:
            f.write("\n".join(str(t) for t in times))

        self.db.cursor.execute("DELETE FROM cf; DELETE FROM rm;")
        self.cleanup()

    def test(self, paths, trial=0):
        self.setup()
        self.env.maincli.onecmd("load routing")
        time.sleep(1)
        elapsed = time.time()
        for src, dst in paths:
            # print src, dst
            self.env.maincli.onecmd("routing addflow {0} {1}".format(src, dst))

        elapsed = time.time() - elapsed
        elapsed = round(elapsed * 1000, 3)
        print elapsed
        self.db.cursor.execute("SELECT COUNT(*) FROM cf;")
        self.rule_counts[trial] = int(self.db.cursor.fetchall()[0][0])
        print "   ", self.rule_counts[trial]
        self.macro_times[trial]  = elapsed

        # self.env.maincli.onecmd("p select * from rm;")
        # self.env.maincli.onecmd("p select * from cf;")

        self.db.cursor.execute("DELETE FROM cf; DELETE FROM rm;")
        self.cleanup()

    def result(self):
        per_rule = []
        for trial in self.macro_times.keys():
            per_rule.append(self.macro_times[trial] / float(self.rule_counts[trial]))

        avg = 0.0
        if len(per_rule) > 0:
            avg = sum(per_rule) / float(len(per_rule))
        return "{0}: {1}".format(self.name, round(avg, 3))

    def cleanup(self):
        pass

class BaselineTest(KernelTest):
    def __init__(self, db, env):
        super(BaselineTest, self).__init__(db, env)

    def setup(self):
        disable_orchestration(self.db)

    def cleanup(self):
        reenable_orchestration(self.db)

class ColumnConstraintTest(KernelTest):
    def __init__(self, db, env):
        super(ColumnConstraintTest, self).__init__(db, env)

    def setup(self):
        disable_orchestration(self.db)
        self.db.cursor.execute("ALTER TABLE cf ADD CONSTRAINT edge_exist1 FOREIGN KEY(nid, sid) REFERENCES tp(sid, nid);")
        self.db.cursor.execute("ALTER TABLE cf ADD CONSTRAINT edge_exist2 FOREIGN KEY(sid, pid) REFERENCES tp(sid, nid);")
        self.db.cursor.execute("ALTER TABLE cf ADD CONSTRAINT cf_pid_uniq UNIQUE(fid, pid);")
        self.db.cursor.execute("ALTER TABLE cf ADD CONSTRAINT cf_nid_uniq UNIQUE(fid, nid);")
        self.db.cursor.execute("ALTER TABLE cf ADD CONSTRAINT cf_sid_uniq UNIQUE(fid, sid);")

    def cleanup(self):
        self.db.cursor.execute("ALTER TABLE cf DROP CONSTRAINT edge_exist1;")
        self.db.cursor.execute("ALTER TABLE cf DROP CONSTRAINT edge_exist2;")
        self.db.cursor.execute("ALTER TABLE cf DROP CONSTRAINT cf_sid_uniq;")
        self.db.cursor.execute("ALTER TABLE cf DROP CONSTRAINT cf_nid_uniq;")
        self.db.cursor.execute("ALTER TABLE cf DROP CONSTRAINT cf_pid_uniq;")
        reenable_orchestration(self.db)

class PyTriggerTest(KernelTest):
    def __init__(self, db, env):
        super(PyTriggerTest, self).__init__(db, env)

    def setup(self):
        self.db.cursor.execute("""
DROP TRIGGER spv_constraint1 on p_spv;
DROP FUNCTION IF EXISTS spv_constraint2_fun() CASCADE;

CREATE OR REPLACE FUNCTION path_validate(f integer, s integer, d integer)
RETURNS integer
AS $$
failed = False
error = "no error"
path = plpy.execute("SELECT * FROM cf WHERE fid=" + str(f) + ";")

path_sn = []
path_ps = []
edges = set()

for edge in path:
    edges.add((edge['pid'], edge['sid']))
    edges.add((edge['sid'], edge['nid']))

    path_ps.append((edge['pid'], edge['sid']))
    path_sn.append((edge['sid'], edge['nid']))

# test uniqueness
sids = []

for edge in path:
    if edge['sid'] in sids:
        failed = True
        error = "sid uniqueness violation"

    sids.append(edge['sid'])

edge_dict = {}
for e1, e2 in edges:
    edge_dict[e1] = e2

for e1,e2 in path_sn + path_ps:
    # e1_exists = plpy.execute("SELECT COUNT(1) FROM tp WHERE nid={0};"
    #                          .format(e1))
    # if int(e1_exists[0]['count']) == 0:
    #     failed = True
    #     error = "node not in topo {0}".format(e1)
    # e2_exists = plpy.execute("SELECT COUNT(1) FROM tp WHERE nid={0};"
    #                          .format(e2))
    # if int(e2_exists[0]['count']) == 0:
    #     failed = True
    #     error = "node not in topo {0}".format(e2)

    edge_exists = plpy.execute("SELECT COUNT(1) FROM tp WHERE nid={0} AND sid={1}"
                               .format(e1, e2))
    if int(edge_exists[0]['count']) == 0:
        failed = True
        error = "edge not in topo {0} {1}".format(e1, e2)

curr = s
count = 0
while True:
    count += 1
    if curr == d:
        break
    elif count > (len(edges)):
        failed = True
        error = "path loop {0}".format(edge_dict)
    elif curr in edge_dict:
        curr = edge_dict[curr]
    elif curr not in edge_dict and curr != d:
        failed = True
        error = "path continuity violated: {0} s={1},d={2} => {3} {4} {5}".format(
                curr, s, d, edge_dict, edges, path)
    else:
        failed = True
        error = "this should not be reachable"

if count != len(edges):
    failed = True
    error = "wrong path length"

if failed:
    # rollback
    plpy.execute("DELETE FROM cf WHERE fid={0}".format(f))
    plpy.execute("DELETE FROM rm WHERE fid={0}".format(f))
    plpy.notice("FAILED")
    raise Exception(error)

return 0
$$ LANGUAGE plpythonu VOLATILE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION spv_constraint2_fun ()
RETURNS TRIGGER
AS $$
rm = plpy.execute("SELECT * FROM rm_delta;")
for t in rm:
    if t["isadd"] == 1:
        f = t["fid"]
        s = t["src"]
        d = t["dst"]
        pv = plpy.execute("SELECT array(SELECT id1 FROM pgr_dijkstra('SELECT 1 as id, sid as source, nid as target, 1.0::float8 as cost FROM tp WHERE isactive = 1'," +str (s) + "," + str (d)  + ",FALSE, FALSE))")[0]['array']

        l = len (pv)
        for i in range (l):
            if i + 2 < l:
                plpy.execute ("INSERT INTO cf (fid,pid,sid,nid) VALUES (" + str (f) + "," + str (pv[i]) + "," +str (pv[i+1]) +"," + str (pv[i+2])+  ");")

        plpy.execute("SELECT path_validate({0}, {1}, {2});".format(f, s, d))

    elif t["isadd"] == 0:
        f = t["fid"]
        plpy.execute ("DELETE FROM cf WHERE fid =" +str (f) +";")

plpy.execute ("DELETE FROM rm_delta;")
return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;

CREATE OR REPLACE RULE rm_ins AS
       ON INSERT TO rm
       DO ALSO (
           INSERT INTO rm_delta values (NEW.fid, NEW.src, NEW.dst, NEW.vol, 1);
           SELECT spv_constraint2_fun(NEW.fid, NEW.src, NEW.dst);
       );
""")

    def cleanup(self):
        reenable_orchestration(self.db)

class OptimizedOrchestrationTest(KernelTest):
    def __init__(self, db, env):
        super(OptimizedOrchestrationTest, self).__init__(db, env)

    def setup(self):
        self.env.maincli.onecmd("orch auto on")
        self.env.maincli.onecmd("orch load routing")

        self.db.cursor.execute("""
DROP TRIGGER IF EXISTS spv_constraint1 on p_spv;
DROP FUNCTION IF EXISTS spv_constraint2_fun() CASCADE;
DROP TRIGGER IF EXISTS run_routing_trigger on p_routing;
DROP FUNCTION IF EXISTS cf_ins();

CREATE FUNCTION spv_constraint2_fun()
RETURNS TRIGGER
AS $$
        DECLARE
            pv integer [];
            row record;
        BEGIN
            FOR row in (SELECT fid, src, dst, isadd FROM rm_delta)
            LOOP
                IF row.isadd = 1 THEN
 	        pv := ARRAY(SELECT id1 FROM
	                    pgr_dijkstra('SELECT 1 AS id, sid AS source, nid AS target, 1.0::float8 AS cost FROM tp WHERE isactive=1', row.src, row.dst, FALSE, FALSE));

                IF array_upper(pv, 1) != 0
                THEN
	            FOR i IN 3 .. array_upper(pv, 1)
	            LOOP
                        INSERT INTO cf (fid, pid, sid, nid) VALUES (row.fid, pv[i-2], pv[i-1], pv[i]);
                    END LOOP;
                END IF;
                END IF;

                IF row.isadd = 0 THEN
                    DELETE FROM cf WHERE fid=row.fid;
                END IF;
            END LOOP;

        DELETE FROM rm_delta;
        RETURN NEW;
        END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;

CREATE TRIGGER run_routing_trigger
     AFTER INSERT ON p_routing
     FOR EACH ROW
   EXECUTE PROCEDURE spv_constraint2_fun();
""")

    def cleanup(self):
        self.env.maincli.onecmd("orch auto off")
        self.db.cursor.execute("DROP TRIGGER IF EXISTS rm_ins ON rm")
        self.db.cursor.execute("DROP RULE IF EXISTS rm_ins ON rm;")
        self.db.cursor.execute("DROP TRIGGER IF EXISTS run_routing_trigger ON p_routing;")
        self.db.cursor.execute("DROP FUNCTION IF EXISTS cf_ins();")

        self.db.cursor.execute("DROP TRIGGER IF EXISTS spv_constraint1 on p_spv;")
        self.db.cursor.execute("DROP FUNCTION IF EXISTS spv_constraint2_fun() CASCADE;")
        self.db.cursor.execute("DROP RULE IF EXISTS rm_ins ON rm CASCADE;")
        self.db.cursor.execute("DROP TRIGGER IF EXISTS run_routing_trigger on p_routing;")
        reenable_orchestration(self.db)

class OrchestrationTest(KernelTest):
    def __init__(self, db, env):
        super(OrchestrationTest, self).__init__(db, env)

    def setup(self):
        self.env.maincli.onecmd("orch auto on")
        self.env.maincli.onecmd("orch load routing")

    def cleanup(self):
        self.env.maincli.onecmd("orch auto off")

class BaselinePrecomputedTest(KernelTest):
    def __init__(self, db, env):
        super(BaselinePrecomputedTest, self).__init__(db, env)

    def setup(self):
        self.db.cursor.execute("""
DROP TRIGGER IF EXISTS spv_constraint1 on p_spv;
DROP FUNCTION IF EXISTS spv_constraint2_fun() CASCADE;

CREATE OR REPLACE FUNCTION cf_ins(f integer, s integer, d integer)
RETURNS integer
AS $$
        DECLARE
            row record;
        BEGIN
            FOR row IN (SELECT pid, sid, nid FROM pre_cf WHERE
                        id = (SELECT id FROM pre_paths WHERE src=s AND dst=d))
            LOOP
                INSERT INTO cf (fid, pid, sid, nid) VALUES (f, row.pid, row.sid, row.nid);
            END LOOP;
            RETURN f;
        END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;

CREATE OR REPLACE RULE rm_ins AS
       ON INSERT TO rm
       DO ALSO (
        SELECT cf_ins(NEW.fid, NEW.src, NEW.dst);
       );
""")

    def cleanup(self):
        self.db.cursor.execute("DROP FUNCTION IF EXISTS cf_ins() CASCADE;")
        reenable_orchestration(self.db)


class OrchestrationPrecomputedTest(KernelTest):
    def __init__(self, db, env):
        super(OrchestrationPrecomputedTest, self).__init__(db, env)

    def setup(self):
        self.env.maincli.onecmd("orch auto on")
        self.env.maincli.onecmd("orch load routing")

        self.db.cursor.execute("""
DROP TRIGGER IF EXISTS spv_constraint1 on p_spv;
DROP FUNCTION IF EXISTS spv_constraint2_fun() CASCADE;
DROP TRIGGER IF EXISTS run_routing_trigger on p_routing;
DROP FUNCTION IF EXISTS cf_ins();

CREATE OR REPLACE FUNCTION cf_ins()
RETURNS TRIGGER
AS $$
        DECLARE
            row record;
            edge record;
        BEGIN
            FOR row in (SELECT fid, src, dst, isadd FROM rm_delta)
            LOOP
                IF row.isadd = 1 THEN
                    FOR edge IN (SELECT pid, sid, nid FROM pre_cf WHERE
                            id = (SELECT id FROM pre_paths WHERE src=row.src AND dst=row.dst))
                    LOOP
                        INSERT INTO cf (fid, pid, sid, nid) VALUES (row.fid, edge.pid, edge.sid, edge.nid);
                    END LOOP;
                END IF;

                IF row.isadd = 0 THEN
                    DELETE FROM cf WHERE fid=row.fid;
                END IF;
            END LOOP;

            DELETE FROM rm_delta;
            RETURN NEW;
        END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;

CREATE TRIGGER run_routing_trigger
     AFTER INSERT ON p_routing
     FOR EACH ROW
   EXECUTE PROCEDURE cf_ins();
""")

    def cleanup(self):
        self.env.maincli.onecmd("orch auto off")
        self.db.cursor.execute("DROP TRIGGER IF EXISTS rm_ins ON rm")
        self.db.cursor.execute("DROP RULE IF EXISTS rm_ins ON rm;")
        self.db.cursor.execute("DROP TRIGGER IF EXISTS run_routing_trigger ON p_routing;")
        self.db.cursor.execute("DROP FUNCTION IF EXISTS cf_ins();")
        reenable_orchestration(self.db)

class ColumnConstraintPrecomputedTest(KernelTest):
    def __init__(self, db, env):
        super(ColumnConstraintPrecomputedTest, self).__init__(db, env)

    def setup(self):
        self.db.cursor.execute("ALTER TABLE cf ADD CONSTRAINT edge_exist1 FOREIGN KEY(nid, sid) REFERENCES tp(sid, nid);")
        self.db.cursor.execute("ALTER TABLE cf ADD CONSTRAINT edge_exist2 FOREIGN KEY(sid, pid) REFERENCES tp(sid, nid);")
        self.db.cursor.execute("ALTER TABLE cf ADD CONSTRAINT cf_pid_uniq UNIQUE(fid, pid);")
        self.db.cursor.execute("ALTER TABLE cf ADD CONSTRAINT cf_nid_uniq UNIQUE(fid, nid);")
        self.db.cursor.execute("ALTER TABLE cf ADD CONSTRAINT cf_sid_uniq UNIQUE(fid, sid);")

        self.db.cursor.execute("""
DROP TRIGGER IF EXISTS spv_constraint1 on p_spv;
DROP FUNCTION IF EXISTS spv_constraint2_fun() CASCADE;

CREATE OR REPLACE FUNCTION cf_ins(f integer, s integer, d integer)
RETURNS integer
AS $$
        DECLARE
            row record;
        BEGIN
            FOR row IN (SELECT pid, sid, nid FROM pre_cf WHERE
                        id = (SELECT id FROM pre_paths WHERE src=s AND dst=d))
            LOOP
                INSERT INTO cf (fid, pid, sid, nid) VALUES (f, row.pid, row.sid, row.nid);
            END LOOP;
            RETURN f;
        END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;

CREATE OR REPLACE RULE rm_ins AS
       ON INSERT TO rm
       DO ALSO (
        SELECT cf_ins(NEW.fid, NEW.src, NEW.dst);
       );
""")

    def cleanup(self):
        self.db.cursor.execute("ALTER TABLE cf DROP CONSTRAINT edge_exist1;")
        self.db.cursor.execute("ALTER TABLE cf DROP CONSTRAINT edge_exist2;")
        self.db.cursor.execute("ALTER TABLE cf DROP CONSTRAINT cf_sid_uniq;")
        self.db.cursor.execute("ALTER TABLE cf DROP CONSTRAINT cf_nid_uniq;")
        self.db.cursor.execute("ALTER TABLE cf DROP CONSTRAINT cf_pid_uniq;")
        self.db.cursor.execute("DROP TRIGGER IF EXISTS rm_ins on rm")
        reenable_orchestration(self.db)

class PyTriggerPrecomputedTest(KernelTest):
    def __init__(self, db, env):
        super(PyTriggerPrecomputedTest, self).__init__(db, env)

    def setup(self):
        self.db.cursor.execute("""
DROP TRIGGER IF EXISTS spv_constraint1 on p_spv;
DROP FUNCTION IF EXISTS spv_constraint2_fun() CASCADE;

CREATE OR REPLACE FUNCTION path_validate(f integer, s integer, d integer)
RETURNS integer
AS $$
failed = False
error = "no error"
path = plpy.execute("SELECT * FROM cf WHERE fid=" + str(f) + ";")

path_sn = []
path_ps = []
edges = set()

for edge in path:
    edges.add((edge['pid'], edge['sid']))
    edges.add((edge['sid'], edge['nid']))

    path_ps.append((edge['pid'], edge['sid']))
    path_sn.append((edge['sid'], edge['nid']))

# test uniqueness
sids = []

for edge in path:
    if edge['sid'] in sids:
        failed = True
        error = "sid uniqueness violation"

    sids.append(edge['sid'])

edge_dict = {}
for e1, e2 in edges:
    edge_dict[e1] = e2

for e1,e2 in path_sn + path_ps:
    # e1_exists = plpy.execute("SELECT COUNT(1) FROM tp WHERE nid={0};"
    #                          .format(e1))
    # if int(e1_exists[0]['count']) == 0:
    #     failed = True
    #     error = "node not in topo {0}".format(e1)
    # e2_exists = plpy.execute("SELECT COUNT(1) FROM tp WHERE nid={0};"
    #                          .format(e2))
    # if int(e2_exists[0]['count']) == 0:
    #     failed = True
    #     error = "node not in topo {0}".format(e2)

    edge_exists = plpy.execute("SELECT COUNT(1) FROM tp WHERE nid={0} AND sid={1}"
                               .format(e1, e2))
    if int(edge_exists[0]['count']) == 0:
        failed = True
        error = "edge not in topo {0} {1}".format(e1, e2)

curr = s
count = 0
while True:
    if curr == d:
        break
    elif count > (len(edges)):
        count += 1
        failed = True
        error = "path loop {0}".format(edge_dict)
    elif curr in edge_dict:
        count += 1
        curr = edge_dict[curr]
    elif curr not in edge_dict and curr != d:
        count += 1
        failed = True
        error = "path continuity violated: {0} s={1},d={2} => {3} {4} {5}".format(
                curr, s, d, edge_dict, edges, path)
    else:
        failed = True
        error = "this should not be reachable"

if count != len(edges):
    failed = True
    error = "wrong path length s:{0}, d:{1}, cnt:{2}, len{3} -- {4}".format(s, d, count, len(edges), edges)

if failed:
    # rollback
    plpy.execute("DELETE FROM cf WHERE fid={0}".format(f))
    plpy.execute("DELETE FROM rm WHERE fid={0}".format(f))
    plpy.notice("FAILED")
    raise Exception(error)

return 0
$$ LANGUAGE plpythonu VOLATILE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION cf_ins(f integer, s integer, d integer)
RETURNS integer
AS $$
        DECLARE
            row record;
        BEGIN
            FOR row IN (SELECT pid, sid, nid FROM pre_cf WHERE
                        id = (SELECT id FROM pre_paths WHERE src=s AND dst=d))
            LOOP
                INSERT INTO cf (fid, pid, sid, nid) VALUES (f, row.pid, row.sid, row.nid);
            END LOOP;

            PERFORM path_validate(f, s, d);
            DELETE FROM rm_delta;
            RETURN f;
        END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;

CREATE OR REPLACE RULE rm_ins AS
       ON INSERT TO rm
       DO ALSO (
           INSERT INTO rm_delta values (NEW.fid, NEW.src, NEW.dst, NEW.vol, 1);
           SELECT cf_ins(NEW.fid, NEW.src, NEW.dst);
       );
""")

    def cleanup(self):
        self.db.cursor.execute("DROP FUNCTION IF EXISTS cf_ins() CASCADE;")
        reenable_orchestration(self.db)

class RibTestConsole(AppConsole):
    def __init__(self, db, env, components):
        AppConsole.__init__(self, db, env, components)

    def map_nodes(self, nodes, attrs):
        nodemap = {}
        size = len(attrs)

        if len(nodes) < len(attrs):
            print "Warning #attrs > #nodes"
            size = len(nodes)

        sample = random.sample(nodes, size)
        for i in range(size):
            nodemap[attrs[i]] = nodes[i]

        return nodemap

    def make_paths(self, nodes, rib_size):
        prefix_file = "apps/ribtest/rib_prefixes.txt"
        ip_file = "apps/ribtest/rib_nodes.txt"

        edge_file = "apps/ribtest/rib_edges{0}.txt".format(rib_size)
        if not os.path.isfile(edge_file):
            print "ERROR: no edge file", edge_file
            return []

        # edges < rib_size

        with open(prefix_file) as f:
            prefixes = [p.strip() for p in f.readlines()]

        with open(ip_file) as f:
            ips = [ip.strip() for ip in f.readlines()]

        with open(edge_file) as f:
            edges = []
            for i, line in enumerate(f):
                if i > rib_size:
                    break
                edges.append(line.strip())

        ipmap = self.map_nodes(nodes, ips)
        prefixmap = {}

        paths = []
        for line in edges:
            tokens = line.split()
            ip = tokens[0]
            prefix = tokens[1]

            if ip not in ipmap:
                continue

            if prefix not in prefixmap:
                node = random.choice(nodes)
                prefixmap[prefix] = node

            src = ipmap[ip]
            dst = prefixmap[prefix]

            # random_border = random.choice(nodemap.values())
            # while random_border == switch:
            #     random_border = random.choice(nodemap.values())
            # dst = random_border

            paths.append((src, dst))

        return paths

    def do_test(self, line):
        if line is None or line == "":
            size = RIB_SIZE
            print "No size specified, default = ", size
        else:
            try:
                size = int(line)
            except:
                print "Invalid integer", line
                return

        self.db.cursor.execute("SELECT name FROM hosts;")
        results = self.db.cursor.fetchall()
        nodes = [n[0] for n in results]

        self.db.cursor.execute("SELECT hid, name FROM hosts;")
        results = self.db.cursor.fetchall()
        nodemap = {}
        for n in results:
            nodemap[n[1]] = n[0]

        paths = self.make_paths(nodes, size)
        print "#paths:", len(paths)

        # disable flow triggers
        self.db.cursor.execute("DROP TRIGGER IF EXISTS add_flow_trigger ON cf;")
        self.db.cursor.execute("DROP TRIGGER IF EXISTS del_flow_trigger ON cf;")

        # disable vacuuming
        vaccuum = "ALTER TABLE {0} SET (autovacuum_enabled = false, " +\
                 "toast.autovacuum_enabled = false);"

        self.db.cursor.execute(vaccuum.format("cf"))
        self.db.cursor.execute(vaccuum.format("rm"))

        precompute_paths(self.db)
        tests = [
            BaselinePrecomputedTest(self.db, self.env),
            OrchestrationPrecomputedTest(self.db, self.env),
            ColumnConstraintPrecomputedTest(self.db, self.env),
            PyTriggerPrecomputedTest(self.db, self.env),

            BaselineTest(self.db, self.env),
            OrchestrationTest(self.db, self.env),
            OptimizedOrchestrationTest(self.db, self.env),
            ColumnConstraintTest(self.db, self.env),
            PyTriggerTest(self.db, self.env)
        ]

        trials = 1
        for i in range(trials):
            for t in tests:
                print i, t.name
                elapsed = time.time()
                t.test_cdf(paths, i)
                elapsed = (time.time() - elapsed) * 1000
                if elapsed > 60000:
                    elapsed = "{0} min".format(round(elapsed / 60000.0, 3))
                elif elapsed > 1000:
                    elapsed = "{0} sec".format(round(elapsed / 1000.0, 3))
                else:
                    elapsed = "{0} ms".format(round(elapsed, 3))

                print "    ", elapsed
                sys.stdout.flush()

        print "---------------------------------------------"
        for test in tests:
            print "*** ", test.result()
        print "---------------------------------------------"

        cleanup_precomputed_paths(self.db)

shortcut = "rib"
description = "rib test"
console = RibTestConsole
