DROP TABLE IF EXISTS clock CASCADE;
CREATE UNLOGGED TABLE clock (
       counts  	integer,
       PRIMARY key (counts)
);
INSERT into clock (counts) values (0) ; -- initialize clock


DROP TABLE IF EXISTS p_spv CASCADE;
CREATE UNLOGGED TABLE p_spv (
       counts  	integer,
       status 	text,
       PRIMARY key (counts)
);

CREATE OR REPLACE FUNCTION protocol_fun() RETURNS TRIGGER AS
$$
plpy.notice ("engage ravel protocol")

ct = plpy.execute("""select max (counts) from clock""")[0]['max']
plpy.execute ("INSERT INTO p_spv VALUES (" + str (ct+1) + ", 'on');")
return None;
$$
LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;


------------------------------------------------------------
------------------------------------------------------------
---------- base tables 

DROP TABLE IF EXISTS tp CASCADE;
CREATE UNLOGGED TABLE tp (
       sid	integer,
       nid	integer,
       ishost   integer,
       isactive integer,
       bw 	integer,
       PRIMARY KEY (sid, nid)
);
CREATE INDEX ON tp(sid, nid);

CREATE TRIGGER tp_up_trigger
     AFTER UPDATE ON tp
     FOR EACH ROW
   EXECUTE PROCEDURE protocol_fun();

CREATE OR REPLACE RULE pox_tp_ins_rule AS
       ON INSERT TO pox_tp
       DO ALSO
           UPDATE tp SET isactive = 1 WHERE sid = NEW.out_switch AND nid = NEW.in_switch;

CREATE OR REPLACE RULE pox_tp_del_rule AS
       ON DELETE TO pox_tp
       DO ALSO
           UPDATE tp SET isactive = 0 WHERE sid = OLD.out_switch AND nid = OLD.in_switch;

DROP TABLE IF EXISTS switches CASCADE;
CREATE UNLOGGED TABLE switches (
       sid	integer PRIMARY KEY,
       dpid	varchar(16),
       ip	varchar(16),
       mac	varchar(17),
       name	varchar(16)
);
CREATE INDEX ON switches(sid);

DROP TABLE IF EXISTS hosts CASCADE;
CREATE UNLOGGED TABLE hosts (
       hid	integer PRIMARY KEY,
       ip	varchar(16),
       mac	varchar(17),
       name	varchar(16)
);
CREATE INDEX ON hosts (hid);

DROP VIEW IF EXISTS nodes CASCADE;
CREATE OR REPLACE VIEW nodes AS (
       SELECT sid AS id, name FROM SWITCHES UNION
       SELECT hid AS id, name FROM HOSTS
);

DROP TABLE IF EXISTS cf CASCADE;
CREATE UNLOGGED TABLE cf (
       fid	integer,
       pid	integer,
       sid	integer,
       nid	integer
--       PRIMARY KEY (fid, sid)
);
CREATE INDEX ON cf(fid,sid);

DROP TABLE IF EXISTS tm CASCADE;
CREATE UNLOGGED TABLE tm (
       fid      integer,
       src	integer,
       dst	integer,
       vol	integer,
       FW	integer,
       LB	integer,
       PRIMARY KEY (fid)
);
CREATE INDEX ON tm (fid,src,dst);

DROP TABLE IF EXISTS tm_delta CASCADE;
CREATE UNLOGGED TABLE tm_delta (
       fid      integer,
       src	integer,
       dst	integer,
       vol	integer,
       isadd	integer
);
CREATE INDEX ON tm_delta (fid,src);

CREATE OR REPLACE RULE tm_ins AS
       ON INSERT TO tm
       DO ALSO
           INSERT INTO tm_delta values (NEW.fid, NEW.src, NEW.dst, NEW.vol, 1);

