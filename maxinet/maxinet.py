#!/usr/bin/python2

import os
import csv

from mininet.topo import Topo
from mininet.node import OVSSwitch

from MaxiNet.Frontend import maxinet
from MaxiNet.tools import Tools

# create topology
topo = Topo()

print('****Setting up topology')

print('Creating switches...')
with open('./conf/switches.mxn', 'r') as file:
    switches = file.readlines()
    for switch in switches:
        topo.addSwitch(switch.replace('\n',''))
file.close()

print('Creating hosts...')
with open('./conf/hosts.mxn', 'r') as file:
    hosts = file.readlines()
    for host in hosts:
        topo.addHost(host.replace('\n',''))
file.close()

print('Creating connections between Mininet elements...')
with open('./conf/connections.mxn', 'r') as file:
    connections = csv.reader(file) 
    for connection in connections:
        topo.addLink(connection[0], connection[1])
file.close()

print('Setting hostname mapping...')
hostnamemapping = {} 
with open('./conf/hostnamemapping.mxn', 'r') as file:
    lines = file.read()
    hostnamemapping = eval('{' + lines + '}')
file.close()
print('hostnamemapping: %s' % hostnamemapping)

print('Setting node mapping...')
nodemapping = {}
with open('./conf/nodemapping.mxn', 'r') as file:
    lines = file.read()
    nodemapping = eval('{' + lines + '}')
file.close()
print('nodemapping: %s' % nodemapping)

# start cluster
print('****Starting Cluster')
cluster = maxinet.Cluster(minWorkers=2, maxWorkers=2)

print('****Startng experiment')
exp = maxinet.Experiment(cluster, topo, switch=OVSSwitch, nodemapping=nodemapping, hostnamemapping=hostnamemapping)
exp.setup()

raw_input('[Continue]')

print('****Closing all')
exp.stop()
