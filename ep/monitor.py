#!/usr/bin/env python

from time import sleep
import psutil
import datetime
import subprocess
import os

monitor_interval = 60
monitor_first_time = True
log = open("log.txt","a")

# -------------------------------------------------------------------
# -------------------------------------------------------------------

def update_backup_script():
	log.write("{0} [INFO] - Process found!  Backing up the database.\n".format(datetime.datetime.now()))
	log.flush()
	os.system("sudo -u ravel pg_dump ravel > /home/ravel/ravel/ep/backup.sql")

# -------------------------------------------------------------------
# -------------------------------------------------------------------

def update_boot_script():
	# Read last Ravel topology from file
	with open("topo.txt","r") as topo_file:
		ravelTopo = topo_file.read()

	# Update log
	log.write("{0} [ERROR] - Process not found! Time to restart with topology: {1}\n".format(datetime.datetime.now(), ravelTopo))
	log.flush()
	
	# Print updated contents of boot shell
	with open("boot.sh","r+w") as boot_shell:
		boot_shell.write("#!/bin/sh \n")
		boot_shell.write("cd /home/ravel/ravel \n")
		boot_shell.write("./ravel.py --clean \n")
		boot_shell.write("./ravel.py --topo={0} --restore \n".format(ravelTopo))
		boot_shell.write("bash")

	# Start Ravel boot script
	subprocess.Popen(["gnome-terminal", "--command", "./boot.sh"])

# -------------------------------------------------------------------
# -------------------------------------------------------------------

def check_process():
	# Read Ravel process ID from file
	with open("pid.txt","r") as pid_file:
		ravelPID = pid_file.read()

	# Attempt to locate process
	# If found, update database backup
	if (psutil.pid_exists(int(ravelPID))):
		update_backup_script()
	# If not found, restart Ravel system
	else:
		update_boot_script()

# -------------------------------------------------------------------
# -------------------------------------------------------------------

# Write this process's ID to file
with open("mpid.txt","w") as mpid_file:
	mpid_file.write("%s" % os.getpid())

# Start monitor loop
while (True):
	check_process()
	sleep(monitor_interval)