CREATE OR REPLACE RULE tm_del AS
       ON DELETE TO tm
       DO ALSO(
           INSERT INTO tm_delta values (OLD.fid, OLD.src, OLD.dst, OLD.vol, 0);
	   DELETE FROM tm_delta WHERE tm_delta.fid = OLD.fid AND isadd = 1;
	   );


----------------------------------------------------------------------
----------------------------------------------------------------------
----------------------------------------------------------------------
---------- traffic matrix facing user

DROP TABLE IF EXISTS utm CASCADE;
CREATE UNLOGGED TABLE utm (
       fid      integer,
       host1	integer,
       host2	integer,
       PRIMARY KEY (fid)
);
CREATE INDEX ON utm(fid,host1);

CREATE OR REPLACE RULE utm_in_rule AS 
       ON INSERT TO utm
       DO ALSO
       INSERT INTO tm VALUES (NEW.fid,
       	      	      	      NEW.host1,
			      NEW.host2,
			      1);

CREATE OR REPLACE RULE utm_del_rule AS 
       ON DELETE TO utm
       DO ALSO DELETE FROM tm WHERE tm.fid = OLD.fid;

CREATE OR REPLACE RULE utm_up_rule AS 
       ON UPDATE TO utm
       DO ALSO (
       	  DELETE FROM tm WHERE tm.fid = OLD.fid;
	  INSERT INTO tm VALUES (OLD.fid,
				 NEW.host1,
				 NEW.host2,
				 1);
       );

----------------------------------------------------------------------
----------------------------------------------------------------------
-- routing application


-- CREATE TRIGGER tm_in_trigger
--      AFTER INSERT ON tm
--      FOR EACH ROW
--    EXECUTE PROCEDURE protocol_fun();


DROP TABLE IF EXISTS rtm_clock CASCADE;
CREATE UNLOGGED TABLE rtm_clock (
       counts  	integer
);
INSERT into rtm_clock (counts) values (0) ;

CREATE TRIGGER rtm_clock_ins
     AFTER INSERT ON rtm_clock
     FOR EACH ROW
   EXECUTE PROCEDURE protocol_fun();


DROP TABLE IF EXISTS rtm CASCADE;
CREATE UNLOGGED TABLE rtm (
       fid      integer,
       host1	integer,
       host2	integer,
       PRIMARY key (fid)
);

CREATE OR REPLACE RULE rtm_ins AS
       ON INSERT TO rtm
       DO ALSO (
       	  INSERT INTO utm VALUES (NEW.fid, NEW.host1, NEW.host2);
	  INSERT INTO rtm_clock VALUES (1);
       );

CREATE OR REPLACE RULE rtm_del AS
       ON DELETE TO rtm
       DO ALSO (
       	  DELETE FROM utm WHERE fid = OLD.fid;
	  INSERT INTO rtm_clock VALUES (2);
       );

-- CREATE OR REPLACE FUNCTION rtm_del_fun() RETURNS TRIGGER AS
-- $$
-- plpy.notice ("rtm_del_fun")
-- f = TD["old"]["fid"]

-- plpy.execute ("DELETE FROM utm WHERE utm.fid = " + str (f) + ";")
-- plpy.execute ("INSERT INTO rtm_clock VALUES (2);")
-- return None;
-- $$
-- LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;

-- CREATE TRIGGER rtm_del_trigger
--      AFTER DELETE ON rtm
--      FOR EACH ROW
--    EXECUTE PROCEDURE rtm_del_fun ();



-- CREATE OR REPLACE RULE rtm_del AS
--        ON DELETE TO rtm
--        DO INSTEAD (
--           DELETE FROM utm WHERE utm.fid = OLD.fid;
--           INSERT INTO rtm_clock VALUES (2);
--        );

DROP TABLE IF EXISTS spv_tb_ins CASCADE;
CREATE UNLOGGED TABLE spv_tb_ins (
       fid  	integer,
       pid	integer,
       sid	integer,
       nid 	integer
);

