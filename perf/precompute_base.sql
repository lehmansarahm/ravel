------------------------------------------------------------
-- BASE TABLES
------------------------------------------------------------

/* Topology table - pairs of connected nodes
 * sid: switch id
 * nid: next-hop id
 * ishost: if nid is a host
 * isactive: if the sid-nid link is online
 * bw: link bandwidth
 */
DROP TABLE IF EXISTS tp CASCADE;
CREATE UNLOGGED TABLE tp (
       sid      integer,
       nid      integer,
       ishost   integer,
       isactive integer,
       bw       integer,
       PRIMARY KEY (sid, nid)
);
CREATE INDEX ON tp(sid, nid);


/* Configuration table - per-switch flow configuration
 * fid: flow id
 * pid: id of previous-hop node
 * sid: switch id
 * nid: id of next-hop node
 */
DROP TABLE IF EXISTS cf CASCADE;
CREATE UNLOGGED TABLE cf (
       fid      integer,
       pid      integer,
       sid      integer,
       nid      integer
);
CREATE INDEX ON cf(fid,sid);


/* Reachability matrix - end-to-end reachability matrix
 * fid: flow id
 * src: the IP address of the source node
 * dst: the IP address of the destination node
 * vol: volume allocated for the flow
 * FW: if flow should pass through a firewall
 * LB: if flow should be load balanced
 */
DROP TABLE IF EXISTS rm CASCADE;
CREATE UNLOGGED TABLE rm (
       fid      integer,
       src      integer,
       dst      integer,
       vol      integer,
       FW       integer,
       LB       integer,
       PRIMARY KEY (fid)
);
CREATE INDEX ON rm (fid,src,dst);



------------------------------------------------------------
-- NODE TABLES
------------------------------------------------------------

/* Switch table
 * sid: switch id (primary key, NOT datapath id)
 * dpid: datapath id
 * ip: switch's IP address
 * mac: switch's MAC address
 * name: switch's name (in Mininet) 
 */
DROP TABLE IF EXISTS switches CASCADE;
CREATE UNLOGGED TABLE switches (
       sid	integer PRIMARY KEY,
       dpid	varchar(16),
       ip	varchar(16),
       mac	varchar(17),
       name	varchar(16)
);
CREATE INDEX ON switches(sid);


/* Host table
 * hid: host id
 * ip: host's IP address
 * mac: host's MAC address
 * name: hostname (in Mininet)
 */
DROP TABLE IF EXISTS hosts CASCADE;
CREATE UNLOGGED TABLE hosts (
       hid	integer PRIMARY KEY,
       ip	varchar(16),
       mac	varchar(17),
       name	varchar(16)
);
CREATE INDEX ON hosts (hid);


/* Node view - all nodes and switches in the network
 * id: the node's id from its respective table (hosts.hid or switches.sid)
 * name: the node's name
 */
DROP VIEW IF EXISTS nodes CASCADE;
CREATE OR REPLACE VIEW nodes AS (
       SELECT sid AS id, name FROM switches UNION
       SELECT hid AS id, name FROM hosts
);


/* Ports table
 * sid - switch id
 * nid - id of next-hop node
 * port - outport on sid for nid
 */
DROP TABLE IF EXISTS ports CASCADE;
CREATE UNLOGGED TABLE ports (
       sid      integer,
       nid      integer,
       port     integer
);


------------------------------------------------------------
-- REACHABILITY MATRIX UPDATES
------------------------------------------------------------

DROP TABLE IF EXISTS rm_delta CASCADE;
CREATE UNLOGGED TABLE rm_delta (
       fid      integer,
       src      integer,
       dst      integer,
       vol      integer,
       isadd    integer
);
CREATE INDEX ON rm_delta (fid,src);

CREATE OR REPLACE RULE rm_ins AS
       ON INSERT TO rm
       DO ALSO
           INSERT INTO rm_delta values (NEW.fid, NEW.src, NEW.dst, NEW.vol, 1);

CREATE OR REPLACE RULE rm_del AS
       ON DELETE TO rm
       DO ALSO(
           INSERT INTO rm_delta values (OLD.fid, OLD.src, OLD.dst, OLD.vol, 0);
           DELETE FROM rm_delta WHERE rm_delta.fid = OLD.fid AND isadd = 1;
           );



------------------------------------------------------------
-- ORCHESTRATION PROTOCOL
------------------------------------------------------------

/* Orchestration token clock */
DROP TABLE IF EXISTS clock CASCADE;
CREATE UNLOGGED TABLE clock (
       counts   integer,
       PRIMARY key (counts)
);


/* Initialize the clock to 0 */
INSERT into clock (counts) values (0) ;


/* Routing shortest path vector priority table */
DROP TABLE IF EXISTS p_spv CASCADE;
CREATE UNLOGGED TABLE p_spv (
       counts   integer,
       status   text,
       PRIMARY key (counts)
);


/* Orchestration enabling function */
CREATE OR REPLACE FUNCTION protocol_fun() RETURNS TRIGGER AS
$$
ct = plpy.execute("""select max (counts) from clock""")[0]['max']
plpy.execute ("INSERT INTO p_spv VALUES (" + str (ct+1) + ", 'on');")
return None;
$$
LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;



------------------------------------------------------------
-- PRECOMPUTED PATHS
------------------------------------------------------------

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

DROP FUNCTION IF EXISTS spv_constraint1_fun_unprofiled();
CREATE OR REPLACE FUNCTION spv_constraint1_fun_unprofiled ()
RETURNS integer
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
            RETURN 0;
        END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION spv_constraint1_fun()
