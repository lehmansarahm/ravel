--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


--
-- Name: plpythonu; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpythonu WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpythonu; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpythonu IS 'PL/PythonU untrusted procedural language';


--
-- Name: plsh; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plsh WITH SCHEMA public;


--
-- Name: EXTENSION plsh; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plsh IS 'PL/sh procedural language';


--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry, geography, and raster spatial types and functions';


--
-- Name: pgrouting; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS pgrouting WITH SCHEMA public;


--
-- Name: EXTENSION pgrouting; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgrouting IS 'pgRouting Extension';


SET search_path = public, pg_catalog;

--
-- Name: add_flow_fun(integer, character varying, character varying, character varying, character varying, character varying, character varying, character varying, integer, integer, character varying); Type: FUNCTION; Schema: public; Owner: ravel
--

CREATE FUNCTION add_flow_fun(flow_id integer, sw_name character varying, sw_ip character varying, sw_dpid character varying, src_ip character varying, src_mac character varying, dst_ip character varying, dst_mac character varying, outport integer, revoutport integer, diff character varying) RETURNS integer
    LANGUAGE plpythonu SECURITY DEFINER
    AS $$
import os
import sys
import time

if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
sys.path.append("/home/ravel/ravel")

from ravel.flow import installFlow, Switch
from ravel.profiling import PerfCounter

pc = PerfCounter("db_select", float(diff))
pc.report()
sw = Switch(sw_name, sw_ip, sw_dpid)
installFlow(flow_id, sw, src_ip, src_mac, dst_ip, dst_mac, outport, revoutport)

return 0
$$;


ALTER FUNCTION public.add_flow_fun(flow_id integer, sw_name character varying, sw_ip character varying, sw_dpid character varying, src_ip character varying, src_mac character varying, dst_ip character varying, dst_mac character varying, outport integer, revoutport integer, diff character varying) OWNER TO ravel;

--
-- Name: add_flow_pre(); Type: FUNCTION; Schema: public; Owner: ravel
--

CREATE FUNCTION add_flow_pre() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
    DECLARE
        sw_name varchar(16);
        sw_ip varchar(16);
        sw_dpid varchar(16);

        src_id int;
        src_ip varchar(16);
        src_mac varchar(17);

        dst_id int;
        dst_ip varchar(16);
        dst_mac varchar(17);

        outport int;
        revoutport int;

        start_time timestamptz;
        end_time timestamptz;
        diff interval;

    BEGIN
        start_time := clock_timestamp();

        SELECT port INTO outport
               FROM ports
               WHERE sid=NEW.sid AND nid=NEW.nid;

        SELECT port INTO revoutport
               FROM ports
               WHERE sid=NEW.sid AND nid=NEW.pid;

        /* get src, dst host uids */
        SELECT src, dst INTO src_id, dst_id
               FROM rm
               WHERE fid=NEW.fid;

        SELECT name, ip, dpid INTO sw_name, sw_ip, sw_dpid
               FROM switches
               WHERE sid=NEW.sid;

        /* get src, dst addresses */
        SELECT ip, mac INTO src_ip, src_mac
               FROM hosts
               WHERE hid=src_id;

        SELECT ip, mac INTO dst_ip, dst_mac
               FROM hosts
               WHERE hid=dst_id;

        /* for profiling */
        end_time := clock_timestamp();
        diff := (EXTRACT(epoch FROM end_time) - EXTRACT(epoch FROM start_time));

        PERFORM add_flow_fun(NEW.fid,
                             sw_name, sw_ip, sw_dpid,
                             src_ip, src_mac,
                             dst_ip, dst_mac,
                             outport, revoutport,
                             to_char(diff, 'MS.US'));

        return NEW;
    END;
$$;


ALTER FUNCTION public.add_flow_pre() OWNER TO ravel;

--
-- Name: add_host_fun(); Type: FUNCTION; Schema: public; Owner: ravel
--

CREATE FUNCTION add_host_fun() RETURNS trigger
    LANGUAGE plpythonu SECURITY DEFINER
    AS $$
import os
import sys

if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
sys.path.append("/home/ravel/ravel")

from ravel.network import AddHostMessage, NetworkProvider
from ravel.messaging import MsgQueueSender

hid = TD["new"]["hid"]
name = TD["new"]["name"]
ip = TD["new"]["ip"]
mac = TD["new"]["mac"]

