import argparse
import datetime
import getopt
import itertools
import os
import sys
import time
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
        self.pid_commands_list = list()
        self.announcement_commands_list = list()
        self.withdrawn_commands_list = list()
        self.prepend_commands_list = list()
        self.monitoring_commands_list = list()
        self.monitoring_current_times_list = list()
        self.monitor_command = ''

    def dfs_from_database(self):

        # get PID from
        query = 'select em.all as all ' \
                'from event_monitoring em ' \
                'where em.id_event_behaviour = %s ' \
                'and em.all = True;' % self.id_event_behaviour
        result_proxy = self.dbsession.bind.execute(query)
        all_autonomous_systems = False
        for row in result_proxy:
            all_autonomous_systems = row[0]

        if not all_autonomous_systems:
            query = 'select a.announcer as autonomous_system ' \
                    'from event_announcement a ' \
                    'where a.id_event_behaviour = %s ' \
                    'union ' \
                    'select w.withdrawer as autonomous_system ' \
                    'from event_withdrawn w ' \
                    'where w.id_event_behaviour = %s ' \
                    'union ' \
                    'select p.prepender as autonomous_system ' \
                    'from event_prepend p ' \
                    'where p.id_event_behaviour = %s ' \
                    'union ' \
                    'select m.monitor as autonomous_system ' \
                    'from event_monitoring m ' \
                    'where m.id_event_behaviour = %s; ' % \
                    (self.id_event_behaviour, self.id_event_behaviour,
                     self.id_event_behaviour, self.id_event_behaviour)
            result_proxy = self.dbsession.bind.execute(query)
        else:
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
            'event_datetime', 'in_out', 'prepender', 'prepended', 'peer', 'hmt', 'id_prepender', 'id_prepended', 'id_peer'])
        # print(self.df_prepend)
        #          event_datetime in_out  prepender  prepended     peer  hmt  id_prepender  id_prepended  id_peer
        # 0   2008-02-24 20:00:00     in       3491      17557  33970.0    2          4227          4288   4327.0
        # 1   2008-02-24 20:00:00     in       3491      17557      NaN   10          4227          4288      NaN
        # 2   2008-02-24 18:48:08    out       1299       3491  29686.0    2          4211          4227   4319.0
        # 3   2008-02-24 18:48:09    out       1299       3491  28917.0    2          4211          4227   4313.0

        # Monitoring
        monitoring_current_times_list_temp = list()
        query = 'select em.event_datetime as event_datetime, ' \
                'em.monitor as monitor, ' \
                'em.all as all ' \
                'from event_monitoring em ' \
                'where em.id_event_behaviour = %s;' % self.id_event_behaviour
        result_proxy = self.dbsession.bind.execute(query)
        monitoring_list_temp = list()
        monitoring_list = list()
        for row in result_proxy:

            monitoring_current_times_list_temp.append(
                str(datetime.datetime.strptime(str(row[0]), '%Y-%m-%d %H:%M:%S').strftime('%s')))

            if row[2]:
                query = 'select asys.autonomous_system as autonomous_system ' \
                        'from autonomous_system asys, ' \
                        'event_behaviour eb ' \
                        'where eb.id = %s ' \
                        'and eb.id_topology = asys.id_topology;' % self.id_event_behaviour
                result_proxy = self.dbsession.bind.execute(query)
                for autonomous_system in result_proxy:
                    monitoring_list_temp.append([row[0], autonomous_system[0]])
            else:
                monitoring_list_temp.append([row[0], row[1]])
            monitoring_list_temp.sort()
            monitoring_list = list(monitoring_list_temp for monitoring_list_temp, _ in itertools.groupby(monitoring_list_temp))
        self.df_monitoring = pd.DataFrame.from_records(monitoring_list, columns=['event_datetime', 'monitor'])
        # print(self.df_monitoring)
        #          event_datetime  monitor  sleep_time
        # 0   2008-02-24 18:45:01      333         240
        # 1   2008-02-24 18:45:01    65001         240
        # 2   2008-02-24 18:45:01    65002         240
        # 3   2008-02-24 18:45:01    65003         240

        self.monitoring_current_times_list = sorted(list(set(monitoring_current_times_list_temp)))
        # print(self.monitoring_current_times_list)
        # ['1203889500', '1203890433', '1203890550', '1203891366', '1203891600', '1203892299', '1203892650', '1203893232']

    def pid_commands(self):
        for pid in self.pid:
            self.pid_commands_list.append(
                'AS%s = str(os.popen(\'ps ax | grep -w "mininet:AS%s" | grep bash | grep -v mnexec | awk \\\'{print $1};\\\'\').read()).strip()' %
                (pid, pid))

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
                                ' child.sendline(\'no ip prefix-list prefix-list-%s-%s-%s permit any\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'ip prefix-list prefix-list-%s-%s-%s deny %s\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'ip prefix-list prefix-list-%s-%s-%s permit any\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'route-map %s-%s-%s permit 10\'); ' \
                                'child.expect(\'.+#\'); ' \
                                'child.sendline(\'match ip address prefix-list prefix-list-%s-%s-%s\'); ' \
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
                'child.sendline(\'clear ip bgp * soft\'); '
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
                    'child.sendline(\'route-map %s-%s-%s permit 10\'); '
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
                    'child.sendline(\'clear ip bgp * soft\'); '
                    'child.expect(\'.+#\')\\"" %s AS%s)\n' %
                    (str(datetime.datetime.strptime(str(row[1]),'%Y-%m-%d %H:%M:%S').strftime('%s')), '%s', str(row[2]),
                     str(row[3]), str(row[5]), hmt_list, str(row[3]), route_map_commands, '%', str(row[3])))

    def monitoring_commands(self):
        for current_time in self.monitoring_current_times_list:
            self.monitoring_commands_list.append(
                '    '
                'if current_time == %s:\n'
                '        time.sleep(%s)\n'
                '        os.popen("./event_monitoring.MiniSecBGP %s")\n'
                '        time.sleep(60)\n' %
                (current_time, '240', current_time))

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

            # get template
            with open('./minisecbgp/static/templates/event_commands.MiniSecBGP_2.template', 'r') as template_file:
                file.write(template_file.read())
            template_file.close()

            # PID
            file.write('\n\n## get Mininet nodes PID\n\n')
            for pid_command in self.pid_commands_list:
                file.write(pid_command + '\n')

            # timer loop begin
            file.write('\n\n## events\n\n')
            file.write('while current_time != %s:\n' % self.end_datetime)

            # Announcements
            file.write('\n    ## Announcements\n\n')
            for announcement_command in self.announcement_commands_list:
                file.write(announcement_command + '\n')

            # Withdrawn
            file.write('\n    ## Withdrawns\n\n')
            for withdrawn_command in self.withdrawn_commands_list:
                file.write(withdrawn_command + '\n')

            # Prepends
            file.write('\n    ## Prepends\n\n')
            for prepend_command in self.prepend_commands_list:
                file.write(prepend_command + '\n')

            # Monitoring
            file.write('\n    ## Monitoring\n\n')
            for monitoring_command in self.monitoring_commands_list:
                file.write(monitoring_command + '\n')

            file.write('    time.sleep(1)\n\n    current_time = current_time + 1\n')

            # get template
            with open('./minisecbgp/static/templates/event_commands.MiniSecBGP_3.template', 'r') as template_file:
                file.write(template_file.read())
            template_file.close()

        file.close()

        os.chmod(self.output_event_command_file, 0o755)

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

            # PID
            file.write('\n\n        ## get Mininet nodes PID\n\n')
            for pid_command in self.pid_commands_list:
                file.write('        ' + pid_command + '\n')

            # Monitoring
            file.write('\n        ## Monitoring\n\n')
            for monitoring_current_time in self.monitoring_current_times_list:
                file.write('\n        if self.timestamp == %s:\n' % monitoring_current_time)
                for row in self.df_monitoring.itertuples():
                    if str(datetime.datetime.strptime(str(row[1]),'%Y-%m-%d %H:%M:%S').strftime('%s')) == monitoring_current_time:
                        file.write('            os.popen("sudo -u minisecbgpuser sudo mnexec -a %s -- sh -c \'echo \\"\\n-->current_time:%s\\" >> log/monitor-%s.log; ./show.exp >> log/monitor-%s.log &\'" %s (AS%s, self.timestamp))\n' % ('%s', '%s', row[2], row[2], '%', row[2]))

            # get template
            with open('./minisecbgp/static/templates/event_monitoring.MiniSecBGP_2.template', 'r') as template_file:
                file.write(template_file.read())
            template_file.close()

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

                time_monitoring_commands = time.time()
                ed.monitoring_commands()
                time_monitoring_commands = time.time() - time_monitoring_commands
                save_to_database(dbsession, ['time_monitoring_commands'], [time_monitoring_commands], id_event_behaviour)

                time_write_config_files = time.time()
                ed.time_write_config_files()
                time_write_config_files = time.time() - time_write_config_files
                save_to_database(dbsession, ['time_write_config_files'], [time_write_config_files], id_event_behaviour)

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