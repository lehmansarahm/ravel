#!/usr/bin/env python

import datetime
import os
import subprocess
import sys
from time import sleep

print "Printing updated contents of boot shell"
with open("../boot.sh","w") as boot_shell:
	ravelLaunch = "#!/bin/sh \n"\
		"cd /home/ravel/ravel \n"\
		"./ravel.py --clean \n"\
		"./ravel.py --topo=web --custom=ep/topo/web.py\n"
	boot_shell.write(ravelLaunch)

print "Starting Ravel boot script"
subprocess.Popen(["gnome-terminal", "--command", "../boot.sh"])

print "Waiting 30sec, then manually taking DB backup"
sleep(420)
with open ("../resource_logs/backuptime.txt", "a") as backupTimeLog:
	backupTimeLog.write("{0} - Backing up Ravel\n".format(datetime.datetime.now()))
	os.system("sudo -u ravel pg_dump ravel > /home/ravel/ravel/ep/backup.sql")
	backupTimeLog.write("{0} - Ravel backup complete\n".format(datetime.datetime.now()))

print "Waiting 30sec, then killing Ravel"
sleep(30)
os.system("cd .. && ./kill_ravel.py")

print "Starting Ravel boot script"
subprocess.Popen(["gnome-terminal", "--command", "../reboot.sh"])

print "Waiting 7min, then killing Ravel"
sleep(420)
os.system("cd .. && ./kill_ravel.py")

print "Renaming logs and ending launch script"
os.system("sudo mv /home/ravel/ravel/ep/resource_logs/boottime.txt /home/ravel/ravel/ep/tests/results-basic_web/boottime.txt")
os.system("sudo mv /home/ravel/ravel/ep/resource_logs/backuptime.txt /home/ravel/ravel/ep/tests/results-basic_web/backuptime.txt")
os.system("sudo mv /home/ravel/ravel/ep/backup.sql /home/ravel/ravel/ep/tests/results-basic_web/backup.sql")
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
