import argparse
import getopt
import ipaddress
import sys
import pandas as pd
import os
import shutil

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError


class RealisticAnalysis(object):
    def __init__(self, realistic_analysis_name, id_topology, topology_length, topology_distribution_method, emulation_platform):
        self.output_dir = os.getcwd() + '/output/topology/%s/' % realistic_analysis_name
        self.id_topology = id_topology                                                          # id_topology
        self.topology_length = topology_length                                                  # STUB / FULL
        self.topology_distribution_method = topology_distribution_method                        # CUSTOMER CONE / METIS /MANUAL /ROUND ROBIN
        self.emulation_platform = emulation_platform                                            # MININET / DOCKER

    def dfs_from_database(self, dbsession):
        query = 'select l.id as id_link, ' \
                'l.id_topology as id_topology, ' \
                'l.id_link_agreement as id_link_agreement, ' \
                'agr.agreement as agreement, ' \
                'l.id_autonomous_system1 as id_autonomous_system1, ' \
                '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system1) as autonomous_system1, ' \
                'l.id_autonomous_system2 as id_autonomous_system2, ' \
                '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system2) as autonomous_system2, ' \
                'l.ip_autonomous_system1 as ip_autonomous_system1, ' \
                'l.ip_autonomous_system2 as ip_autonomous_system2, ' \
                'l.mask as mask, ' \
                'l.description as description, ' \
                'l.bandwidth as bandwidth, ' \
                'l.delay as delay, ' \
                'l.load as load ' \
                'from link l, ' \
                'link_agreement agr ' \
                'where l.id_topology = %s ' \
                'and l.id_link_agreement = agr.id;' % self.id_topology
        result_proxy = dbsession.bind.execute(query)
        self.df_as = pd.DataFrame(result_proxy, columns=[
            'id_link', 'id_topology', 'id_link_agreement', 'agreement', 'id_autonomous_system1', 'autonomous_system1',
            'id_autonomous_system2', 'autonomous_system2', 'ip_autonomous_system1', 'ip_autonomous_system2',
            'mask', 'description', 'bandwidth', 'delay', 'load', ])
        # print(self.df_as)
        #        id_link  id_topology  id_link_agreement agreement  id_autonomous_system1  autonomous_system1  id_autonomous_system2  autonomous_system2  ip_autonomous_system1  ip_autonomous_system2  mask description bandwidth delay  load
        # 0           31            5                  2       p2p                     27                   2                  45118              135853               16777217               16777218    30        None      None  None  None
        # 1           32            5                  2       p2p                     27                   2                  45459              136319               16777221               16777222    30        None      None  None  None
        # 2           33            5                  1       p2c                     27                   2                  65228              327840               16777225               16777226    30        None      None  None  None

        query = 'select r.id as id_router_id, ' \
                'r.id_autonomous_system as id_autonomous_system, ' \
                'asys.autonomous_system as autonomous_system, ' \
                'r.router_id as router_id ' \
                'from router_id r, ' \
                'autonomous_system asys ' \
                'where r.id_autonomous_system = asys.id ' \
                'and asys.id_topology = %s' % self.id_topology
        result_proxy = dbsession.bind.execute(query)
        self.df_router_id = pd.DataFrame(data=result_proxy, columns=[
            'id_router_id', 'id_autonomous_system', 'autonomous_system', 'router_id'])
        self.df_router_id.set_index('autonomous_system', inplace=True)
        # print(self.df_router_id)
        #   id_router_id  id_autonomous_system  autonomous_system  router_id
        # 0        67029                 67031              65003   16843011
        # 1        67028                 67030              65002   16843010
        # 2        67027                 67029              65001   16843009

        query = 'select p.id as id_prefix, ' \
                'p.id_autonomous_system as id_autonomous_system, ' \
                'asys.autonomous_system as autonomous_system, ' \
                'p.prefix as prefix, ' \
                'p.mask as mask ' \
                'from prefix p, ' \
                'autonomous_system asys ' \
                'where p.id_autonomous_system = asys.id ' \
                'and asys.id_topology = %s' % self.id_topology
        result_proxy = dbsession.bind.execute(query)
        self.df_prefix = pd.DataFrame(data=result_proxy, columns=[
            'id_prefix', 'id_autonomous_system', 'autonomous_system', 'prefix', 'mask'])
        self.df_prefix.set_index('autonomous_system', inplace=True)

        # print(self.df_prefix)
        #    id_prefix  id_autonomous_system  autonomous_system     prefix  mask
        # 0         31                    26              65003  335544320    30
        # 1         32                    27              65002  335544324    30
        # 2         33                    28              65001  335544328    30

    def data_frames(self):
        sr_all_ases = pd.concat([self.df_as.reset_index()['autonomous_system1'],
                                 self.df_as['autonomous_system2']], ignore_index=True)
        sr_unique_as = sr_all_ases.drop_duplicates(keep='first')                                # save all unique ASes (stub and not stub)

        if self.topology_length == 'STUB':                                                      # STUB / FULL
            sr_stub = sr_all_ases.drop_duplicates(keep=False)                                   # save only stub ASes
            stub_list = list()
            for row in self.df_as.itertuples():
                if row[6] in sr_stub.values:
                    stub_list.append({'AS_stub': row[6], 'AS_parent': row[8]})
                elif row[8] in sr_stub.values:
                    stub_list.append({'AS_stub': row[8], 'AS_parent': row[6]})
            self.df_stub = pd.DataFrame(data=stub_list)
            self.df_stub.set_index('AS_stub', inplace=True)
            self.sr_unique_as = pd.concat([sr_unique_as, sr_stub]).drop_duplicates(keep=False)  # save all ASes removing stub ASes
        elif self.topology_length == 'FULL':
            self.sr_unique_as = sr_unique_as

        self.sr_unique_as = self.sr_unique_as.sort_values(ascending=True)

        # print('Number of ASes: %s' % len(self.sr_unique_as))
        # print('Number of stub ASes: %s (Number of ASes not stub: %s)\n' % (len(self.sr_stub), len(self.sr_unique_as) - len(self.sr_stub)))

    def emulation_commands(self):
        # Mininet elements
        self.list_create_mininet_elements_commands = list()
        if self.emulation_platform == 'MININET':                                                # MININET /DOCKER
            for AS in self.sr_unique_as:
                self.list_create_mininet_elements_commands.append("AS%s = net.addHost('AS%s', ip=None)" % (AS, AS))
        elif self.emulation_platform == 'DOCKER':
            for AS in self.sr_unique_as:
                self.list_create_mininet_elements_commands.append(
                    "AS%s = net.addDocker('AS%s', ip=None, dimage='alpine-quagga:latest')" % (AS, AS))

        # print(self.list_create_mininet_elements_commands)
        # AS25970 = net.addHost('AS25970', ip=None)
        # AS265702 = net.addHost('AS265702', ip=None)

        # Mininet elements links
        self.list_create_mininet_links_commands = list()
        for row in self.df_as.itertuples():
            if row[6] in self.sr_unique_as.values and \
                    row[8] in self.sr_unique_as.values:                                         # do not link stub ASes if necessary
                self.list_create_mininet_links_commands.\
                    append("net.addLink(AS%s, AS%s, intfName1='%s-%s', intfName2 = '%s-%s', "
                           "params1={'ip':'%s/%s'}, params2={'ip':'%s/%s'})" %
                           (row[6], row[8], row[6], row[8], row[8], row[6],
                            str(ipaddress.ip_address(row[9])), row[11], str(ipaddress.ip_address(row[10])), row[11]))

        # print(self.list_create_mininet_links_commands)
        # net.addLink(AS1, AS2, intfName1='1-2', intfName2='2-1', params1={'ip': '1.1.1.1/24'}, params2={'ip': '1.1.1.254/24'})
        # net.addLink(AS2, AS3, intfName1='2-3', intfName2='3-2', params1={'ip': '1.1.2.1/24'}, params2={'ip': '1.1.2.254/24'})

    def quagga_commands(self):
        """
            Quagga configuration
        """
        # zebra and bgpd
        list_create_zebra_interfaces = list()
        list_create_bgpd_neighbor = list()
        list_create_bgpd_prefix = list()
        list_create_bgpd_router_id = list()
        for row in self.df_as.itertuples():
            if row[6] in self.sr_unique_as.values and \
                    row[8] in self.sr_unique_as.values:                                         # do not link stub ASes if necessary
                # zebra
                list_create_zebra_interfaces.append(
                    {'AS': row[6], 'command': 'interface %s-%s\n  ip address %s/%s\n\n' % (
                        row[6], row[8], str(ipaddress.ip_address(row[9])), str(row[11]))})
                list_create_zebra_interfaces.append(
                    {'AS': row[8], 'command': 'interface %s-%s\n  ip address %s/%s\n\n' % (
                        row[8], row[6], str(ipaddress.ip_address(row[10])), str(row[11]))})
                # bgpd - neighbor
                list_create_bgpd_neighbor.append(
                    {'AS': row[6],
                     'command': '  neighbor %s remote-as %s\n' % (str(ipaddress.ip_address(row[10])), row[8])})
                list_create_bgpd_neighbor.append(
                    {'AS': row[8],
                     'command': '  neighbor %s remote-as %s\n' % (str(ipaddress.ip_address(row[9])), row[6])})

        # bgpd - router
        if not self.df_router_id.empty:
            for row in self.df_router_id.itertuples():
                if row[0] in self.sr_unique_as.values:                                              # do not link stub ASes if
                    list_create_bgpd_router_id.append(
                        {'AS': row[0], 'command': '  bgp router-id %s\n' % str(ipaddress.ip_address(row[3]))})

        # bgpd - network (prefix)
        for row in self.df_prefix.itertuples():
            if row[0] in self.sr_unique_as.values:                                              # do not link stub ASes if necessary
                list_create_bgpd_prefix.append({'AS': row[0], 'command': '  network %s\n' % (
                            str(ipaddress.ip_address(row[3])) + '/' + str(row[4]))})
        if self.topology_length == 'STUB':                                                      # do not link stub ASes if necessary
            df_stub_prefix = pd.concat([self.df_prefix[['prefix', 'mask']], self.df_stub.reindex(self.df_prefix.index)], axis=1, join='inner')
            df_stub_prefix = df_stub_prefix.dropna()
            for row in df_stub_prefix.itertuples():
                list_create_bgpd_prefix.append({'AS': int(row[3]), 'command': '  network %s\n' % (
                        str(ipaddress.ip_address(row[1])) + '/' + str(row[2]))})

        list_startup_zebra_commands = list()
        list_startup_bgpd_commands = list()
        for AS in self.sr_unique_as.values:
            # zebra startup commands
            list_startup_zebra_commands.append('AS%s.cmd(\'/home/minisecbgpuser/quagga-1.2.4/sbin/./zebra '
                                               '-f ./AS/%s/zebra.conf '
                                               '-z /var/run/quagga/%s.socket '
                                               '-i /var/run/quagga/zebra-%s.pid > '
                                               './log/zebra-%s.log &\')' % (AS, AS, AS, AS, AS))
            # bgpd startup commands
            list_startup_bgpd_commands.append('AS%s.cmd (\'/home/minisecbgpuser/quagga-1.2.4/sbin/./bgpd '
                                              '-f ./AS/%s/bgpd.conf '
                                              '-z /var/run/quagga/%s.socket '
                                              '-i /var/run/quagga/bgpd-%s.pid > '
                                              './log/bgpd-%s.log &\')' % (AS, AS, AS, AS, AS))

        self.df_create_zebra_interfaces = pd.DataFrame(list_create_zebra_interfaces)
        self.df_create_zebra_interfaces.set_index('AS', inplace=True)
        self.df_create_bgpd_neighbor = pd.DataFrame(list_create_bgpd_neighbor)
        self.df_create_bgpd_neighbor.set_index('AS', inplace=True)
        self.df_create_bgpd_prefix = pd.DataFrame(list_create_bgpd_prefix)
        self.df_create_bgpd_prefix.set_index('AS', inplace=True)
        self.df_create_bgpd_router_id = pd.DataFrame(list_create_bgpd_router_id)
        if not self.df_create_bgpd_router_id.empty:
            self.df_create_bgpd_router_id.set_index('AS', inplace=True)
        self.list_startup_zebra_commands = list_startup_zebra_commands
        self.list_startup_bgpd_commands = list_startup_bgpd_commands

        # -------------->> topology STUB

        # pd.set_option('display.max_rows', None)
        # pd.set_option('display.max_columns', None)
        # pd.set_option('display.width', None)
        # pd.set_option('display.max_colwidth', None)

        # print(self.df_create_zebra_interfaces)

        # AS      command
        # 65002   interface 65002-65004\n  ip address 10.0.0.9/30\n\n
        # 65004   interface 65004-65002\n  ip address 10.0.0.10/30\n\n
        # 65001   interface 65001-65003\n  ip address 10.0.0.5/30\n\n
        # 65003   interface 65003-65001\n  ip address 10.0.0.6/30\n\n
        # 65001   interface 65001-65002\n  ip address 10.0.0.1/30\n\n
        # 65002   interface 65002-65001\n  ip address 10.0.0.2/30\n\n

        # print(self.df_create_bgpd_neighbor)

        # AS        command
        # 65002     neighbor 10.0.0.10 remote-as 65004\n
        # 65004     neighbor 10.0.0.9 remote-as 65002\n
        # 65001     neighbor 10.0.0.6 remote-as 65003\n
        # 65003     neighbor 10.0.0.5 remote-as 65001\n
        # 65001     neighbor 10.0.0.2 remote-as 65002\n
        # 65002     neighbor 10.0.0.1 remote-as 65001\n

        # print(self.df_create_bgpd_prefix)
        # AS       command
        # 65004         network 27.0.0.0/24\n
        # 65003        network 113.0.0.0/24\n
        # 65003        network 112.0.0.0/24\n
        # 65003        network 111.0.0.0/24\n
        # 65003        network 110.0.0.0/24\n
        # 65002    network 222.222.222.0/30\n
        # 65001          network 66.0.0.0/8\n
        # 65001        network 100.0.0.0/24\n
        # 65001        network 200.0.0.0/24\n

        # print(self.df_create_bgpd_router_id)
        # AS       command
        # 65004    bgp router-id 1.1.1.4\n
        # 65003    bgp router-id 1.1.1.3\n
        # 65002    bgp router-id 1.1.1.2\n
        # 65001    bgp router-id 1.1.1.1\n

        # -------------->> topology STUB

        #pd.set_option('display.max_rows', None)
        #pd.set_option('display.max_columns', None)
        #pd.set_option('display.width', None)
        #pd.set_option('display.max_colwidth', None)

        # print(self.df_create_zebra_interfaces)
        # AS     command
        # 65001  interface 65001-65002\n  ip address 10.0.0.1/30\n\n
        # 65002  interface 65002-65001\n  ip address 10.0.0.2/30\n\n

        # print(self.df_create_bgpd_neighbor)
        # AS       comand
        # 65001    neighbor 10.0.0.2 remote-as 65002\n
        # 65002    neighbor 10.0.0.1 remote-as 65001\n

        # print(self.df_create_bgpd_prefix)
        # AS         command
        # 65002.0    network 222.222.222.0/30\n
        # 65001.0          network 66.0.0.0/8\n
        # 65001.0        network 100.0.0.0/24\n
        # 65001.0        network 200.0.0.0/24\n
        # 65002.0         network 27.0.0.0/24\n
        # 65001.0        network 113.0.0.0/24\n
        # 65001.0        network 112.0.0.0/24\n
        # 65001.0        network 111.0.0.0/24\n
        # 65001.0        network 110.0.0.0/24\n

        # print(self.df_create_bgpd_router_id)
        # AS       command
        # 65002    bgp router-id 1.1.1.2\n
        # 65001    bgp router-id 1.1.1.1\n

    def save_to_db(self):
        """
            Save configuration to database
        """

        # save to realistic_analysis

        # save to realistic_analysis_detail

    def write_to_file(self):
        """
            Write configuration to files
        """

        # erase previews configuration
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir + 'AS')
        os.makedirs(self.output_dir + 'log')

        # Mininet
        with open(self.output_dir + 'topology.py', 'w') as file_topology:
            with open('./minisecbgp/static/templates/mininet_begin.template', 'r') as file_to_read:
                file_topology.write(file_to_read.read())
            file_to_read.close()
            for mininet_element in self.list_create_mininet_elements_commands:
                file_topology.write(mininet_element + '\n')
            for mininet_link in self.list_create_mininet_links_commands:
                file_topology.write(mininet_link + '\n')
            with open('./minisecbgp/static/templates/mininet_middle.template', 'r') as file_to_read:
                file_topology.write(file_to_read.read())
            file_to_read.close()
            for startup_zebra_command in self.list_startup_zebra_commands:
                file_topology.write(startup_zebra_command + '\n')
            for startup_bgpd_command in self.list_startup_bgpd_commands:
                file_topology.write(startup_bgpd_command + '\n')
            with open('./minisecbgp/static/templates/mininet_end.template', 'r') as file_to_read:
                file_topology.write(file_to_read.read())
            file_to_read.close()
        file_topology.close()
        os.chmod(self.output_dir + 'topology.py', 0o755)

        for AS in self.sr_unique_as:
            os.makedirs(self.output_dir + 'AS/' + str(AS))

        # zebra.conf and bgpd.conf header
        for AS in self.sr_unique_as:
            with open(self.output_dir + 'AS/' + str(AS) + '/zebra.conf', 'w') as file_zebra:
                with open('./minisecbgp/static/templates/zebra.conf.template', 'r') as file_to_read_zebra:
                    file_zebra.write(file_to_read_zebra.read().replace('*AS*', str(AS)))
                file_to_read_zebra.close()
            with open(self.output_dir + 'AS/' + str(AS) + '/bgpd.conf', 'w') as file_bgpd:
                with open('./minisecbgp/static/templates/bgpd.conf.template', 'r') as file_to_read_bgpd:
                    file_bgpd.write(file_to_read_bgpd.read().replace('*AS*', str(AS)))
                file_to_read_bgpd.close()
            file_zebra.close()
            file_bgpd.close()

        # zebra.conf interfaces
        for row in self.df_create_zebra_interfaces.itertuples():
            with open(self.output_dir + 'AS/' + str(row[0]) + '/zebra.conf', 'a') as file_zebra:
                file_zebra.write(row[1])
            file_zebra.close()

        # bgpd.conf router ID
        for row in self.df_create_bgpd_router_id.itertuples():
            with open(self.output_dir + 'AS/' + str(row[0]) + '/bgpd.conf', 'a') as file_bgpd:
                file_bgpd.write(row[1])
            file_bgpd.close()

        # bgpd.conf neighbor
        for row in self.df_create_bgpd_neighbor.itertuples():
            with open(self.output_dir + 'AS/' + str(row[0]) + '/bgpd.conf', 'a') as file_bgpd:
                file_bgpd.write(row[1])
            file_bgpd.close()

        # bgpd.conf prefix
        for row in self.df_create_bgpd_prefix.itertuples():
            with open(self.output_dir + 'AS/' + str(row[0]) + '/bgpd.conf', 'a') as file_bgpd:
                file_bgpd.write(row[1])
            file_bgpd.close()