msg = AddHostMessage(hid, name, ip, mac)
sender = MsgQueueSender(NetworkProvider.QueueId)
sender.send(msg)

return None;
$$;


ALTER FUNCTION public.add_host_fun() OWNER TO ravel;

--
-- Name: add_link_fun(); Type: FUNCTION; Schema: public; Owner: ravel
--

CREATE FUNCTION add_link_fun() RETURNS trigger
    LANGUAGE plpythonu SECURITY DEFINER
    AS $$
import os
import sys

if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
sys.path.append("/home/ravel/ravel")

from ravel.network import AddLinkMessage, NetworkProvider
from ravel.messaging import MsgQueueSender

sid = TD["new"]["sid"]
nid = TD["new"]["nid"]
isHost = TD["new"]["ishost"]
isActive = TD["new"]["ishost"]

msg = AddLinkMessage(sid, nid, isHost, isActive)
sender = MsgQueueSender(NetworkProvider.QueueId)
sender.send(msg)

return None;
$$;


ALTER FUNCTION public.add_link_fun() OWNER TO ravel;

--
-- Name: add_switch_fun(); Type: FUNCTION; Schema: public; Owner: ravel
--

CREATE FUNCTION add_switch_fun() RETURNS trigger
    LANGUAGE plpythonu SECURITY DEFINER
    AS $$
import os
import sys

if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
sys.path.append("/home/ravel/ravel")

from ravel.network import AddSwitchMessage, NetworkProvider
from ravel.messaging import MsgQueueSender

sid = TD["new"]["sid"]
name = TD["new"]["name"]
dpid = TD["new"]["dpid"]
ip = TD["new"]["ip"]
mac = TD["new"]["mac"]

msg = AddSwitchMessage(sid, name, dpid, ip, mac)
sender = MsgQueueSender(NetworkProvider.QueueId)
sender.send(msg)

return None;
$$;


ALTER FUNCTION public.add_switch_fun() OWNER TO ravel;

--
-- Name: del_flow_fun(integer, character varying, character varying, character varying, character varying, character varying, character varying, character varying, integer, integer, character varying); Type: FUNCTION; Schema: public; Owner: ravel
--

CREATE FUNCTION del_flow_fun(flow_id integer, sw_name character varying, sw_ip character varying, sw_dpid character varying, src_ip character varying, src_mac character varying, dst_ip character varying, dst_mac character varying, outport integer, revoutport integer, diff character varying) RETURNS integer
    LANGUAGE plpythonu SECURITY DEFINER
    AS $$
import os
import sys
import time

if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
sys.path.append("/home/ravel/ravel")

from ravel.flow import removeFlow, Switch
from ravel.profiling import PerfCounter

pc = PerfCounter("db_select", float(diff))
pc.report()

sw = Switch(sw_name, sw_ip, sw_dpid)
removeFlow(flow_id, sw, src_ip, src_mac, dst_ip, dst_mac, outport, revoutport)

return 0
$$;


ALTER FUNCTION public.del_flow_fun(flow_id integer, sw_name character varying, sw_ip character varying, sw_dpid character varying, src_ip character varying, src_mac character varying, dst_ip character varying, dst_mac character varying, outport integer, revoutport integer, diff character varying) OWNER TO ravel;

--
-- Name: del_flow_pre(); Type: FUNCTION; Schema: public; Owner: ravel
--

CREATE FUNCTION del_flow_pre() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
    DECLARE
        sw_name varchar(16);
        sw_ip varchar(16);
        sw_dpid varchar(16);

        src_id int;
        src_ip varchar(16);
        src_mac varchar(17);

        dst_id int;
        dst_ip varchar(16);
        dst_mac varchar(17);

        outport int;
        revoutport int;

        start_time timestamptz;
        end_time timestamptz;
        diff interval;
    BEGIN
        start_time := clock_timestamp();

        SELECT port INTO outport
               FROM ports
               WHERE sid=OLD.sid and nid=OLD.nid;

        SELECT port INTO revoutport
               FROM ports
               WHERE sid=OLD.sid and nid=OLD.pid;

        /* get src, dst host uids */
        SELECT src, dst INTO src_id, dst_id
               FROM rm_delta
               WHERE fid=OLD.fid;

        /* get src, dst addresses */
        SELECT name, ip, dpid INTO sw_name, sw_ip, sw_dpid
               FROM switches
               WHERE sid=OLD.sid;

        /* get src, dst addresses */
        SELECT ip, mac INTO src_ip, src_mac
               FROM hosts
               WHERE hid=src_id;

        SELECT ip, mac INTO dst_ip, dst_mac
               FROM hosts
               WHERE hid=dst_id;

        /* for profiling */
        end_time := clock_timestamp();
        diff := (extract(epoch from end_time) - extract(epoch from start_time));

        PERFORM del_flow_fun(OLD.fid,
                             sw_name, sw_ip, sw_dpid,
                             src_ip, src_mac,
                             dst_ip, dst_mac,
                             outport, revoutport,
                             to_char(diff, 'MS.US'));

        return OLD;
    END;
