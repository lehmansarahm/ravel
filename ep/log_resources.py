#!/usr/bin/env python

import subprocess

# Start the EP monitor
subprocess.Popen(["gnome-terminal", "--command", "sudo ./monitor.py"])
