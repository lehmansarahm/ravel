#!/usr/bin/env python

import os
import random
import shutil
import sys
import threading
import time

import numpy
import networkx
import networkx.exception
import psycopg2.extras

import plot

CWD = os.path.dirname(os.path.realpath(__file__))
LOG = os.path.join(CWD, "..", "log.txt")
LOGDEST = os.path.join(CWD, "plot", "log")
PRECOMPUTE_BASE = os.path.join(CWD, "precompute_base.sql")
PROFILED = False

def addRavelPath():
    # add ravel to path
    path = ""
    if 'PYTHONPATH' in os.environ:
        path = os.environ['PYTHONPATH']

    sys.path = path.split(':') + sys.path
    cwd = os.path.dirname(os.path.abspath(__file__))
    raveldir = os.path.normpath(os.path.join(cwd, ".."))
    sys.path.append(os.path.abspath(raveldir))

addRavelPath()

from ravel.db import RavelDb, BASE_SQL
from fattree import FattreeTopo
from isp import IspTopo

class Evaluation(object):
    def __init__(self, db, testname, rounds=10):
        self.f = open(LOG, 'a')
        self.rounds = rounds
        self.name = testname
        self.db = db
        print testname
        self.logdest = os.path.join(LOGDEST, "{0}.txt".format(str(testname).replace(",", "_")))
        print "LOGDEST", testname, self.logdest
        self.cur = db.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        self.fetch()

    def close(self):
        self.f.close()
        open(self.logdest, 'w').close()
        shutil.copyfile(LOG, self.logdest)

    def fetch(self):
        self.cur.execute("SELECT count(*) FROM switches;")
        self.switch_size = int(self.cur.fetchall()[0]['count'])

        self.cur.execute("SELECT * FROM hosts;")
        cs = self.cur.fetchall()
        self.hosts = [h['hid'] for h in cs]

        self.cur.execute("SELECT * FROM switches;")
        cs = self.cur.fetchall()
        self.switches = [h['sid'] for h in cs]

        self.cur.execute("SELECT sid,nid FROM tp where ishost = 0;")
        cs = self.cur.fetchall()
        self.links = [[h['sid'], h['nid']] for h in cs]

        self.cur.execute("SELECT src, dst FROM pre_paths;")
        cs = self.cur.fetchall()
        self.cached_paths = [(h['src'], h['dst']) for h in cs]

    def init_acl(self):
        self.cur.execute("select distinct src, dst from rm;")
        cs = self.cur.fetchall()
        t_ends = [(h['src'], h['dst']) for h in cs]
        print "init_acl ends size: " + str(len(t_ends))
        if len(t_ends) > self.rounds:
            ends = t_ends[: self.rounds]
        else:
            ends = t_ends

        for i in range(len(ends)):
            [e1, e2] = ends[i]
            is_inblacklist = numpy.random.choice([0,1], 1, p=[0.8, 0.2])[0]
            print e1, e2, is_inblacklist
            self.cur.execute("INSERT INTO acl_tb VALUES("+ str(e1)+ ","+ str(e2) + "," + str(is_inblacklist) +");")

    def init_lb(self):
        self.cur.execute("select distinct dst from rm ;")
        cs = self.cur.fetchall()
        t_ends = [h['dst'] for h in cs]
        print "init_lb ends size: " + str(len(t_ends))
        if len(t_ends) > self.rounds:
            ends = t_ends[: self.rounds]
        else:
            ends = t_ends

        for i in range(len(ends)):
            e = ends[i]
            self.cur.execute("INSERT INTO lb_tb VALUES("+ str(e)+ ");")

    def init_acl_lb(self):
        self.cur.execute("select sum(load) from lb ;")
        agg_load = self.cur.fetchall()[0]['sum']

        self.cur.execute("select count(*) from lb ;")
        switch_size = self.cur.fetchall()[0]['count']

        self.cur.execute("select max(load) from lb;")
        max_load = self.cur.fetchall()[0]['max']

        self.cur.execute("""
        CREATE OR REPLACE RULE lb_constraint AS
        ON INSERT TO p1
        WHERE(NEW.status = 'on')
        DO ALSO(
            UPDATE lb SET load = """ +str(max_load+1)+ """ WHERE load > """ +str(max_load+1)+""";
	    UPDATE p1 SET status = 'off' WHERE counts = NEW.counts;
	   );
""")

        residual_load = switch_size * max_load - agg_load
        return residual_load

    def update_max_fid(self):
        self.cur.execute("SELECT max(fid) FROM rm;")
        cs = self.cur.fetchall()
        if cs == [[None]]:
            self.max_fid = 0
        else:
            self.max_fid = cs[0]['max']

    def rtm_ins(self, rounds):
        self.f.write("#rtm_ins----------------------------------------------\n")
        self.update_max_fid()
        max_fid = self.max_fid

        for r in range(max_fid+1, max_fid + rounds + 1):
            h1, h2 = random.choice(self.cached_paths)

            self.f.write("#round " + str(r-1) + '\n')
            self.f.flush()
            t1 = time.time()
            self.cur.execute("INSERT INTO rm values({0},{1},{2});".format(r, h1, h2))
            if PROFILED:
                self.cur.execute("SELECT spv_constraint1_fun_profiled();")
            else:
                self.cur.execute("SELECT spv_constraint1_fun_unprofiled();")
            t2 = time.time()
            self.f.write('----rt: route ins----' + str((t2-t1)*1000) + '\n')
            self.f.write('#pi----rt: route ins----' + str((t2-t1)*1000) + '\n')
            self.f.flush()

    def rtm_del(self):
        self.f.write("#rtm_del----------------------------------------------\n")
        self.cur.execute("SELECT fid FROM rm;")
        cs = self.cur.fetchall()
        fids = [h['fid'] for h in cs]

        for r in range(0, self.rounds):
            self.f.write("#round " + str(r) + '\n')
            self.f.flush()
            t1 = time.time()
            self.cur.execute("DELETE FROM rm WHERE fid =" +str(fids[r])+ ";")
            if PROFILED:
                self.cur.execute("SELECT spv_constraint1_fun_profiled();")
            else:
                self.cur.execute("SELECT spv_constraint1_fun_unprofiled();")
            t2 = time.time()
            self.f.write('----rt: route del----' + str((t2-t1)*1000) + '\n')
            self.f.write('#pd----rt: route del----' + str((t2-t1)*1000) + '\n')
            self.f.flush()

    def op_lb(self):
        cur = self.cur
        f = self.f
        # try: # add comments here

        t1 = time.time()
        cur.execute("select max(load) from lb ;")
        t2 = time.time()
        f.write('----lb: check max load----' + str((t2-t1)*1000) + '\n')
        f.flush()
        max_load = cur.fetchall()[0]['max']

        # TODO: check for bug here?
        if max_load is None:
            max_load = 0

        cur.execute("select sid from lb where load = "+str(max_load)+" limit 1;")
        s_id = cur.fetchall()[0]['sid']

        t1 = time.time()
        cur.execute("update lb set load = " +str(max_load - 1)+" where sid = "+str(s_id)+";")
        #print "update lb set load = " +str(max_load - 1)+" where sid = "+str(s_id)+";"
        t2 = time.time()
        f.write('----lb: re-balance(absolute)----' + str((t2-t1)*1000) + '\n')
        f.flush()

        t3 = time.time()
        cur.execute("SELECT * from p_spv;")
        ct = cur.fetchall()
        cur.execute("select max(counts) from clock;")
        ct = cur.fetchall() [0]['max']
        cur.execute("INSERT INTO p_spv VALUES(" + str(ct+1) + ", 'on');")
        t4 = time.time()
        f.write('----lb+rt: re-balance(per rule)----' + str((t2-t1 + t4-t3)*1000) + '\n')
        f.write('----lb+rt: re-balance(absolute)----' + str((t2-t1 + t4-t3)*1000) + '\n')
        f.flush()
        # except psycopg2.DatabaseError, e:
        #     print 'op_lb fail Error %s' % e

    def op_acl(self):
        cur = self.cur
        f = self.f

        t1 = time.time()
        cur.execute("select end1, end2 from acl limit 1;")
        t2 = time.time()
        f.write('----acl: check violation----' + str((t2-t1)*1000) + '\n')
        f.flush()
        t = cur.fetchall()[0]
        e1 = t['end1']
        e2 = t['end2']

        t1 = time.time()
        cur.execute("update acl set isviolated = 0 where end1 = "+ str(e1) +" and end2 = "+str(e2)+";")
        t2 = time.time()
        f.write('----acl: fix violation----' + str((t2-t1)*1000) + '\n')
        f.flush()

        t3 = time.time()
        cur.execute("select max(counts) from clock;")
        ct = cur.fetchall() [0]['max']
        cur.execute("INSERT INTO p_spv VALUES(" + str(ct+1) + ", 'on');")
        t4 = time.time()
        f.write('----acl+rt: fix violation(per rule)----' + str((t2-t1 + t4-t3)*1000) + '\n')
        f.write('----acl+rt: fix violation(absolute)----' + str((t2-t1 + t4-t3)*1000) + '\n')
        f.flush()

    def routing_ins_acl_lb(self, h1s, h2s):
        cur = self.cur
        f = self.f

        self.update_max_fid()
        fid = self.max_fid + 1

        h1 = random.sample(h1s, 1)[0]
        h2 = random.sample(h2s, 1)[0]

        t1 = time.time()
        cur.execute("INSERT INTO rm VALUES("+str(fid) +"," +str(h1) + "," + str(h2)+");")
        cur.execute("select max(counts) from clock;")
        ct = cur.fetchall() [0]['max']
        cur.execute("INSERT INTO p1 VALUES(" + str(ct+1) + ", 'on');")
        t2 = time.time()
        f.write('----acl+lb+rt: route ins----' + str((t2-t1)*1000) + '\n')
        f.flush()

    def op_profile(self):
        self.rtm_ins(self.rounds)
        self.rtm_del()

    def op_primitive(self):
        cur = self.cur
        f = self.f

        f.write("#primitive: op_lb ----------------------------------------------\n")
        for r in range(0, 20):
            self.op_lb()

        f.write("#primitive: op_acl ----------------------------------------------\n")
        cur.execute("select count(*) from acl;")
        ct = cur.fetchall() [0]['count']
        if ct > 20:
            ct = 20
        for i in range(ct):
            self.op_acl()

        f.write("#primitive: routing_ins_acl_lb ----------------------------------------------\n")
        capacity = self.init_acl_lb()
        cur.execute("SELECT DISTINCT end1 FROM acl_tb;")
        cs = cur.fetchall()
        h1s = [h['end1'] for h in cs]
        cur.execute("SELECT DISTINCT end2 FROM acl_tb;")
        cs = cur.fetchall()
        h2s = [h['end2'] for h in cs]
        if capacity > 20:
            capacity = 20
        for i in range(capacity):
            self.routing_ins_acl_lb(h1s, h2s)

