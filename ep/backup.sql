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
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
55
56
57
58
59
60
61
62
63
64
65
66
67
68
69
70
71
72
73
74
75
76
77
78
79
80
81
82
83
84
85
86
87
88
89
90
91
92
93
94
95
96
97
98
99
100
101
102
103
104
105
106
107
108
109
110
111
112
113
114
115
116
117
118
119
120
121
122
123
124
125
126
127
128
129
130
131
132
133
134
135
136
137
138
139
140
141
142
143
144
145
146
147
148
149
150
151
152
153
154
155
156
157
158
159
160
161
162
163
164
165
166
167
168
169
170
171
172
173
174
175
176
177
178
179
180
181
182
183
184
185
186
187
188
189
190
191
192
193
194
195
196
197
198
199
200
201
202
203
204
205
206
207
208
209
210
211
212
213
214
215
216
217
218
219
220
221
222
223
224
225
226
227
228
229
230
231
232
233
234
235
236
237
238
239
240
241
242
243
244
245
246
247
248
249
250
251
252
253
254
255
256
257
258
259
260
261
262
263
264
265
266
267
268
269
270
271
272
273
274
275
276
277
278
279
280
281
282
283
284
285
286
287
288
289
290
291
292
293
294
295
296
297
298
299
300
301
302
303
304
305
306
307
308
309
310
311
312
313
314
315
316
317
318
319
320
321
322
323
324
325
326
327
328
329
330
331
332
333
334
335
336
337
338
339
340
341
342
343
344
345
346
347
348
349
350
351
352
353
354
355
356
357
358
359
360
361
362
363
364
365
366
367
368
369
370
371
372
373
374
375
376
377
378
379
380
381
382
383
384
385
386
387
388
389
390
391
392
393
394
395
396
397
398
399
400
401
402
403
404
405
406
407
408
409
410
411
412
413
414
415
416
417
418
419
420
421
422
423
424
425
426
427
428
429
430
431
432
433
434
435
436
437
438
439
440
441
442
443
444
445
446
447
448
449
450
451
452
453
454
455
456
457
458
459
460
461
462
463
464
465
466
467
468
469
470
471
472
473
474
475
476
477
478
479
480
481
482
483
484
485
486
487
488
489
490
491
492
493
494
495
496
497
498
499
500
501
502
503
504
505
506
507
508
509
510
511
512
513
514
515
516
517
518
519
520
521
522
523
524
525
526
527
528
529
530
531
532
533
534
535
536
537
538
539
540
541
542
543
544
545
546
547
548
549
550
551
552
553
554
555
556
557
558
559
560
561
562
563
564
565
566
567
568
569
570
571
572
573
574
575
576
577
578
579
580
581
582
583
584
585
586
587
588
589
590
591
592
593
594
595
596
597
598
599
600
601
602
603
604
605
606
607
608
609
610
611
612
613
614
615
616
617
618
619
620
621
622
623
624
625
626
627
628
629
630
631
632
633
634
635
636
637
638
639
640
641
642
643
644
645
646
647
648
649
650
651
652
653
654
655
656
657
658
659
660
661
662
663
664
665
666
667
668
669
670
671
672
673
674
675
676
677
678
679
680
681
682
683
684
685
686
687
688
689
690
691
692
693
694
695
696
697
698
699
700
701
702
703
704
705
706
707
708
709
710
711
712
713
714
715
716
717
718
719
720
721
722
723
724
725
726
727
728
729
730
731
732
733
734
735
736
737
738
739
740
741
742
743
744
745
746
747
748
749
750
751
752
753
754
755
756
757
758
759
760
761
762
763
764
765
766
767
768
769
770
771
772
773
774
775
776
777
778
779
780
781
782
783
784
785
786
787
788
789
790
791
792
793
794
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
17	off
18	off
19	off
20	off
21	off
22	off
23	off
24	off
25	off
26	off
27	off
28	off
29	off
30	off
31	off
32	off
33	off
34	off
35	off
36	off
37	off
38	off
39	off
40	off
41	off
42	off
43	off
44	off
45	off
46	off
47	off
48	off
49	off
50	off
51	off
52	off
53	off
54	off
55	off
56	off
57	off
58	off
59	off
60	off
61	off
62	off
63	off
64	off
65	off
66	off
67	off
68	off
69	off
70	off
71	off
72	off
73	off
74	off
75	off
76	off
77	off
78	off
79	off
80	off
81	off
82	off
83	off
84	off
85	off
86	off
87	off
88	off
89	off
90	off
91	off
92	off
93	off
94	off
95	off
96	off
97	off
98	off
99	off
100	off
101	off
102	off
103	off
104	off
105	off
106	off
107	off
108	off
109	off
110	off
111	off
112	off
113	off
114	off
115	off
116	off
117	off
118	off
119	off
120	off
121	off
122	off
123	off
124	off
125	off
126	off
127	off
128	off
129	off
130	off
131	off
132	off
133	off
134	off
135	off
136	off
137	off
138	off
139	off
140	off
141	off
142	off
143	off
144	off
145	off
146	off
147	off
148	off
149	off
150	off
151	off
152	off
153	off
154	off
155	off
156	off
157	off
158	off
159	off
160	off
161	off
162	off
163	off
164	off
165	off
166	off
167	off
168	off
169	off
170	off
171	off
172	off
173	off
174	off
175	off
176	off
177	off
178	off
179	off
180	off
181	off
182	off
183	off
184	off
185	off
186	off
187	off
188	off
189	off
190	off
191	off
192	off
193	off
194	off
195	off
196	off
197	off
198	off
199	off
200	off
201	off
202	off
203	off
204	off
205	off
206	off
207	off
208	off
209	off
210	off
211	off
212	off
213	off
214	off
215	off
216	off
217	off
218	off
219	off
220	off
221	off
222	off
223	off
224	off
225	off
226	off
227	off
228	off
229	off
230	off
231	off
232	off
233	off
234	off
235	off
236	off
237	off
238	off
239	off
240	off
241	off
242	off
243	off
244	off
245	off
246	off
247	off
248	off
249	off
250	off
251	off
252	off
253	off
254	off
255	off
256	off
257	off
258	off
259	off
260	off
261	off
262	off
263	off
264	off
265	off
266	off
267	off
268	off
269	off
270	off
271	off
272	off
273	off
274	off
275	off
276	off
277	off
278	off
279	off
280	off
281	off
282	off
283	off
284	off
285	off
286	off
287	off
288	off
289	off
290	off
291	off
292	off
293	off
294	off
295	off
296	off
297	off
298	off
299	off
300	off
301	off
302	off
303	off
304	off
305	off
306	off
307	off
308	off
309	off
310	off
311	off
312	off
313	off
314	off
315	off
316	off
317	off
318	off
319	off
320	off
321	off
322	off
323	off
324	off
325	off
326	off
327	off
328	off
329	off
330	off
331	off
332	off
333	off
334	off
335	off
336	off
337	off
338	off
339	off
340	off
341	off
342	off
343	off
344	off
345	off
346	off
347	off
348	off
349	off
350	off
351	off
352	off
353	off
354	off
355	off
356	off
357	off
358	off
359	off
360	off
361	off
362	off
363	off
364	off
365	off
366	off
367	off
368	off
369	off
370	off
371	off
372	off
373	off
374	off
375	off
376	off
377	off
378	off
379	off
380	off
381	off
382	off
383	off
384	off
385	off
386	off
387	off
388	off
389	off
390	off
391	off
392	off
393	off
394	off
395	off
396	off
397	off
398	off
399	off
400	off
401	off
402	off
403	off
404	off
405	off
406	off
407	off
408	off
409	off
410	off
411	off
412	off
413	off
414	off
415	off
416	off
417	off
418	off
419	off
420	off
421	off
422	off
423	off
424	off
425	off
426	off
427	off
428	off
429	off
430	off
431	off
432	off
433	off
434	off
435	off
436	off
437	off
438	off
439	off
440	off
441	off
442	off
443	off
444	off
445	off
446	off
447	off
448	off
449	off
450	off
451	off
452	off
453	off
454	off
455	off
456	off
457	off
458	off
459	off
460	off
461	off
462	off
463	off
464	off
465	off
466	off
467	off
468	off
469	off
470	off
471	off
472	off
473	off
474	off
475	off
476	off
477	off
478	off
479	off
480	off
481	off
482	off
483	off
484	off
485	off
486	off
487	off
488	off
489	off
490	off
491	off
492	off
493	off
494	off
495	off
496	off
497	off
498	off
499	off
500	off
501	off
502	off
503	off
504	off
505	off
506	off
507	off
508	off
509	off
510	off
511	off
512	off
513	off
514	off
515	off
516	off
517	off
518	off
519	off
520	off
521	off
522	off
523	off
524	off
525	off
526	off
527	off
528	off
529	off
530	off
531	off
532	off
533	off
534	off
535	off
536	off
537	off
538	off
539	off
540	off
541	off
542	off
543	off
544	off
545	off
546	off
547	off
548	off
549	off
550	off
551	off
552	off
553	off
554	off
555	off
556	off
557	off
558	off
559	off
560	off
561	off
562	off
563	off
564	off
565	off
566	off
567	off
568	off
569	off
570	off
571	off
572	off
573	off
574	off
575	off
576	off
577	off
578	off
579	off
580	off
581	off
582	off
583	off
584	off
585	off
586	off
587	off
588	off
589	off
590	off
591	off
592	off
593	off
594	off
595	off
596	off
597	off
598	off
599	off
600	off
601	off
602	off
603	off
604	off
605	off
606	off
607	off
608	off
609	off
610	off
611	off
612	off
613	off
614	off
615	off
616	off
617	off
618	off
619	off
620	off
621	off
622	off
623	off
624	off
625	off
626	off
627	off
628	off
629	off
630	off
631	off
632	off
633	off
634	off
635	off
636	off
637	off
638	off
639	off
640	off
641	off
642	off
643	off
644	off
645	off
646	off
647	off
648	off
649	off
650	off
651	off
652	off
653	off
654	off
655	off
656	off
657	off
658	off
659	off
660	off
661	off
662	off
663	off
664	off
665	off
666	off
667	off
668	off
669	off
670	off
671	off
672	off
673	off
674	off
675	off
676	off
677	off
678	off
679	off
680	off
681	off
682	off
683	off
684	off
685	off
686	off
687	off
688	off
689	off
690	off
691	off
692	off
693	off
694	off
695	off
696	off
697	off
698	off
699	off
700	off
701	off
702	off
703	off
704	off
705	off
706	off
707	off
708	off
709	off
710	off
711	off
712	off
713	off
714	off
715	off
716	off
717	off
718	off
719	off
720	off
721	off
722	off
723	off
724	off
725	off
726	off
727	off
728	off
729	off
730	off
731	off
732	off
733	off
734	off
735	off
736	off
737	off
738	off
739	off
740	off
741	off
742	off
743	off
744	off
745	off
746	off
747	off
748	off
749	off
750	off
751	off
752	off
753	off
754	off
755	off
756	off
757	off
758	off
759	off
760	off
761	off
762	off
763	off
764	off
765	off
766	off
767	off
768	off
769	off
770	off
771	off
772	off
773	off
774	off
775	off
776	off
777	off
778	off
779	off
780	off
781	off
782	off
783	off
784	off
785	off
786	off
787	off
788	off
789	off
790	off
791	off
792	off
793	off
794	off
\.


