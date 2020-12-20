#!/usr/bin/python

import os
import time

from termcolor import colored

from mininet.topo import Topo
from mininet.node import OVSSwitch

from MaxiNet.Frontend import maxinet
from MaxiNet.Frontend.container import Docker
from MaxiNet.tools import Tools


class Run(object):
    def __init__(self, server, workers):
        self.server = server
        self.workers = workers
        self.option = 1000
        self.option_executed = list()
        self.exp = ''

    def start_topology(self):

        print('\n*** Trying to start topology emulation.')
        time.sleep(2)

        self.restart_MaxiNet()

        print('*** Creating topology')
        topo = Topo()

        print(colored('\n*** If the application freezes for a long time, type ctrl-c to finish it '
                      'and execute the command "./topology.py" to run the application again.\n', 'yellow'))

        print("*** Starting MaxiNet cluster nodes")
        cluster = maxinet.Cluster(minWorkers=1, maxWorkers=1)

        print("*** Starting cluster node mapping")
        hnmap = {"lpttch": 0}

        print('*** Starting the experiment on cluster')
        self.exp = maxinet.Experiment(cluster, topo, switch=OVSSwitch, hostnamemapping=hnmap)
        self.exp.setup()

        print("*** Creating nodes")
        AS65001 = self.exp.addHost('AS65001', ip=None, wid=0)
        AS65002 = self.exp.addHost('AS65002', ip=None, wid=0)
        AS65003 = self.exp.addHost('AS65003', ip=None, wid=0)
        AS65004 = self.exp.addHost('AS65004', ip=None, wid=0)

        print("*** Creating links")
        self.exp.addLink(AS65001, AS65003, intfName1='65001-65003', intfName2='65003-65001',
                         params1={'ip': '10.0.0.5/30'}, params2={'ip': '10.0.0.6/30'}, autoconf=True)
        self.exp.addLink(AS65002, AS65004, intfName1='65002-65004', intfName2='65004-65002',
                         params1={'ip': '10.0.0.9/30'}, params2={'ip': '10.0.0.10/30'}, autoconf=True)
        self.exp.addLink(AS65001, AS65002, intfName1='65001-65002', intfName2='65002-65001',
                         params1={'ip': '10.0.0.1/30'}, params2={'ip': '10.0.0.2/30'}, autoconf=True)

        print("*** Creating zebra commands")
        AS65001.cmd(
            '/home/minisecbgpuser/quagga-1.2.4/sbin/./zebra -f /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//AS/65001/zebra.conf -z /var/run/quagga/65001.socket -i /var/run/quagga/zebra-65001.pid > /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//log/zebra-65001.log &')
        AS65002.cmd(
            '/home/minisecbgpuser/quagga-1.2.4/sbin/./zebra -f /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//AS/65002/zebra.conf -z /var/run/quagga/65002.socket -i /var/run/quagga/zebra-65002.pid > /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//log/zebra-65002.log &')
        AS65003.cmd(
            '/home/minisecbgpuser/quagga-1.2.4/sbin/./zebra -f /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//AS/65003/zebra.conf -z /var/run/quagga/65003.socket -i /var/run/quagga/zebra-65003.pid > /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//log/zebra-65003.log &')
        AS65004.cmd(
            '/home/minisecbgpuser/quagga-1.2.4/sbin/./zebra -f /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//AS/65004/zebra.conf -z /var/run/quagga/65004.socket -i /var/run/quagga/zebra-65004.pid > /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//log/zebra-65004.log &')

        print("*** Creating bgpd commands")
        AS65001.cmd(
            '/home/minisecbgpuser/quagga-1.2.4/sbin/./bgpd -f /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//AS/65001/bgpd.conf -z /var/run/quagga/65001.socket -i /var/run/quagga/bgpd-65001.pid > /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//log/bgpd-65001.log &')
        AS65002.cmd(
            '/home/minisecbgpuser/quagga-1.2.4/sbin/./bgpd -f /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//AS/65002/bgpd.conf -z /var/run/quagga/65002.socket -i /var/run/quagga/bgpd-65002.pid > /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//log/bgpd-65002.log &')
        AS65003.cmd(
            '/home/minisecbgpuser/quagga-1.2.4/sbin/./bgpd -f /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//AS/65003/bgpd.conf -z /var/run/quagga/65003.socket -i /var/run/quagga/bgpd-65003.pid > /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//log/bgpd-65003.log &')
        AS65004.cmd(
            '/home/minisecbgpuser/quagga-1.2.4/sbin/./bgpd -f /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//AS/65004/bgpd.conf -z /var/run/quagga/65004.socket -i /var/run/quagga/bgpd-65004.pid > /tmp/MiniSecBGP/output/topology/Manual\ Topology\ 1//log/bgpd-65004.log &')

        self.option_executed.append(1)

    def cli_mode(self):
        print('\n*** Exposing the CLI')
        maxinet.Experiment.CLI(self.exp, None, None)

    def stop_topology(self):
        print('\n*** Closing all')
        self.exp.stop()
        print('*** Killing all router process')
        os.system('sudo -u minisecbgpuser -s ssh %s sudo pkill -9 zebra' % self.server)
        os.system('sudo -u minisecbgpuser -s ssh %s sudo pkill -9 bgpd' % self.server)
        self.option_executed.remove(1)

    def restart_MaxiNet(self):
        print('\n*** Restarting MiniSecBGP cluster nodes (MaxiNet)')
        print('\n  * Restarting MaxiNetFrontendServer on node "%s"' % self.server)
        os.system('sudo -u minisecbgpuser bash -c \'ssh %s sudo systemctl restart MaxiNetFrontendServer\'' % self.server)
        time.sleep(3)
        print('  * Restarting MaxiNetWorkers')
        for worker in self.workers:
            print('    * on node "%s"' % worker)
            os.system('sudo -u minisecbgpuser bash -c \'ssh %s sudo systemctl restart MaxiNetWorker\'' % worker)
        time.sleep(5)
        print('\n*** MaxiNetStatus')
        os.system('sudo -u minisecbgpuser bash -c \'MaxiNetStatus\'')

    def start_hijack_scenario(self):
        pass

    @staticmethod
    def input_to_continue(phrase, color):
        try:
            print(colored('\nAttention: %s. Press any key to continue...' % phrase, color))
            input()
        except SyntaxError:
            pass

    def menu(self):
        clear = lambda: os.system('clear')

        while self.option != 0:

            while True:
                try:
                    clear()

                    print('\n\n'
                          '    [ 1 ] start topology emulation\n'
                          '    [ 2 ] enter CLI mode\n'
                          '    [ 3 ] stop topology emulation\n'
                          '    [ 4 ] start hijack scenario\n'
                          '    [ 9 ] restart MaxiNetFrontendServer and MaxiNetWorkers\n'
                          '    [ 0 ] exit\n')

                    self.option = int(input('\n>>> Choose an option: '))
                    break
                except Exception:
                    self.input_to_continue('Choose a valid option', 'red')

            if self.option == 0:
                if 1 in self.option_executed:
                    self.stop_topology()
                print('\nexiting...\n')
                exit()

            elif self.option == 1:
                if self.option not in self.option_executed:
                    self.start_topology()
                    self.input_to_continue('Topology emulation started successfully', 'green')
                else:
                    self.input_to_continue('Topology already started', 'red')

            elif self.option == 2:
                if 1 in self.option_executed:
                    self.cli_mode()
                else:
                    self.input_to_continue('You need start topology first (menu option [1])', 'red')

            elif self.option == 3:
                if 1 in self.option_executed:
                    self.stop_topology()
                    self.input_to_continue('Topology emulation stopped successfully', 'green')
                else:
                    self.input_to_continue('You need start topology first (menu option [1])', 'red')

            elif self.option == 4:
                if 1 in self.option_executed:
                    self.start_hijack_scenario()
                    self.input_to_continue('Hijacking attack scenario started successfully.\n\nYou can interact with this scenario through the Mininet terminal (menu option [2])', 'green')
                else:
                    self.input_to_continue('You need start topology first (menu option [1])', 'red')

            elif self.option == 9:
                self.restart_MaxiNet()
                self.input_to_continue('MaxiNet Services restarted successfully', 'green')

            else:
                self.input_to_continue('Choose a valid option', 'red')


if __name__ == '__main__':
    server = 'lpttch'
    workers = ['lpttch']
    run = Run(server, workers)
    run.menu()