$$;


ALTER FUNCTION public.del_flow_pre() OWNER TO ravel;

--
-- Name: del_host_fun(); Type: FUNCTION; Schema: public; Owner: ravel
--

CREATE FUNCTION del_host_fun() RETURNS trigger
    LANGUAGE plpythonu SECURITY DEFINER
    AS $$
import os
import sys

if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
sys.path.append("/home/ravel/ravel")

from ravel.network import RemoveHostMessage, NetworkProvider
from ravel.messaging import MsgQueueSender

hid = TD["old"]["hid"]
name = TD["old"]["name"]

msg = RemoveHostMessage(hid, name)
sender = MsgQueueSender(NetworkProvider.QueueId)
sender.send(msg)

return None;
$$;


ALTER FUNCTION public.del_host_fun() OWNER TO ravel;

--
-- Name: del_link_fun(); Type: FUNCTION; Schema: public; Owner: ravel
--

CREATE FUNCTION del_link_fun() RETURNS trigger
    LANGUAGE plpythonu SECURITY DEFINER
    AS $$
import os
import sys

if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
sys.path.append("/home/ravel/ravel")

from ravel.network import RemoveLinkMessage, NetworkProvider
from ravel.messaging import MsgQueueSender

sid = TD["old"]["sid"]
nid = TD["old"]["nid"]

msg = RemoveLinkMessage(sid, nid)
sender = MsgQueueSender(NetworkProvider.QueueId)
sender.send(msg)

return None;
$$;


ALTER FUNCTION public.del_link_fun() OWNER TO ravel;

--
-- Name: del_switch_fun(); Type: FUNCTION; Schema: public; Owner: ravel
--

CREATE FUNCTION del_switch_fun() RETURNS trigger
    LANGUAGE plpythonu SECURITY DEFINER
    AS $$
import os
import sys

if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
sys.path.append("/home/ravel/ravel")

from ravel.network import RemoveSwitchMessage, NetworkProvider
from ravel.messaging import MsgQueueSender

sid = TD["old"]["sid"]
name = TD["old"]["name"]

msg = RemoveSwitchMessage(sid, name)
sender = MsgQueueSender(NetworkProvider.QueueId)
sender.send(msg)

return None;
$$;


ALTER FUNCTION public.del_switch_fun() OWNER TO ravel;

--
-- Name: protocol_fun(); Type: FUNCTION; Schema: public; Owner: ravel
--

CREATE FUNCTION protocol_fun() RETURNS trigger
    LANGUAGE plpythonu SECURITY DEFINER
    AS $$
ct = plpy.execute("""select max (counts) from clock""")[0]['max']
plpy.execute ("INSERT INTO p_spv VALUES (" + str (ct+1) + ", 'on');")
return None;
$$;


ALTER FUNCTION public.protocol_fun() OWNER TO ravel;

--
-- Name: spv_constraint1_fun(); Type: FUNCTION; Schema: public; Owner: ravel
--

CREATE FUNCTION spv_constraint1_fun() RETURNS trigger
    LANGUAGE plpythonu SECURITY DEFINER
    AS $$
plpy.notice ("spv_constraint1_fun")
if TD["new"]["status"] == 'on':
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
return None;
$$;


ALTER FUNCTION public.spv_constraint1_fun() OWNER TO ravel;

--
-- Name: tp2spv_fun(); Type: FUNCTION; Schema: public; Owner: ravel
--

CREATE FUNCTION tp2spv_fun() RETURNS trigger
    LANGUAGE plpythonu SECURITY DEFINER
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
$$;


ALTER FUNCTION public.tp2spv_fun() OWNER TO ravel;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: cf; Type: TABLE; Schema: public; Owner: ravel; Tablespace: 
--

CREATE UNLOGGED TABLE cf (
    fid integer,
    pid integer,
    sid integer,
    nid integer
);