--
-- Data for Name: ports; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY ports (sid, nid, port) FROM stdin;
2	18	2
18	2	1
5	22	1
22	5	2
9	30	2
30	9	1
54	14	2
14	54	1
19	70	2
70	19	1
7	41	1
41	7	2
11	51	1
51	11	2
23	63	1
63	23	2
13	29	2
29	13	1
15	43	2
43	15	1
17	43	1
43	17	2
6	28	2
28	6	1
16	86	1
86	16	2
6	52	1
52	6	2
42	34	2
34	42	1
42	46	1
46	42	2
8	39	2
39	8	1
45	55	2
55	45	1
30	72	2
72	30	1
53	56	1
56	53	2
48	67	2
67	48	1
32	66	2
66	32	1
34	106	2
106	34	1
46	47	1
47	46	2
31	57	2
57	31	1
35	27	1
27	35	2
47	96	1
96	47	2
25	66	1
66	25	2
60	24	1
24	60	2
70	92	2
92	70	1
65	104	1
104	65	2
2	105	1
105	2	2
65	113	2
113	65	1
67	41	2
41	67	1
63	49	1
49	63	2
64	80	1
80	64	2
64	114	2
114	64	1
74	78	1
78	74	2
74	135	2
135	74	1
50	78	2
78	50	1
40	99	1
99	40	2
40	103	2
103	40	1
36	27	2
27	36	1
36	90	1
90	36	2
28	49	2
49	28	1
26	24	2
24	26	1
26	106	1
106	26	2
37	102	2
102	37	1
51	93	1
93	51	2
11	80	2
80	11	1
19	57	1
57	19	2
55	9	2
9	55	1
23	86	2
86	23	1
21	91	1
91	21	2
5	107	2
107	5	1
15	108	1
108	15	2
7	112	2
112	7	1
33	141	1
141	33	2
79	103	1
103	79	2
17	129	2
129	17	1
18	98	2
98	18	1
20	130	2
130	20	1
81	131	1
131	81	2
20	136	1
136	20	2
79	105	2
105	79	1
82	85	2
85	82	1
82	88	1
88	82	2
81	90	2
90	81	1
83	115	2
115	83	1
84	99	2
99	84	1
89	130	1
130	89	2
84	140	1
140	84	2
93	129	1
129	93	2
94	144	2
144	94	1
95	128	1
128	95	2
92	1	2
1	92	1
54	100	1
100	54	2
3	97	2
97	3	1
16	122	2
122	16	1
53	10	2
10	53	1
3	139	1
139	3	2
38	145	1
145	38	2
45	138	1
138	45	2
38	143	2
143	38	1
85	126	2
126	85	1
97	73	2
73	97	1
96	113	1
113	96	2
98	121	2
121	98	1
114	123	2
123	114	1
104	107	1
107	104	2
58	139	6
139	58	1
101	116	2
116	101	1
101	112	1
112	101	2
108	132	1
132	108	2
102	140	2
140	102	1
48	110	1
110	48	2
100	12	1
12	100	2
32	116	1
116	32	2
52	142	1
142	52	2
109	137	2
137	109	1
31	115	1
115	31	2
110	137	1
137	110	2
111	77	2
77	111	1
111	126	1
126	111	2
35	142	2
142	35	1
29	128	2
128	29	1
56	133	1
133	56	2
60	145	2
145	60	1
59	61	2
61	59	1
127	133	2
133	127	1
59	10	1
10	59	2
127	76	1
76	127	2
14	132	2
132	14	1
71	75	2
75	71	1
71	61	1
61	71	2
135	125	2
125	135	1
134	117	2
117	134	1
134	122	1
122	134	2
72	131	2
131	72	1
143	136	2
136	143	1
50	119	1
119	50	2
39	76	2
76	39	1
1	141	2
141	1	1
37	117	1
117	37	2
138	123	1
123	138	2
44	4	1
4	44	2
21	62	2
62	21	1
13	120	1
120	13	2
44	118	2
118	44	1
12	125	1
125	12	2
4	144	1
144	4	2
33	124	2
124	33	1
87	119	2
119	87	1
87	73	1
73	87	2
22	62	1
62	22	2
83	118	1
118	83	2
89	120	2
120	89	1
124	68	2
68	124	1
94	69	1
69	94	2
91	121	1
121	91	2
8	68	1
68	8	2
95	69	2
69	95	1
88	75	1
75	88	2
58	163	997
163	58	2
165	174	2
174	165	1
154	177	2
177	154	1
168	156	1
156	168	2
168	182	2
182	168	1
147	160	1
160	147	2
154	186	1
186	154	2
165	196	1
196	165	2
170	192	1
192	170	2
147	187	2
187	147	1
153	158	2
158	153	1
153	176	1
176	153	2
161	190	2
190	161	1
161	182	1
182	161	2
175	160	2
160	175	1
174	184	2
184	174	1
175	188	1
188	175	2
163	166	1
166	163	2
148	159	1
159	148	2
169	149	2
149	169	1
169	152	1
152	169	2
148	181	2
181	148	1
151	183	2
183	151	1
151	190	1
190	151	2
149	179	2
179	149	1
167	189	2
189	167	1
164	171	2
171	164	1
159	189	1
189	159	2
164	150	1
150	164	2
157	191	2
191	157	1
157	197	1
197	157	2
166	173	1
173	166	2
155	156	2
156	155	1
162	178	1
178	162	2
173	179	1
179	173	2
155	193	1
193	155	2
162	192	2
192	162	1
171	176	2
176	171	1
158	193	2
193	158	1
150	195	1
195	150	2
181	196	2
196	181	1
188	170	1
170	188	2
152	172	1
172	152	2
177	172	2
172	177	1
184	194	2
194	184	1
183	199	2
199	183	1
185	194	1
194	185	2
185	197	2
197	185	1
178	191	1
191	178	2
180	186	2
186	180	1
180	198	1
198	180	2
187	195	2
195	187	1
198	199	1
199	198	2
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
1	000000000000006e	\N	\N	s1
2	000000000000003f	\N	\N	s2
3	0000000000000003	\N	\N	s3
4	0000000000000064	\N	\N	s4
5	0000000000000047	\N	\N	s5
6	000000000000002c	\N	\N	s6
7	000000000000008c	\N	\N	s7
8	0000000000000073	\N	\N	s8
9	0000000000000021	\N	\N	s9
10	000000000000007a	\N	\N	s10
11	0000000000000019	\N	\N	s11
12	000000000000000d	\N	\N	s12
13	000000000000005d	\N	\N	s13
14	0000000000000010	\N	\N	s14
15	0000000000000013	\N	\N	s15
16	0000000000000032	\N	\N	s16
17	0000000000000015	\N	\N	s17
18	0000000000000040	\N	\N	s18
19	000000000000006b	\N	\N	s19
20	0000000000000059	\N	\N	s20
21	0000000000000044	\N	\N	s21
22	0000000000000046	\N	\N	s22
23	0000000000000030	\N	\N	s23
24	0000000000000053	\N	\N	s24
25	0000000000000092	\N	\N	s25
26	0000000000000052	\N	\N	s26
27	0000000000000028	\N	\N	s27
28	000000000000002d	\N	\N	s28
29	000000000000005e	\N	\N	s29
30	0000000000000022	\N	\N	s30
31	0000000000000069	\N	\N	s31
32	0000000000000090	\N	\N	s32
33	0000000000000070	\N	\N	s33
34	0000000000000050	\N	\N	s34
35	0000000000000029	\N	\N	s35
36	0000000000000027	\N	\N	s36
37	0000000000000036	\N	\N	s37
38	0000000000000056	\N	\N	s38
39	0000000000000074	\N	\N	s39
40	000000000000003b	\N	\N	s40
41	000000000000008b	\N	\N	s41
42	000000000000004f	\N	\N	s42
43	0000000000000014	\N	\N	s43
44	0000000000000065	\N	\N	s44
45	000000000000001f	\N	\N	s45
46	000000000000004e	\N	\N	s46
47	000000000000004d	\N	\N	s47
48	0000000000000089	\N	\N	s48
49	000000000000002e	\N	\N	s49
50	0000000000000008	\N	\N	s50
51	0000000000000018	\N	\N	s51
52	000000000000002b	\N	\N	s52
53	0000000000000079	\N	\N	s53
54	000000000000000f	\N	\N	s54
55	0000000000000020	\N	\N	s55
56	0000000000000078	\N	\N	s56
57	000000000000006a	\N	\N	s57
58	0000000000000001	\N	\N	s58
59	000000000000007b	\N	\N	s59
60	0000000000000054	\N	\N	s60
61	000000000000007c	\N	\N	s61
62	0000000000000045	\N	\N	s62
63	000000000000002f	\N	\N	s63
64	000000000000001b	\N	\N	s64
65	000000000000004a	\N	\N	s65
66	0000000000000091	\N	\N	s66
67	000000000000008a	\N	\N	s67
68	0000000000000072	\N	\N	s68
69	0000000000000061	\N	\N	s69
70	000000000000006c	\N	\N	s70
71	000000000000007d	\N	\N	s71
72	0000000000000023	\N	\N	s72
73	0000000000000005	\N	\N	s73
74	000000000000000a	\N	\N	s74
75	000000000000007e	\N	\N	s75
76	0000000000000075	\N	\N	s76
77	0000000000000084	\N	\N	s77
78	0000000000000009	\N	\N	s78
79	000000000000003d	\N	\N	s79
80	000000000000001a	\N	\N	s80
81	0000000000000025	\N	\N	s81
82	0000000000000080	\N	\N	s82
83	0000000000000067	\N	\N	s83
84	0000000000000039	\N	\N	s84
85	0000000000000081	\N	\N	s85
86	0000000000000031	\N	\N	s86
87	0000000000000006	\N	\N	s87
88	000000000000007f	\N	\N	s88
89	000000000000005b	\N	\N	s89
90	0000000000000026	\N	\N	s90
91	0000000000000043	\N	\N	s91
92	000000000000006d	\N	\N	s92
93	0000000000000017	\N	\N	s93
94	0000000000000062	\N	\N	s94
95	0000000000000060	\N	\N	s95
96	000000000000004c	\N	\N	s96
97	0000000000000004	\N	\N	s97
98	0000000000000041	\N	\N	s98
99	000000000000003a	\N	\N	s99
100	000000000000000e	\N	\N	s100
101	000000000000008e	\N	\N	s101
102	0000000000000037	\N	\N	s102
103	000000000000003c	\N	\N	s103
104	0000000000000049	\N	\N	s104
105	000000000000003e	\N	\N	s105
106	0000000000000051	\N	\N	s106
107	0000000000000048	\N	\N	s107
108	0000000000000012	\N	\N	s108
109	0000000000000086	\N	\N	s109
110	0000000000000088	\N	\N	s110
111	0000000000000083	\N	\N	s111
112	000000000000008d	\N	\N	s112
113	000000000000004b	\N	\N	s113
114	000000000000001c	\N	\N	s114
115	0000000000000068	\N	\N	s115
116	000000000000008f	\N	\N	s116
117	0000000000000035	\N	\N	s117
118	0000000000000066	\N	\N	s118
119	0000000000000007	\N	\N	s119
120	000000000000005c	\N	\N	s120
121	0000000000000042	\N	\N	s121
122	0000000000000033	\N	\N	s122
123	000000000000001d	\N	\N	s123
124	0000000000000071	\N	\N	s124
125	000000000000000c	\N	\N	s125
126	0000000000000082	\N	\N	s126
127	0000000000000076	\N	\N	s127
128	000000000000005f	\N	\N	s128
129	0000000000000016	\N	\N	s129
130	000000000000005a	\N	\N	s130
131	0000000000000024	\N	\N	s131
132	0000000000000011	\N	\N	s132
133	0000000000000077	\N	\N	s133
134	0000000000000034	\N	\N	s134
135	000000000000000b	\N	\N	s135
136	0000000000000058	\N	\N	s136
137	0000000000000087	\N	\N	s137
138	000000000000001e	\N	\N	s138
139	0000000000000002	\N	\N	s139
140	0000000000000038	\N	\N	s140
141	000000000000006f	\N	\N	s141
142	000000000000002a	\N	\N	s142
143	0000000000000057	\N	\N	s143
144	0000000000000063	\N	\N	s144
145	0000000000000055	\N	\N	s145
146	0000000000000085	\N	\N	s146
147	00000000000000a9	\N	\N	s147
148	0000000000000097	\N	\N	s148
149	00000000000000c4	\N	\N	s149
150	00000000000000ac	\N	\N	s150
151	00000000000000b9	\N	\N	s151
152	00000000000000c2	\N	\N	s152
153	00000000000000b0	\N	\N	s153
154	00000000000000bf	\N	\N	s154
155	00000000000000b3	\N	\N	s155
156	00000000000000b4	\N	\N	s156
157	00000000000000a0	\N	\N	s157
158	00000000000000b1	\N	\N	s158
159	0000000000000096	\N	\N	s159
160	00000000000000a8	\N	\N	s160
161	00000000000000b7	\N	\N	s161
162	00000000000000a3	\N	\N	s162
163	00000000000000c8	\N	\N	s163
164	00000000000000ad	\N	\N	s164
165	000000000000009a	\N	\N	s165
166	00000000000000c7	\N	\N	s166
167	0000000000000094	\N	\N	s167
168	00000000000000b5	\N	\N	s168
169	00000000000000c3	\N	\N	s169
170	00000000000000a5	\N	\N	s170
171	00000000000000ae	\N	\N	s171
172	00000000000000c1	\N	\N	s172
173	00000000000000c6	\N	\N	s173
174	000000000000009b	\N	\N	s174
175	00000000000000a7	\N	\N	s175
176	00000000000000af	\N	\N	s176
177	00000000000000c0	\N	\N	s177
178	00000000000000a2	\N	\N	s178
179	00000000000000c5	\N	\N	s179
180	00000000000000bd	\N	\N	s180
181	0000000000000098	\N	\N	s181
182	00000000000000b6	\N	\N	s182
183	00000000000000ba	\N	\N	s183
184	000000000000009c	\N	\N	s184
185	000000000000009e	\N	\N	s185
186	00000000000000be	\N	\N	s186
187	00000000000000aa	\N	\N	s187
188	00000000000000a6	\N	\N	s188
189	0000000000000095	\N	\N	s189
190	00000000000000b8	\N	\N	s190
191	00000000000000a1	\N	\N	s191
192	00000000000000a4	\N	\N	s192
193	00000000000000b2	\N	\N	s193
194	000000000000009d	\N	\N	s194
195	00000000000000ab	\N	\N	s195
196	0000000000000099	\N	\N	s196
197	000000000000009f	\N	\N	s197
198	00000000000000bc	\N	\N	s198
199	00000000000000bb	\N	\N	s199
200	0000000000000093	\N	\N	s200
\.


