# Ravel CLI

* Run the Ravel CLI with `./ravel.py --topo [topo]`
* Arguments:
  * --topo - topology name, parameters
  * --custom - load custom topology file
  * --verbosity - logging output verbosity
  * --db - specify db name
  * --user - specify db user
  * --password - specify db password
  * --remote - start mininet with connection to a remote controller
  * --onlydb - start without mininet

### TODO
- [ ] from config: auto start controller (eg, pox, ovs) 
- [ ] optparse deprecated
- [ ] use Eggs package resources instead of manual path
- [x] config file, parser
- [x] from config: load flow trigger/protocol
- [x] start mn with remote controller
