#!/usr/bin/env python

import os
import psutil
import subprocess
import time
from time import sleep

resourceLog = '/home/ravel/ravel/ep/resource_logs/{0}_{1}.txt'
testLog = '/home/ravel/ravel/ep/resource_logs/{0}_test{1}_{2}.txt'

ravelResourceLog = resourceLog.format('ravel', time.strftime("%m-%d-%Y"))
epResourceLog = resourceLog.format('ep', time.strftime("%m-%d-%Y"))

# -------------------------------------------------------------------
# -------------------------------------------------------------------
#	Test 1 - run Ravel w/o EP for 5min (topo=single,3)
# -------------------------------------------------------------------
# -------------------------------------------------------------------
subprocess.Popen(["gnome-terminal", "--command", "sudo ./ravel.py --topo=single,3"], cwd="/home/ravel/ravel")

with open("configs/pid.txt","r") as pid_file:
	# Grab current Ravel process ID and today's log file name
	ravelPID = pid_file.read()

	# Every 10 sec, log Ravel process resource use
	testTime = 0
	while (testTime < 60):
		os.system('ps -p {0} -o %cpu,%mem,cmd >> {1}'.format(ravelPID, ravelResourceLog))
		sleep(10)
		testTime += 10

	# after 5min, kill the Ravel controller process
	p = psutil.Process(int(ravelPID))
	p.kill()

	# Rename log file for later review
	ravelTestLog = testLog.format('ravel','1',time.strftime("%m-%d-%Y"))
	os.system('mv {0} {1}'.format(ravelResourceLog, ravelTestLog))

# -------------------------------------------------------------------
# -------------------------------------------------------------------
#	Test 2 - run Ravel w/ EP for 5min w/ 1 restart (topo=single,3)
# -------------------------------------------------------------------
# -------------------------------------------------------------------

# -------------------------------------------------------------------
# -------------------------------------------------------------------
#	Test 3 - run EP w/o Ravel for 5min w/ 1 restart (topo=single,3)
# -------------------------------------------------------------------
# -------------------------------------------------------------------
subprocess.Popen(["gnome-terminal", "--command", "sudo ./monitor.py --logResources --autoclose=5"])

# after 2min, kill the Ravel controller process
sleep(120)
with open("configs/pid.txt","r") as pid_file:
	# Grab current Ravel process ID
	ravelPID = pid_file.read()
	p = psutil.Process(int(ravelPID))
	p.kill()

# Rename log file for later review
ravelTestLog = testLog.format('ravel','3',time.strftime("%m-%d-%Y"))
os.system('mv {0} {1}'.format(ravelResourceLog, ravelTestLog))

# -------------------------------------------------------------------
# -------------------------------------------------------------------
#	Test 4 - run EP w/o Ravel for 5min w/ 1 restart (large custom topo)
# -------------------------------------------------------------------
# -------------------------------------------------------------------
