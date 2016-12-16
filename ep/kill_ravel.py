#!/usr/bin/env python

import psutil

with open("configs/pid.txt","r") as pid_file:
	ravelPID = pid_file.read()
	p = psutil.Process(int(ravelPID))
	p.kill()
