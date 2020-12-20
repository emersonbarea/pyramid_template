import argparse
import datetime
import getopt
import json
import os
import shutil
import subprocess
import sys
import ipaddress
import time

import pandas as pd

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy import func
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
        self.output_file = '/tmp/MiniSecBGP/output/topology/%s/event_commands.MiniSecBGP' % self.topology.Topology.topology
        self.start_datetime = str(
            datetime.datetime.strptime(str(self.event_behaviour.start_datetime), '%Y-%m-%d %H:%M:%S').strftime('%s'))
        self.end_datetime = str(
            datetime.datetime.strptime(str(self.event_behaviour.end_datetime), '%Y-%m-%d %H:%M:%S').strftime('%s'))
        self.current_time = str(
            datetime.datetime.strptime(str(self.event_behaviour.start_datetime), '%Y-%m-%d %H:%M:%S').strftime('%s'))

    def dfs_from_database(self):

        # get PID from
        query = 'select e.announcer as autonomous_system ' \
                'from event e ' \
                'where e.id_event_behaviour = %s ' \
                'and e.id_type_of_event = (' \
                'select toe.id ' \
                'from type_of_event toe ' \
                'where lower(toe.type_of_event) = \'announcement\') ' \
                '' \
                'union ' \
                '' \
                'select e.withdrawer as autonomous_system ' \
                'from event e ' \
                'where e.id_event_behaviour = %s ' \
                'and e.id_type_of_event = (' \
                'select toe.id ' \
                'from type_of_event toe ' \
                'where lower(toe.type_of_event) = \'withdrawn\') ' \
                '' \
                'union ' \
                'select e.prepender as autonomous_system ' \
                'from event e ' \
                'where e.id_event_behaviour = %s ' \
                'and e.id_type_of_event = (' \
                'select toe.id ' \
                'from type_of_event toe ' \
                'where lower(toe.type_of_event) = \'prepend\');' % \
                (self.id_event_behaviour, self.id_event_behaviour, self.id_event_behaviour)
        result_proxy = self.dbsession.bind.execute(query)
        self.pid = list()
        for row in result_proxy:
            self.pid.append(row['autonomous_system'])

        # Announcement
        query = 'select e.event_datetime as event_datetime, ' \
                'e.announced_prefix as announced_prefix, ' \
                'e.announcer as announcer ' \
                'from event e ' \
                'where e.id_event_behaviour = %s ' \
                'and e.id_type_of_event = (' \
                'select toe.id ' \
                'from type_of_event toe ' \
                'where lower(toe.type_of_event) = \'announcement\');' % self.id_event_behaviour
        result_proxy = self.dbsession.bind.execute(query)
        self.df_announcement = pd.DataFrame(result_proxy, columns=['event_datetime', 'announced_prefix', 'announcer'])
        # print(self.df_announcement)
        #         event_datetime announced_prefix announcer
        # 0  2020-12-20 08:00:30    33.44.55.0/24     65001
        # 1  2020-12-20 08:01:40    55.55.55.0/24     65003
        # 2  2020-12-20 08:00:40    55.66.77.0/24     65004

        # Withdrawn
        query = 'select e.event_datetime as event_datetime, ' \
                'e.withdrawn_prefix as withdrawn_prefix, ' \
                'e.withdrawer as withdrawer ' \
                'from event e ' \
                'where e.id_event_behaviour = %s ' \
                'and e.id_type_of_event = (' \
                'select toe.id ' \
                'from type_of_event toe ' \
                'where lower(toe.type_of_event) = \'withdrawn\');' % self.id_event_behaviour
        result_proxy = self.dbsession.bind.execute(query)
        self.df_withdrawn = pd.DataFrame(result_proxy, columns=['event_datetime', 'withdrawn_prefix', 'withdrawer'])
        # print(self.df_withdrawn)
        #         event_datetime withdrawn_prefix withdrawer
        # 0  2020-12-20 08:01:00    55.66.77.0/24      65004
        # 1  2020-12-20 08:01:20    33.44.55.0/24      65002

        # Prepend
        query = 'select e.event_datetime as event_datetime, ' \
                'e.prepended as prepended, ' \
                'e.prepender as prepender, ' \
                'e.times_prepended as times_prepended ' \
                'from event e ' \
                'where e.id_event_behaviour = %s ' \
                'and e.id_type_of_event = (' \
                'select toe.id ' \
                'from type_of_event toe ' \
                'where lower(toe.type_of_event) = \'prepend\');' % self.id_event_behaviour
        result_proxy = self.dbsession.bind.execute(query)
        self.df_prepend = pd.DataFrame(result_proxy, columns=['event_datetime', 'prepended', 'prepender', 'times_prepended'])
        # print(self.df_prepend)
        #         event_datetime prepended prepender times_prepended
        # 0  2020-12-20 08:01:50     65003     65002               3

    def pid_commands(self):
        self.pid_commands_list = list()
        for pid in self.pid:
            self.pid_commands_list.append(
                'AS%s = str(os.popen(\'ps ax | grep "mininet:AS%s" | grep bash | grep -v mnexec | awk \\\'{print $1};\\\'\').read()).strip()' %
                (pid, pid))

    def announcement_commands(self):
        self.announcement_commands_list = list()
        for row in self.df_announcement.itertuples():
            self.announcement_commands_list.\
                append('    '
                       'if current_time == %s:\n'
                       '        '
                       'os.system("sudo -u minisecbgpuser sudo mnexec -a %s '
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
        self.withdrawn_commands_list = list()

    def prepend_commands(self):
        self.prepend_commands_list = list()

    def time_write_files(self):
        """
            Write configuration files to server filesystem
        """

        # erase previews configuration
        try:
            os.remove(self.output_file)
        except FileNotFoundError:
            pass

        with open(self.output_file, 'w') as file:

            # get template
            with open('./minisecbgp/static/templates/event_commands.MiniSecBGP.template', 'r') as template_file:
                file.write(template_file.read())
            template_file.close()

            # start_datetime and end_datetime
            file.write('\n\n## timers\n\nstart_datetime = %s\nend_datetime = %s\ncurrent_time = %s' %
                       (self.start_datetime, self.end_datetime, self.current_time))

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

            file.write('    time.sleep(1)\n\n    current_time = current_time + 1\n')
        file.close()

        os.chmod(self.output_file, 0o755)

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

                time_write_files = time.time()
                ed.time_write_files()
                time_write_files = time.time() - time_write_files
                save_to_database(dbsession, ['time_write_files'], [time_write_files], id_event_behaviour)
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
