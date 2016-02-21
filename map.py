#!/usr/bin/env python

from sqlalchemy import Table, Column, MetaData, create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import Integer, String

class Node(object):
    def __init__(self, name, dbid, ip, mac):
        self.name = name
        self.IP = ip
        self.MAC = mac

class Switch(Node):
    def __init__(self, name, dbid, dpid, ip, mac):
        super(Switch, self).__init__(name, dbid, ip, mac)
        self.dpid = dpid

class Host(Node):
    def __init__(self, name, dbid, ip, mac):
        super(Host, self).__init__(name, dbid, ip, mac)

class MapObject(object):
    def __init__(self, db):
        self.db = db
        self.automap()

    def automap(self):
        self.engine = create_engine('postgresql+psycopg2://{0}@/{1}'
                                    .format(self.db.user, self.db.name))
        self.metadata = MetaData()
        self.metadata.reflect(self.engine, only=['switches', 'hosts'])
        Table("nodes", self.metadata,
              Column("id", Integer, primary_key=True),
              Column("name", String(16))
        )

        self.Base = automap_base(metadata=self.metadata)
        self.Base.prepare()
        self.Session = sessionmaker()
        self.Session.configure(bind=self.engine)

    @property
    def classes(self):
        return self.Base.classes

class Topology(object):
    def __init__(self, db):
        self.map = MapObject(db)

    def isSwitch(self, idx):
        names = self.names()
        if idx in names:
            idx = names[idx]
        return idx in self.switches()

    def names(self):
        s = self.map.Session()
        return dict((str(row.name), row.id) for row in s.query(self.map.classes.nodes))

    def switches(self):
        s = self.map.Session()
        return [row.sid for row in s.query(self.map.classes.switches)]

    def hosts(self):
        s = self.map.Session()
        return [row.hid for row in s.query(self.map.classes.hosts)]

    def nodes(self):
        s = self.map.Session()
        return [row.hid for row in s.query(self.map.classes.hosts)]

    def getNodeById(self, idx):
        s = self.map.Session()
        if self.isSwitch(idx):
            row = s.query(self.map.classes.switches).filter_by(sid=idx)
            row = row[0]
            return Switch(row.name, row.sid, row.dpid, row.ip, row.mac)
        else:
            row = s.query(self.map.classes.hosts).filter_by(hid=idx)
            row = row[0]
            return Host(row.name, row.hid, row.ip, row.mac)

    def getNodeByName(self, name):
        return self.getNodeById(self.names()[name])

if __name__ == "__main__":
    from mininet.net import Mininet
    import mndeps
    import db
    topo = mndeps.build("linear,2")
    net = Mininet(topo)
    net.start()
    raveldb = db.RavelDb("mininet", "mininet", "primitive.sql")
    raveldb.load_topo(net)
    net.stop()

    t = Topology(raveldb)
    print t.getNodeByName('s1').IP
    print t.getNodeByName('h1').IP
