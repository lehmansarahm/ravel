#!/usr/bin/env python

from ravel.app import AppConsole

class RoutingConsole(AppConsole):
    def do_addflow(self, line):
        """Add a flow between two hosts, using Mininet hostnames
           Usage: addflow [host1] [host2]"""
        args = line.split()
        if len(args) != 2:
            print "Invalid syntax"
            return

        hostnames = self.env.provider.cache_name
        src,dst = args
        if src not in hostnames:
            print "Unknown host", src
            return

        if dst not in hostnames:
            print "Unknown host", dst
            return

        src = hostnames[src]
        dst = hostnames[dst]

        # TODO: will remove this when we delete uhosts
        # convert to host uhid
        self.db.cursor.execute("SELECT u_hid FROM uhosts WHERE hid={0}"
                               .format(src))
        src = int(self.db.cursor.fetchall()[0][0])
        self.db.cursor.execute("SELECT u_hid FROM uhosts WHERE hid={0}"
                               .format(dst))
        dst = int(self.db.cursor.fetchall()[0][0])

        try:
            # get next flow id
            # TODO: change to tm?
            self.db.cursor.execute("SELECT * FROM rtm;")
            fid = len(self.db.cursor.fetchall()) + 1
            self.db.cursor.execute("INSERT INTO rtm (fid, host1, host2) "
                                   "VALUES ({0}, {1}, {2});"
                                   .format(fid, src, dst))
            self.db.cursor.execute ("UPDATE tm set FW = 0 where fid = {0};"
                                    .format(fid, src, dst))
        except Exception, e:
            print "Failure: flow not installed --", e
            return

        print "Success: installed flow with fid", fid

    def _delFlowByName(self, src, dst):
        hostnames = self.env.provider.cache_name

        if src not in hostnames:
            print "Unknown host", src
            return

        if dst not in hostnames:
            print "Unknown host", dst
            return

        src = hostnames[src]
        dst = hostnames[dst]

        # TODO: will remove this when we delete uhosts
        # convert to host uhid
        self.db.cursor.execute("SELECT u_hid FROM uhosts WHERE hid={0}"
                               .format(src))
        src = int(self.db.cursor.fetchall()[0][0])
        self.db.cursor.execute("SELECT u_hid FROM uhosts WHERE hid={0}"
                               .format(dst))
        dst = int(self.db.cursor.fetchall()[0][0])

        # TODO: change to tm?
        self.db.cursor.execute("SELECT fid FROM rtm WHERE host1={0} and host2={1};"
                               .format(src, dst))
        result = self.db.cursor.fetchall()

        if len(result) == 0:
            logger.warning("no flow installed for hosts {0},{1}".format(src, dst))
            return None

        fids = [res[0] for res in result]
        for fid in fids:
            self._delFlowById(fid)

        return fids

    def _delFlowById(self, fid):
        try:
            # does the flow exist?
            self.db.cursor.execute("SELECT fid FROM rtm WHERE fid={0}".format(fid))
            if len(self.db.cursor.fetchall()) == 0:
                logger.warning("no flow installed with fid %s", fid)
                return None

            self.db.cursor.execute("DELETE FROM rtm WHERE fid={0}".format(fid))
            return fid
        except Exception, e:
            print e
            return None

    def do_delflow(self, line):
        """Delete a flow between two hosts, using flow ID or Mininet hostnames"
           Usage: delflow [host1] [host2]
                  delflow [flow id]"""
        args = line.split()
        if len(args) == 1:
            fid = self._delFlowById(args[0])
        elif len(args) == 2:
            fid = self._delFlowByName(args[0], args[1])
        else:
            print "Invalid syntax"
            return

        if fid is not None:
            print "Success: removed flow with fid", fid
        else:
            print "Failure: flow not removed"

shortcut = "rt"
description = "IP routing"
console = RoutingConsole
