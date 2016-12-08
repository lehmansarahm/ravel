#!/usr/bin/env python

import psutil

# Read last monitor process ID from file
with open("mpid.txt","r") as mpid_file:
	monitorPID = mpid_file.read()
	p = psutil.Process(int(monitorPID))
	p.kill()