def parse_args(config_file):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(config_file.split())


def main(argv=sys.argv[1:]):
    try:
        opts, args = getopt.getopt(argv, "h:",
                                   ["config-file=", "realistic-analysis-name=", "topology=", "topology-length=", "topology-distribution-method=",
                                    "emulation-platform=", "router-platform="])
    except getopt.GetoptError as error:
        print('config '
              '--config-file=<pyramid config file .ini> '
              '--realistic-analysis-name=<realistic analysis name/description> '
              '--topology=<id_topology> '
              '--topology-length=<FULL|STUB> '
              '--topology-distribution-method=<CUSTOMER CONE|METIS|MANUAL|ROUND ROBIN> '
              '--emulation-platform=<MININET|DOCKER> '
              '--router-platform=<QUAGGA|BIRD>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('config '
                  '--config-file=<pyramid config file .ini> '
                  '--realistic-analysis-name=<realistic analysis name/description> '
                  '--topology=<id_topology> '
                  '--topology-length=<FULL|STUB> '
                  '--topology-distribution-method=<CUSTOMER CONE|METIS|MANUAL|ROUND ROBIN> '
                  '--emulation-platform=<MININET|DOCKER> '
                  '--router-platform=<QUAGGA|BIRD>')
            sys.exit()
        elif opt == '--config-file':
            config_file = arg
        elif opt == '--realistic-analysis-name':
            realistic_analysis_name = arg
        elif opt == '--topology':
            id_topology = arg
        elif opt == '--topology-length':
            topology_length = arg
        elif opt == '--topology-distribution-method':
            topology_distribution_method = arg
        elif opt == '--emulation-platform':
            emulation_platform = arg
        elif opt == '--router-platform':
            router_platform = arg

    args = parse_args(config_file)
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)
    try:
        ra = RealisticAnalysis(realistic_analysis_name, id_topology, topology_length, topology_distribution_method, emulation_platform)
        with env['request'].tm:
            dbsession = env['request'].dbsession
            ra.dfs_from_database(dbsession)

        ra.data_frames()

        ra.emulation_commands()

        if router_platform == 'QUAGGA':
            pass
            ra.quagga_commands()
        elif router_platform == 'BIRD':
            pass

        ra.save_to_db()

        ra.write_to_file()

    except OperationalError:
        print('Database error')