DROP TABLE IF EXISTS spv_tb_del CASCADE;
CREATE UNLOGGED TABLE spv_tb_del (
       fid  	integer,
       pid	integer,
       sid	integer,
       nid 	integer
);

CREATE OR REPLACE FUNCTION spv_constraint1_fun ()
RETURNS TRIGGER
AS $$
plpy.notice ("spv_constraint1_fun")
if TD["new"]["status"] == 'on':
    tm = plpy.execute ("SELECT * FROM tm_delta;")

    for t in tm:
        if t["isadd"] == 1:
            f = t["fid"]	   
            s = t["src"]
            d = t["dst"]
            pv = plpy.execute("""SELECT array(SELECT id1 FROM pgr_dijkstra('SELECT 1 as id, sid as source, nid as target, 1.0::float8 as cost FROM tp WHERE isactive = 1',""" +str (s) + "," + str (d)  + ",FALSE, FALSE))""")[0]['array']
	   
            l = len (pv)
            for i in range (l):
                if i + 2 < l:
                    plpy.execute ("INSERT INTO cf (fid,pid,sid,nid) VALUES (" + str (f) + "," + str (pv[i]) + "," +str (pv[i+1]) +"," + str (pv[i+2])+  ");")

        elif t["isadd"] == 0:
            f = t["fid"]
            plpy.execute ("DELETE FROM cf WHERE fid =" +str (f) +";")

    plpy.execute ("DELETE FROM tm_delta;")
return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;

CREATE TRIGGER spv_constraint1
     AFTER INSERT ON p_spv
     FOR EACH ROW
   EXECUTE PROCEDURE spv_constraint1_fun();

-- CREATE OR REPLACE FUNCTION tm_del2spv_fun ()
-- RETURNS TRIGGER
-- AS $$
-- f = TD["old"]["fid"]
-- plpy.notice (f)
-- plpy.execute("INSERT INTO spv_tb_del VALUES (fid) (" + str (f) + ");")
-- return None;
-- $$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION tp2spv_fun () RETURNS TRIGGER
AS $$

isactive = TD["new"]["isactive"]
sid = TD["new"]["sid"]
nid = TD["new"]["nid"]

plpy.notice ("tp2spv_fun executed")

if isactive == 0:
   fid_delta = plpy.execute ("SELECT fid FROM cf where (sid =" + str (sid) + "and nid =" + str (nid) +") or (sid = "+str (nid)+" and nid = "+str (sid)+");")
   if len (fid_delta) != 0:
      for fid in fid_delta:
          plpy.execute ("INSERT INTO spv_tb_del (SELECT * FROM cf WHERE fid = "+str (fid["fid"])+");")

          s = plpy.execute ("SELECT * FROM tm WHERE fid =" +str (fid["fid"]))[0]["src"]
          d = plpy.execute ("SELECT * FROM tm WHERE fid =" +str (fid["fid"]))[0]["dst"]

          pv = plpy.execute("""SELECT array(SELECT id1 FROM pgr_dijkstra('SELECT 1 as id, sid as source, nid as target, 1.0::float8 as cost FROM tp WHERE isactive = 1',""" +str (s) + "," + str (d)  + ",FALSE, FALSE))""")[0]['array']
	     
          for i in range (len (pv)):	   		     
              if i + 2 < len (pv):
                  plpy.execute ("INSERT INTO spv_tb_ins (fid,pid,sid,nid) VALUES (" + str (fid["fid"]) + "," + str (pv[i]) + "," +str (pv[i+1]) +"," + str (pv[i+2])+  ");")
	      
return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;

CREATE TRIGGER tp_up_spv_trigger
     AFTER UPDATE ON tp
     FOR EACH ROW
   EXECUTE PROCEDURE tp2spv_fun();

