DROP TABLE IF EXISTS sample CASCADE;
CREATE UNLOGGED TABLE sample (
       id  integer PRIMARY KEY
);

DROP VIEW IF EXISTS sample_view;
CREATE OR REPLACE VIEW sample_view AS (
       SELECT id
       FROM sample
);

DROP FUNCTION IF EXISTS sample_fun(blah varchar(16));
CREATE OR REPLACE FUNCTION sample_fun(blah varchar(16)) RETURNS TRIGGER AS
$$
plpy.notice ("engage ravel protocol")
return None;
$$
LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;
