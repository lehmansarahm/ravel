#!/usr/bin/env python

import os
import sys

def compute_irq(fname):
    with open(fname) as f:
        lines = [float(n.strip()) for n in f.readlines()]
        lines.sort()

        p25 = round(lines[int(len(lines) * 0.25)], 3)
        p50 = round(lines[int(len(lines) * 0.50)], 3)
        p75 = round(lines[int(len(lines) * 0.75)], 3)
        p90 = round(lines[int(len(lines) * 0.90)], 3)
        return p25, p50, p75, p90, len(lines)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(0)

    for path in sys.argv[1:]:
        if not os.path.isdir(path):
            print "Directory does not exist", path
            continue

        files = [os.path.join(path, f) for f in os.listdir(path)]
        print "------------------------------"
        print path

        for f in files:
            p25, p50, p75, p90, tot = compute_irq(f)
            testname = os.path.basename(f)
            testname = testname[:testname.index("Test_")]

            print " ", testname, " ({0})".format(tot)
            print "     25th: ", p25
            print "     50th: ", p50
            print "     75th: ", p75
            print "     90th: ", p90