RETURNS TRIGGER
AS $$
   BEGIN
      PERFORM spv_constraint1_fun_unprofiled();
      RETURN NEW;
   END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;

CREATE TRIGGER spv_constraint1
       AFTER INSERT ON p_spv
       FOR EACH ROW
       EXECUTE PROCEDURE spv_constraint1_fun();

CREATE OR REPLACE RULE spv_constaint2 AS
       ON INSERT TO p_spv
       WHERE NEW.status = 'on'
       DO ALSO
           (UPDATE p_spv SET status = 'off' WHERE counts = NEW.counts;
           );

DROP FUNCTION IF EXISTS spv_constraint1_fun_profiled();
CREATE OR REPLACE FUNCTION spv_constraint1_fun_profiled ()
RETURNS integer
AS $$
import time

fo = open("/home/croft1/src/ravel/next-ravel/log.txt", "a")
def logfunc(msg,f=fo):
    f.write(msg + "\n")
    f.flush()

rm = plpy.execute("SELECT * FROM rm_delta;")
for r in rm:
    if r["isadd"] == 1:
        f = r["fid"]
        s = r["src"]
        d = r["dst"]

        elapsed = time.time()
        records = plpy.execute("SELECT pid, sid, nid FROM pre_cf WHERE id = "
                               "(SELECT id FROM pre_paths WHERE src={0} and dst={1});"
                               .format(s, d))
        elapsed = round((time.time() - elapsed) * 1000, 3)
        logfunc("#pi----select_pre_ms----{0}".format(elapsed))

        elapsed = time.time()
        for r in records:
            plpy.execute("INSERT INTO cf (fid, pid, sid, nid) VALUES ({0}, {1}, {2}, {3});"
                        .format(f, r['pid'], r['sid'], r['nid']))

        elapsed = round((time.time() - elapsed) * 1000, 3)
        logfunc("#pi----insert_into_cf_ms----{0}".format(elapsed))

    elif r["isadd"] == 0:
        f = r["fid"]
        elapsed = time.time()
        plpy.execute("DELETE FROM cf WHERE fid={0};".format(f))
        elapsed = round((time.time() - elapsed) * 1000, 3)
        logfunc("#pd----delete_from_cf_ms----{0}".format(elapsed))

    plpy.execute("DELETE FROM rm_delta;")
return 0
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;



------------------------------------------------------------
-- USER-FACING REACHABILITY MATRIX
------------------------------------------------------------

/* User reachability matrix */
DROP TABLE IF EXISTS urm CASCADE;
CREATE UNLOGGED TABLE urm (
       fid      integer,
       host1    integer,
       host2    integer,
       PRIMARY KEY (fid)
);
CREATE INDEX ON urm(fid,host1);


/* User reachability matrix insertion */
CREATE OR REPLACE RULE urm_in_rule AS
       ON INSERT TO urm
       DO ALSO
       INSERT INTO rm VALUES (NEW.fid,
                              NEW.host1,
                              NEW.host2,
                              1);


/* User reachability matrix deletion */
CREATE OR REPLACE RULE urm_del_rule AS
       ON DELETE TO urm
       DO ALSO DELETE FROM rm WHERE rm.fid = OLD.fid;

/* User reachability matrix update */
CREATE OR REPLACE RULE urm_up_rule AS
       ON UPDATE TO urm
       DO ALSO (
          DELETE FROM rm WHERE rm.fid = OLD.fid;
          INSERT INTO rm VALUES (OLD.fid,
                                 NEW.host1,
                                 NEW.host2,
                                 1);
       );



------------------------------------------------------------
-- TOPOLOGY UPDATES/REROUTING
------------------------------------------------------------

CREATE OR REPLACE FUNCTION tp2spv_fun () RETURNS TRIGGER
AS $$
isactive = TD["new"]["isactive"]
sid = TD["new"]["sid"]
nid = TD["new"]["nid"]
if isactive == 0:
   fid_delta = plpy.execute ("SELECT fid FROM cf where (sid =" + str (sid) + "and nid =" + str (nid) +") or (sid = "+str (nid)+" and nid = "+str (sid)+");")
   if len (fid_delta) != 0:
      for fid in fid_delta:
          plpy.execute ("INSERT INTO spv_tb_del (SELECT * FROM cf WHERE fid = "+str (fid["fid"])+");")

          s = plpy.execute ("SELECT * FROM rm WHERE fid =" +str (fid["fid"]))[0]["src"]
          d = plpy.execute ("SELECT * FROM rm WHERE fid =" +str (fid["fid"]))[0]["dst"]

          pv = plpy.execute("""SELECT array(SELECT id1 FROM pgr_dijkstra('SELECT 1 as id, sid as source, nid as target, 1.0::float8 as cost FROM tp WHERE isactive = 1',""" +str (s) + "," + str (d)  + ",FALSE, FALSE))""")[0]['array']

          for i in range (len (pv)):
              if i + 2 < len (pv):
                  plpy.execute ("INSERT INTO spv_tb_ins (fid,pid,sid,nid) VALUES (" + str (fid["fid"]) + "," + str (pv[i]) + "," +str (pv[i+1]) +"," + str (pv[i+2])+  ");")

return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;

CREATE TRIGGER tp_up_trigger
       AFTER UPDATE ON tp
       FOR EACH ROW
       EXECUTE PROCEDURE protocol_fun();

CREATE TRIGGER tp_up_spv_trigger
       AFTER UPDATE ON tp
       FOR EACH ROW
       EXECUTE PROCEDURE tp2spv_fun();

