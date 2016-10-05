from pox.lib.addresses import EthAddr

from pyretic.lib.corelib import *
from pyretic.lib.std import *

def blacklist():
    blocked = [("10.0.0.1", "10.0.0.2"),
               ("10.0.0.3", "10.0.0.4")]

    return ~union([(match(srcip=ip1) &
                    match(dstip=ip2)) |
                   (match(dstip=ip1) &
                    match(srcip=ip2))
                   for (ip1, ip2)
                   in blocked])

def main():
    return blacklist() >> flood()


