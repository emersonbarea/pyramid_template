#!/usr/bin/python

import os

from mininet.topo import Topo
from mininet.node import OVSSwitch

from MaxiNet.Frontend import maxinet
from MaxiNet.Frontend.container import Docker
from MaxiNet.tools import Tools

print('*** Creating topology')
topo = Topo()

print("*** Starting cluster")
cluster = maxinet.Cluster(minWorkers=1, maxWorkers=1)

print("*** Starting cluster node mapping")
hnmap = {"lpttch":0}

print('*** Starting the experiment on cluster')
exp = maxinet.Experiment(cluster, topo, switch=OVSSwitch, hostnamemapping=hnmap)
exp.setup()

print("*** Creating nodes")
AS65001 = exp.addHost('AS65001', ip=None, wid=0)
AS65002 = exp.addHost('AS65002', ip=None, wid=0)
AS65003 = exp.addHost('AS65003', ip=None, wid=0)
AS65004 = exp.addHost('AS65004', ip=None, wid=0)

print("*** Creating links")
exp.addLink(AS65001, AS65003, intfName1='65001-65003', intfName2 = '65003-65001', params1={'ip':'10.0.0.5/30'}, params2={'ip':'10.0.0.6/30'}, autoconf=True)
exp.addLink(AS65002, AS65004, intfName1='65002-65004', intfName2 = '65004-65002', params1={'ip':'10.0.0.9/30'}, params2={'ip':'10.0.0.10/30'}, autoconf=True)
exp.addLink(AS65001, AS65002, intfName1='65001-65002', intfName2 = '65002-65001', params1={'ip':'10.0.0.1/30'}, params2={'ip':'10.0.0.2/30'}, autoconf=True)

print("*** Creating zebra commands")
AS65001.cmd('/home/minisecbgpuser/quagga-1.2.4/sbin/./zebra -f /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//AS/65001/zebra.conf -z /var/run/quagga/65001.socket -i /var/run/quagga/zebra-65001.pid > /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//log/zebra-65001.log &')
AS65002.cmd('/home/minisecbgpuser/quagga-1.2.4/sbin/./zebra -f /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//AS/65002/zebra.conf -z /var/run/quagga/65002.socket -i /var/run/quagga/zebra-65002.pid > /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//log/zebra-65002.log &')
AS65003.cmd('/home/minisecbgpuser/quagga-1.2.4/sbin/./zebra -f /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//AS/65003/zebra.conf -z /var/run/quagga/65003.socket -i /var/run/quagga/zebra-65003.pid > /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//log/zebra-65003.log &')
AS65004.cmd('/home/minisecbgpuser/quagga-1.2.4/sbin/./zebra -f /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//AS/65004/zebra.conf -z /var/run/quagga/65004.socket -i /var/run/quagga/zebra-65004.pid > /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//log/zebra-65004.log &')

print("*** Creating bgpd commands")
AS65001.cmd ('/home/minisecbgpuser/quagga-1.2.4/sbin/./bgpd -f /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//AS/65001/bgpd.conf -z /var/run/quagga/65001.socket -i /var/run/quagga/bgpd-65001.pid > /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//log/bgpd-65001.log &')
AS65002.cmd ('/home/minisecbgpuser/quagga-1.2.4/sbin/./bgpd -f /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//AS/65002/bgpd.conf -z /var/run/quagga/65002.socket -i /var/run/quagga/bgpd-65002.pid > /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//log/bgpd-65002.log &')
AS65003.cmd ('/home/minisecbgpuser/quagga-1.2.4/sbin/./bgpd -f /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//AS/65003/bgpd.conf -z /var/run/quagga/65003.socket -i /var/run/quagga/bgpd-65003.pid > /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//log/bgpd-65003.log &')
AS65004.cmd ('/home/minisecbgpuser/quagga-1.2.4/sbin/./bgpd -f /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//AS/65004/bgpd.conf -z /var/run/quagga/65004.socket -i /var/run/quagga/bgpd-65004.pid > /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//log/bgpd-65004.log &')

print('*** Exposing the CLI')
maxinet.Experiment.CLI(exp, None, None)

print('*** Closing all')
exp.stop()

print('*** Killing all router process')
os.system("sudo -u minisecbgpuser -s ssh lpttch sudo pkill -9 zebra")
os.system("sudo -u minisecbgpuser -s ssh lpttch sudo pkill -9 bgpd")
