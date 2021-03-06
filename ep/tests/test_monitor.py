#!/usr/bin/env python

import os
import subprocess
import sys
from time import sleep

# Print updated contents of boot shell
with open("../boot.sh","w") as boot_shell:
	ravelLaunch = "#!/bin/sh \n"\
		"cd /home/ravel/ravel \n"\
		"./ravel.py --clean \n"\
		"./ravel.py --topo=single,3"
	boot_shell.write(ravelLaunch)

# Start Ravel boot script
subprocess.Popen(["gnome-terminal", "--command", "../boot.sh"])

# Wait 30sec, then start EP boot script
sleep(30)
subprocess.Popen(["gnome-terminal", "--command", "../monitor.sh"])

# Wait 1min, then kill Ravel (EP will restore)
sleep(60)
os.system("cd .. && ./kill_ravel.py")

# Wait another 30sec for restore, then kill both processes
sleep(30)
os.system("cd .. && ./kill_monitor.py")
os.system("cd .. && ./kill_ravel.py")

# Rename logs and end launch script
os.system("sudo mv /home/ravel/ravel/ep/resource_logs/boottime.txt /home/ravel/ravel/ep/tests/results-monitor/boottime.txt")
os.system("sudo mv /home/ravel/ravel/ep/resource_logs/backuptime.txt /home/ravel/ravel/ep/tests/results-monitor/backuptime.txt")
os.system("sudo mv /home/ravel/ravel/ep/backup.sql /home/ravel/ravel/ep/tests/results-monitor/backup.sql")
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
