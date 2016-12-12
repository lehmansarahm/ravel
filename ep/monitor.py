#!/usr/bin/env python

import time
from time import sleep
import psutil
import datetime
import subprocess
import os
import sys, getopt
from optparse import OptionParser

monitor_interval = 60
monitor_first_time = True

useAutoclose = False
autoCloseTime = 0

# Set up new log file for a new day
logFilename = "log_{0}.txt".format(time.strftime("%m-%d-%Y"))
log = open(logFilename,"a")

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
		ravelLaunch = "#!/bin/sh \n"\
			"cd /home/ravel/ravel \n"\
			"./ravel.py --clean \n"\
			"./ravel.py --topo={0} --restore".format(ravelTopo)
		boot_shell.write(ravelLaunch)

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

# List out the available parameters
def optParser():
    desc = "EverPresent console"
    usage = "%prog [options]\ntype %prog -h for details"

    parser = OptionParser(description=desc, usage=usage)
    parser.add_option("--autoclose", "-a", type="string", default=None,
                      help="auto-close EP monitor after the designated number of minutes")
    return parser

# -------------------------------------------------------------------
# -------------------------------------------------------------------

if __name__ == "__main__":
	# Parse any necessary arguments
	try:
		opts, args = getopt.getopt(sys.argv[1:],"ha:",["autoclose="])
	except getopt.GetoptError:
		print 'monitor.py -a <close time in whole minutes>'
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			print 'monitor.py -a <close time in whole minutes>'
			sys.exit()
		elif opt in ("-a", "--autoclose"):
			useAutoclose = True
			autoCloseTime = int(arg)

	# Write this process's ID to file
	with open("mpid.txt","w") as mpid_file:
		mpid_file.write("%s" % os.getpid())

	# Start monitor loop
	while (not useAutoclose or (autoCloseTime > 0)):
		if (useAutoclose):
			print "EverPresent will autoclose in {0} minutes".format(autoCloseTime)
		check_process()
		sleep(monitor_interval)
		autoCloseTime -= (monitor_interval/60)

	# Once loop is complete, exit
	log.close()
	sys.exit()
