DROP TABLE IF EXISTS Merlin_policy CASCADE;
CREATE UNLOGGED TABLE MERLIN_policy (
       fid	      integer,
       rate 	      integer,
       PRIMARY key (fid)
);

CREATE OR REPLACE VIEW MERLIN_violation AS (
       SELECT tm.fid, rate AS req, vol AS asgn
       FROM tm, Merlin_policy
       WHERE tm.fid = Merlin_policy.fid AND rate > vol
);

CREATE OR REPLACE RULE Merlin_repair AS
       ON DELETE TO Merlin_violation
       DO INSTEAD
              UPDATE tm SET vol = OLD.req WHERE fid = OLD.fid;