class FattreeEvaluation(Evaluation):
    def __init__(self, db, testname, rounds=10):
        super(FattreeEvaluation, self).__init__(db, testname, rounds)

    def close(self):
        shutil.copyfile(LOG, self.logdest)

        if PROFILED == True:
            dest = os.path.join(CWD, "plot", "log", "profile")
        else:
            dest = os.path.join(CWD, "plot", "log", "fattree")

        os.system("mkdir -p {0}; mv {1} {0}".format(dest, self.logdest))
        #super(FattreeEvaluation, self).close()

    def primitive(self):
        size = 10
        self.rtm_ins(size)
        self.init_acl()
        self.init_lb()
        self.op_primitive()
        self.logdest = os.path.join(LOGDEST, "primitive_{0}.txt".format(self.name.replace(",", "_")))

    def tenant(self):
        size = 10
        self.init_tenant(size)
        self.init_tacl()
        self.init_tlb()

        for i in range(size*3):
            self.op_tlb()

        self.cur.execute("select count(*) from tacl;")
        ct = self.cur.fetchall() [0]['count']
        for i in range(ct):
            self.op_tacl()

        self.cur.execute("select * from tenant_hosts ;")
        cs = self.cur.fetchall()
        thosts = [h['hid'] for h in cs]
        for i in range(size):
            self.routing_ins_acl_lb_tenant(thosts)

        dbname = self.logdest.split('.')[0]
        self.logdest = dbname + '_tenant.log'

    def routing_ins_acl_lb_tenant(self,hosts):
        cur = self.cur
        f = self.f

        [h1, h2] = random.sample(hosts, 2)
        self.update_max_fid()
        fid = self.max_fid + 1

        try:
            t1 = time.time()
            cur.execute("INSERT INTO tenant_policy VALUES("+str(fid) +"," +str(h1) + "," + str(h2)+");")
            cur.execute("select max(counts) from clock;")
            ct = cur.fetchall() [0]['max']
            cur.execute("INSERT INTO t1 VALUES(" + str(ct+1) + ", 'on');")
            t2 = time.time()
            f.write('----(acl+lb+rt)*tenant: route ins----' + str((t2-t1)*1000) + '\n')
            f.flush()
        except Exception, e:
            raise

    def init_tacl(self):
        cur = self.cur
        cur.execute("select distinct host1, host2 from tenant_policy ;")
        cs = cur.fetchall()
        ends = [[h['host1'], h['host2']] for h in cs]

        for i in range(len(ends)):
            [e1, e2] = ends[i]
            # is_inblacklist = random.choice([0,1])
            is_inblacklist = numpy.random.choice([0,1], 1, p=[0.8, 0.2])[0]
            cur.execute("INSERT INTO tacl_tb VALUES("+ str(e1)+ ","+ str(e2) + "," + str(is_inblacklist) +");")

    def init_tlb(self):
        cur = self.cur
        cur.execute("select distinct host2 from tenant_policy ;")
        cs = cur.fetchall()
        ends = [h['host2'] for h in cs]

        for e in ends:
            cur.execute("INSERT INTO tlb_tb VALUES("+ str(e)+ ");")

    def tenant_fullmesh(self, hosts):
        f = self.f
        cur = self.cur

        self.update_max_fid()
        fid = self.max_fid + 1

        cur.execute("select max(counts) from clock;")
        ct = cur.fetchall()[0]['max'] + 1

        for i in range(len(hosts)):
            for j in range(i+1,len(hosts)):
                print "tenant_fullmesh: [" + str(hosts[i]) + "," + str(hosts[j]) + "]"
                t1 = time.time()
                cur.execute("INSERT INTO tenant_policy values(%s,%s,%s);",([str(fid) ,int(hosts[i]), int(hosts[j])]))
                cur.execute("INSERT INTO p_spv values(%s,'on');",([ct]))
                t2 = time.time()
                f.write('----rt*tenant: route ins----' + str((t2-t1)*1000) + '\n')
                f.flush()
                ct += 1
                fid += 1

    def init_tenant(self,size):
        cur = self.cur

        # add tenant schema
        cur.execute(open(os.path.join(CWD, "tenant.sql")).read())

        cur.execute("SELECT * FROM hosts;")
        cs = cur.fetchall()
        hosts = [int(s['hid']) for s in cs]

        selected_hosts = [ hosts[i] for i in random.sample(xrange(len(hosts)), size) ]

        for h in selected_hosts:
            cur.execute("insert into tenant_hosts values(" + str(h) + ");")

        # print selected_hosts
        self.tenant_fullmesh(selected_hosts)

    def op_tlb(self):
        cur = self.cur
        f = self.f

        t1 = time.time()
        cur.execute("select * from tlb order by load DESC limit 1;")
        t2 = time.time()
        f.write('----lb*tenant: check max load----' + str((t2-t1)*1000) + '\n')
        f.flush()
        max_load = cur.fetchall()[0]['load']

        cur.execute("select sid from tlb where load = "+str(max_load)+" limit 1;")
        s_id = cur.fetchall()[0]['sid']

        t1 = time.time()
        cur.execute("update tlb set load = " +str(max_load - 1)+" where sid = "+str(s_id)+";")
        t2 = time.time()
        f.write('----lb*tenant: re-balance----' + str((t2-t1)*1000) + '\n')
        f.flush()

        t3 = time.time()
        cur.execute("select max(counts) from clock;")
        ct = cur.fetchall() [0]['max']
        cur.execute("INSERT INTO p_spv VALUES(" + str(ct+1) + ", 'on');")
        t4 = time.time()
        f.write('----(lb+rt)*tenant: re-balance----' + str((t2-t1 + t4-t3)*1000) + '\n')
        # f.write('----lb+rt: re-balance(absolute)----' + str((t2-t1 + t4-t3)*1000) + '\n')
        f.flush()

    def op_tacl(self):
        cur = self.cur
        f = self.f

        t1 = time.time()
        cur.execute("select end1, end2 from tacl limit 1;")
        t2 = time.time()
        f.write('----acl*tenant: check violation----' + str((t2-t1)*1000) + '\n')
        f.flush()
        t = cur.fetchall()[0]
        e1 = t['end1']
        e2 = t['end2']

        t1 = time.time()
        cur.execute("update tacl set isviolated = 0 where end1 = "+ str(e1) +" and end2 = "+str(e2)+";")
        t2 = time.time()
        f.write('----acl*tenant: fix violation----' + str((t2-t1)*1000) + '\n')
        f.flush()

        t3 = time.time()
        cur.execute("select max(counts) from clock;")
        ct = cur.fetchall() [0]['max']
        cur.execute("INSERT INTO p_spv VALUES(" + str(ct+1) + ", 'on');")
        t4 = time.time()
        f.write('----acl+rt*tenant: fix violation----' + str((t2-t1 + t4-t3)*1000) + '\n')
        f.flush()

