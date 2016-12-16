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
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
\.


--
-- Data for Name: hosts; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY hosts (hid, ip, mac, name) FROM stdin;
\.


--
-- Data for Name: p_spv; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY p_spv (counts, status) FROM stdin;
1	off
2	off
3	off
4	off
5	off
6	off
7	off
8	off
9	off
10	off
11	off
12	off
13	off
14	off
15	off
16	off
\.


--
-- Data for Name: ports; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY ports (sid, nid, port) FROM stdin;
1	15	2
15	1	1
19	7	1
7	19	2
18	21	2
21	18	1
13	36	1
36	13	2
16	48	1
48	16	2
3	26	2
26	3	1
4	65	1
65	4	2
18	62	1
62	18	2
5	47	2
47	5	1
10	47	1
47	10	2
11	63	1
63	11	2
12	46	2
46	12	1
8	42	2
42	8	1
8	23	1
23	8	2
14	95	2
95	14	1
6	79	1
79	6	2
21	45	2
45	21	1
20	31	1
31	20	2
2	49	2
49	2	1
2	56	1
56	2	2
33	40	2
40	33	1
33	100	1
100	33	2
32	34	2
34	32	1
30	62	2
62	30	1
32	35	1
35	32	2
35	22	1
22	35	2
29	113	1
113	29	2
27	54	2
54	27	1
36	104	1
104	36	2
29	56	2
56	29	1
34	106	2
106	34	1
28	59	1
59	28	2
22	96	1
96	22	2
37	54	1
54	37	2
38	57	1
57	38	2
40	63	2
63	40	1
41	111	2
111	41	1
41	98	1
98	41	2
48	61	1
61	48	2
49	91	2
91	49	1
51	66	1
66	51	2
55	102	2
102	55	1
55	92	1
92	55	2
45	125	2
125	45	1
51	117	2
117	51	1
16	79	2
79	16	1
9	83	1
83	9	2
50	66	2
66	50	1
43	97	1
97	43	2
43	108	2
108	43	1
52	84	1
84	52	2
52	59	2
59	52	1
42	61	2
61	42	1
53	57	2
57	53	1
53	106	1
106	53	2
65	82	1
82	65	2
60	107	2
107	60	1
64	133	1
133	64	2
19	99	2
99	19	1
11	112	2
112	11	1
10	138	2
138	10	1
15	101	2
101	15	1
88	108	1
108	88	2
4	92	2
92	4	1
5	109	1
109	5	2
88	110	2
110	88	1
93	90	1
90	93	2
93	94	2
94	93	1
81	113	2
113	81	1
87	125	1
125	87	2
87	84	2
84	87	1
86	121	1
121	86	2
85	97	2
97	85	1
85	127	1
127	85	2
82	138	1
138	82	2
80	137	2
137	80	1
89	131	1
131	89	2
90	72	1
72	90	2
91	128	2
128	91	1
94	139	2
139	94	1
95	75	2
75	95	1
17	121	2
121	17	1
17	124	1
124	17	2
14	129	1
129	14	2
96	111	1
111	96	2
6	141	2
141	6	1
7	74	1
74	7	2
102	142	2
142	102	1
20	126	2
126	20	1
24	145	1
145	24	2
12	77	1
77	12	2
98	99	1
99	98	2
103	112	1
112	103	2
103	115	2
115	103	1
110	1	2
1	110	1
109	130	1
130	109	2
107	127	2
127	107	1
25	129	6
129	25	1
104	122	1
122	104	2
24	123	2
123	24	1
105	119	2
119	105	1
100	119	1
119	100	2
105	143	1
143	105	2
114	139	1
139	114	2
114	71	2
71	114	1
23	120	1
120	23	2
30	132	1
132	30	2
27	115	1
115	27	2
116	136	2
136	116	1
116	73	1
73	116	2
28	120	2
120	28	1
117	68	2
68	117	1
26	131	2
131	26	1
118	140	2
140	118	1
118	141	1
141	118	2
31	136	1
136	31	2
39	126	1
126	39	2
38	145	2
145	38	1
39	78	2
78	39	1
130	13	1
13	130	2
44	78	1
78	44	2
44	72	2
72	44	1
123	124	2
124	123	1
9	74	2
74	9	1
128	133	2
133	128	1
50	135	1
135	50	2
46	73	2
73	46	1
132	142	1
142	132	2
60	140	1
140	60	2
58	134	1
134	58	2
58	70	2
70	58	1
122	68	1
68	122	2
134	137	1
137	134	2
64	144	2
144	64	1
67	135	2
135	67	1
67	75	1
75	67	2
3	69	1
69	3	2
143	71	1
71	143	2
81	70	1
70	81	2
86	69	2
69	86	1
80	76	1
76	80	2
144	77	2
77	144	1
89	76	2
76	89	1
25	167	997
167	25	2
147	176	2
176	147	1
147	197	1
197	147	2
153	152	2
152	153	1
148	172	1
172	148	2
159	198	2
198	159	1
153	161	1
161	153	2
159	183	1
183	159	2
170	185	2
185	170	1
157	180	2
180	157	1
170	192	1
192	170	2
157	178	1
178	157	2
166	176	1
176	166	2
150	198	1
198	150	2
152	187	2
187	152	1
166	172	2
172	166	1
167	163	1
163	167	2
165	188	1
188	165	2
165	169	2
169	165	1
158	164	1
164	158	2
151	184	2
184	151	1
158	177	2
177	158	1
169	190	2
190	169	1
149	194	2
194	149	1
149	156	1
156	149	2
164	194	1
194	164	2
162	182	2
182	162	1
163	179	1
179	163	2
162	175	1
175	162	2
173	196	2
196	173	1
173	171	1
171	173	2
174	183	2
183	174	1
181	186	1
186	181	2
181	197	2
197	181	1
174	199	1
199	174	2
179	190	1
190	179	2
182	178	2
178	182	1
175	154	1
154	175	2
180	199	2
199	180	1
177	161	2
161	177	1
188	168	1
168	188	2
185	168	2
168	185	1
184	155	2
155	184	1
187	193	2
193	187	1
189	193	1
193	189	2
189	171	2
171	189	1
191	192	2
192	191	1
186	196	1
196	186	2
191	160	1
160	191	2
37	156	2
156	37	1
195	148	1
148	195	2
195	154	2
154	195	1
160	155	1
155	160	2
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
1	000000000000003f	\N	\N	s1
2	000000000000006b	\N	\N	s2
3	000000000000005d	\N	\N	s3
4	0000000000000019	\N	\N	s4
5	0000000000000013	\N	\N	s5
6	0000000000000032	\N	\N	s6
7	0000000000000046	\N	\N	s7
8	000000000000002c	\N	\N	s8
9	0000000000000044	\N	\N	s9
10	0000000000000015	\N	\N	s10
11	000000000000008c	\N	\N	s11
12	0000000000000073	\N	\N	s12
13	0000000000000010	\N	\N	s13
14	0000000000000003	\N	\N	s14
15	0000000000000040	\N	\N	s15
16	0000000000000030	\N	\N	s16
17	0000000000000059	\N	\N	s17
18	0000000000000021	\N	\N	s18
19	0000000000000047	\N	\N	s19
20	0000000000000079	\N	\N	s20
21	0000000000000022	\N	\N	s21
22	000000000000004d	\N	\N	s22
23	000000000000002b	\N	\N	s23
24	0000000000000056	\N	\N	s24
25	0000000000000001	\N	\N	s25
26	000000000000005e	\N	\N	s26
27	0000000000000090	\N	\N	s27
28	0000000000000029	\N	\N	s28
29	0000000000000069	\N	\N	s29
30	000000000000001f	\N	\N	s30
31	0000000000000078	\N	\N	s31
32	000000000000004f	\N	\N	s32
33	0000000000000089	\N	\N	s33
34	0000000000000050	\N	\N	s34
35	000000000000004e	\N	\N	s35
36	000000000000000f	\N	\N	s36
37	0000000000000092	\N	\N	s37
38	0000000000000054	\N	\N	s38
39	000000000000007b	\N	\N	s39
40	000000000000008a	\N	\N	s40
41	000000000000004a	\N	\N	s41
42	000000000000002d	\N	\N	s42
43	000000000000003b	\N	\N	s43
44	000000000000007d	\N	\N	s44
45	0000000000000023	\N	\N	s45
46	0000000000000074	\N	\N	s46
47	0000000000000014	\N	\N	s47
48	000000000000002f	\N	\N	s48
49	000000000000006c	\N	\N	s49
50	0000000000000008	\N	\N	s50
51	000000000000000a	\N	\N	s51
52	0000000000000027	\N	\N	s52
53	0000000000000052	\N	\N	s53
54	0000000000000091	\N	\N	s54
55	000000000000001b	\N	\N	s55
56	000000000000006a	\N	\N	s56
57	0000000000000053	\N	\N	s57
58	0000000000000065	\N	\N	s58
59	0000000000000028	\N	\N	s59
60	0000000000000036	\N	\N	s60
61	000000000000002e	\N	\N	s61
62	0000000000000020	\N	\N	s62
63	000000000000008b	\N	\N	s63
64	0000000000000070	\N	\N	s64
65	0000000000000018	\N	\N	s65
66	0000000000000009	\N	\N	s66
67	0000000000000006	\N	\N	s67
68	000000000000000c	\N	\N	s68
69	000000000000005c	\N	\N	s69
70	0000000000000066	\N	\N	s70
71	0000000000000084	\N	\N	s71
72	000000000000007e	\N	\N	s72
73	0000000000000075	\N	\N	s73
74	0000000000000045	\N	\N	s74
75	0000000000000005	\N	\N	s75
76	0000000000000061	\N	\N	s76
77	0000000000000072	\N	\N	s77
78	000000000000007c	\N	\N	s78
79	0000000000000031	\N	\N	s79
80	0000000000000062	\N	\N	s80
81	0000000000000067	\N	\N	s81
82	0000000000000017	\N	\N	s82
83	0000000000000043	\N	\N	s83
84	0000000000000026	\N	\N	s84
85	0000000000000039	\N	\N	s85
86	000000000000005b	\N	\N	s86
87	0000000000000025	\N	\N	s87
88	000000000000003d	\N	\N	s88
89	0000000000000060	\N	\N	s89
90	000000000000007f	\N	\N	s90
91	000000000000006d	\N	\N	s91
92	000000000000001a	\N	\N	s92
93	0000000000000080	\N	\N	s93
94	0000000000000081	\N	\N	s94
95	0000000000000004	\N	\N	s95
96	000000000000004c	\N	\N	s96
97	000000000000003a	\N	\N	s97
98	0000000000000049	\N	\N	s98
99	0000000000000048	\N	\N	s99
100	0000000000000088	\N	\N	s100
101	0000000000000041	\N	\N	s101
102	000000000000001c	\N	\N	s102
103	000000000000008e	\N	\N	s103
104	000000000000000e	\N	\N	s104
105	0000000000000086	\N	\N	s105
106	0000000000000051	\N	\N	s106
107	0000000000000037	\N	\N	s107
108	000000000000003c	\N	\N	s108
109	0000000000000012	\N	\N	s109
110	000000000000003e	\N	\N	s110
111	000000000000004b	\N	\N	s111
112	000000000000008d	\N	\N	s112
113	0000000000000068	\N	\N	s113
114	0000000000000083	\N	\N	s114
115	000000000000008f	\N	\N	s115
116	0000000000000076	\N	\N	s116
117	000000000000000b	\N	\N	s117
118	0000000000000034	\N	\N	s118
119	0000000000000087	\N	\N	s119
120	000000000000002a	\N	\N	s120
121	000000000000005a	\N	\N	s121
122	000000000000000d	\N	\N	s122
123	0000000000000057	\N	\N	s123
124	0000000000000058	\N	\N	s124
125	0000000000000024	\N	\N	s125
126	000000000000007a	\N	\N	s126
127	0000000000000038	\N	\N	s127
128	000000000000006e	\N	\N	s128
129	0000000000000002	\N	\N	s129
130	0000000000000011	\N	\N	s130
131	000000000000005f	\N	\N	s131
132	000000000000001e	\N	\N	s132
133	000000000000006f	\N	\N	s133
134	0000000000000064	\N	\N	s134
135	0000000000000007	\N	\N	s135
136	0000000000000077	\N	\N	s136
137	0000000000000063	\N	\N	s137
138	0000000000000016	\N	\N	s138
139	0000000000000082	\N	\N	s139
140	0000000000000035	\N	\N	s140
141	0000000000000033	\N	\N	s141
142	000000000000001d	\N	\N	s142
143	0000000000000085	\N	\N	s143
144	0000000000000071	\N	\N	s144
145	0000000000000055	\N	\N	s145
146	0000000000000042	\N	\N	s146
147	00000000000000a5	\N	\N	s147
148	00000000000000a9	\N	\N	s148
149	0000000000000094	\N	\N	s149
150	00000000000000b7	\N	\N	s150
151	00000000000000b9	\N	\N	s151
152	000000000000009b	\N	\N	s152
153	000000000000009a	\N	\N	s153
154	00000000000000ab	\N	\N	s154
155	00000000000000bb	\N	\N	s155
156	0000000000000093	\N	\N	s156
157	00000000000000b0	\N	\N	s157
158	0000000000000097	\N	\N	s158
159	00000000000000b5	\N	\N	s159
160	00000000000000bc	\N	\N	s160
161	0000000000000099	\N	\N	s161
162	00000000000000ad	\N	\N	s162
163	00000000000000c7	\N	\N	s163
164	0000000000000096	\N	\N	s164
165	00000000000000c3	\N	\N	s165
166	00000000000000a7	\N	\N	s166
167	00000000000000c8	\N	\N	s167
168	00000000000000c1	\N	\N	s168
169	00000000000000c4	\N	\N	s169
170	00000000000000bf	\N	\N	s170
171	000000000000009f	\N	\N	s171
172	00000000000000a8	\N	\N	s172
173	00000000000000a0	\N	\N	s173
174	00000000000000b3	\N	\N	s174
175	00000000000000ac	\N	\N	s175
176	00000000000000a6	\N	\N	s176
177	0000000000000098	\N	\N	s177
178	00000000000000af	\N	\N	s178
179	00000000000000c6	\N	\N	s179
180	00000000000000b1	\N	\N	s180
181	00000000000000a3	\N	\N	s181
182	00000000000000ae	\N	\N	s182
183	00000000000000b4	\N	\N	s183
184	00000000000000ba	\N	\N	s184
185	00000000000000c0	\N	\N	s185
186	00000000000000a2	\N	\N	s186
187	000000000000009c	\N	\N	s187
188	00000000000000c2	\N	\N	s188
189	000000000000009e	\N	\N	s189
190	00000000000000c5	\N	\N	s190
191	00000000000000bd	\N	\N	s191
192	00000000000000be	\N	\N	s192
193	000000000000009d	\N	\N	s193
194	0000000000000095	\N	\N	s194
195	00000000000000aa	\N	\N	s195
196	00000000000000a1	\N	\N	s196
197	00000000000000a4	\N	\N	s197
198	00000000000000b6	\N	\N	s198
199	00000000000000b2	\N	\N	s199
200	00000000000000b8	\N	\N	s200
\.


