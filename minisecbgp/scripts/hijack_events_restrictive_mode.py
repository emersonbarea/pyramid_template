import argparse
import datetime
import getopt
import ipaddress
import itertools
import os
import sys
import time
import json
import pandas as pd

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError, IntegrityError

from minisecbgp import models


class EventDetail(object):
    def __init__(self, dbsession, id_event_behaviour):
        self.dbsession = dbsession
        self.id_event_behaviour = id_event_behaviour
        self.topology = dbsession.query(models.Topology, models.EventBehaviour).\
            filter(models.EventBehaviour.id == self.id_event_behaviour).\
            filter(models.EventBehaviour.id_topology == models.Topology.id).first()
        self.event_behaviour = self.dbsession.query(models.EventBehaviour).\
            filter_by(id=self.id_event_behaviour).first()
        self.output_event_command_file = '/tmp/MiniSecBGP/output/topology/%s/event_commands.MiniSecBGP' % self.topology.Topology.topology
        self.output_event_monitoring_file = '/tmp/MiniSecBGP/output/topology/%s/event_monitoring.MiniSecBGP' % self.topology.Topology.topology
        self.show_exp_file = '/tmp/MiniSecBGP/output/topology/%s/show.exp' % self.topology.Topology.topology
        self.start_datetime = str(
            datetime.datetime.strptime(str(self.event_behaviour.start_datetime), '%Y-%m-%d %H:%M:%S').strftime('%s'))
        self.end_datetime = str(
            datetime.datetime.strptime(str(self.event_behaviour.end_datetime), '%Y-%m-%d %H:%M:%S').strftime('%s'))
        self.current_time = str(
            datetime.datetime.strptime(str(self.event_behaviour.start_datetime), '%Y-%m-%d %H:%M:%S').strftime('%s'))

        self.pid = list()
        self.df_announcement = pd.DataFrame()
        self.df_withdrawn = pd.DataFrame()
        self.df_prepend = pd.DataFrame()
        self.df_monitoring = pd.DataFrame()
        self.pid_commands_list = list()
        self.automatic_output_filter_rules_commands_list = list()
        self.automatic_prepend_initial_state_rules_commands_list = list()
        self.automatic_output_initial_state_rules_commands_list = list()
        self.automatic_output_event_rules_commands_list = list()
        self.automatic_prepend_event_rules_commands_list = list()
        self.announcement_commands_list = list()
        self.withdrawn_commands_list = list()
        self.prepend_commands_list = list()

    def dfs_from_database(self):

        # get PID from
        query = 'select asys.autonomous_system as autonomous_system ' \
                'from autonomous_system asys, ' \
                'event_behaviour eb ' \
                'where eb.id = %s ' \
                'and eb.id_topology = asys.id_topology;' % self.id_event_behaviour
        result_proxy = self.dbsession.bind.execute(query)

        for row in result_proxy:
            self.pid.append(row['autonomous_system'])

        # Announcement
        query = 'select a.event_datetime as event_datetime, ' \
                'a.prefix as prefix, ' \
                'a.announcer as announcer ' \
                'from event_announcement a ' \
                'where a.id_event_behaviour = %s;' % self.id_event_behaviour
        result_proxy = self.dbsession.bind.execute(query)
        self.df_announcement = pd.DataFrame(result_proxy, columns=['event_datetime', 'prefix', 'announcer'])
        # print(self.df_announcement)
        #         event_datetime           prefix  announcer
        # 0  2020-12-20 08:00:30    33.44.55.0/24     65001
        # 1  2020-12-20 08:01:40    55.55.55.0/24     65003
        # 2  2020-12-20 08:00:40    55.66.77.0/24     65004

        # Withdrawn
        query = 'select ' \
                'w.event_datetime as event_datetime, ' \
                'w.prefix as prefix, ' \
                'w.withdrawer as withdrawer, ' \
                'w.in_out as in_out, ' \
                'w.peer as peer, ' \
                '(select asys.id ' \
                'from autonomous_system asys ' \
                'where asys.id_topology = eb.id_topology ' \
                'and asys.autonomous_system = w.withdrawer) as id_withdrawer, ' \
                '(select asys.id ' \
                'from autonomous_system asys ' \
                'where asys.id_topology = eb.id_topology ' \
                'and asys.autonomous_system = w.peer) as id_peer, ' \
                'w.withdrawn::varchar(255) as withdrawn ' \
                'from event_withdrawn w, ' \
                'event_behaviour eb ' \
                'where w.id_event_behaviour = %s ' \
                'and w.id_event_behaviour = eb.id;' % self.id_event_behaviour
        result_proxy = self.dbsession.bind.execute(query)
        self.df_withdrawn = pd.DataFrame(result_proxy, columns=[
            'event_datetime', 'prefix', 'withdrawer', 'in_out', 'peer', 'id_withdrawer', 'id_peer', 'withdrawn'])
        # print(self.df_withdrawn)
        #          event_datetime             prefix  withdrawer in_out   peer  id_withdrawer  id_peer withdrawn
        # 0   2008-02-24 20:33:53    208.65.153.0/24       16467     in   2914            229      160      None
        # 1   2008-02-24 20:33:53    208.65.153.0/24       16467     in   3356            229      166      None
        # 2   2008-02-24 20:52:18    208.65.153.0/24       16034     in  16150            225      226      None
        # 3   2008-02-24 20:33:53               None        3491     in  12989            167      218     17557
        # 4   2008-02-24 21:23:34               None         174    out  24963            144      248      1916

        # Prepend
        query = 'select ' \
                'p.event_datetime as event_datetime, ' \
                'p.in_out as in_out, ' \
                'p.prefix as prefix, ' \
                'p.prepender as prepender, ' \
                'p.prepended as prepended, ' \
                'p.peer as peer, ' \
                'p.hmt as hmt, ' \
                '(select asys.id ' \
                'from autonomous_system asys ' \
                'where asys.id_topology = eb.id_topology ' \
                'and asys.autonomous_system = p.prepender) as id_prepender, ' \
                '(select asys.id ' \
                'from autonomous_system asys ' \
                'where asys.id_topology = eb.id_topology ' \
                'and asys.autonomous_system = p.prepended) as id_prepended, ' \
                '(select asys.id ' \
                'from autonomous_system asys ' \
                'where asys.id_topology = eb.id_topology ' \
                'and asys.autonomous_system = p.peer) as id_peer ' \
                'from event_prepend p, ' \
                'event_behaviour eb ' \
                'where p.id_event_behaviour = %s ' \
                'and p.id_event_behaviour = eb.id;' % self.id_event_behaviour
        result_proxy = self.dbsession.bind.execute(query)
        self.df_prepend = pd.DataFrame(result_proxy, columns=[
            'event_datetime', 'in_out', 'prefix', 'prepender', 'prepended',
            'peer', 'hmt', 'id_prepender', 'id_prepended', 'id_peer'])
        # print(self.df_prepend)
        #          event_datetime in_out  prepender  prepended     peer  hmt  id_prepender  id_prepended  id_peer
        # 0   2008-02-24 20:00:00     in       3491      17557  33970.0    2          4227          4288   4327.0
        # 1   2008-02-24 20:00:00     in       3491      17557      NaN   10          4227          4288      NaN
        # 2   2008-02-24 18:48:08    out       1299       3491  29686.0    2          4211          4227   4319.0
        # 3   2008-02-24 18:48:09    out       1299       3491  28917.0    2          4211          4227   4313.0

        # Monitoring
        query = 'select em.event_datetime as event_datetime, ' \
                'em.monitor as monitor, ' \
                'em.all as all, ' \
                'em.sleep_time ' \
                'from event_monitoring em ' \
                'where em.id_event_behaviour = %s;' % self.id_event_behaviour
        result_proxy = self.dbsession.bind.execute(query)
        monitoring_list_temp = list()
        monitoring_list = list()
        for row in result_proxy:
            if row[2]:
                query = 'select asys.autonomous_system as autonomous_system ' \
                        'from autonomous_system asys, ' \
                        'event_behaviour eb ' \
                        'where eb.id = %s ' \
                        'and eb.id_topology = asys.id_topology;' % self.id_event_behaviour
                result_proxy = self.dbsession.bind.execute(query)
                for autonomous_system in result_proxy:
                    monitoring_list_temp.append([row[0], autonomous_system[0], row[3]])
            else:
                monitoring_list_temp.append([row[0], row[1], row[3]])
            monitoring_list_temp.sort()
            monitoring_list = list(monitoring_list_temp for monitoring_list_temp, _ in itertools.groupby(monitoring_list_temp))
        self.df_monitoring = pd.DataFrame.from_records(monitoring_list, columns=['event_datetime', 'monitor', 'sleep_time'])
        print(self.df_monitoring)
        #          event_datetime  monitor  sleep_time
        # 0   2008-02-24 18:45:01      333         240
        # 1   2008-02-24 18:45:01    65001         240
        # 2   2008-02-24 18:45:01    65002         240
        # 3   2008-02-24 18:45:01    65003         240

    def pid_commands(self):
        for pid in self.pid:
            self.pid_commands_list.append(
                'AS%s = str(os.popen(\'ps ax | grep -w "mininet:AS%s" | grep bash | grep -v mnexec | awk \\\'{print $1};\\\'\').read()).strip()' %
                (pid, pid))

    def automatic_filter_rules_commands(self, file):

        # validate if IPv4 network
        def validNetworkIPv4(ip_address):
            try:
                return True if type(ipaddress.ip_network(ip_address)) is \
                               ipaddress.IPv4Network else False
            except ValueError:
                return False

        # validate if IPv4 address
        def validIPv4(ip_address):
            try:
                return True if type(ipaddress.ip_address(ip_address)) is ipaddress.IPv4Address else False
            except ValueError:
                return False

        # read json file data
        with open(file) as json_file:
            data = json.load(json_file)
        json_file.close()

        # get all peering relationship information
        all_peering_relationship = list()
        query = 'select ' \
                '(select asys.autonomous_system ' \
                'from autonomous_system asys ' \
                'where asys.id = l.id_autonomous_system1) as target_as, ' \
                '(select asys.autonomous_system ' \
                'from autonomous_system asys ' \
                'where asys.id = l.id_autonomous_system2) as peer_as, ' \
                'l.ip_autonomous_system2 as peer_ip ' \
                'from link l ' \
                'where l.id_topology = %s ' \
                'union ' \
                'select ' \
                '(select asys.autonomous_system ' \
                'from autonomous_system asys ' \
                'where asys.id = l.id_autonomous_system2) as target_as, ' \
                '(select asys.autonomous_system ' \
                'from autonomous_system asys ' \
                'where asys.id = l.id_autonomous_system1) as peer_as, ' \
                'l.ip_autonomous_system1 as peer_ip ' \
                'from link l ' \
                'where l.id_topology = %s;' % (self.topology.Topology.id, self.topology.Topology.id)
        result_proxy = self.dbsession.bind.execute(query)

        for peering_relationship in result_proxy:
            all_peering_relationship.append({'target_as': peering_relationship[0],
                                             'peer_as': peering_relationship[1],
                                             'peer_ip': peering_relationship[2],
                                             'count': 1})

        # print(all_peering_relationship)
        # return
        # [
        #   {'target_as': 65001, 'peer_as': 65002, 'peer_ip': '192.168.0.2', 'count': 1},
        #   {'target_as': 65001, 'peer_as': 65003, 'peer_ip': '192.168.0.10', 'count': 1},
        #   {'target_as': 65002, 'peer_as': 65001, 'peer_ip': '192.168.0.1', 'count': 1},
        #   {'target_as': 65002, 'peer_as': 65006, 'peer_ip': '192.168.0.6', 'count': 1}
        # ]

        #################################################
        #
        # create all automatic filter rules (output cleanup)
        #
        #################################################

        header = 'os.popen("sudo -u minisecbgpuser sudo mnexec -a %s ' \
                 '/usr/bin/python -c \\"import pexpect; ' \
                 'child = pexpect.spawn(\'telnet 0 bgpd\'); ' \
                 'child.expect(\'Password: \'); ' \
                 'child.sendline(\'en\'); ' \
                 'child.expect(\'.+>\'); ' \
                 'child.sendline(\'enable\'); ' \
                 'child.expect([\'Password: \',\'.+#\']); ' \
                 'child.sendline(\'en\'); ' \
                 'child.expect(\'.+#\'); ' \
                 'child.sendline(\'configure terminal\'); ' \
                 'child.expect(\'.+#\'); ' % '%s'

        for peering_relationship in all_peering_relationship:
            target_as = peering_relationship['target_as']
            peer_as = peering_relationship['peer_as']
            for i, row in enumerate(all_peering_relationship):
                if row['target_as'] == target_as and row['peer_as'] == peer_as:
                    peer_ip = all_peering_relationship[i]['peer_ip']
                    route_map_count = str(all_peering_relationship[i]['count'])
                    all_peering_relationship[i]['count'] = all_peering_relationship[i]['count'] + 1
            prefix_list_name = 'pl-out-deny-all-%s-%s' % (str(target_as), str(peer_as))
            prefix_list_command = 'child.sendline(\'ip prefix-list %s deny any\'); child.expect(\'.+#\');' % prefix_list_name
            as_path_name = 'ap-out-deny-all-%s-%s' % (str(target_as), str(peer_as))
            as_path_command = 'child.sendline(\'ip as-path access-list %s deny .*\'); child.expect(\'.+#\');' % as_path_name
            route_map_name = 'out-%s-%s' % (str(target_as), str(peer_as))
            route_map_command = 'child.sendline(\'route-map %s permit 1\'); child.expect(\'.+#\');' \
                                'child.sendline(\'match ip address prefix-list %s\'); child.expect(\'.+#\');' \
                                'child.sendline(\'match as-path %s\'); child.expect(\'.+#\');' \
                                'child.sendline(\'exit\'); child.expect(\'.+#\');' % \
                                (route_map_name, prefix_list_name, as_path_name)
            router_bgp_command = 'child.sendline(\'router bgp %s\'); child.expect(\'.+#\');' \
                                 'child.sendline(\'neighbor %s route-map %s out\'); child.expect(\'.+#\');' \
                                 'child.sendline(\'exit\'); child.expect(\'.+#\');' % \
                                 (str(target_as), peer_ip, route_map_name)
            clear_bpg_command = 'child.sendline(\'exit\'); child.expect(\'.+#\');' \
                                'child.sendline(\'clear bgp *\'); child.expect(\'.+#\')\\"" %s AS%s)\n' % \
                                ('%', str(target_as))

            self.automatic_output_filter_rules_commands_list.append(header +
                                                                    prefix_list_command +
                                                                    as_path_command +
                                                                    route_map_command +
                                                                    router_bgp_command +
                                                                    clear_bpg_command)

        # for output_filter_rules_commands in self.automatic_output_filter_rules_commands_list:
        #    print(output_filter_rules_commands)
        # return

        # os.popen("sudo -u minisecbgpuser sudo mnexec -a %s /usr/bin/python -c \"import pexpect; child = pexpect.spawn('telnet 0 bgpd');
        # child.expect('Password: '); child.sendline('en'); child.expect('.+>'); child.sendline('enable'); child.expect(['Password: ','.+#']);
        # child.sendline('en'); child.expect('.+#');
        # child.sendline('configure terminal'); child.expect('.+#');
        # child.sendline('ip prefix-list pl-out-deny-all-29686-3257 deny any'); child.expect('.+#');
        # child.sendline('ip as-path access-list ap-out-deny-all-29686-3257 deny .*'); child.expect('.+#');
        # child.sendline('route-map out-29686-3257 permit 1'); child.expect('.+#');
        # child.sendline('match ip address prefix-list pl-out-deny-all-29686-3257'); child.expect('.+#');
        # child.sendline('match as-path ap-out-deny-all-29686-3257'); child.expect('.+#');
        # child.sendline('exit'); child.expect('.+#');child.sendline('router bgp 29686'); child.expect('.+#');
        # child.sendline('neighbor 1.0.2.118 route-map out-29686-3257 out'); child.expect('.+#');
        # child.sendline('exit'); child.expect('.+#');
        # child.sendline('exit'); child.expect('.+#');
        # child.sendline('clear bgp *'); child.expect('.+#')\"" % AS29686)

        #################################################
        #
        # get json initial state information
        #
        #################################################

        initial_states = data['data']['initial_state']

        #################################################
        #
        # create all automatic filter rules (prepends from initial state)
        #
        #################################################

        # make prepends from initial state
        for initial_state in initial_states:
            seen = {}
            for x in initial_state['path']:
                if x not in seen:
                    seen[x] = 1
                else:
                    seen[x] += 1

            # print(seen)
            # {8331: 1, 12695: 4, 174: 1, 36561: 4}

            prepender_as = ''
            hmt = ''
            for x in seen.items():
                if prepender_as and x[1] > 1:
                    prepended_as = x[0]
                    for i in range(x[1] - 1):
                        hmt = hmt + ' ' + str(prepended_as)
                    for j, row in enumerate(all_peering_relationship):
                        if row['target_as'] == prepender_as and row['peer_as'] == prepended_as:
                            peer_ip = all_peering_relationship[j]['peer_ip']
                    route_map_name = 'in-%s-%s' % (str(prepender_as), str(prepended_as))
                    route_map_command = 'child.sendline(\'route-map %s permit 1\'); child.expect(\'.+#\');' \
                                        'child.sendline(\'set as-path prepend %s\'); child.expect(\'.+#\');' \
                                        'child.sendline(\'exit\'); child.expect(\'.+#\');' % \
                                        (route_map_name, hmt)
                    router_bgp_command = 'child.sendline(\'router bgp %s\'); child.expect(\'.+#\');' \
                                         'child.sendline(\'neighbor %s route-map %s in\'); child.expect(\'.+#\');' \
                                         'child.sendline(\'exit\'); child.expect(\'.+#\');' % \
                                         (str(prepender_as), peer_ip, route_map_name)
                    clear_bpg_command = 'child.sendline(\'exit\'); child.expect(\'.+#\');' \
                                        'child.sendline(\'clear bgp *\'); child.expect(\'.+#\')\\"" %s AS%s)\n' % \
                                        ('%', str(prepender_as))

                    self.automatic_prepend_initial_state_rules_commands_list.append(header +
                                                                                    route_map_command +
                                                                                    router_bgp_command +
                                                                                    clear_bpg_command)
                prepender_as = x[0]

        # for automatic_prepend_initial_state_rule in self.automatic_prepend_initial_state_rules_commands_list:
        #     print(automatic_prepend_rule)
        # return

        # os.popen("sudo -u minisecbgpuser sudo mnexec -a %s /usr/bin/python -c \"import pexpect; child = pexpect.spawn('telnet 0 bgpd');
        # child.expect('Password: '); child.sendline('en'); child.expect('.+>'); child.sendline('enable'); child.expect(['Password: ','.+#']);
        # child.sendline('en'); child.expect('.+#');
        # child.sendline('configure terminal'); child.expect('.+#');
        # child.sendline('route-map in-31323-3549 permit 1'); child.expect('.+#');
        # child.sendline('set as-path prepend  3549'); child.expect('.+#');
        # child.sendline('exit'); child.expect('.+#');
        # child.sendline('router bgp 3549'); child.expect('.+#');
        # child.sendline('neighbor 1.0.1.82 route-map in-31323-3549 in'); child.expect('.+#');
        # child.sendline('exit'); child.expect('.+#');
        # child.sendline('exit'); child.expect('.+#');
        # child.sendline('clear bgp *'); child.expect('.+#')\"" % AS3549)

        existing_pl_ap = list()

        #################################################
        #
        # create all automatic filter rules (permit paths from initial state)
        #
        #################################################

        for initial_state in initial_states:
            if validNetworkIPv4(initial_state['target_prefix']):
                # get source AS information
                source_as = initial_state['path'][-1]
                for i, target_as in enumerate(initial_state['path']):
                    if i + 1 <= len(initial_state['path']) - 1:
                        peer_as = initial_state['path'][i + 1]
                        for j, row in enumerate(all_peering_relationship):
                            if row['target_as'] == peer_as and row['peer_as'] == target_as:
                                route_map_entry_idx = j
                                peer_ip = all_peering_relationship[j]['peer_ip']
                                route_map_count = str(all_peering_relationship[j]['count'])
                        prefix = initial_state['target_prefix']

                        as_path = initial_state['path'][i + 2:]
                        if peer_as in as_path:
                            as_path.remove(peer_as)
                        as_path = ' '.join(map(str, as_path))
                        prefix_list_name = 'pl-out-permit-%s-%s-%s' % \
                                           (str(initial_state['target_prefix']).split('/')[0],
                                            str(initial_state['target_prefix']).split('/')[1],
                                            str(target_as) + '-' + str('-'.join(map(str, initial_state['path'][i + 1:]))))
                        prefix_list_command = ' child.sendline(\'no ip prefix-list %s deny any\'); child.expect(\'.+#\');' \
                                              ' child.sendline(\'ip prefix-list %s permit %s\'); child.expect(\'.+#\');' \
                                              ' child.sendline(\'ip prefix-list %s deny any\'); child.expect(\'.+#\');' % \
                                              (prefix_list_name,
                                               prefix_list_name,
                                               prefix,
                                               prefix_list_name)
                        if peer_as == source_as:
                            as_path_name = ''
                            as_path_command = ''
                        else:
                            as_path_name = 'ap-out-permit-%s-%s-%s' % \
                                           (str(initial_state['target_prefix']).split('/')[0],
                                            str(initial_state['target_prefix']).split('/')[1],
                                            str(target_as) + '-' + str('-'.join(map(str, initial_state['path'][i + 1:]))))
                            as_path_command = ' child.sendline(\'no ip as-path access-list %s deny .*\'); child.expect(\'.+#\');' \
                                              ' child.sendline(\'ip as-path access-list %s permit %s\'); child.expect(\'.+#\');' \
                                              ' child.sendline(\'ip as-path access-list %s deny .*\'); child.expect(\'.+#\');' % \
                                              (as_path_name,
                                               as_path_name,
                                               as_path,
                                               as_path_name)

                        route_map_name = 'out-%s-%s' % (str(peer_as), str(target_as))
                        route_map_command = ' child.sendline(\'route-map %s permit %s\'); child.expect(\'.+#\');' \
                                            ' child.sendline(\'match ip address prefix-list %s\'); child.expect(\'.+#\');' % \
                                            (route_map_name,
                                             route_map_count,
                                             prefix_list_name)
                        if peer_as == source_as:
                            route_map_command = route_map_command + \
                                                ' child.sendline(\'exit\'); child.expect(\'.+#\');'
                        else:
                            route_map_command = route_map_command + \
                                                ' child.sendline(\'match as-path %s\'); child.expect(\'.+#\');' \
                                                ' child.sendline(\'exit\'); child.expect(\'.+#\');' % as_path_name
                        router_bgp_command = ' child.sendline(\'router bgp %s\'); child.expect(\'.+#\');' \
                                             ' child.sendline(\'neighbor %s route-map %s out\'); child.expect(\'.+#\');' \
                                             ' child.sendline(\'exit\'); child.expect(\'.+#\');' % \
                                             (str(peer_as),
                                              peer_ip,
                                              route_map_name)
                        clear_bpg_command = ' child.sendline(\'exit\'); child.expect(\'.+#\');' \
                                            ' child.sendline(\'clear bgp *\'); child.expect(\'.+#\')\\"" %s AS%s)\n' % ('%', str(peer_as))

                        # print(target_as, ' | ',
                        #       peer_as, ' | ',
                        #       source_as, ' | ',
                        #       prefix, ' | ',
                        #       as_path, ' | ',
                        #       prefix_list_name, ' | ',
                        #       prefix_list_command, ' | ',
                        #       as_path_name, ' | ',
                        #       as_path_command,
                        #       route_map_name, ' | ',
                        #       route_map_command, ' | ',
                        #       router_bgp_command, ' | ',
                        #       clear_bpg_command)

                        # [22548, 8167, 1239, 36561]
                        #
                        # ----------------------------------------------------------------------------------------------------
                        # 22548  |  8167  |  36561  |  208.65.152.0/22  |  8167 1239 36561  |
                        #
                        # pl-out-208.65.152.0-22-22548-8167-1239-36561  |
                        #
                        # child.sendline('no ip prefix-list pl-out-permit-208.65.152.0-22-22548-8167-1239-36561 deny any')
                        # child.sendline('ip prefix-list pl-out-permit-208.65.152.0-22-22548-8167-1239-36561 permit 208.65.152.0/22')
                        # child.sendline('ip prefix-list pl-out-permit-208.65.152.0-22-22548-8167-1239-36561 deny any')  |
                        #
                        # ap-out-208.65.152.0-22-22548-8167-1239-36561  |
                        #
                        # child.sendline('no ip as-path access-list ap-out-permit-208.65.152.0-22-22548-8167-1239-36561 deny .*')
                        # child.sendline('ip as-path access-list ap-out-permit-208.65.152.0-22-22548-8167-1239-36561 permit 8167 1239 36561')
                        # child.sendline('ip as-path access-list ap-out-permit-208.65.152.0-22-22548-8167-1239-36561 deny .*')
                        #
                        # out-8167-22548  |
                        #
                        # child.sendline('route-map out-8167-22548 permit 2')
                        # child.sendline('match ip address prefix-list pl-out-permit-208.65.152.0-22-22548-8167-1239-36561')
                        # child.sendline('match as-path ap-out-permit-208.65.152.0-22-22548-8167-1239-36561')
                        # child.sendline('exit')  |
                        #
                        # child.sendline('router bgp 8167')
                        # child.sendline('neighbor 1.0.4.101 route-map out-8167-22548 out')
                        # child.sendline('exit')  |

                        found = False
                        if existing_pl_ap:
                            for idx, val in enumerate(existing_pl_ap):
                                if existing_pl_ap[idx]['target_as'] == peer_as and \
                                        existing_pl_ap[idx]['prefix_list_name'] == prefix_list_name and \
                                        existing_pl_ap[idx]['as_path_name'] == as_path_name or \
                                        target_as == peer_as:
                                    found = True
                            if not found:
                                existing_pl_ap.append({'target_as': peer_as,
                                                       'peer_as': target_as,
                                                       'prefix_list_name': prefix_list_name,
                                                       'as_path_name': as_path_name,
                                                       'prefix': prefix})
                                self.automatic_output_initial_state_rules_commands_list.append(header +
                                                                                               prefix_list_command +
                                                                                               as_path_command +
                                                                                               route_map_command +
                                                                                               router_bgp_command +
                                                                                               clear_bpg_command)
                                all_peering_relationship[route_map_entry_idx]['count'] = \
                                    all_peering_relationship[route_map_entry_idx]['count'] + 1
                        else:
                            existing_pl_ap.append({'target_as': peer_as,
                                                   'peer_as': target_as,
                                                   'prefix_list_name': prefix_list_name,
                                                   'as_path_name': as_path_name,
                                                   'prefix': prefix})
                            self.automatic_output_initial_state_rules_commands_list.append(header +
                                                                                           prefix_list_command +
                                                                                           as_path_command +
                                                                                           route_map_command +
                                                                                           router_bgp_command +
                                                                                           clear_bpg_command)
                            all_peering_relationship[route_map_entry_idx]['count'] = \
                                all_peering_relationship[route_map_entry_idx]['count'] + 1

        # for x in self.automatic_output_initial_state_rules_commands_list:
        #     print(x)
        # return
        #
        # os.popen("sudo -u minisecbgpuser sudo mnexec -a %s /usr/bin/python -c \"import pexpect; child = pexpect.spawn('telnet 0 bgpd');
        # child.expect('Password: '); child.sendline('en'); child.expect('.+>'); child.sendline('enable'); child.expect(['Password: ','.+#']);
        # child.sendline('en'); child.expect('.+#');
        # child.sendline('configure terminal'); child.expect('.+#');
        # child.sendline('no ip prefix-list pl-out-permit-208.65.152.0-22-3549-36561 deny any'); child.expect('.+#');
        # child.sendline('ip prefix-list pl-out-permit-208.65.152.0-22-3549-36561 permit 208.65.152.0/22'); child.expect('.+#');
        # child.sendline('ip prefix-list pl-out-permit-208.65.152.0-22-3549-36561 deny any'); child.expect('.+#');
        # child.sendline('route-map out-36561-3549 permit 27'); child.expect('.+#');
        # child.sendline('match ip address prefix-list pl-out-208.65.152.0-22-3549-36561'); child.expect('.+#');
        # child.sendline('exit'); child.expect('.+#'); child.sendline('router bgp 36561'); child.expect('.+#');
        # child.sendline('neighbor 1.0.1.177 route-map out-36561-3549 out'); child.expect('.+#');
        # child.sendline('exit'); child.expect('.+#');
        # child.sendline('exit'); child.expect('.+#');
        # child.sendline('clear bgp *'); child.expect('.+#')\"" % AS36561)

        # for x in existing_pl_ap:
        #     print(x)
        # return
        #
        # {'target_as': 174, 'peer_as': 3327, 'prefix_list_name': 'pl-out-permit-208.65.152.0-22-3327-174-36561', 'as_path_name': 'ap-out-permit-208.65.152.0-22-3327-174-36561'}
        # {'target_as': 174, 'peer_as': 6461, 'prefix_list_name': 'pl-out-permit-208.65.152.0-22-6461-174-36561', 'as_path_name': 'ap-out-permit-208.65.152.0-22-6461-174-36561'}
        # {'target_as': 3549, 'peer_as': 1280, 'prefix_list_name': 'pl-out-permit-208.65.152.0-22-1280-3549-36561', 'as_path_name': 'ap-out-permit-208.65.152.0-22-1280-3549-36561'}
        # {'target_as': 8167, 'peer_as': 22548, 'prefix_list_name': 'pl-out-permit-208.65.152.0-22-22548-8167-1239-36561', 'as_path_name': 'ap-out-permit-208.65.152.0-22-22548-8167-1239-36561'}
        # {'target_as': 1239, 'peer_as': 8167, 'prefix_list_name': 'pl-out-permit-208.65.152.0-22-8167-1239-36561', 'as_path_name': 'ap-out-permit-208.65.152.0-22-8167-1239-36561'}
        # {'target_as': 3549, 'peer_as': 19089, 'prefix_list_name': 'pl-out-permit-208.65.152.0-22-19089-3549-36561', 'as_path_name': 'ap-out-permit-208.65.152.0-22-19089-3549-36561'}
        # {'target_as': 3549, 'peer_as': 27664, 'prefix_list_name': 'pl-out-permit-208.65.152.0-22-27664-3549-36561', 'as_path_name': 'ap-out-permit-208.65.152.0-22-27664-3549-36561'}
        # {'target_as': 3549, 'peer_as': 1916, 'prefix_list_name': 'pl-out-permit-208.65.152.0-22-1916-3549-36561', 'as_path_name': 'ap-out-permit-208.65.152.0-22-1916-3549-36561'}

        #################################################
        #
        # get json events information
        #
        #################################################

        events = data['data']['events']

        #################################################
        #
        # get json sources information
        #
        #################################################

        sources = data['data']['sources']

        for event in events:

            #################################################
            #
            # create all automatic filter rules (permit paths from events)
            #
            #################################################

            if event['type'] == 'A':
                if validNetworkIPv4(event['attrs']['target_prefix']):
                    # get source AS information
                    source_as = event['attrs']['path'][-1]
                    for i, target_as in enumerate(event['attrs']['path']):
                        if i + 1 <= len(event['attrs']['path']) - 1:
                            timestamp = str(datetime.datetime.strptime(str(event['timestamp']), '%Y-%m-%dT%H:%M:%S').strftime('%s'))
                            header = '    ' \
                                     'if current_time == %s:\n' \
                                     '        ' \
                                     'os.popen("sudo -u minisecbgpuser sudo mnexec -a %s ' \
                                     '/usr/bin/python -c \\"import pexpect; ' \
                                     'child = pexpect.spawn(\'telnet 0 bgpd\'); ' \
                                     'child.expect(\'Password: \'); ' \
                                     'child.sendline(\'en\'); ' \
                                     'child.expect(\'.+>\'); ' \
                                     'child.sendline(\'enable\'); ' \
                                     'child.expect([\'Password: \',\'.+#\']); ' \
                                     'child.sendline(\'en\'); ' \
                                     'child.expect(\'.+#\'); ' \
                                     'child.sendline(\'configure terminal\'); ' \
                                     'child.expect(\'.+#\'); ' % (timestamp, '%s')
                            peer_as = event['attrs']['path'][i + 1]
                            for j, row in enumerate(all_peering_relationship):
                                if row['target_as'] == peer_as and row['peer_as'] == target_as:
                                    route_map_entry_idx = j
                                    peer_ip = all_peering_relationship[j]['peer_ip']
                                    route_map_count = str(all_peering_relationship[j]['count'])
                            prefix = event['attrs']['target_prefix']
                            as_path = event['attrs']['path'][i + 2:]
                            if peer_as in as_path:
                                as_path.remove(peer_as)
                            as_path = ' '.join(map(str, as_path))
                            prefix_list_name = 'pl-out-permit-%s-%s-%s' % \
                                               (str(event['attrs']['target_prefix']).split('/')[0],
                                                str(event['attrs']['target_prefix']).split('/')[1],
                                                str(target_as) + '-' + str('-'.join(map(str, event['attrs']['path'][i + 1:]))))
                            prefix_list_command = ' child.sendline(\'no ip prefix-list %s deny any\'); child.expect(\'.+#\');' \
                                                  ' child.sendline(\'ip prefix-list %s permit %s\'); child.expect(\'.+#\');' \
                                                  ' child.sendline(\'ip prefix-list %s deny any\'); child.expect(\'.+#\');' % \
                                                  (prefix_list_name,
                                                   prefix_list_name,
                                                   prefix,
                                                   prefix_list_name)
                            if peer_as == source_as:
                                as_path_name = ''
                                as_path_command = ''
                            else:
                                as_path_name = 'ap-out-permit-%s-%s-%s' % \
                                               (str(event['attrs']['target_prefix']).split('/')[0],
                                                str(event['attrs']['target_prefix']).split('/')[1],
                                                str(target_as) + '-' + str('-'.join(map(str, event['attrs']['path'][i + 1:]))))
                                as_path_command = ' child.sendline(\'no ip as-path access-list %s deny .*\'); child.expect(\'.+#\');' \
                                                  ' child.sendline(\'ip as-path access-list %s permit %s\'); child.expect(\'.+#\');' \
                                                  ' child.sendline(\'ip as-path access-list %s deny .*\'); child.expect(\'.+#\');' % \
                                                  (as_path_name,
                                                   as_path_name,
                                                   as_path,
                                                   as_path_name)
                            route_map_name = 'out-%s-%s' % (str(peer_as), str(target_as))
                            route_map_command = ' child.sendline(\'route-map %s permit %s\'); child.expect(\'.+#\');' \
                                                ' child.sendline(\'match ip address prefix-list %s\'); child.expect(\'.+#\');' % \
                                                (route_map_name,
                                                 route_map_count,
                                                 prefix_list_name)
                            if peer_as == source_as:
                                route_map_command = route_map_command + \
                                                    ' child.sendline(\'exit\'); child.expect(\'.+#\');'
                            else:
                                route_map_command = route_map_command + \
                                                    ' child.sendline(\'match as-path %s\'); child.expect(\'.+#\');' \
                                                    ' child.sendline(\'exit\'); child.expect(\'.+#\');' % as_path_name
                            router_bgp_command = ' child.sendline(\'router bgp %s\'); child.expect(\'.+#\');' \
                                                 ' child.sendline(\'neighbor %s route-map %s out\'); child.expect(\'.+#\');' \
                                                 ' child.sendline(\'exit\'); child.expect(\'.+#\');' % \
                                                 (str(peer_as),
                                                  peer_ip,
                                                  route_map_name)
                            clear_bpg_command = ' child.sendline(\'exit\'); child.expect(\'.+#\');' \
                                                ' child.sendline(\'clear bgp *\'); child.expect(\'.+#\')\\"" %s AS%s)\n' % \
                                                ('%', str(peer_as))

                            # print(target_as, ' | ',
                            #       peer_as, ' | ',
                            #       source_as, ' | ',
                            #       prefix, ' | ',
                            #       as_path, ' | ',
                            #       prefix_list_name, ' | ',
                            #       prefix_list_command, ' | ',
                            #       as_path_name, ' | ',
                            #       as_path_command,
                            #       route_map_name, ' | ',
                            #       route_map_command, ' | ',
                            #       router_bgp_command, ' | ',
                            #       clear_bpg_command)
                            #
                            # 9080  |  8928  |  36561  |  208.65.153.0/24  |  36561  |
                            #
                            # pl-out-208.65.153.0-24-9080-36561  |
                            #
                            # child.sendline('no ip prefix-list pl-out-permit-208.65.153.0-24-9080-36561 deny any'); child.expect('.+#');
                            # child.sendline('ip prefix-list pl-out-permit-208.65.153.0-24-9080-36561 permit 208.65.153.0/24'); child.expect('.+#');
                            # child.sendline('ip prefix-list pl-out-permit-208.65.153.0-24-9080-36561 deny any'); child.expect('.+#');  |
                            #
                            # ap-out-208.65.153.0-24-9080-36561  |
                            #
                            # child.sendline('no ip as-path access-list ap-out-permit-208.65.153.0-24-9080-36561 deny .*'); child.expect('.+#');
                            # child.sendline('ip as-path access-list ap-out-permit-208.65.153.0-24-9080-36561 permit 36561'); child.expect('.+#');
                            # child.sendline('ip as-path access-list ap-out-permit-208.65.153.0-24-9080-36561 deny .*'); child.expect('.+#');
                            #
                            # out-8928-9080  |
                            #
                            # child.sendline('route-map out-8928-9080 permit 2'); child.expect('.+#');
                            # child.sendline('match ip address prefix-list pl-out-permit-208.65.153.0-24-9080-36561'); child.expect('.+#');
                            # child.sendline('match as-path ap-out-permit-208.65.153.0-24-9080-36561'); child.expect('.+#');
                            # child.sendline('exit'); child.expect('.+#');  |
                            #
                            # child.sendline('router bgp 8928'); child.expect('.+#');
                            # child.sendline('neighbor 1.0.2.241 route-map out-8928-9080 out'); child.expect('.+#');
                            # child.sendline('exit');

                            found = False
                            if existing_pl_ap:
                                for idx, val in enumerate(existing_pl_ap):
                                    if existing_pl_ap[idx]['target_as'] == peer_as and \
                                            existing_pl_ap[idx]['prefix_list_name'] == prefix_list_name and \
                                            existing_pl_ap[idx]['as_path_name'] == as_path_name or \
                                            target_as == peer_as:
                                        found = True
                                if not found:
                                    existing_pl_ap.append({'target_as': peer_as,
                                                           'peer_as': target_as,
                                                           'prefix_list_name': prefix_list_name,
                                                           'as_path_name': as_path_name,
                                                           'prefix': prefix})
                                    self.automatic_output_event_rules_commands_list.append(header +
                                                                                           prefix_list_command +
                                                                                           as_path_command +
                                                                                           route_map_command +
                                                                                           router_bgp_command +
                                                                                           clear_bpg_command)
                                    all_peering_relationship[route_map_entry_idx]['count'] = \
                                        all_peering_relationship[route_map_entry_idx]['count'] + 1
                            else:
                                existing_pl_ap.append({'target_as': peer_as,
                                                       'peer_as': target_as,
                                                       'prefix_list_name': prefix_list_name,
                                                       'as_path_name': as_path_name,
                                                       'prefix': prefix})
                                self.automatic_output_event_rules_commands_list.append(header +
                                                                                       prefix_list_command +
                                                                                       as_path_command +
                                                                                       route_map_command +
                                                                                       router_bgp_command +
                                                                                       clear_bpg_command)
                                all_peering_relationship[route_map_entry_idx]['count'] = \
                                    all_peering_relationship[route_map_entry_idx]['count'] + 1

                # for x in self.automatic_output_event_rules_commands_list:
                #    print(x)
                #
                # if current_time == 1203889677:
                # os.popen("sudo -u minisecbgpuser sudo mnexec -a %s /usr/bin/python -c \"import pexpect; child = pexpect.spawn('telnet 0 bgpd');
                # child.expect('Password: '); child.sendline('en'); child.expect('.+>'); child.sendline('enable'); child.expect(['Password: ','.+#']);
                # child.sendline('en'); child.expect('.+#'); child.sendline('configure terminal'); child.expect('.+#');
                # child.sendline('no ip prefix-list pl-out-permit-208.65.153.0-24-29636-2914-3491-17557 deny any'); child.expect('.+#');
                # child.sendline('ip prefix-list pl-out-permit-208.65.153.0-24-29636-2914-3491-17557 permit 208.65.153.0/24'); child.expect('.+#');
                # child.sendline('ip prefix-list pl-out-permit-208.65.153.0-24-29636-2914-3491-17557 deny any'); child.expect('.+#');
                # child.sendline('no ip as-path access-list ap-out-permit-208.65.153.0-24-29636-2914-3491-17557 deny .*'); child.expect('.+#');
                # child.sendline('ip as-path access-list ap-out-permit-208.65.153.0-24-29636-2914-3491-17557 permit 3491 17557'); child.expect('.+#');
                # child.sendline('ip as-path access-list ap-out-permit-208.65.153.0-24-29636-2914-3491-17557 deny .*'); child.expect('.+#');
                # child.sendline('route-map out-2914-29636 permit 3'); child.expect('.+#');
                # child.sendline('match ip address prefix-list pl-out-permit-208.65.153.0-24-29636-2914-3491-17557'); child.expect('.+#');
                # child.sendline('match as-path ap-out-permit-208.65.153.0-24-29636-2914-3491-17557'); child.expect('.+#');
                # child.sendline('exit'); child.expect('.+#');
                # child.sendline('router bgp 2914'); child.expect('.+#');
                # child.sendline('neighbor 1.0.1.145 route-map out-2914-29636 out'); child.expect('.+#');
                # child.sendline('exit'); child.expect('.+#');
                # child.sendline('exit'); child.expect('.+#');
                # child.sendline('clear bgp *'); child.expect('.+#')\"" % AS2914)

            #################################################
            #
            # create all automatic filter rules (withdraw from events)
            #
            #################################################

            if event['type'] == 'W':

                for source in sources:
                    if validIPv4(source['ip']) and event['attrs']['source_id'] == source['id']:
                        # get all source['as_number'] peers
                        peers = list()
                        for peering_relationship in all_peering_relationship:
                            if source['as_number'] == peering_relationship['target_as']:
                                peers.append(peering_relationship['peer_as'])
                        existing_pl_ap_temp = list()
                        for idx, row in enumerate(existing_pl_ap):
                            for peer in peers:
                                if row['target_as'] == peer and \
                                        row['peer_as'] == source['as_number'] and \
                                        row['prefix'] == event['attrs']['target_prefix']:
                                    timestamp = str(datetime.datetime.strptime(str(event['timestamp']),
                                                                               '%Y-%m-%dT%H:%M:%S').strftime('%s'))
                                    command = '    ' \
                                              'if current_time == %s:\n' \
                                              '        ' \
                                              'os.popen("sudo -u minisecbgpuser sudo mnexec -a %s ' \
                                              '/usr/bin/python -c \\"import pexpect; ' \
                                              'child = pexpect.spawn(\'telnet 0 bgpd\'); ' \
                                              'child.expect(\'Password: \'); ' \
                                              'child.sendline(\'en\'); ' \
                                              'child.expect(\'.+>\'); ' \
                                              'child.sendline(\'enable\'); ' \
                                              'child.expect([\'Password: \',\'.+#\']); ' \
                                              'child.sendline(\'en\'); ' \
                                              'child.expect(\'.+#\'); ' \
                                              'child.sendline(\'configure terminal\'); ' \
                                              'child.expect(\'.+#\'); ' \
                                              'child.sendline(\'no ip prefix-list %s permit %s\'); ' \
                                              'child.expect(\'.+#\'); ' \
                                              'child.sendline(\'exit\'); child.expect(\'.+#\');' \
                                              ' child.sendline(\'clear bgp *\'); child.expect(\'.+#\')\\"" %s AS%s)\n' % \
                                              (timestamp, '%s', row['prefix_list_name'],
                                               row['prefix'], '%', row['target_as'])
                                    self.automatic_output_event_rules_commands_list.append(command)
                                    existing_pl_ap_temp.append(idx)
                        existing_pl_ap_temp.sort(reverse=True)

                        # remove existing_pl_ap row from existing_pl_ap list
                        for idx in existing_pl_ap_temp:
                            del existing_pl_ap[idx]

        #################################################
        #
        # create all automatic filter rules (prepends from events)
        #
        #################################################

        # make prepends from events
        for event in events:
            if event['type'] == 'A':
                seen = {}
                for x in event['attrs']['path']:
                    if x not in seen:
                        seen[x] = 1
                    else:
                        seen[x] += 1

                # print(seen)
                # {8331: 1, 12695: 4, 174: 1, 36561: 4}

                timestamp = str(datetime.datetime.strptime(str(event['timestamp']), '%Y-%m-%dT%H:%M:%S').strftime('%s'))
                header = '    ' \
                         'if current_time == %s:\n' \
                         '        ' \
                         'os.popen("sudo -u minisecbgpuser sudo mnexec -a %s ' \
                         '/usr/bin/python -c \\"import pexpect; ' \
                         'child = pexpect.spawn(\'telnet 0 bgpd\'); ' \
                         'child.expect(\'Password: \'); ' \
                         'child.sendline(\'en\'); ' \
                         'child.expect(\'.+>\'); ' \
                         'child.sendline(\'enable\'); ' \
                         'child.expect([\'Password: \',\'.+#\']); ' \
                         'child.sendline(\'en\'); ' \
                         'child.expect(\'.+#\'); ' \
                         'child.sendline(\'configure terminal\'); ' \
                         'child.expect(\'.+#\'); ' % (timestamp, '%s')
                prepender_as = ''
                hmt = ''
                for x in seen.items():
                    if prepender_as and x[1] > 1:
                        prepended_as = x[0]
                        for i in range(x[1] - 1):
                            hmt = hmt + ' ' + str(prepended_as)
                        for j, row in enumerate(all_peering_relationship):
                            if row['target_as'] == prepender_as and row['peer_as'] == prepended_as:
                                peer_ip = all_peering_relationship[j]['peer_ip']
                        route_map_name = 'in-%s-%s' % (str(prepender_as), str(prepended_as))
                        route_map_command = 'child.sendline(\'route-map %s permit 1\'); child.expect(\'.+#\');' \
                                            'child.sendline(\'set as-path prepend %s\'); child.expect(\'.+#\');' \
                                            'child.sendline(\'exit\'); child.expect(\'.+#\');' % \
                                            (route_map_name, hmt)
                        router_bgp_command = 'child.sendline(\'router bgp %s\'); child.expect(\'.+#\');' \
                                             'child.sendline(\'neighbor %s route-map %s in\'); child.expect(\'.+#\');' \
                                             'child.sendline(\'exit\'); child.expect(\'.+#\');' % \
                                             (str(prepender_as), peer_ip, route_map_name)
                        clear_bpg_command = 'child.sendline(\'exit\'); child.expect(\'.+#\');' \
                                            'child.sendline(\'clear bgp *\'); child.expect(\'.+#\')\\"" %s AS%s)\n' % \
                                            ('%', str(prepender_as))

                        self.automatic_prepend_event_rules_commands_list.append(header +
                                                                                route_map_command +
                                                                                router_bgp_command +
                                                                                clear_bpg_command)
                    prepender_as = x[0]

        # for automatic_prepend_event_rule in self.automatic_prepend_event_rules_commands_list:
        #     print(automatic_prepend_event_rule)
        # return

        # if current_time == 2008-02-24T18:48:13:
        # os.popen("sudo -u minisecbgpuser sudo mnexec -a %s /usr/bin/python -c \"import pexpect;
        # child = pexpect.spawn('telnet 0 bgpd'); child.expect('Password: '); child.sendline('en');
        # child.expect('.+>'); child.sendline('enable');
        # child.expect(['Password: ','.+#']); child.sendline('en'); child.expect('.+#');
        # child.sendline('configure terminal'); child.expect('.+#');
        # child.sendline('route-map in-31323-3549 permit 1'); child.expect('.+#');
        # child.sendline('set as-path prepend  3549'); child.expect('.+#');
        # child.sendline('exit'); child.expect('.+#');
        # child.sendline('router bgp 31323'); child.expect('.+#');
        # child.sendline('neighbor 1.0.1.82 route-map in-31323-3549 in'); child.expect('.+#');
        # child.sendline('exit'); child.expect('.+#');
        # child.sendline('exit'); child.expect('.+#');
        # child.sendline('clear bgp *'); child.expect('.+#')\"" % AS31323)

    def announcement_commands(self):
        for row in self.df_announcement.itertuples():
            self.announcement_commands_list.append(
                '    '
                'if current_time == %s:\n'
                '        '
                'os.popen("sudo -u minisecbgpuser sudo mnexec -a %s '
                '/usr/bin/python -c \\"import pexpect; '
                'child = pexpect.spawn(\'telnet 0 bgpd\'); '
                'child.expect(\'Password: \'); '
                'child.sendline(\'en\'); '
                'child.expect(\'.+>\'); '
                'child.sendline(\'enable\'); '
                'child.expect([\'Password: \',\'.+#\']); '
                'child.sendline(\'en\'); '
                'child.expect(\'.+#\'); '
                'child.sendline(\'configure terminal\'); '
                'child.expect(\'.+#\'); '
                'child.sendline(\'router bgp %s\'); '
                'child.expect(\'.+#\'); '
                'child.sendline(\'network %s\'); '
                'child.expect(\'.+#\')\\"" %s AS%s)\n' %
                (str(datetime.datetime.strptime(str(row[1]), '%Y-%m-%d %H:%M:%S').strftime('%s')),
                 '%s', str(row[3]), str(row[2]), '%', str(row[3])))

    def withdrawn_commands(self):
        for row in self.df_withdrawn.itertuples():
            query = 'select l.ip_autonomous_system2 as ip_prepended ' \
                    'from link l ' \
                    'where l.id_autonomous_system1 = %s ' \
                    'and l.id_autonomous_system2 = %s ' \
                    'union ' \
                    'select l.ip_autonomous_system1 as ip_prepended ' \
                    'from link l ' \
                    'where l.id_autonomous_system1 = %s ' \
                    'and l.id_autonomous_system2 = %s;' % \
                    (str(row[6]), str(row[7]), str(row[7]), str(row[6]))
            result_proxy = self.dbsession.bind.execute(query)

            for ip in result_proxy:
                ip_peer = ip[0]

            list_commands = ''
            if row[2]:  # if prefix
                list_commands = list_commands + \
                                ' child.sendline(\'no ip prefix-list pl-in-deny-%s-%s-%s permit any\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'ip prefix-list pl-in-deny-%s-%s-%s deny %s\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'ip prefix-list pl-in-deny-%s-%s-%s permit any\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'route-map %s-%s-%s permit 10\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'match ip address prefix-list pl-in-deny-%s-%s-%s\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'exit\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'router bgp %s\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'neighbor %s route-map %s-%s-%s %s\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'exit\'); ' \
                                'child.expect(\'.+#\'); ' % \
                                (str(row[4]), str(row[3]), str(row[5]),
                                 str(row[4]), str(row[3]), str(row[5]), str(row[2]),
                                 str(row[4]), str(row[3]), str(row[5]),
                                 str(row[4]), str(row[3]), str(row[5]),
                                 str(row[4]), str(row[3]), str(row[5]),
                                 str(row[3]),
                                 str(ip_peer), str(row[4]), str(row[3]), str(row[5]), str(row[4]))
            elif row[4]:  # if AS source
                list_commands = list_commands + \
                                ' child.sendline(\'no ip as-path access-list as-path-%s-%s-%s permit .*\'); ' \
                                'child.expect(\'.+#\');' \
                                ' child.sendline(\'ip as-path access-list as-path-%s-%s-%s deny _%s$\'); ' \
                                'child.expect(\'.+#\');' \
                                ' child.sendline(\'ip as-path access-list as-path-%s-%s-%s permit .*\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'route-map %s-%s-%s permit 10\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'match as-path as-path-%s-%s-%s\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'exit\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'router bgp %s\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'neighbor %s route-map %s-%s-%s %s\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'exit\'); ' \
                                'child.expect(\'.+#\'); ' % \
                                (str(row[4]), str(row[3]), str(row[5]),
                                 str(row[4]), str(row[3]), str(row[5]), str(row[8]),
                                 str(row[4]), str(row[3]), str(row[5]),
                                 str(row[4]), str(row[3]), str(row[5]),
                                 str(row[4]), str(row[3]), str(row[5]),
                                 str(row[3]),
                                 str(ip_peer), str(row[4]), str(row[3]), str(row[5]), str(row[4]))

            self.withdrawn_commands_list.append(
                '    '
                'if current_time == %s:\n'
                '        '
                'os.popen("sudo -u minisecbgpuser sudo mnexec -a %s '
                '/usr/bin/python -c \\"import pexpect; '
                'child = pexpect.spawn(\'telnet 0 bgpd\'); '
                'child.expect(\'Password: \'); '
                'child.sendline(\'en\'); '
                'child.expect(\'.+>\'); '
                'child.sendline(\'enable\'); '
                'child.expect([\'Password: \',\'.+#\']); '
                'child.sendline(\'en\'); '
                'child.expect(\'.+#\'); '
                'child.sendline(\'configure terminal\'); '
                'child.expect(\'.+#\'); '
                '%s'
                'child.sendline(\'exit\'); '
                'child.expect(\'.+#\'); '
                'child.sendline(\'clear ip bgp *\'); '
                'child.expect(\'.+#\')\\"" %s AS%s)\n' %
                (str(datetime.datetime.strptime(str(row[1]), '%Y-%m-%d %H:%M:%S').strftime('%s')),
                 '%s', list_commands, '%', str(row[3])))

    def prepend_commands(self):
        for row in self.df_prepend.itertuples():
            # get the IP address of the Prepended AS interface of the link with the AS Prepender
            query = 'select l.ip_autonomous_system2 as ip_prepended ' \
                    'from link l ' \
                    'where l.id_autonomous_system1 = %s ' \
                    'and l.id_autonomous_system2 = %s ' \
                    'union ' \
                    'select l.ip_autonomous_system1 as ip_prepended ' \
                    'from link l ' \
                    'where l.id_autonomous_system1 = %s ' \
                    'and l.id_autonomous_system2 = %s;' % \
                    (str(row[7]), str(row[8]), str(row[8]), str(row[7]))
            result_proxy = self.dbsession.bind.execute(query)
            route_map_commands = ''
            for internal_row in result_proxy:
                route_map_commands = route_map_commands + \
                                     ' child.sendline(\'neighbor %s route-map %s-%s-%s %s\'); ' \
                                     'child.expect(\'.+#\');' % \
                                     (str(list(internal_row)[0]), str(row[2]), str(row[3]), str(row[5]), str(row[2]))

                hmt_list = ''
                for hmt in range(row[6]):
                    hmt_list = hmt_list + ' %s' % str(row[4])

                self.prepend_commands_list.append(
                    '    '
                    'if current_time == %s:\n'
                    '        '
                    'os.popen("sudo -u minisecbgpuser sudo mnexec -a %s '
                    '/usr/bin/python -c \\"import pexpect; '
                    'child = pexpect.spawn(\'telnet 0 bgpd\'); '
                    'child.expect(\'Password: \'); '
                    'child.sendline(\'en\'); '
                    'child.expect(\'.+>\'); '
                    'child.sendline(\'enable\'); '
                    'child.expect([\'Password: \',\'.+#\']); '
                    'child.sendline(\'en\'); '
                    'child.expect(\'.+#\'); '
                    'child.sendline(\'configure terminal\'); '
                    'child.expect(\'.+#\'); '
                    'child.sendline(\'route-map %s-%s-%s permit 1\'); '
                    'child.expect(\'.+#\'); '
                    'child.sendline(\'set as-path prepend %s\'); '
                    'child.expect(\'.+#\'); '
                    'child.sendline(\'exit\'); '
                    'child.expect(\'.+#\'); '
                    'child.sendline(\'router bgp %s\'); '
                    'child.expect(\'.+#\'); '
                    '%s'
                    ' child.sendline(\'exit\'); '
                    'child.expect(\'.+#\'); '
                    'child.sendline(\'exit\'); '
                    'child.expect(\'.+#\'); '
                    'child.sendline(\'clear ip bgp *\'); '
                    'child.expect(\'.+#\')\\"" %s AS%s)\n' %
                    (str(datetime.datetime.strptime(str(row[1]),'%Y-%m-%d %H:%M:%S').strftime('%s')), '%s', str(row[2]),
                     str(row[3]), str(row[5]), hmt_list, str(row[3]), route_map_commands, '%', str(row[3])))

    def time_write_config_files(self):
        """
            Write configuration files to server filesystem
        """

        # erase previews configuration
        try:
            os.remove(self.output_event_command_file)
        except FileNotFoundError:
            pass

        with open(self.output_event_command_file, 'w') as file:

            # get template
            with open('./minisecbgp/static/templates/event_commands.MiniSecBGP_1.template', 'r') as template_file:
                file.write(template_file.read())
            template_file.close()

            # start_datetime and end_datetime
            file.write('\n\n## timers\n\nstart_datetime = %s\nend_datetime = %s\ncurrent_time = %s' %
                       (self.start_datetime, self.end_datetime, self.current_time))

            # PID
            file.write('\n\n## get Mininet nodes PID\n\n')
            for pid_command in self.pid_commands_list:
                file.write(pid_command + '\n')

            # Automatic output filter rules
            file.write('\n## Automatic output filter rules\n\n')
            for automatic_output_filter_rule in self.automatic_output_filter_rules_commands_list:
                file.write(automatic_output_filter_rule + '\n')

            # Automatic prepend rules
            file.write('\n## Automatic prepend rules\n\n')
            for automatic_prepend_initial_state_rule in self.automatic_prepend_initial_state_rules_commands_list:
                file.write(automatic_prepend_initial_state_rule + '\n')

            # Automatic output initial state rules
            file.write('\n## Automatic output initial state rules\n\n')
            for automatic_output_initial_state_rule in self.automatic_output_initial_state_rules_commands_list:
                file.write(automatic_output_initial_state_rule + '\n')

            # delay to wait for all BGP convergence time
            file.write('\n\n## delay to wait for all BGP convergence time\n\n')
            file.write('time.sleep(120)\n')

            # get template
            with open('./minisecbgp/static/templates/event_commands.MiniSecBGP_2.template', 'r') as template_file:
                file.write(template_file.read())
            template_file.close()

            # starting monitoring process
            file.write('\n\n## starting monitoring process\n\n')
            file.write('subprocess.Popen([\'./event_monitoring.MiniSecBGP\'])\n')

            # timer loop begin
            file.write('\n\n## events\n\n')
            file.write('while current_time != %s:\n' % self.end_datetime)

            # Automatic output event rules
            file.write('\n    ## Automatic output event rules\n\n')
            for automatic_output_event_rule in self.automatic_output_event_rules_commands_list:
                file.write(automatic_output_event_rule + '\n')

            # Announcements
            file.write('\n    ## Announcements\n\n')
            for announcement_command in self.announcement_commands_list:
                file.write(announcement_command + '\n')