class IspEvaluation(Evaluation):
    def __init__(self, db, testname, ispnum, feeds=0, rounds=10):
        super(IspEvaluation, self).__init__(db, testname, rounds)
        self.isp = ispnum
        self.name = testname

        isp_path = os.path.join(CWD, "ISP_topo")
        rib_path = os.path.join(CWD, "rib_feeds")

        self.ISP_edges_file = os.path.join(isp_path, "{0}_edges.txt".format(self.isp))
        self.ISP_nodes_file = os.path.join(isp_path, "{0}_nodes.txt".format(self.isp))
        self.rib_prefixes_file = os.path.join(rib_path, "rib20011204_prefixes.txt")
        self.rib_peerIPs_file = os.path.join(rib_path, "rib20011204_nodes.txt")
        rib_feeds_all = os.path.join(rib_path, "rib20011204_edges.txt")

        if feeds > 0:
            self.rib_edges_file = os.path.join(rib_path, "rib20011204_edges_{0}.txt".format(feeds))
            os.system("head -n " + str(feeds) + " " + rib_feeds_all + " > " + self.rib_edges_file)
        else:
            self.rib_edges_file = os.path.join(rib_path, "rib20011204_edges.txt".format(feeds))

        self.init_rib()

    def close(self):
        shutil.copyfile(LOG, self.logdest)

        if self.isp == '4755' or self.isp == '3356' or self.isp == '7018':
            t = 'isp_3sizes'
        elif self.isp == '2914':
            t = 'isp' + self.isp + '_3ribs'

        if PROFILED == True:
            dest = "plot/profile/log"
        else:
            dest = "plot/{0}/log/".format(t)

        os.system("mkdir -p {0}; mv {1} {0}".format(dest, self.logdest))
        super(IspEvaluation, self).close()

    def primitive(self):
        self.init_acl()
        self.init_lb()
        self.op_primitive()

    def init_rib(self):
        cursor = self.cur
        ISP_edges_file = self.ISP_edges_file
        ISP_nodes_file = self.ISP_nodes_file
        rib_prefixes_file = self.rib_prefixes_file
        rib_peerIPs_file = self.rib_peerIPs_file
        rib_edges_file = self.rib_edges_file

        def peerIP_ISP_map(peerIP_nodes_file, ISP_nodes_file):
            pf = [line.strip() for line in open(peerIP_nodes_file, "r").readlines()]
            ispf = [line.strip() for line in open(ISP_nodes_file, "r").readlines()]

            node_map = {}
            for pn in pf:
                ISP_node = random.choice(ispf)
                ispf.remove(ISP_node)
                node_map[pn] = int(ISP_node)
            return node_map

        # map(randomly picked) ISP nodes(switch nodes in tp table)
        # to peer IPs in rib feeds
        nm = peerIP_ISP_map(rib_peerIPs_file, ISP_nodes_file)
        ISP_borders = nm.values()

        cursor.execute("""
DROP TABLE IF EXISTS borders CASCADE;
CREATE UNLOGGED TABLE borders(
       sid     integer,
       peerip  text
);
""")
        # set up borders table, randomly pick 21 switches, and assign
        # each switch a unique peer IP
        for key in nm.keys():
            cursor.execute("""INSERT INTO borders(sid, peerip) VALUES(%s,  %s)""",(nm[key], key))

