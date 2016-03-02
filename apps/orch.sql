----------------------------------------------------------------------
-- orchestration protocol for (Merlin, Kinetic, PGA, routing)
----------------------------------------------------------------------

DROP TABLE IF EXISTS p_PGA CASCADE;
CREATE UNLOGGED TABLE p_PGA (
       counts  	integer,
       status 	text,
       PRIMARY key (counts)
);

CREATE OR REPLACE RULE run_PGA AS
       ON INSERT TO p_PGA
       WHERE (NEW.status = 'on')
       DO ALSO (
           DELETE FROM PGA_violation;
	   UPDATE p_PGA SET status = 'off' WHERE counts = NEW.counts;
	  );


DROP TABLE IF EXISTS p_FW CASCADE;
CREATE UNLOGGED TABLE p_FW (
       counts  	integer,
       status 	text,
       PRIMARY key (counts)
);

CREATE OR REPLACE RULE run_FW AS
       ON INSERT TO p_FW
       WHERE (NEW.status = 'on')
       DO ALSO (
           DELETE FROM FW_violation;
	   UPDATE p_FW SET status = 'off' WHERE counts = NEW.counts;
	  );


DROP TABLE IF EXISTS p_Merlin CASCADE;
CREATE UNLOGGED TABLE p_Merlin (
       counts  	integer,
       status 	text,
       PRIMARY key (counts)
);

CREATE OR REPLACE RULE run_Merlin AS
       ON INSERT TO p_Merlin
       WHERE (NEW.status = 'on')
       DO ALSO (
           DELETE FROM FW_violation;
	   UPDATE p_Merlin SET status = 'off' WHERE counts = NEW.counts;
	  );



-------- hook up with routing (existing code)

DROP TABLE IF EXISTS p_RT CASCADE;
CREATE UNLOGGED TABLE p_RT (
       counts  	integer,
       status 	text,
       PRIMARY key (counts)
);

-- run_RT_trigger instead is analogous to
-- DELETE FROM rt_violation;
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

-- CREATE OR REPLACE RULE rt2c AS
--        ON UPDATE TO p_spv
--        WHERE (NEW.status = 'off')
--        DO ALSO
--            INSERT INTO clock values (NEW.counts);


-------- implement a total order

CREATE OR REPLACE RULE PGA2FW AS
       ON UPDATE TO p_PGA
       WHERE (NEW.status = 'off')
       DO ALSO
           INSERT INTO p_FW values (NEW.counts, 'on');

CREATE OR REPLACE RULE FW2Merlin AS
       ON UPDATE TO p_FW
       WHERE (NEW.status = 'off')
       DO ALSO
           INSERT INTO p_Merlin values (NEW.counts, 'on');

-- CREATE OR REPLACE RULE Merlin2c AS
--        ON UPDATE TO p_Merlin
--        WHERE (NEW.status = 'off')
--        DO ALSO
--            INSERT INTO clock values (NEW.counts);

CREATE OR REPLACE RULE Merlin2c AS
       ON UPDATE TO p_Merlin
       WHERE (NEW.status = 'off')
       DO ALSO
           INSERT INTO p_RT values (NEW.counts, 'on');

CREATE OR REPLACE RULE Routing2c AS
       ON UPDATE TO p_RT
       WHERE (NEW.status = 'off')
       DO ALSO
           INSERT INTO clock values (NEW.counts);

----------------------------------------------------------------------
-- policy configuration in companion with toy topology 
-- "cli-ravel/topo/toy_tdp.py"
----------------------------------------------------------------------

-- PGA configuration
INSERT INTO PGA_policy (gid1, gid2, MB)
VALUES (1,2,'FW'),
       (4,3,'LB');

INSERT INTO PGA_group 
       (gid, sid_array)
VALUES
	(1, ARRAY[5]),
	(2, ARRAY[6]),
	(3, ARRAY[6,7]),
	(4, ARRAY[5,8]);

-- (Kinetic) configuration
INSERT INTO FW_policy_acl VALUES (8,7,0);
INSERT INTO FW_policy_user VALUES (6),(8);