#            # Withdrawn
#            file.write('\n    ## Withdrawns\n\n')
#            for withdrawn_command in self.withdrawn_commands_list:
#                file.write(withdrawn_command + '\n')

#            # Prepends
#            file.write('\n    ## Prepends\n\n')
#            for prepend_command in self.prepend_commands_list:
#                file.write(prepend_command + '\n')

            # Automatic prepend event rules
            file.write('\n## Automatic prepend event rules\n\n')
            for automatic_prepend_event_rule in self.automatic_prepend_event_rules_commands_list:
                file.write(automatic_prepend_event_rule + '\n')

            file.write('    time.sleep(1)\n\n    current_time = current_time + 1\n')

            # get template
            with open('./minisecbgp/static/templates/event_commands.MiniSecBGP_3.template', 'r') as template_file:
                file.write(template_file.read())
            template_file.close()

        file.close()

        os.chmod(self.output_event_command_file, 0o755)

    def monitoring_commands(self):
        self.monitoring_commands_list = list()
        for row in self.df_monitoring.itertuples():
#            self.monitoring_commands_list.append(
#                '    '
#                'if current_time == %s:\n'
#                '        '
#                'os.popen("sudo -u minisecbgpuser sudo mnexec -a %s '
#                '/usr/bin/python -c \\"import pexpect; '
#                'child = pexpect.spawn(\'telnet 0 bgpd\'); '
#                'child.expect(\'Password: \'); '
#                'child.sendline(\'en\'); '
#                'child.expect(\'.+>\'); '
#                'child.sendline(\'enable\'); '
#                'child.expect([\'Password: \',\'.+#\']); '
#                'child.sendline(\'en\'); '
#                'child.expect(\'.+#\'); '
#                'child.sendline(\'show ip bgp\'); '
#                'child.expect(\'.+#\'); '
#                'print(\'-->Monitoring Datetime:%s\'); '
#                'print(child.after)\\" >> log/monitoring_%s.log" %s AS%s)\n'
#                '\n'
#                '' %
#                (str(datetime.datetime.strptime(str(row[1]), '%Y-%m-%d %H:%M:%S').strftime('%s')),
#                 '%s', str(datetime.datetime.strptime(str(row[1]), '%Y-%m-%d %H:%M:%S').strftime('%s')),
#                 str(row[2]), '%', str(row[2])))

            self.monitoring_commands_list.append(
                '    '
                'if current_time == %s:\n'
                '        '
                'os.popen("sudo -u minisecbgpuser sudo mnexec -a %s '
                '-- sh -c \'echo \\"\\n-->current_time:%s\\" >> log/monitor-%s.log; '
                './show.exp >> log/monitor-%s.log &\'" %s AS%s)\n'
                '\n'
                '' %
                (str(datetime.datetime.strptime(str(row[1]), '%Y-%m-%d %H:%M:%S').strftime('%s')), '%s',
                 str(datetime.datetime.strptime(str(row[1]), '%Y-%m-%d %H:%M:%S').strftime('%s')),
                 str(row[2]), str(row[2]), '%', str(row[2])))

    def time_write_monitoring_files(self):
        """
            Write monitoring files to server filesystem
        """

        # erase previews configuration
        try:
            os.remove(self.output_event_monitoring_file)
        except FileNotFoundError:
            pass

        with open(self.show_exp_file, 'w') as file:

            # get template
            with open('./minisecbgp/static/templates/show.exp.template', 'r') as template_file:
                file.write(template_file.read())
            template_file.close()

        file.close()
        os.chmod(self.show_exp_file, 0o755)

        with open(self.output_event_monitoring_file, 'w') as file:

            # get template
            with open('./minisecbgp/static/templates/event_monitoring.MiniSecBGP_1.template', 'r') as template_file:
                file.write(template_file.read())
            template_file.close()

            # current_time for loop
            file.write('\n\n## timers\n\ncurrent_time = %s' % self.current_time)

            # PID
            file.write('\n\n## get Mininet nodes PID\n\n')
            for pid_command in self.pid_commands_list:
                file.write(pid_command + '\n')

            # timer loop begin
            file.write('\n\n## events\n\n')
            file.write('while current_time != %s:\n' % self.end_datetime)

            # Monitoring
            file.write('\n    ## Monitoring\n\n')
            for monitoring_command in self.monitoring_commands_list:
                file.write(monitoring_command + '\n')

            file.write('    time.sleep(1)\n\n    current_time = current_time + 1\n')

        file.close()
        os.chmod(self.output_event_monitoring_file, 0o755)

    @staticmethod
    def downloading(dbsession, downloading):
        entry = dbsession.query(models.DownloadingTopology).first()
        entry.downloading = downloading