#         cursor.execute("""
# SELECT *
# FROM hosts, borders WHERE
# hid = 100000 + sid;
# """)
        # cs = self.cur.fetchall()
        # sid2u_hid = {h['sid']: int(h['hid']) for h in cs}

        ribs = open(rib_edges_file, "r").readlines()
        self.update_max_fid()
        fid = self.max_fid + 1
        for r in ribs:
            switch_id = int(nm [r.split()[0]])
            random_border = int(random.choice(ISP_borders))

            if random_border != switch_id:
                #cursor.execute("INSERT INTO rm VALUES(%s,%s,%s);",(fid, sid2u_hid[switch_id], sid2u_hid[random_border]))
                cursor.execute("INSERT INTO rm VALUES(%s,%s,%s);",(fid, switch_id, random_border))
                fid += 1

def insert_topo(db, topo):
    nodecount = 0
    nodemap = {}
    hosts = []
    for sw in topo.switches():
        db.cursor.execute("INSERT INTO SWITCHES(sid, name) VALUES({0}, '{1}');"
                          .format(nodecount, sw))
        nodemap[sw] = nodecount
        nodecount += 1

    for host in topo.hosts():
        db.cursor.execute("INSERT INTO hosts(hid, name) VALUES({0}, '{1}');"
                          .format(nodecount, host))
        nodemap[host] = nodecount
        hosts.append(host)
        nodecount += 1

    for edge1, edge2 in topo.links():
        sid = nodemap[edge1]
        nid = nodemap[edge2]
        if edge1 in hosts or edge2 in hosts:
            ishost = 1
        else:
            ishost = 0

        if hasattr(topo, "bidirectional") and not topo.bidirectional:
            db.cursor.execute("INSERT INTO tp(sid, nid, ishost, isactive) "
                              "VALUES({0}, {1}, {2}, 1);"
                              .format(sid, nid, ishost))
        else:
            db.cursor.execute("INSERT INTO tp(sid, nid, ishost, isactive) "
                              "VALUES({0}, {1}, {2}, 1),({1}, {0}, {2}, 1);"
                              .format(sid, nid, ishost))

