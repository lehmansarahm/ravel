#/usr/bin/env python

import psycopg2

import util
from log import logger

ISOLEVEL = psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT

class RavelDb():
    def __init__(self, name, user, base, passwd=None):
        self.dbname = name
        self.user = user
        self.passwd = passwd
        self.init(base)
        
    @property
    def name(self):
        return self.dbname

    def init(self, base):
        self.clean()
        self.create()
        self.add_extensions()
        self.load_schema(base)

    def connect(self, db=None):
        if db is None:
            db = self.name

        conn = psycopg2.connect(database=db,
                                user=self.user,
                                password=self.passwd)
        conn.set_isolation_level(ISOLEVEL)
        return conn

    def fmt_errmsg(self, exception):
        return str(exception).strip()

    def load_schema(self, script):
        conn = None
        try:
            conn = self.connect()
            cursor = conn.cursor()
            s = open(script, 'r').read()
            logger.debug("loaded schema %s", script)
            cursor.execute(s)
        except psycopg2.DatabaseError, e:
            logger.warning("error loading schema: %s", self.fmt_errmsg(e))

        finally:
            if conn:
                conn.close()

    def load_topo(self, net):
        topo = net.topo
        conn = None
        try:
            conn = self.connect()
            cursor = conn.cursor()

            node_count = 0
            nodes = {}
            for sw in topo.switches():
                node_count += 1
                dpid = net.getNodeByName(sw).dpid
                ip = net.getNodeByName(sw).IP()
                mac = net.getNodeByName(sw).MAC()
                nodes[sw] = node_count
                cursor.execute("INSERT INTO switches (sid, dpid, ip, mac, name) "
                               "VALUES ({0}, '{1}', '{2}', '{3}', '{4}');"
                               .format(node_count, dpid, ip, mac, sw))

            for host in topo.hosts():
                node_count += 1
                ip = net.getNodeByName(host).IP()
                mac = net.getNodeByName(host).MAC()
                nodes[host] = node_count
                cursor.execute("INSERT INTO hosts (hid, ip, mac, name) "
                               "VALUES ({0}, '{1}', '{2}', '{3}');"
                               .format(node_count, ip, mac, host))

            for link in topo.links():
                h1,h2 = link
                if h1 in topo.switches() and h2 in topo.switches():
                    ishost = 0
                else:
                    ishost = 1

                sid = nodes[h1]
                nid = nodes[h2]
                cursor.execute("INSERT INTO tp(sid, nid, ishost, isactive) "
                               "VALUES ({0}, {1}, {2}, {3});"
                               .format(sid, nid, ishost, 1))

                cursor.execute("INSERT INTO ports(sid, nid, port) "
                               "VALUES ({0}, {1}, {2}), ({1}, {0}, {3});"
                               .format(sid, nid,
                                       topo.port(h1, h2)[0],
                                       topo.port(h1, h2)[1]))

        except psycopg2.DatabaseError, e:
            logger.warning("error loading topology: %s", self.fmt_errmsg(e))
        finally:
            if conn:
                conn.close()

    def create(self):
        conn = None
        try:
            conn = self.connect("postgres")
            cursor = conn.cursor()
            cursor.execute("SELECT datname FROM pg_database WHERE " +
                           "datistemplate = false;")
            fetch = cursor.fetchall()
            
            dblist = [fetch[i][0] for i in range(len(fetch))]
            if self.name not in dblist:
                cursor.execute("CREATE DATABASE %s;" % self.name)
                logger.debug("created databse %s", self.name)
        except psycopg2.DatabaseError, e:
            logger.warning("error creating database: %s", self.fmt_errmsg(e))
        finally:
            if conn:
                conn.close()

    def add_extensions(self):
        conn = None
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM pg_catalog.pg_namespace n JOIN " +
                           "pg_catalog.pg_proc p ON pronamespace = n.oid " +
                           "WHERE proname = 'pgr_dijkstra';")
            fetch = cursor.fetchall()

            if fetch == []:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS plpythonu;")
                cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                cursor.execute("CREATE EXTENSION IF NOT EXISTS pgrouting;")
                cursor.execute("CREATE EXTENSION plsh;")
                logger.debug("created extensions")
        except psycopg2.DatabaseError, e:
            logger.warning("error loading extensions: %s", self.fmt_errmsg(e))
        finally:
            if conn:
                conn.close()
            
    def query(self, qry):
        conn = None
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(qry)
            fetch = cursor.fetchall()
            return fetch
        except psycopg2.DatabaseError, e:
            logger.warning("error executing query: %s", self.fmt_errmsg(e))
        finally:
            if conn:
                conn.close()

    def clean(self):
        conn = None
        try:
            conn = self.connect("postgres")
            cursor = conn.cursor()
            cursor.execute("drop database %s" % self.name)
        except psycopg2.DatabaseError, e:
            logger.warning("error cleaning database: %s", self.fmt_errmsg(e))
        finally:
            if conn:
                conn.close()

    def truncate(self):
        conn = None
        try:
            tables = ["cf", "clock", "p1", "p2", "p3", "p_spv", "pox_hosts", 
                      "pox_switches", "pox_tp", "rtm", "rtm_clock",
                      "spatial_ref_sys", "spv_tb_del", "spv_tb_ins", "tm",
                      "tm_delta", "utm", "acl_tb", "acl_tb", "lb_tb"]
            tenants = ["t1", "t2", "t3", "tacl_tb", "tenant_hosts", "tlb_tb"]

            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("truncate %s;" % ", ".join(tables))
            logger.debug("truncated tables")

            cursor.execute("INSERT INTO clock values (0);")
            # TODO: fix
            #cursor.execute("truncate %s;" % ", ".join(tenants))
            logger.debug("truncated tenant tables")
        except psycopg2.DatabaseError, e:
            logger.warning("error truncating databases: %s", self.fmt_errmsg(e))
        finally:
            if conn:
                conn.close()