--
-- Data for Name: tp; Type: TABLE DATA; Schema: public; Owner: ravel
--

COPY tp (sid, nid, ishost, isactive, bw) FROM stdin;
30	72	0	0	\N
72	30	0	0	\N
42	46	0	0	\N
46	42	0	0	\N
6	52	0	0	\N
15	108	0	0	\N
25	66	0	0	\N
38	145	0	0	\N
145	38	0	0	\N
38	143	0	0	\N
143	38	0	0	\N
11	80	0	0	\N
80	11	0	0	\N
95	128	0	0	\N
128	95	0	0	\N
82	85	0	0	\N
85	82	0	0	\N
33	141	0	0	\N
47	96	0	0	\N
96	47	0	0	\N
2	18	0	0	\N
18	2	0	0	\N
13	29	0	0	\N
29	13	0	0	\N
18	98	0	0	\N
98	18	0	0	\N
79	103	0	0	\N
98	121	0	0	\N
121	98	0	0	\N
20	136	0	0	\N
136	20	0	0	\N
114	123	0	0	\N
123	114	0	0	\N
54	100	0	0	\N
100	54	0	0	\N
54	14	0	0	\N
14	54	0	0	\N
70	92	0	0	\N
92	70	0	0	\N
19	70	0	0	\N
70	19	0	0	\N
52	6	0	0	\N
53	10	0	0	\N
82	88	0	0	\N
46	47	0	0	\N
47	46	0	0	\N
8	39	0	0	\N
39	8	0	0	\N
53	56	0	0	\N
64	80	0	0	\N
93	129	0	0	\N
129	93	0	0	\N
51	93	0	0	\N
93	51	0	0	\N
108	15	0	0	\N
28	49	0	0	\N
49	28	0	0	\N
5	107	0	0	\N
107	5	0	0	\N
103	79	0	0	\N
42	34	0	0	\N
26	24	0	0	\N
24	26	0	0	\N
84	99	0	0	\N
6	28	0	0	\N
28	6	0	0	\N
11	51	0	0	\N
51	11	0	0	\N
16	86	0	0	\N
86	16	0	0	\N
2	105	0	0	\N
105	2	0	0	\N
37	102	0	0	\N
10	53	0	0	\N
94	144	0	0	\N
40	99	0	0	\N
99	40	0	0	\N
35	27	0	0	\N
27	35	0	0	\N
74	78	0	0	\N
81	131	0	0	\N
26	106	0	0	\N
144	94	0	0	\N
48	67	0	0	\N
45	138	0	0	\N
138	45	0	0	\N
74	135	0	0	\N
135	74	0	0	\N
16	122	0	0	\N
122	16	0	0	\N
3	97	0	0	\N
97	3	0	0	\N
85	126	0	0	\N
23	86	0	0	\N
50	78	0	0	\N
55	9	0	0	\N
9	55	0	0	\N
97	73	0	0	\N
73	97	0	0	\N
7	41	0	0	\N
99	84	0	0	\N
96	113	0	0	\N
113	96	0	0	\N
60	145	0	0	\N
145	60	0	0	\N
33	124	0	0	\N
124	33	0	0	\N
12	125	0	0	\N
170	192	0	0	\N
192	170	0	0	\N
181	196	0	0	\N
196	181	0	0	\N
134	117	0	0	\N
117	134	0	0	\N
161	190	0	0	\N
190	161	0	0	\N
29	128	0	0	\N
175	160	0	0	\N
87	119	0	0	\N
157	191	0	0	\N
127	76	0	0	\N
151	183	0	0	\N
183	151	0	0	\N
164	171	0	0	\N
171	164	0	0	\N
94	69	0	0	\N
69	94	0	0	\N
155	193	0	0	\N
127	133	0	0	\N
133	127	0	0	\N
32	116	0	0	\N
116	32	0	0	\N
161	182	0	0	\N
182	161	0	0	\N
50	119	0	0	\N
119	50	0	0	\N
149	179	0	0	\N
179	149	0	0	\N
148	181	0	0	\N
56	133	0	0	\N
133	56	0	0	\N
157	197	0	0	\N
4	144	0	0	\N
21	62	0	0	\N
62	21	0	0	\N
102	140	0	0	\N
140	102	0	0	\N
87	73	0	0	\N
134	122	0	0	\N
122	134	0	0	\N
171	176	0	0	\N
176	171	0	0	\N
165	174	0	0	\N
174	165	0	0	\N
37	117	0	0	\N
117	37	0	0	\N
110	137	0	0	\N
137	110	0	0	\N
160	175	0	0	\N
91	121	0	0	\N
121	91	0	0	\N
48	110	0	0	\N
110	48	0	0	\N
188	170	0	0	\N
135	125	0	0	\N
125	135	0	0	\N
159	189	0	0	\N
189	159	0	0	\N
150	195	0	0	\N
13	120	0	0	\N
120	13	0	0	\N
168	182	0	0	\N
182	168	0	0	\N
109	137	0	0	\N
137	109	0	0	\N
163	166	0	0	\N
166	163	0	0	\N
175	188	0	0	\N
169	149	0	0	\N
149	169	0	0	\N
143	136	0	0	\N
73	87	0	0	\N
22	62	0	0	\N
62	22	0	0	\N
162	192	0	0	\N
192	162	0	0	\N
52	142	0	0	\N
181	148	0	0	\N
119	87	0	0	\N
39	76	0	0	\N
76	39	0	0	\N
100	12	0	0	\N
12	100	0	0	\N
14	132	0	0	\N
132	14	0	0	\N
153	176	0	0	\N
153	158	0	0	\N
158	153	0	0	\N
164	150	0	0	\N
150	164	0	0	\N
154	186	0	0	\N
186	154	0	0	\N
138	123	0	0	\N
123	138	0	0	\N
59	61	0	0	\N
95	69	0	0	\N
69	95	0	0	\N
15	43	0	0	\N
43	15	0	0	\N
66	25	0	0	\N
170	188	0	0	\N
187	195	0	0	\N
195	187	0	0	\N
20	130	0	0	\N
130	20	0	0	\N
56	53	0	0	\N
17	43	0	0	\N
142	52	0	0	\N
147	187	0	0	\N
187	147	0	0	\N
102	37	0	0	\N
106	26	0	0	\N
67	48	0	0	\N
168	156	0	0	\N
156	168	0	0	\N
136	143	0	0	\N
101	112	0	0	\N
112	101	0	0	\N
72	131	0	0	\N
131	72	0	0	\N
155	156	0	0	\N
156	155	0	0	\N
148	159	0	0	\N
159	148	0	0	\N
174	184	0	0	\N
184	174	0	0	\N
166	173	0	0	\N
173	166	0	0	\N
128	29	0	0	\N
41	7	0	0	\N
162	178	0	0	\N
178	162	0	0	\N
7	112	0	0	\N
112	7	0	0	\N
36	27	0	0	\N
27	36	0	0	\N
65	104	0	0	\N
104	65	0	0	\N
58	139	0	0	\N
139	58	0	0	\N
23	63	0	0	\N
63	23	0	0	\N
31	115	0	0	\N
115	31	0	0	\N
40	103	0	0	\N
103	40	0	0	\N
35	142	0	0	\N
142	35	0	0	\N
154	177	0	0	\N
177	154	0	0	\N
169	152	0	0	\N
152	169	0	0	\N
34	106	0	0	\N
106	34	0	0	\N
147	160	0	0	\N
160	147	0	0	\N
64	114	0	0	\N
114	64	0	0	\N
63	49	0	0	\N
49	63	0	0	\N
108	132	0	0	\N
132	108	0	0	\N
58	163	0	0	\N
163	58	0	0	\N
176	153	0	0	\N
111	126	0	0	\N
126	111	0	0	\N
92	1	0	0	\N
1	92	0	0	\N
104	107	0	0	\N
107	104	0	0	\N
1	141	0	0	\N
141	1	0	0	\N
67	41	0	0	\N
41	67	0	0	\N
59	10	0	0	\N
10	59	0	0	\N
188	175	0	0	\N
32	66	0	0	\N
66	32	0	0	\N
65	113	0	0	\N
113	65	0	0	\N
180	186	0	0	\N
186	180	0	0	\N
141	33	0	0	\N
81	90	0	0	\N
101	116	0	0	\N
116	101	0	0	\N
89	130	0	0	\N
130	89	0	0	\N
71	61	0	0	\N
61	71	0	0	\N
79	105	0	0	\N
105	79	0	0	\N
111	77	0	0	\N
77	111	0	0	\N
151	190	0	0	\N
190	151	0	0	\N
178	191	0	0	\N
191	178	0	0	\N
183	199	0	0	\N
199	183	0	0	\N
31	57	0	0	\N
57	31	0	0	\N
90	81	0	0	\N
78	74	0	0	\N
131	81	0	0	\N
34	42	0	0	\N
36	90	0	0	\N
90	36	0	0	\N
44	118	0	0	\N
118	44	0	0	\N
185	194	0	0	\N
194	185	0	0	\N
167	189	0	0	\N
189	167	0	0	\N
9	30	0	0	\N
30	9	0	0	\N
165	196	0	0	\N
196	165	0	0	\N
124	68	0	0	\N
68	124	0	0	\N
195	150	0	0	\N
83	115	0	0	\N
115	83	0	0	\N
8	68	0	0	\N
68	8	0	0	\N
125	12	0	0	\N
158	193	0	0	\N
193	158	0	0	\N
17	129	0	0	\N
129	17	0	0	\N
191	157	0	0	\N
76	127	0	0	\N
60	24	0	0	\N
24	60	0	0	\N
84	140	0	0	\N
140	84	0	0	\N
5	22	0	0	\N
22	5	0	0	\N
78	50	0	0	\N
177	172	0	0	\N
172	177	0	0	\N
152	172	0	0	\N
172	152	0	0	\N
71	75	0	0	\N
44	4	0	0	\N
4	44	0	0	\N
88	75	0	0	\N
75	88	0	0	\N
197	157	0	0	\N
193	155	0	0	\N
185	197	0	0	\N
43	17	0	0	\N
180	198	0	0	\N
198	180	0	0	\N
83	118	0	0	\N
118	83	0	0	\N
173	179	0	0	\N
179	173	0	0	\N
198	199	0	0	\N
199	198	0	0	\N
21	91	0	0	\N
45	55	0	0	\N
55	45	0	0	\N
184	194	0	0	\N
194	184	0	0	\N
89	120	0	0	\N
120	89	0	0	\N
75	71	0	0	\N
3	139	0	0	\N
139	3	0	0	\N
19	57	0	0	\N
57	19	0	0	\N
144	4	0	0	\N
197	185	0	0	\N
88	82	0	0	\N
126	85	0	0	\N
91	21	0	0	\N
86	23	0	0	\N
61	59	0	0	\N
80	64	0	0	\N
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