def precompute_paths(db):
    db.cursor.execute("SELECT hid FROM hosts;")
    results = db.cursor.fetchall()
    nodes = [n[0] for n in results]

    db.cursor.execute("SELECT sid, nid FROM tp;")
    results = db.cursor.fetchall()
    edges = [(e[0], e[1]) for e in results]

    g = networkx.Graph()
    g.add_edges_from(edges)

    count = 0
    pre_paths = []
    pre_cf = []

    for src in nodes:
        for dst in nodes:
            if src == dst:
                continue

            if count > 1000000:
                break

            count += 1

            try:
                path = networkx.shortest_path(g, src, dst)
            except networkx.exception.NetworkXNoPath:
                continue

            path_edges = []

            # TODO: how to handle pathlen=2?
            for i in range(2, len(path)):
                path_edges.append((path[i-2], path[i-1], path[i]))

            pre_paths.append((count, src, dst))
            for row in path_edges:
                pre_cf.append((count, row[0], row[1], row[2]))

    print "Paths computed, inserting"
    open("pre_paths.sql", 'w').close()
    with open("pre_paths.sql", 'w') as f:
        f.write("INSERT INTO pre_paths(id, src, dst) VALUES {0};".format(
            ",".join("({0}, {1}, {2})".format(*t) for t in pre_paths)))

    open("pre_cf.sql", 'w').close()
    with open("pre_cf.sql", 'w') as f:
        f.write("INSERT INTO pre_cf(id, pid, sid, nid) VALUES {0};".format(
            ",".join("({0}, {1}, {2}, {3})".format(*t) for t in pre_cf)))

    db.cursor.execute(open("pre_paths.sql").read())
    db.cursor.execute(open("pre_cf.sql").read())
    os.remove("pre_paths.sql")
    os.remove("pre_cf.sql")

