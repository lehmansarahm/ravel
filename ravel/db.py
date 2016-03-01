#/usr/bin/env python

import psycopg2

from ravel.log import logger
from ravel.util import libpath

ISOLEVEL = psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT

BASE_SQL = libpath("ravel/sql/primitive.sql")
FLOW_SQL = libpath("ravel/sql/flows.sql")
TOPO_SQL = libpath("ravel/sql/topo.sql")

class RavelDb():
    def __init__(self, name, user, base, passwd=None, reconnect=False):
        self.name = name
        self.user = user
        self.passwd = passwd
        self.cleaned = not reconnect
        self._cursor = None
        self._conn = None

        if not reconnect and self.num_connections() > 0:
            logger.warning("existing connections to database, skipping reinit")
            self.cleaned = False
        elif not reconnect:
            self.init(base)
            self.cleaned = True

    @property
    def conn(self):
        if not self._conn or self._conn.closed:
            self._conn = psycopg2.connect(database=self.name,
                                          user=self.user,
                                          password=self.passwd)
            self._conn.set_isolation_level(ISOLEVEL)
        return self._conn

    @property
    def cursor(self):
        if not self._cursor or self._cursor.closed:
            self._cursor = self.conn.cursor()
        return self._cursor

    def num_connections(self):
        try:
            self.cursor.execute("SELECT * FROM pg_stat_activity WHERE "
                                "datname='{0}'".format(self.name))

            # ignore cursor connection
            return len(self.cursor.fetchall()) - 1
        except psycopg2.DatabaseError, e:
            logger.warning("error loading schema: %s", self.fmt_errmsg(e))

        return 0

    def init(self, base):
        self.clean()
        self.create()
        self.add_extensions()
        self.load_schema(base)

    def fmt_errmsg(self, exception):
        return str(exception).strip()

    def load_schema(self, script):
        try:
            s = open(script, 'r').read()
            logger.debug("loaded schema %s", script)
            self.cursor.execute(s)
        except psycopg2.DatabaseError, e:
            logger.warning("error loading schema: %s", self.fmt_errmsg(e))

    def load_topo(self, provider):
        topo = provider.topo
        try:
            node_count = 0
            nodes = {}
            for sw in topo.switches():
                node_count += 1
                dpid = provider.getNodeByName(sw).dpid
                ip = provider.getNodeByName(sw).IP()
                mac = provider.getNodeByName(sw).MAC()
                nodes[sw] = node_count
                self.cursor.execute("INSERT INTO switches (sid, dpid, ip, mac, name) "
                                    "VALUES ({0}, '{1}', '{2}', '{3}', '{4}');"
                                    .format(node_count, dpid, ip, mac, sw))

            for host in topo.hosts():
                node_count += 1
                ip = provider.getNodeByName(host).IP()
                mac = provider.getNodeByName(host).MAC()
                nodes[host] = node_count
                self.cursor.execute("INSERT INTO hosts (hid, ip, mac, name) "
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
                self.cursor.execute("INSERT INTO tp(sid, nid, ishost, isactive) "
                                    "VALUES ({0}, {1}, {2}, {3});"
                                    .format(sid, nid, ishost, 1))

                self.cursor.execute("INSERT INTO ports(sid, nid, port) "
                                    "VALUES ({0}, {1}, {2}), ({1}, {0}, {3});"
                                    .format(sid, nid,
                                            topo.port(h1, h2)[0],
                                            topo.port(h1, h2)[1]))

        except psycopg2.DatabaseError, e:
            logger.warning("error loading topology: %s", self.fmt_errmsg(e))

    def create(self):
        conn = None
        try:
            conn = psycopg2.connect(database="postgres",
                                    user=self.user,
                                    password=self.passwd)
            conn.set_isolation_level(ISOLEVEL)
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
            conn.close()

    def add_extensions(self):
        try:
            self.cursor.execute("SELECT 1 FROM pg_catalog.pg_namespace n JOIN " +
                                "pg_catalog.pg_proc p ON pronamespace = n.oid " +
                                "WHERE proname = 'pgr_dijkstra';")
            fetch = self.cursor.fetchall()

            if fetch == []:
                self.cursor.execute("CREATE EXTENSION IF NOT EXISTS plpythonu;")
                self.cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                self.cursor.execute("CREATE EXTENSION IF NOT EXISTS pgrouting;")
                self.cursor.execute("CREATE EXTENSION plsh;")
                logger.debug("created extensions")
        except psycopg2.DatabaseError, e:
            logger.warning("error loading extensions: %s", self.fmt_errmsg(e))
            
    def clean(self):
        # close existing connections
        self.conn.close()

        conn = None
        try:
            conn = psycopg2.connect(database="postgres",
                                    user=self.user,
                                    password=self.passwd)
            conn.set_isolation_level(ISOLEVEL)
            cursor = conn.cursor()
            cursor.execute("drop database %s" % self.name)
        except psycopg2.DatabaseError, e:
            logger.warning("error cleaning database: %s", self.fmt_errmsg(e))
        finally:
            if conn:
                conn.close()

    def truncate(self):
        try:
            tables = ["cf", "clock", "p1", "p2", "p3", "p_spv", "pox_hosts", 
                      "pox_switches", "pox_tp", "rtm", "rtm_clock",
                      "spatial_ref_sys", "spv_tb_del", "spv_tb_ins", "tm",
                      "tm_delta", "utm", "acl_tb", "acl_tb", "lb_tb"]
            tenants = ["t1", "t2", "t3", "tacl_tb", "tenant_hosts", "tlb_tb"]

            self.cursor.execute("truncate %s;" % ", ".join(tables))
            logger.debug("truncated tables")

            self.cursor.execute("INSERT INTO clock values (0);")
            # TODO: fix
            #self.cursor.execute("truncate %s;" % ", ".join(tenants))
            logger.debug("truncated tenant tables")
        except psycopg2.DatabaseError, e:
            logger.warning("error truncating databases: %s", self.fmt_errmsg(e))