def save_to_database(dbsession, field, value, id_event_behaviour):
    try:
        for i in range(len(field)):
            update = 'update event_detail set %s = \'%s\' where id_event_behaviour = %s' % (field[i], str(value[i]), id_event_behaviour)
            dbsession.bind.execute(update)
            dbsession.flush()
    except Exception as error:
        dbsession.rollback()
        print(error)


def parse_args(config_file):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(config_file.split())


def main(argv=sys.argv[1:]):
    try:
        opts, args = getopt.getopt(argv, "h", ["config-file=", "id-event-behaviour="])
    except getopt.GetoptError:
        print('\n'
              'Usage: MiniSecBGP_hijack_events [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
              '--id-event-behaviour=<id_event_behaviour>        event behaviour ID\n')
        sys.exit(2)
    config_file = id_event_behaviour = ''
    for opt, arg in opts:
        if opt == '-h':
            print('\n'
                  'Usage: MiniSecBGP_hijack_events [options]\n'
                  '\n'
                  'options (with examples):\n'
                  '\n'
                  '-h                                               this help\n'
                  '\n'
                  '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
                  '--id-event-behaviour=<id_event_behaviour>        event behaviour ID\n')
            sys.exit()
        elif opt == '--config-file':
            config_file = arg
        elif opt == '--id-event-behaviour':
            id_event_behaviour = arg
    if config_file and id_event_behaviour:
        args = parse_args(config_file)
        setup_logging(args.config_uri)
        env = bootstrap(args.config_uri)
        try:
            with env['request'].tm:
                dbsession = env['request'].dbsession
                ed = EventDetail(dbsession, id_event_behaviour)

                time_get_data = time.time()
                ed.dfs_from_database()
                time_get_data = time.time() - time_get_data
                save_to_database(dbsession, ['time_get_data'], [time_get_data], id_event_behaviour)

                time_pid_commands = time.time()
                ed.pid_commands()
                time_pid_commands = time.time() - time_pid_commands
                save_to_database(dbsession, ['time_pid_commands'], [time_pid_commands], id_event_behaviour)

                file = '/home/tocha/Documentos/projetos/MiniSecBGP/minisecbgp/static/topology/Youtube_vs_Pakistan_Telecom.BGPlay'
                ed.automatic_filter_rules_commands(file)

                time_announcement_commands = time.time()
                ed.announcement_commands()
                time_announcement_commands = time.time() - time_announcement_commands
                save_to_database(dbsession, ['time_announcement_commands'], [time_announcement_commands], id_event_behaviour)

                time_withdrawn_commands = time.time()
                ed.withdrawn_commands()
                time_withdrawn_commands = time.time() - time_withdrawn_commands
                save_to_database(dbsession, ['time_withdrawn_commands'], [time_withdrawn_commands], id_event_behaviour)

                time_prepends_commands = time.time()
                ed.prepend_commands()
                time_prepends_commands = time.time() - time_prepends_commands
                save_to_database(dbsession, ['time_prepends_commands'], [time_prepends_commands], id_event_behaviour)

                time_write_config_files = time.time()
                ed.time_write_config_files()
                time_write_config_files = time.time() - time_write_config_files
                save_to_database(dbsession, ['time_write_config_files'], [time_write_config_files], id_event_behaviour)

                time_monitoring_commands = time.time()
                ed.monitoring_commands()
                time_monitoring_commands = time.time() - time_monitoring_commands
                save_to_database(dbsession, ['time_monitoring_commands'], [time_monitoring_commands], id_event_behaviour)

                time_write_monitoring_files = time.time()
                ed.time_write_monitoring_files()
                time_write_monitoring_files = time.time() - time_write_monitoring_files
                save_to_database(dbsession, ['time_write_monitoring_files'], [time_write_monitoring_files], id_event_behaviour)

        except OperationalError:
            print('Database error')
    else:
        print('\n'
              'Usage: MiniSecBGP_hijack_events [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
              '--id-event-behaviour=<id_event_behaviour>        event behaviour ID\n')