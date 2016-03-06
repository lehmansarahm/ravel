# Ravel CLI

* Run the Ravel CLI with `./ravel.py --topo [topo]`
* Arguments:
  * --topo - topology name, parameters
  * --custom - load custom topology file
  * --verbosity - logging output verbosity (debug, info, error)
  * --db - specify db name
  * --user - specify db user
  * --password - prompt for db password
  * --noctl - start Ravel without a controller
  * --onlydb - start without Mininet
  * --reconnect - connect to existing db session, skipping reinit

* Commands:
  * stat - show running configuration
  * apps - list discovered applications
  * load - load application into Postgres
  * unload - unload application from Postgres
  * addflow - install a new flow between two hosts
  * delflow - remove a flow by hosts or flow id
  * m - execute Mininet command
  * p - execute SQL statement
  * time - print execution time
  * profile - print detailed execution time
  * reinit - truncate database tables except topology
  * watch - spawn new xterm watching database tables

### TODO
- [ ] optparse deprecated
- [x] from config: auto start controller (eg, pox, ovs) 
- [x] package resource manager
- [x] config file, parser
- [x] from config: load flow trigger/protocol
- [x] start mn with remote controller

### NOTES
- To use OVS channel, must add postgres to sudoers `sudo adduser postgres sudo`
- Must also allow passwordless sudo: %sudo   ALL=(ALL:ALL) NOPASSWD:ALL  
