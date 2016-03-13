----------------------------------------------------------------------
-- kinetic (stateful firewall)
----------------------------------------------------------------------
DROP TABLE IF EXISTS FW_policy_acl CASCADE;
CREATE UNLOGGED TABLE FW_policy_acl (
       end1	      integer,
       end2 	      integer,
       allow	      integer,
       PRIMARY key (end1, end2)		
);
CREATE INDEX ON FW_policy_acl (end1,end2);

DROP TABLE IF EXISTS FW_policy_user CASCADE;
CREATE UNLOGGED TABLE FW_policy_user (
       uid	      integer
);

CREATE OR REPLACE RULE FW1 AS
       ON INSERT TO tm
       WHERE ((NEW.src, NEW.dst) NOT IN (SELECT end2, end1 FROM FW_policy_acl)) AND 
       	      (NEW.src IN (SELECT * FROM FW_policy_user))
       DO ALSO (
       	  INSERT INTO FW_policy_acl VALUES (NEW.dst, NEW.src, 1);
       );

CREATE OR REPLACE RULE FW2 AS
       ON DELETE TO tm
       WHERE (SELECT count(*) FROM tm WHERE src = OLD.src AND dst = OLD.dst) = 1 AND 
       	     (OLD.src IN (SELECT * FROM FW_policy_user))
       DO ALSO 
       	  DELETE FROM FW_policy_acl WHERE end2 = OLD.src AND end1 = OLD.dst;

CREATE OR REPLACE VIEW FW_violation AS (
       SELECT fid
       FROM tm 
       WHERE FW = 1  AND (src, dst) NOT IN (SELECT end1, end2 FROM FW_policy_acl)
);

CREATE OR REPLACE RULE FW_repair AS
       ON DELETE TO FW_violation
       DO INSTEAD
       	  DELETE FROM tm WHERE fid = OLD.fid;

-- ------------------------------------------------------------------
-- -- (Kinetic) firewall configuration for the toy example
--INSERT INTO FW_policy_acl VALUES (8,7,0);
--INSERT INTO FW_policy_user VALUES (6),(8);