def cleanup_precomputed_paths(db):
    db.cursor.execute("DELETE FROM pre_paths;")
    db.cursor.execute("DELETE FROM pre_cf;")

def enable_profiling(db):
    global PROFILED
    PROFILED = True
    db.cursor.execute("""
CREATE OR REPLACE FUNCTION spv_constraint1_fun()
RETURNS TRIGGER
AS $$
   BEGIN
      PERFORM spv_constraint1_fun_profiled();
      RETURN NEW;
   END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;
""")

def disable_profiling(db):
    global PROFILED
    PROFILED = False
    db.cursor.execute("""
CREATE OR REPLACE FUNCTION spv_constraint1_fun()
RETURNS TRIGGER
AS $$
   BEGIN
      PERFORM spv_constraint1_fun_unprofiled();
      RETURN NEW;
   END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;
""")

TOPOS = { "fattree" : FattreeTopo,
          "isp" : IspTopo
        }

def reset_log(log=LOG):
    open(log, 'w').close()

def setup(testname):
    elapsed = time.time()
    tokens = testname.split(",")
    if tokens[0] not in TOPOS:
        raise Exception("Invalid topo name {0}".format(tokens[0]))

    topo = TOPOS[tokens[0]](*tokens[1:])
    elapsed = time.time() - elapsed
    print "----------", topo.name
    print "Created topo", round(elapsed * 1000, 3)

    db = RavelDb(topo.name, "mininet", PRECOMPUTE_BASE)
    # force db refresh
    db.init()

    elapsed = time.time()
    insert_topo(db, topo)
    elapsed = time.time() - elapsed
    print "Inserted topo", round(elapsed * 1000, 3)

    print "Paths to compute", len(topo.hosts())**2
    elapsed = time.time()
    precompute_paths(db)
    elapsed = time.time() - elapsed
    print "Precomputed paths", round(elapsed * 1000, 3)

    return db, topo

