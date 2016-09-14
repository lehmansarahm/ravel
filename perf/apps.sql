DROP TABLE IF EXISTS mt_tb CASCADE;
CREATE UNLOGGED TABLE mt_tb (
       sid	integer
);

CREATE OR REPLACE VIEW mt AS (
       SELECT mt_tb.sid,
	      sum (isactive) AS isactive 
       FROM mt_tb, tp
       WHERE mt_tb.sid = tp.sid
       GROUP BY mt_tb.sid 
);

CREATE OR REPLACE RULE mt2tp AS
       ON UPDATE TO mt
       DO INSTEAD
       	  UPDATE tp SET isactive = NEW.isactive WHERE sid = NEW.sid OR nid = NEW.sid;

----------------------------------------------------------------------
-- acl application
----------------------------------------------------------------------

DROP TABLE IF EXISTS acl_tb CASCADE;
CREATE UNLOGGED TABLE acl_tb (
       end1	      integer,
       end2 	      integer,
       inBlklist      integer,
       PRIMARY key (end1, end2)		
);
CREATE INDEX ON acl_tb (end1,end2);

CREATE OR REPLACE VIEW acl AS(
       SELECT DISTINCT end1, end2, inBlklist, 1 as isViolated
       FROM acl_tb, rm
       WHERE acl_tb.end1 = rm.src and acl_tb.end2 = rm.dst and inBlklist = 1);

CREATE OR REPLACE RULE acl2utm AS
       ON UPDATE TO acl
       DO INSTEAD
       	  DELETE FROM rm WHERE src = NEW.end1 AND dst = NEW.end2;

----------------------------------------------------------------------
-- load_balance application
----------------------------------------------------------------------

DROP TABLE IF EXISTS lb_tb CASCADE;
CREATE UNLOGGED TABLE lb_tb (
       sid	integer,
       PRIMARY key (sid)
);
CREATE INDEX ON lb_tb (sid);

CREATE OR REPLACE VIEW lb AS(
       SELECT sid,
       	      (SELECT count(*) FROM rm
	       WHERE dst = sid) AS load
       FROM lb_tb
       );

CREATE OR REPLACE RULE lb2utm AS
       ON UPDATE TO lb
       DO INSTEAD 
          UPDATE rm
          SET dst =
	      (SELECT sid FROM lb
	       WHERE load = (SELECT min (load) FROM lb LIMIT (OLD.load - NEW.load)) LIMIT 1)
              WHERE fid IN
       	       (SELECT fid FROM rm WHERE dst = NEW.sid LIMIT (OLD.load - NEW.load));


DROP TABLE IF EXISTS p1 CASCADE;
CREATE UNLOGGED TABLE p1 (
       counts  	integer,
       status 	text,
       PRIMARY key (counts)
);

DROP TABLE IF EXISTS p2 CASCADE;
CREATE UNLOGGED TABLE p2 (
       counts  	integer,
       status 	text,
       PRIMARY key (counts)
);

DROP TABLE IF EXISTS p3 CASCADE;
CREATE UNLOGGED TABLE p3 (
       counts  	integer,
       status 	text,
       PRIMARY key (counts)
);

CREATE OR REPLACE RULE lb_constraint AS
       ON INSERT TO p1
       WHERE (NEW.status = 'on')
       DO ALSO (
           UPDATE lb SET load = 2 WHERE load > 2;
	   UPDATE p1 SET status = 'off' WHERE counts = NEW.counts;
	  );

CREATE OR REPLACE RULE p12 AS
       ON UPDATE TO p1
       WHERE (NEW.status = 'off')
       DO ALSO
           INSERT INTO p2 values (NEW.counts, 'on');

CREATE OR REPLACE RULE acl_constraint AS
       ON INSERT TO p2
       WHERE (NEW.status = 'on')
       DO ALSO (
           UPDATE acl SET isviolated = 0 WHERE isviolated = 1;
	   UPDATE p2 SET status = 'off' WHERE counts = NEW.counts;
	  );

CREATE OR REPLACE RULE p23 AS
       ON UPDATE TO p2
       WHERE (NEW.status = 'off')
       DO ALSO
           INSERT INTO p3 values (NEW.counts, 'on');

CREATE TRIGGER rt_constraint_trigger
     AFTER INSERT ON p3
     FOR EACH ROW
        EXECUTE PROCEDURE spv_constraint1_fun();

CREATE OR REPLACE RULE rt_constraint AS
       ON INSERT TO p3
       WHERE (NEW.status = 'on')
       DO ALSO (
	   UPDATE p3 SET status = 'off' WHERE counts = NEW.counts;
	  );

CREATE OR REPLACE RULE p3c AS
       ON UPDATE TO p3
       WHERE (NEW.status = 'off')
       DO ALSO
           INSERT INTO clock values (NEW.counts);

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

plpy.notice ("DELETE FROM rm;")

ct = plpy.execute("""select max (counts) from clock""")[0]['max']
plpy.execute ("INSERT INTO p_spv VALUES (" + str (ct+1) + ", 'on');")

$$
LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;


DROP TABLE IF EXISTS borders CASCADE;
CREATE UNLOGGED TABLE borders (
       sid  	text,
       peerip	text,
       primary key (sid)
);
CREATE INDEX ON borders (sid);