CREATE OR REPLACE RULE spv_constaint2 AS
       ON INSERT TO p_spv
       WHERE NEW.status = 'on'
       DO ALSO
           (UPDATE p_spv SET status = 'off' WHERE counts = NEW.counts;
	   DELETE FROM cf WHERE (fid,pid,sid,nid) IN (SELECT * FROM spv_tb_del);
           INSERT INTO cf (fid,pid,sid,nid) (SELECT * FROM spv_tb_ins);
	   DELETE FROM spv_tb_del ;   
	   DELETE FROM spv_tb_ins ;   
	   );

CREATE OR REPLACE RULE tick_spv AS
       ON UPDATE TO p_spv
       WHERE (NEW.status = 'off')
       DO ALSO
           INSERT INTO clock values (NEW.counts);

DROP VIEW IF EXISTS spv CASCADE;
CREATE OR REPLACE VIEW spv AS (
       SELECT fid,
       	      src,
	      dst,
	      (SELECT array(SELECT id1 FROM pgr_dijkstra('SELECT 1 as id,
	      	      	     	       	             sid as source,
						     nid as target,
						     1.0::float8 as cost
			                             FROM tp
						     WHERE isactive = 1', src, dst,FALSE, FALSE))) as pv
       FROM tm
);

DROP VIEW IF EXISTS spv_edge CASCADE;
CREATE OR REPLACE VIEW spv_edge AS (
       WITH num_list AS (
       SELECT UNNEST (ARRAY[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]) AS num
       )
       SELECT DISTINCT fid, num, ARRAY[pv[num], pv[num+1], pv[num+2]] as edge
       FROM spv, num_list
       WHERE pv != '{}' AND num < array_length (pv, 1) - 1
       ORDER BY fid, num
);

DROP VIEW IF EXISTS spv_switch CASCADE;
CREATE OR REPLACE VIEW spv_switch AS (
       SELECT DISTINCT fid,
       	      edge[1] as pid,
	      edge[2] as sid,
       	      edge[3] as nid
       FROM spv_edge
       ORDER BY fid
);

DROP VIEW IF EXISTS spv_ins CASCADE;
CREATE OR REPLACE VIEW spv_ins AS (
       SELECT * FROM spv_switch
       EXCEPT (SELECT * FROM cf)
       ORDER BY fid
);

DROP VIEW IF EXISTS spv_del CASCADE;
CREATE OR REPLACE VIEW spv_del AS (
       SELECT * FROM cf
       EXCEPT (SELECT * FROM spv_switch)
       ORDER BY fid
);

------------------------------------------------------------
-- auxiliary function
------------------------------------------------------------

DROP TABLE IF EXISTS ports CASCADE;
CREATE UNLOGGED TABLE ports (
       sid	integer,
       nid	integer,
       port	integer
);


CREATE OR REPLACE FUNCTION protocolp1_fun() RETURNS TRIGGER AS
$$
plpy.notice ("engage ravel protocolp1_fun starting with p1")

ct = plpy.execute("""select max (counts) from clock""")[0]['max']
plpy.execute ("INSERT INTO p1 VALUES (" + str (ct+1) + ", 'on');")
return None;
$$
LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;


CREATE OR REPLACE FUNCTION ravelall() RETURNS void AS
$$
plpy.notice ("engage ravel protocol for talb, tacl, rt")

ct = plpy.execute("""select max (counts) from clock""")[0]['max']
plpy.execute ("INSERT INTO p1 VALUES (" + str (ct+1) + ", 'on');")

$$
LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION ravel() RETURNS void AS
$$
plpy.notice ("engage ravel protocol for applications and rt")

ct = plpy.execute("""select max (counts) from clock""")[0]['max']
plpy.execute ("INSERT INTO p_spv VALUES (" + str (ct+1) + ", 'on');")

$$
LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION clean() RETURNS void AS
$$
plpy.notice ("clean db")

plpy.notice ("DELETE FROM utm;")

ct = plpy.execute("""select max (counts) from clock""")[0]['max']
plpy.execute ("INSERT INTO p_spv VALUES (" + str (ct+1) + ", 'on');")

$$
LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;