def profile(rounds=30):
    topos_ft = ["fattree,8","fattree,16", "fattree,32", "fattree,64"]
    topos_isp1 = ["isp,2914,{0}".format(rounds),
                  "isp,2914,{0}".format(rounds*10),
                  "isp,2914,{0}".format(rounds*100)]
    topos_isp2 = ["isp,4755", "isp,3356", "isp,7018"]

    topos = topos_ft + topos_isp1 + topos_isp2
    for toponame in topos:
        reset_log()
        db, topo = setup(toponame)
        enable_profiling(db)
        testname = "profile_" + "_".join(toponame.split(","))
        e = Evaluation(db, testname, rounds)
        e.op_profile()

        e.close()
        plot.profile_dat(e.logdest, rounds)
        disable_profiling(db)

def scenario(rounds, name):
    tests = []

    if name == "3sizes":
        tests.extend(["isp,4755", "isp,3356", "isp,7-18"])
        # tests.append("isp,4755,100")
    elif name == "3ribs":
        tests.extend(["isp,2914,{0}".format(rounds),
                      "isp,2914,{0}".format(rounds*10),
                      "isp,2914,{0}".format(rounds*100)])
        # tests.extend(["isp,2914,30"])
    elif name == "primitive" or name == "tenant":
        tests.extend(["fattree,16", "fattree,32", "fattree,64"])
        # tests.extend(["fattree,4"])
    else:
        raise Exception("unknown test {0}".format(name))

    for test in tests:
        reset_log()
        db, topo = setup(test)
        disable_profiling(db)
        db.cursor.execute(open(os.path.join(CWD, "apps.sql")).read())

        if isinstance(topo, FattreeTopo):
            e = FattreeEvaluation(db, test, rounds)
            if name == "primitive":
                e.primitive()
            elif name == "tenant":
                e.tenant()
            e.close()
        elif isinstance(topo, IspTopo):
            tokens = test.split(",")
            ispnum = tokens[1]
            feeds = None
            if len(tokens) > 2:
                feeds = tokens[2]
            e = IspEvaluation(db, test, ispnum, feeds)
            e.primitive()
            e.close()
        else:
            raise Exception("unknown topo type {0}".format(topo.__class__.__name__))

if __name__ == "__main__":
    if not os.path.exists(LOGDEST):
        os.makedirs(LOGDEST)

    # profile()
    scenario(100, "primitive")
    scenario(100, "tenant")
    scenario(100, "3sizes")
    scenario(100, "3ribs")

    #t = IspTopo(1221,10)
    # db = RavelDb("ravel", "ravel", PRECOMPUTE_BASE)
    # enable_profiling(db)
    # setup(db, FattreeTopo(k=4))
    # precompute_paths(db)
    # ev = Evaluation(db, rounds=1)
