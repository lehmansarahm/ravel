
DROP TABLE IF EXISTS p_fw CASCADE;
CREATE UNLOGGED TABLE p_fw (
       counts integer,
       status text,
       PRIMARY key (counts)
);

CREATE OR REPLACE RULE run_fw AS
    ON INSERT TO p_fw
    WHERE (NEW.status = 'on')
    DO ALSO (
        DELETE FROM fw_violation;
        UPDATE p_fw SET status = 'off' WHERE counts = NEW.counts;
        );

CREATE OR REPLACE RULE fw2Clock AS
    ON UPDATE TO p_fw
    WHERE (NEW.status = 'off')
    DO ALSO
        INSERT INTO clock values (NEW.counts);
