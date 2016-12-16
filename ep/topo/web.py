from mininet.topo import Topo

# 10k hosts, clustered to a switch in sets of 5
# each switch connected to two neighboring switch in a ring
class WebTopo(Topo):
	def __init__( self ):
		Topo.__init__( self )
		clusterSize = 5
		hostCount = 1000
		switchCount = (hostCount / clusterSize)

		hostNum = 1
		switchNum = 1
		rootSwitch = self.addSwitch('s1')
		previousSwitch = rootSwitch

		# hostNum will be incremented by "clusterSize" every iteration
		while (hostNum <= hostCount):
			# create switch first
			if (switchNum == 1):
				switch = rootSwitch
				switchNum += 1
			else:
				switch = self.addSwitch('s{0}'.format(switchNum))
				switchNum += 1
				
				# create link to previous switch
				self.addLink(switch,previousSwitch)
				previousSwitch = switch

				# if last switch, also create link to root
				if (switchNum > switchCount):
					self.addLink(switch,rootSwitch)

			# create cluster hosts
			clusterHostNum = 0
			while (clusterHostNum < clusterSize):
				host = self.addHost('h{0}'.format(hostNum))
				clusterHostNum += 1
				hostNum += 1

				# add links to hub switch
				self.addLink(host,rootSwitch)#switch)

topos = { 'web': ( lambda: WebTopo() ) }