ALTER TABLE public.cf OWNER TO ravel;

--
-- Name: clock; Type: TABLE; Schema: public; Owner: ravel; Tablespace: 
--

CREATE UNLOGGED TABLE clock (
    counts integer NOT NULL
);


ALTER TABLE public.clock OWNER TO ravel;

--
-- Name: hosts; Type: TABLE; Schema: public; Owner: ravel; Tablespace: 
--

CREATE UNLOGGED TABLE hosts (
    hid integer NOT NULL,
    ip character varying(16),
    mac character varying(17),
    name character varying(16)
);


ALTER TABLE public.hosts OWNER TO ravel;

--
-- Name: switches; Type: TABLE; Schema: public; Owner: ravel; Tablespace: 
--

CREATE UNLOGGED TABLE switches (
    sid integer NOT NULL,
    dpid character varying(16),
    ip character varying(16),
    mac character varying(17),
    name character varying(16)
);


ALTER TABLE public.switches OWNER TO ravel;

--
-- Name: nodes; Type: VIEW; Schema: public; Owner: ravel
--

CREATE VIEW nodes AS
 SELECT switches.sid AS id,
    switches.name
   FROM switches
UNION
 SELECT hosts.hid AS id,
    hosts.name
   FROM hosts;


ALTER TABLE public.nodes OWNER TO ravel;

--
-- Name: p_spv; Type: TABLE; Schema: public; Owner: ravel; Tablespace: 
--

CREATE UNLOGGED TABLE p_spv (
    counts integer NOT NULL,
    status text
);


ALTER TABLE public.p_spv OWNER TO ravel;

--
-- Name: ports; Type: TABLE; Schema: public; Owner: ravel; Tablespace: 
--

CREATE UNLOGGED TABLE ports (
    sid integer,
    nid integer,
    port integer
);


ALTER TABLE public.ports OWNER TO ravel;

--
-- Name: rm; Type: TABLE; Schema: public; Owner: ravel; Tablespace: 
--

CREATE UNLOGGED TABLE rm (
    fid integer NOT NULL,
    src integer,
    dst integer,
    vol integer,
    fw integer,
    lb integer
);


ALTER TABLE public.rm OWNER TO ravel;

--
-- Name: rm_delta; Type: TABLE; Schema: public; Owner: ravel; Tablespace: 
--

CREATE UNLOGGED TABLE rm_delta (
    fid integer,
    src integer,
    dst integer,
    vol integer,
    isadd integer
);


ALTER TABLE public.rm_delta OWNER TO ravel;

--
-- Name: spv; Type: VIEW; Schema: public; Owner: ravel
--

