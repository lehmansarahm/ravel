#!/usr/bin/env python

import datetime
import os
import subprocess
import sys
from time import sleep

# Print updated contents of boot shell
with open("../boot.sh","w") as boot_shell:
	ravelLaunch = "#!/bin/sh \n"\
		"cd /home/ravel/ravel \n"\
		"./ravel.py --clean \n"\
		"./ravel.py --topo=web --custom=ep/topo/web_large.py\n"
	boot_shell.write(ravelLaunch)

# Start Ravel boot script
subprocess.Popen(["gnome-terminal", "--command", "../boot.sh"])

# Wait 1 hour, then manually take a DB backup
sleep(3600)
with open ("../resource_logs/backuptime.txt", "a") as backupTimeLog:
	backupTimeLog.write("{0} - Backing up Ravel\n".format(datetime.datetime.now()))
	os.system("sudo -u ravel pg_dump ravel > /home/ravel/ravel/ep/backup.sql")
	backupTimeLog.write("{0} - Ravel backup complete\n".format(datetime.datetime.now()))

# Wait 30sec, then kill Ravel
sleep(30)
os.system("cd .. && ./kill_ravel.py")

# Start Ravel boot script
subprocess.Popen(["gnome-terminal", "--command", "../reboot.sh"])

# Wait another hour, then kill Ravel
sleep(3600)
os.system("cd .. && ./kill_ravel.py")

# Rename logs and end launch script
os.system("sudo mv /home/ravel/ravel/ep/resource_logs/boottime.txt /home/ravel/ravel/ep/tests/results-basic_web_large/boottime.txt")
os.system("sudo mv /home/ravel/ravel/ep/resource_logs/backuptime.txt /home/ravel/ravel/ep/tests/results-basic_web_large/backuptime.txt")
os.system("sudo mv /home/ravel/ravel/ep/backup.sql /home/ravel/ravel/ep/tests/results-basic_web_large/backup.sql")
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