--
-- Data for Name: tp; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY tp (sid, nid, ishost, isactive, bw) FROM stdin;
89	131	0	1	\N
131	89	0	1	\N
90	72	0	1	\N
72	90	0	1	\N
91	128	0	1	\N
128	91	0	1	\N
94	139	0	1	\N
139	94	0	1	\N
16	48	0	1	\N
48	16	0	1	\N
3	26	0	1	\N
26	3	0	1	\N
4	65	0	1	\N
65	4	0	1	\N
18	62	0	1	\N
62	18	0	1	\N
5	47	0	1	\N
47	5	0	1	\N
10	47	0	1	\N
47	10	0	1	\N
11	63	0	1	\N
63	11	0	1	\N
18	21	0	0	\N
21	18	0	0	\N
19	7	0	0	\N
7	19	0	0	\N
1	15	0	0	\N
15	1	0	0	\N
13	36	0	0	\N
36	13	0	0	\N
12	46	0	1	\N
46	12	0	1	\N
8	42	0	1	\N
42	8	0	1	\N
8	23	0	1	\N
23	8	0	1	\N
14	95	0	1	\N
95	14	0	1	\N
6	79	0	1	\N
79	6	0	1	\N
21	45	0	1	\N
45	21	0	1	\N
20	31	0	1	\N
31	20	0	1	\N
2	49	0	1	\N
49	2	0	1	\N
2	56	0	1	\N
56	2	0	1	\N
33	40	0	1	\N
40	33	0	1	\N
33	100	0	1	\N
100	33	0	1	\N
32	34	0	1	\N
34	32	0	1	\N
30	62	0	1	\N
62	30	0	1	\N
32	35	0	1	\N
35	32	0	1	\N
35	22	0	1	\N
22	35	0	1	\N
29	113	0	1	\N
113	29	0	1	\N
27	54	0	1	\N
54	27	0	1	\N
36	104	0	1	\N
104	36	0	1	\N
29	56	0	1	\N
56	29	0	1	\N
34	106	0	1	\N
106	34	0	1	\N
28	59	0	1	\N
59	28	0	1	\N
22	96	0	1	\N
96	22	0	1	\N
37	54	0	1	\N
54	37	0	1	\N
38	57	0	1	\N
57	38	0	1	\N
40	63	0	1	\N
63	40	0	1	\N
41	111	0	1	\N
111	41	0	1	\N
41	98	0	1	\N
98	41	0	1	\N
48	61	0	1	\N
61	48	0	1	\N
49	91	0	1	\N
91	49	0	1	\N
51	66	0	1	\N
66	51	0	1	\N
55	102	0	1	\N
102	55	0	1	\N
55	92	0	1	\N
92	55	0	1	\N
45	125	0	1	\N
125	45	0	1	\N
51	117	0	1	\N
117	51	0	1	\N
16	79	0	1	\N
79	16	0	1	\N
9	83	0	1	\N
83	9	0	1	\N
50	66	0	1	\N
66	50	0	1	\N
43	97	0	1	\N
97	43	0	1	\N
43	108	0	1	\N
108	43	0	1	\N
52	84	0	1	\N
84	52	0	1	\N
52	59	0	1	\N
59	52	0	1	\N
42	61	0	1	\N
61	42	0	1	\N
53	57	0	1	\N
57	53	0	1	\N
53	106	0	1	\N
106	53	0	1	\N
65	82	0	1	\N
82	65	0	1	\N
60	107	0	1	\N
107	60	0	1	\N
64	133	0	1	\N
133	64	0	1	\N
19	99	0	1	\N
99	19	0	1	\N
11	112	0	1	\N
112	11	0	1	\N
10	138	0	1	\N
138	10	0	1	\N
15	101	0	1	\N
101	15	0	1	\N
88	108	0	1	\N
108	88	0	1	\N
4	92	0	1	\N
92	4	0	1	\N
5	109	0	1	\N
109	5	0	1	\N
88	110	0	1	\N
110	88	0	1	\N
93	90	0	1	\N
90	93	0	1	\N
93	94	0	1	\N
94	93	0	1	\N
81	113	0	1	\N
113	81	0	1	\N
87	125	0	1	\N
125	87	0	1	\N
87	84	0	1	\N
84	87	0	1	\N
86	121	0	1	\N
121	86	0	1	\N
85	97	0	1	\N
97	85	0	1	\N
85	127	0	1	\N
127	85	0	1	\N
82	138	0	1	\N
138	82	0	1	\N
80	137	0	1	\N
137	80	0	1	\N
95	75	0	1	\N
75	95	0	1	\N
17	121	0	1	\N
121	17	0	1	\N
17	124	0	1	\N
124	17	0	1	\N
14	129	0	1	\N
129	14	0	1	\N
96	111	0	1	\N
111	96	0	1	\N
6	141	0	1	\N
141	6	0	1	\N
7	74	0	1	\N
74	7	0	1	\N
102	142	0	1	\N
142	102	0	1	\N
20	126	0	1	\N
126	20	0	1	\N
24	145	0	1	\N
145	24	0	1	\N
12	77	0	1	\N
77	12	0	1	\N
98	99	0	1	\N
99	98	0	1	\N
103	112	0	1	\N
112	103	0	1	\N
103	115	0	1	\N
115	103	0	1	\N
110	1	0	1	\N
1	110	0	1	\N
109	130	0	1	\N
130	109	0	1	\N
107	127	0	1	\N
127	107	0	1	\N
25	129	0	1	\N
129	25	0	1	\N
104	122	0	1	\N
122	104	0	1	\N
24	123	0	1	\N
123	24	0	1	\N
105	119	0	1	\N
119	105	0	1	\N
100	119	0	1	\N
119	100	0	1	\N
105	143	0	1	\N
143	105	0	1	\N
114	139	0	1	\N
139	114	0	1	\N
114	71	0	1	\N
71	114	0	1	\N
23	120	0	1	\N
120	23	0	1	\N
30	132	0	1	\N
132	30	0	1	\N
27	115	0	1	\N
115	27	0	1	\N
116	136	0	1	\N
136	116	0	1	\N
116	73	0	1	\N
73	116	0	1	\N
28	120	0	1	\N
120	28	0	1	\N
117	68	0	1	\N
68	117	0	1	\N
26	131	0	1	\N
131	26	0	1	\N
118	140	0	1	\N
140	118	0	1	\N
118	141	0	1	\N
141	118	0	1	\N
31	136	0	1	\N
136	31	0	1	\N
39	126	0	1	\N
126	39	0	1	\N
38	145	0	1	\N
145	38	0	1	\N
39	78	0	1	\N
78	39	0	1	\N
130	13	0	1	\N
13	130	0	1	\N
44	78	0	1	\N
78	44	0	1	\N
44	72	0	1	\N
72	44	0	1	\N
123	124	0	1	\N
124	123	0	1	\N
9	74	0	1	\N
74	9	0	1	\N
128	133	0	1	\N
133	128	0	1	\N
50	135	0	1	\N
135	50	0	1	\N
46	73	0	1	\N
73	46	0	1	\N
132	142	0	1	\N
142	132	0	1	\N
60	140	0	1	\N
140	60	0	1	\N
58	134	0	1	\N
134	58	0	1	\N
58	70	0	1	\N
70	58	0	1	\N
122	68	0	1	\N
68	122	0	1	\N
134	137	0	1	\N
137	134	0	1	\N
64	144	0	1	\N
144	64	0	1	\N
67	135	0	1	\N
135	67	0	1	\N
67	75	0	1	\N
75	67	0	1	\N
3	69	0	1	\N
69	3	0	1	\N
143	71	0	1	\N
71	143	0	1	\N
81	70	0	1	\N
70	81	0	1	\N
86	69	0	1	\N
69	86	0	1	\N
80	76	0	1	\N
76	80	0	1	\N
144	77	0	1	\N
77	144	0	1	\N
89	76	0	1	\N
76	89	0	1	\N
25	167	0	1	\N
167	25	0	1	\N
147	176	0	1	\N
176	147	0	1	\N
147	197	0	1	\N
197	147	0	1	\N
153	152	0	1	\N
152	153	0	1	\N
148	172	0	1	\N
172	148	0	1	\N
159	198	0	1	\N
198	159	0	1	\N
153	161	0	1	\N
161	153	0	1	\N
159	183	0	1	\N
183	159	0	1	\N
170	185	0	1	\N
185	170	0	1	\N
157	180	0	1	\N
180	157	0	1	\N
170	192	0	1	\N
192	170	0	1	\N
157	178	0	1	\N
178	157	0	1	\N
166	176	0	1	\N
176	166	0	1	\N
150	198	0	1	\N
198	150	0	1	\N
152	187	0	1	\N
187	152	0	1	\N
166	172	0	1	\N
172	166	0	1	\N
167	163	0	1	\N
163	167	0	1	\N
165	188	0	1	\N
188	165	0	1	\N
165	169	0	1	\N
169	165	0	1	\N
158	164	0	1	\N
164	158	0	1	\N
151	184	0	1	\N
184	151	0	1	\N
158	177	0	1	\N
177	158	0	1	\N
169	190	0	1	\N
190	169	0	1	\N
149	194	0	1	\N
194	149	0	1	\N
149	156	0	1	\N
156	149	0	1	\N
164	194	0	1	\N
194	164	0	1	\N
162	182	0	1	\N
182	162	0	1	\N
163	179	0	1	\N
179	163	0	1	\N
162	175	0	1	\N
175	162	0	1	\N
173	196	0	1	\N
196	173	0	1	\N
173	171	0	1	\N
171	173	0	1	\N
174	183	0	1	\N
183	174	0	1	\N
181	186	0	1	\N
186	181	0	1	\N
181	197	0	1	\N
197	181	0	1	\N
174	199	0	1	\N
199	174	0	1	\N
179	190	0	1	\N
190	179	0	1	\N
182	178	0	1	\N
178	182	0	1	\N
175	154	0	1	\N
154	175	0	1	\N
180	199	0	1	\N
199	180	0	1	\N
177	161	0	1	\N
161	177	0	1	\N
188	168	0	1	\N
168	188	0	1	\N
185	168	0	1	\N
168	185	0	1	\N
184	155	0	1	\N
155	184	0	1	\N
187	193	0	1	\N
193	187	0	1	\N
189	193	0	1	\N
193	189	0	1	\N
189	171	0	1	\N
171	189	0	1	\N
191	192	0	1	\N
192	191	0	1	\N
186	196	0	1	\N
196	186	0	1	\N
191	160	0	1	\N
160	191	0	1	\N
37	156	0	1	\N
156	37	0	1	\N
195	148	0	1	\N
148	195	0	1	\N
195	154	0	1	\N
154	195	0	1	\N
160	155	0	1	\N
155	160	0	1	\N
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