CREATE VIEW spv AS
 SELECT rm.fid,
    rm.src,
    rm.dst,
    ( SELECT ARRAY( SELECT pgr_dijkstra.id1
                   FROM pgr_dijkstra('SELECT 1 as id,
                                                     sid as source,
                                                     nid as target,
                                                     1.0::float8 as cost
                                                     FROM tp
                                                     WHERE isactive = 1'::text, rm.src, rm.dst, false, false) pgr_dijkstra(seq, id1, id2, cost)) AS "array") AS pv
   FROM rm;


ALTER TABLE public.spv OWNER TO ravel;

--
-- Name: spv_edge; Type: VIEW; Schema: public; Owner: ravel
--

CREATE VIEW spv_edge AS
 WITH num_list AS (
         SELECT unnest(ARRAY[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]) AS num
        )
 SELECT DISTINCT spv.fid,
    num_list.num,
    ARRAY[spv.pv[num_list.num], spv.pv[(num_list.num + 1)], spv.pv[(num_list.num + 2)]] AS edge
   FROM spv,
    num_list
  WHERE ((spv.pv <> '{}'::integer[]) AND (num_list.num < (array_length(spv.pv, 1) - 1)))
  ORDER BY spv.fid, num_list.num;


ALTER TABLE public.spv_edge OWNER TO ravel;

--
-- Name: spv_switch; Type: VIEW; Schema: public; Owner: ravel
--

CREATE VIEW spv_switch AS
 SELECT DISTINCT spv_edge.fid,
    spv_edge.edge[1] AS pid,
    spv_edge.edge[2] AS sid,
    spv_edge.edge[3] AS nid
   FROM spv_edge
  ORDER BY spv_edge.fid;


ALTER TABLE public.spv_switch OWNER TO ravel;

--
-- Name: spv_del; Type: VIEW; Schema: public; Owner: ravel
--

CREATE VIEW spv_del AS
 SELECT cf.fid,
    cf.pid,
    cf.sid,
    cf.nid
   FROM cf
EXCEPT
 SELECT spv_switch.fid,
    spv_switch.pid,
    spv_switch.sid,
    spv_switch.nid
   FROM spv_switch
  ORDER BY 1;


ALTER TABLE public.spv_del OWNER TO ravel;

--
-- Name: spv_ins; Type: VIEW; Schema: public; Owner: ravel
--

CREATE VIEW spv_ins AS
 SELECT spv_switch.fid,
    spv_switch.pid,
    spv_switch.sid,
    spv_switch.nid
   FROM spv_switch
EXCEPT
 SELECT cf.fid,
    cf.pid,
    cf.sid,
    cf.nid
   FROM cf
  ORDER BY 1;


ALTER TABLE public.spv_ins OWNER TO ravel;

--
-- Name: spv_tb_del; Type: TABLE; Schema: public; Owner: ravel; Tablespace: 
--

CREATE UNLOGGED TABLE spv_tb_del (
    fid integer,
    pid integer,
    sid integer,
    nid integer
);


ALTER TABLE public.spv_tb_del OWNER TO ravel;

--
-- Name: spv_tb_ins; Type: TABLE; Schema: public; Owner: ravel; Tablespace: 
--

CREATE UNLOGGED TABLE spv_tb_ins (
    fid integer,
    pid integer,
    sid integer,
    nid integer
);


ALTER TABLE public.spv_tb_ins OWNER TO ravel;

--
-- Name: tp; Type: TABLE; Schema: public; Owner: ravel; Tablespace: 
--

CREATE UNLOGGED TABLE tp (
    sid integer NOT NULL,
    nid integer NOT NULL,
    ishost integer,
    isactive integer,
    bw integer
);


ALTER TABLE public.tp OWNER TO ravel;

--
-- Name: urm; Type: TABLE; Schema: public; Owner: ravel; Tablespace: 
--

CREATE UNLOGGED TABLE urm (
    fid integer NOT NULL,
    host1 integer,
    host2 integer
);


ALTER TABLE public.urm OWNER TO ravel;

--
-- Data for Name: cf; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY cf (fid, pid, sid, nid) FROM stdin;
\.


--
-- Data for Name: clock; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY clock (counts) FROM stdin;
0
\.


--
-- Data for Name: hosts; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY hosts (hid, ip, mac, name) FROM stdin;
2	10.0.0.1	e6:40:bf:dd:76:b1	h1
3	10.0.0.2	fe:81:24:33:00:54	h2
4	10.0.0.3	8a:58:da:45:b6:ee	h3
\.


--
-- Data for Name: p_spv; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY p_spv (counts, status) FROM stdin;
\.


--
-- Data for Name: ports; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY ports (sid, nid, port) FROM stdin;
3	1	0
1	3	2
4	1	0
1	4	3
2	1	0
1	2	1
\.


--
-- Data for Name: rm; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY rm (fid, src, dst, vol, fw, lb) FROM stdin;
\.


--
-- Data for Name: rm_delta; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY rm_delta (fid, src, dst, vol, isadd) FROM stdin;
\.


--
-- Data for Name: spatial_ref_sys; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY spatial_ref_sys  FROM stdin;
\.


--
-- Data for Name: spv_tb_del; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY spv_tb_del (fid, pid, sid, nid) FROM stdin;
\.


--
-- Data for Name: spv_tb_ins; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY spv_tb_ins (fid, pid, sid, nid) FROM stdin;
\.


--
-- Data for Name: switches; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY switches (sid, dpid, ip, mac, name) FROM stdin;
1	0000000000000001	127.0.0.1	None	s1
\.


--
-- Data for Name: tp; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY tp (sid, nid, ishost, isactive, bw) FROM stdin;
3	1	1	1	\N
1	3	1	1	\N
4	1	1	1	\N
1	4	1	1	\N
2	1	1	1	\N
1	2	1	1	\N
\.


--
-- Data for Name: urm; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY urm (fid, host1, host2) FROM stdin;
\.


--
-- Name: clock_pkey; Type: CONSTRAINT; Schema: public; Owner: ravel; Tablespace: 
--

ALTER TABLE ONLY clock
    ADD CONSTRAINT clock_pkey PRIMARY KEY (counts);


--
-- Name: hosts_pkey; Type: CONSTRAINT; Schema: public; Owner: ravel; Tablespace: 
--

ALTER TABLE ONLY hosts
    ADD CONSTRAINT hosts_pkey PRIMARY KEY (hid);


--
-- Name: p_spv_pkey; Type: CONSTRAINT; Schema: public; Owner: ravel; Tablespace: 
--

ALTER TABLE ONLY p_spv
    ADD CONSTRAINT p_spv_pkey PRIMARY KEY (counts);


--
-- Name: rm_pkey; Type: CONSTRAINT; Schema: public; Owner: ravel; Tablespace: 
--

ALTER TABLE ONLY rm
    ADD CONSTRAINT rm_pkey PRIMARY KEY (fid);


--
-- Name: switches_pkey; Type: CONSTRAINT; Schema: public; Owner: ravel; Tablespace: 
--

ALTER TABLE ONLY switches
    ADD CONSTRAINT switches_pkey PRIMARY KEY (sid);


--
-- Name: tp_pkey; Type: CONSTRAINT; Schema: public; Owner: ravel; Tablespace: 
--

ALTER TABLE ONLY tp
    ADD CONSTRAINT tp_pkey PRIMARY KEY (sid, nid);


--
-- Name: urm_pkey; Type: CONSTRAINT; Schema: public; Owner: ravel; Tablespace: 
--

ALTER TABLE ONLY urm
    ADD CONSTRAINT urm_pkey PRIMARY KEY (fid);


--
-- Name: cf_fid_sid_idx; Type: INDEX; Schema: public; Owner: ravel; Tablespace: 
--

CREATE INDEX cf_fid_sid_idx ON cf USING btree (fid, sid);


--
-- Name: hosts_hid_idx; Type: INDEX; Schema: public; Owner: ravel; Tablespace: 
--

CREATE INDEX hosts_hid_idx ON hosts USING btree (hid);


--
-- Name: rm_delta_fid_src_idx; Type: INDEX; Schema: public; Owner: ravel; Tablespace: 
--

CREATE INDEX rm_delta_fid_src_idx ON rm_delta USING btree (fid, src);


--
-- Name: rm_fid_src_dst_idx; Type: INDEX; Schema: public; Owner: ravel; Tablespace: 
--

CREATE INDEX rm_fid_src_dst_idx ON rm USING btree (fid, src, dst);


--
-- Name: switches_sid_idx; Type: INDEX; Schema: public; Owner: ravel; Tablespace: 
--

CREATE INDEX switches_sid_idx ON switches USING btree (sid);


--
-- Name: tp_sid_nid_idx; Type: INDEX; Schema: public; Owner: ravel; Tablespace: 
--

CREATE INDEX tp_sid_nid_idx ON tp USING btree (sid, nid);


--
-- Name: urm_fid_host1_idx; Type: INDEX; Schema: public; Owner: ravel; Tablespace: 
--

CREATE INDEX urm_fid_host1_idx ON urm USING btree (fid, host1);


--
-- Name: rm_del; Type: RULE; Schema: public; Owner: ravel
--

CREATE RULE rm_del AS
    ON DELETE TO rm DO ( INSERT INTO rm_delta (fid, src, dst, vol, isadd)
  VALUES (old.fid, old.src, old.dst, old.vol, 0);
 DELETE FROM rm_delta
  WHERE ((rm_delta.fid = old.fid) AND (rm_delta.isadd = 1));
);


--
-- Name: rm_ins; Type: RULE; Schema: public; Owner: ravel
--

CREATE RULE rm_ins AS
    ON INSERT TO rm DO  INSERT INTO rm_delta (fid, src, dst, vol, isadd)
  VALUES (new.fid, new.src, new.dst, new.vol, 1);


--
-- Name: spv_constaint2; Type: RULE; Schema: public; Owner: ravel
--

CREATE RULE spv_constaint2 AS
    ON INSERT TO p_spv
   WHERE (new.status = 'on'::text) DO ( UPDATE p_spv SET status = 'off'::text
  WHERE (p_spv.counts = new.counts);
 DELETE FROM cf
  WHERE ((cf.fid, cf.pid, cf.sid, cf.nid) IN ( SELECT spv_tb_del.fid,
            spv_tb_del.pid,
            spv_tb_del.sid,
            spv_tb_del.nid
           FROM spv_tb_del));
 INSERT INTO cf (fid, pid, sid, nid)  SELECT spv_tb_ins.fid,
            spv_tb_ins.pid,
            spv_tb_ins.sid,
            spv_tb_ins.nid
           FROM spv_tb_ins;
 DELETE FROM spv_tb_del;
 DELETE FROM spv_tb_ins;
);


--
-- Name: tick_spv; Type: RULE; Schema: public; Owner: ravel
--

CREATE RULE tick_spv AS
    ON UPDATE TO p_spv
   WHERE (new.status = 'off'::text) DO  INSERT INTO clock (counts)
  VALUES (new.counts);


--
-- Name: urm_del_rule; Type: RULE; Schema: public; Owner: ravel
--

CREATE RULE urm_del_rule AS
    ON DELETE TO urm DO  DELETE FROM rm
  WHERE (rm.fid = old.fid);


--
-- Name: urm_in_rule; Type: RULE; Schema: public; Owner: ravel
--

CREATE RULE urm_in_rule AS
    ON INSERT TO urm DO  INSERT INTO rm (fid, src, dst, vol)
  VALUES (new.fid, new.host1, new.host2, 1);


--
-- Name: urm_up_rule; Type: RULE; Schema: public; Owner: ravel
--

CREATE RULE urm_up_rule AS
    ON UPDATE TO urm DO ( DELETE FROM rm
  WHERE (rm.fid = old.fid);
 INSERT INTO rm (fid, src, dst, vol)
  VALUES (old.fid, new.host1, new.host2, 1);
);


--
-- Name: add_flow_trigger; Type: TRIGGER; Schema: public; Owner: ravel
--

CREATE TRIGGER add_flow_trigger AFTER INSERT ON cf FOR EACH ROW EXECUTE PROCEDURE add_flow_pre();


--
-- Name: add_host_trigger; Type: TRIGGER; Schema: public; Owner: ravel
--

CREATE TRIGGER add_host_trigger AFTER INSERT ON hosts FOR EACH ROW EXECUTE PROCEDURE add_host_fun();


--
-- Name: add_link_trigger; Type: TRIGGER; Schema: public; Owner: ravel
--

CREATE TRIGGER add_link_trigger AFTER INSERT ON tp FOR EACH ROW EXECUTE PROCEDURE add_link_fun();


--
-- Name: add_switch_trigger; Type: TRIGGER; Schema: public; Owner: ravel
--

CREATE TRIGGER add_switch_trigger AFTER INSERT ON switches FOR EACH ROW EXECUTE PROCEDURE add_switch_fun();


--
-- Name: del_flow_trigger; Type: TRIGGER; Schema: public; Owner: ravel
--

CREATE TRIGGER del_flow_trigger AFTER DELETE ON cf FOR EACH ROW EXECUTE PROCEDURE del_flow_pre();


--
-- Name: del_host_trigger; Type: TRIGGER; Schema: public; Owner: ravel
--

CREATE TRIGGER del_host_trigger AFTER DELETE ON hosts FOR EACH ROW EXECUTE PROCEDURE del_host_fun();


--
-- Name: del_link_trigger; Type: TRIGGER; Schema: public; Owner: ravel
--

CREATE TRIGGER del_link_trigger AFTER DELETE ON tp FOR EACH ROW EXECUTE PROCEDURE del_link_fun();


--
-- Name: del_switch_trigger; Type: TRIGGER; Schema: public; Owner: ravel
--

CREATE TRIGGER del_switch_trigger AFTER DELETE ON switches FOR EACH ROW EXECUTE PROCEDURE del_switch_fun();


--
-- Name: spv_constraint1; Type: TRIGGER; Schema: public; Owner: ravel
--

CREATE TRIGGER spv_constraint1 AFTER INSERT ON p_spv FOR EACH ROW EXECUTE PROCEDURE spv_constraint1_fun();


--
-- Name: tp_up_spv_trigger; Type: TRIGGER; Schema: public; Owner: ravel
--

CREATE TRIGGER tp_up_spv_trigger AFTER UPDATE ON tp FOR EACH ROW EXECUTE PROCEDURE tp2spv_fun();


--
-- Name: tp_up_trigger; Type: TRIGGER; Schema: public; Owner: ravel
--

CREATE TRIGGER tp_up_trigger AFTER UPDATE ON tp FOR EACH ROW EXECUTE PROCEDURE protocol_fun();


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

