#!/usr/bin/env python

import os
import subprocess
import sys
from time import sleep

print "Printing updated contents of boot shell"
with open("../boot.sh","w") as boot_shell:
	ravelLaunch = "#!/bin/sh \n"\
		"cd /home/ravel/ravel \n"\
		"./ravel.py --clean \n"\
		"./ravel.py --topo=web --custom=ep/topo/web.py"
	boot_shell.write(ravelLaunch)

print "Starting Ravel boot script"
subprocess.Popen(["gnome-terminal", "--command", "../boot.sh"])

print "Waiting 30sec, then starting EP boot script"
sleep(30)
subprocess.Popen(["gnome-terminal", "--command", "../monitor.sh"])

print "Waiting 7min, then killing Ravel (EP will restore)"
sleep(420)
os.system("cd .. && ./kill_ravel.py")

print "Waiting another 7min for restore, then killing both processes"
sleep(420)
os.system("cd .. && sudo ./kill_monitor.py")
sleep(30)
os.system("cd .. && sudo ./kill_ravel.py")

print "Renaming logs and ending launch script"
os.system("sudo mv /home/ravel/ravel/ep/resource_logs/boottime.txt /home/ravel/ravel/ep/tests/results-monitor_web/boottime.txt")
os.system("sudo mv /home/ravel/ravel/ep/resource_logs/backuptime.txt /home/ravel/ravel/ep/tests/results-monitor_web/backuptime.txt")
os.system("sudo mv /home/ravel/ravel/ep/backup.sql /home/ravel/ravel/ep/tests/results-monitor_web/backup.sql")
sys.exit()

# -------------------------------------------------------------------
# -------------------------------------------------------------------
#	Boot Time Log Contents
# -------------------------------------------------------------------
# -------------------------------------------------------------------
#	Ravel "clean" launch time
#	Ravel "basic" launch time
#	Ravel "basic" launch complete time
#	Ravel "clean" launch time (restore)
#	Ravel "restore" launch time
#	Ravel "restore" launch complete time

# -------------------------------------------------------------------
# -------------------------------------------------------------------
#	Back-up Time Log Contents
# -------------------------------------------------------------------
# -------------------------------------------------------------------
#	Ravel backup start time
#	Ravel backup end time
