#!/usr/bin/python3
import copy
import sys
import os
import json
import ipaddress

from datetime import datetime

import pandas as pd


class Parser(object):
    def __init__(self, argv0, argv1):

        self.config_directory = argv0 + '/AS/'
        self.log_directory = argv0 + '/log/'
        self.file_from = argv1
        self.log_files = list()
        self.monitor_files = list()
        self.sources = list()
        self.id_sources = list()
        self.nodes = list()
        self.others = list()

        # read BGPlay json file and parse it
        try:
            with open(self.file_from) as file:
                self.data_from = json.load(file)
        except Exception as error:
            print(error)
        finally:
            file.close()

    def read_file(self, path, file):
        try:
            with open(path + '/' + file, 'r') as opened_file:
                data = opened_file.read()
        except Exception as error:
            print(error)
        finally:
            opened_file.close()
            return data

    def number_of_autonomous_system_from_json(self):
        def validIPv4(ip_address):
            try:
                return True if type(ipaddress.ip_address(ip_address)) is ipaddress.IPv4Address else False
            except ValueError:
                return False

        try:
            nodes = self.data_from['data']['nodes']
            sources = self.data_from['data']['sources']

            for source in sources:
                if validIPv4(source['id'].split('-')[1]):
                    self.sources.append(source['as_number'])
                    self.id_sources.append({'id_source': source['id'], 'source': source['as_number']})

                    print(str(source['as_number']) + ',' + str(source['id']))

            sources = set(self.sources)

            for node in nodes:
                self.nodes.append(node['as_number'])
            nodes = set(self.nodes)

            self.others = list(nodes - sources)

            self.sources = list(sources)
            self.nodes = list(nodes)

        except Exception as error:
            print(error)
        else:
            print('\nTotal number of Nodes: %s' % len(self.nodes))  # Total number of Nodes: 136
            print('Total number of Sources: %s' % len(self.sources))  # Total number of Sources: 85

    def clear_log_files(self):
        for other in self.others:
            try:
                os.remove(self.log_directory + 'bgpd-%s.log' % other)
                os.remove(self.log_directory + 'zebra-%s.log' % other)
                os.remove(self.log_directory + 'monitor-%s.log' % other)
            except FileNotFoundError:
                pass

    def list_log_files(self):
        for file in os.listdir(self.log_directory):
            if file.startswith('bgp'):
                self.log_files.append(file)

        for file in os.listdir(self.log_directory):
            if file.startswith('monitor'):
                self.monitor_files.append(file)

    def adjacency_time_from_log_file(self):
        try:
            for file in self.log_files:
                data = self.read_file(self.log_directory, file)
                start_time = False
                peer_list = list()
                for line in data.splitlines():

                    # get file start_time
                    if not start_time:
                        start_time = datetime.timestamp(
                            datetime.strptime(str(line.split('BGP:')[0])[:-3], '%Y/%m/%d %H:%M:%S.%f'))

                    # get last "%ADJCHANGE: neighbor ... Up" event before hijack
                    if '%ADJCHANGE: neighbor ' in line and line.endswith('Up'):
                        peer = line.split()[-2]
                        if peer not in peer_list:
                            peer_list.append(peer)
                            last_adjacency_time = datetime.timestamp(
                                datetime.strptime(str(line.split('BGP:')[0])[:-3], '%Y/%m/%d %H:%M:%S.%f'))

                # print the BGP adjacency time per AS
                print('%s,%s' % (file.split('-')[1].split('.')[0], str(last_adjacency_time - start_time)))

        except Exception as error:
            print(error)

    def original_convergence_time_for_prefix_from_log_file(self, data):
        try:
            for prefix, prefix_hijacker in data:
                for file in self.log_files:
                    data = self.read_file(self.log_directory, file)
                    start_time = False
                    peer_list = list()
                    last_route_add_event = False
                    for line in data.splitlines():

                        # get last "%ADJCHANGE: neighbor ... Up" event before hijack
                        #if '%ADJCHANGE: neighbor ' in line and line.endswith('Up'):
                        #    peer = line.split()[-2]
                        #    if peer not in peer_list:
                        #        peer_list.append(peer)
                        #        last_adjacency_time = datetime.timestamp(
                        #            datetime.strptime(str(line.split('BGP:')[0])[:-3], '%Y/%m/%d %H:%M:%S.%f'))

                        # get file start_time
                        if not start_time:
                            start_time = datetime.timestamp(
                                datetime.strptime(str(line.split('BGP:')[0])[:-3], '%Y/%m/%d %H:%M:%S.%f'))

                    for line in data.splitlines():

                        # get first "prefix" valid route add event
                        if 'Zebra send: IPv4 route add %s nexthop' % prefix in line:
                            last_route_add_event = datetime.timestamp(
                                datetime.strptime(str(line.split('BGP:')[0])[:-3], '%Y/%m/%d %H:%M:%S.%f'))
                            break

                        # break when "rcvd UPDATE w/ attr: nexthop ... "prefix_hijacker"" was found
                        if last_route_add_event and \
                                'rcvd UPDATE w/ attr: nexthop ' in line and line.endswith(prefix_hijacker):
                            break

                        # break when "ADJCHANGE: neighbor ... Down User reset" was found
                        if last_route_add_event and \
                                'ADJCHANGE: neighbor ' in line and line.endswith("Down User reset"):
                            break

                    # print the original route convergence time per AS
                    #print('%s,%s' % (file.split('-')[1].split('.')[0], str(last_route_add_event - last_adjacency_time)))
                    print('%s,%s' % (file.split('-')[1].split('.')[0], str(last_route_add_event - start_time)))

        except Exception as error:
            print(error)

    def all_data_from_log_file(self, data):
        try:
            row = list()
            current_time_list = list()
            prefix_list = list()
            origin_AS_list = list()
            for prefix in data:

                # remove prefix length from prefix when prefix length is 24 bits
                #    Network          Next Hop            Metric LocPrf Weight Path
                # *> 208.65.152.0/22  1.0.2.165                              0 3491 23352 36561 i
                # *> 208.65.153.0     0.0.0.0                  0         32768 i

                if prefix.split('/')[1] == '24':
                    prefix_temp = prefix.split('/')[0]
                else:
                    prefix_temp = prefix

                for file in self.monitor_files:
                    data = self.read_file(self.log_directory, file)
                    prefix_found = False
                    big_prefix_found = False

                    for line in data.splitlines():

                        if line.startswith('-->current_time:'):
                            current_time = line.split(':')[1]
                            prefix_found = False
                            big_prefix_found = False

                        if len(line.split()) == 2 and line.startswith('*>') and line.split()[1] == prefix_temp:
                            big_prefix_found = True
                            continue

                        if big_prefix_found:
                            if line.split()[0] == '0.0.0.0':
                                row.append([int(current_time),
                                            int(file.split('-')[1].split('.')[0]),
                                            prefix,
                                            int(file.split('-')[1].split('.')[0]),
                                            [int(file.split('-')[1].split('.')[0])]])
                                current_time_list.append(int(current_time))
                                prefix_list.append(prefix)
                                origin_AS_list.append(int(file.split('-')[1].split('.')[0]))
                            else:
                                path = list()
                                for hop in reversed(line.split()[:-1]):
                                    if hop == '0':
                                        break
                                    else:
                                        path.append(int(hop))
                                path.reverse()
                                row.append([int(current_time),
                                            int(file.split('-')[1].split('.')[0]),
                                            prefix,
                                            int(line.split()[-2]),
                                            path])
                                current_time_list.append(int(current_time))
                                prefix_list.append(prefix)
                                origin_AS_list.append(int(line.split()[-2]))
                            big_prefix_found = False
                            continue

                        if line.startswith('*>') and line.split()[1] == prefix_temp and line.split()[2] == '0.0.0.0':
                            row.append([int(current_time),
                                        int(file.split('-')[1].split('.')[0]),
                                        prefix,
                                        int(file.split('-')[1].split('.')[0]),
                                        [int(file.split('-')[1].split('.')[0])]])
                            current_time_list.append(int(current_time))
                            prefix_list.append(prefix)
                            origin_AS_list.append(int(file.split('-')[1].split('.')[0]))
                            prefix_found = False
                            continue

                        if line.startswith('*>') and line.split()[1] == prefix_temp:
                            path = list()
                            for hop in reversed(line.split()[:-1]):
                                if hop == '0':
                                    break
                                else:
                                    path.append(int(hop))
                            path.reverse()
                            row.append([int(current_time),
                                        int(file.split('-')[1].split('.')[0]),
                                        prefix,
                                        int(line.split()[-2]),
                                        path])
                            current_time_list.append(int(current_time))
                            prefix_list.append(prefix)
                            origin_AS_list.append(int(line.split()[-2]))
                            prefix_found = False
                            continue

                        if len(line.split()) > 1 and line.split()[1] == prefix_temp and not line.startswith('*>'):
                            prefix_found = True

                        if prefix_found:
                            if line.startswith('*>'):
                                path = list()
                                for hop in reversed(line.split()[:-1]):
                                    if hop == '0':
                                        break
                                    else:
                                        path.append(int(hop))
                                path.reverse()
                                row.append([int(current_time),
                                            int(file.split('-')[1].split('.')[0]),
                                            prefix,
                                            int(line.split()[-2]),
                                            path])
                                current_time_list.append(int(current_time))
                                prefix_list.append(prefix)
                                origin_AS_list.append(int(line.split()[-2]))
                                prefix_found = False
                                continue

            df_all_data = pd.DataFrame(data=row, columns=['current_time',
                                                          'monitored_AS',
                                                          'prefix',
                                                          'origin_AS',
                                                          'route_path'])
            df_all_data = df_all_data.sort_values(by=['current_time', 'prefix', 'origin_AS', 'monitored_AS'])

            current_time_list = sorted(list(set(current_time_list)))
            prefix_list = sorted(list(set(prefix_list)))
            origin_AS_list = sorted(list(set(origin_AS_list)))

            print(df_all_data)
            #       current_time  monitored_AS             prefix  origin_AS                                route_path
            # 0       1203889500         16243    208.65.152.0/22      36561                      [3491, 23352, 36561]
            # 1       1203890433         16243    208.65.152.0/22      36561                      [3491, 23352, 36561]
            # 2       1203891366         16243    208.65.152.0/22      36561                      [3491, 23352, 36561]
            # 3       1203892299         16243    208.65.152.0/22      36561                      [3491, 23352, 36561]
            # 4       1203893232         16243    208.65.152.0/22      36561                      [3491, 23352, 36561]
            # 5       1203894165         16243    208.65.152.0/22      36561                      [3491, 23352, 36561]
            # 6       1203895038         16243    208.65.152.0/22      36561                      [3491, 23352, 36561]
            # 7       1203895971         16243    208.65.152.0/22      36561                      [3491, 23352, 36561]
            # 8       1203896964         16243    208.65.152.0/22      36561                      [3491, 23352, 36561]
            # 9       1203897897         16243    208.65.152.0/22      36561                       [24875, 174, 36561]
            # 10      1203889500          5511    208.65.152.0/22      36561                             [3356, 36561]
            # 11      1203890433          5511    208.65.152.0/22      36561                             [3356, 36561]
            # 12      1203891366          5511    208.65.152.0/22      36561                             [3356, 36561]
            # 13      1203892299          5511    208.65.152.0/22      36561                             [3356, 36561]

            return df_all_data, current_time_list, prefix_list, origin_AS_list

        except Exception as error:
            print(error)

    def all_data_from_json_file(self, data, current_time_list):
        try:

            # from initial state

            initial_states = self.data_from['data']['initial_state']
            all_data_initial_states = list()
            current_time = int(datetime.strptime(str(self.data_from['data']['query_starttime']).replace('T', ' '),
                                                 '%Y-%m-%d %H:%M:%S').strftime('%s'))
            sources = copy.copy(self.id_sources)
            for initial_state in initial_states:
                for prefix in data:
                    if prefix == initial_state['target_prefix']:
                        for id_source in sources:
                            if id_source['id_source'] == initial_state['source_id']:
                                all_data_initial_states.append(
                                    [current_time, id_source['source'], initial_state['target_prefix'],
                                     initial_state['path'][-1], initial_state['path'][1:]])
                                for remove_source in sources:
                                    if id_source['source'] == remove_source['source']:
                                        sources.remove(remove_source)

            # from events

            events = self.data_from['data']['events']
            all_data_events = list()
            all_data_temp = list()
            for event in events:

                for id_source in self.id_sources:
                    if id_source['id_source'] == event['attrs']['source_id']:
                        event['attrs']['source_id'] = id_source['source']

                all_data_temp.append([
                    event['type'],
                    int(datetime.strptime(str(event['timestamp']).replace('T', ' '),
                                          '%Y-%m-%d %H:%M:%S').strftime('%s')),
                    event['attrs']['source_id'],
                    event['attrs']['target_prefix'],
                    event['attrs']['path'][-1] if event['type'] == 'A' else None,
                    event['attrs']['path'][1:] if event['type'] == 'A' else [None]
                ])

            for current_time in current_time_list:
                for source in self.sources:
                    for prefix in data:
                        route_found = False
                        for data_temp in reversed(all_data_temp):
                            if not route_found:
                                if current_time > data_temp[1]:
                                    if data_temp[0] == 'A' and \
                                            source == data_temp[2] and \
                                            prefix == data_temp[3]:
                                        all_data_events.append([current_time,
                                                                source,
                                                                prefix,
                                                                data_temp[4],
                                                                data_temp[5]])
                                        route_found = True

                                    elif data_temp[0] == 'W' and \
                                            source == data_temp[2] and \
                                            prefix == data_temp[3]:
                                        route_found = True

                        if not route_found:
                            for row in all_data_initial_states:
                                if current_time > row[0] and \
                                        source == row[1] and \
                                        prefix == row[2]:
                                    all_data_events.append([current_time,
                                                            source,
                                                            prefix,
                                                            row[3],
                                                            row[4]])

            all_data = all_data_initial_states + all_data_events

            df_all_data = pd.DataFrame(data=all_data, columns=['current_time',
                                                               'monitored_AS',
                                                               'prefix',
                                                               'origin_AS',
                                                               'route_path'])

            df_all_data = df_all_data.sort_values(by=['current_time', 'prefix', 'origin_AS', 'monitored_AS'])

            print(df_all_data)
            return df_all_data

        except Exception as error:
            print(error)

    def number_of_autonomous_system(self, df_all_data, current_time_list, prefix_list, origin_AS_list):
        try:
            df_groupby = df_all_data[['current_time',
                                      'monitored_AS',
                                      'prefix',
                                      'origin_AS']].groupby(['current_time',
                                                             'prefix',
                                                             'origin_AS']).agg(['count'])
            df_groupby.columns = ['number_of_AS']

            print(df_groupby)
            # current_time prefix            origin_AS           number_of_AS
            # 1203889500   208.65.152.0/22   36561               143
            # 1203890433   208.65.152.0/22   36561               143
            #              208.65.153.0/24   17557               143
            # 1203891366   208.65.152.0/22   36561               143

            row = list()
            for current_time in current_time_list:
                for prefix in prefix_list:
                    for origin_AS in origin_AS_list:
                        if df_groupby.query("current_time == '%s' and prefix == '%s' and origin_AS == '%s'" %
                                            (current_time, prefix, origin_AS)).empty:
                            row.append([current_time, prefix, origin_AS, 0])
            df_groupby_temp = pd.DataFrame(data=row, columns=['current_time',
                                                              'prefix',
                                                              'origin_AS',
                                                              'number_of_AS'])

            df_groupby.reset_index(inplace=True)
            df_number_of_autonomous_system = pd.concat([df_groupby, df_groupby_temp], ignore_index=True).\
                sort_values(by=['current_time', 'prefix', 'origin_AS'])

            row = list()
            for current_time in current_time_list:
                for prefix in prefix_list:
                    sum_of_AS = 0
                    for row1 in df_number_of_autonomous_system.iterrows():
                        if current_time == row1[1][0] and prefix == row1[1][1]:
                            sum_of_AS = sum_of_AS + row1[1][3]
                    row.append([current_time, prefix, 0, len(self.sources) - sum_of_AS])

            df_groupby_temp = pd.DataFrame(data=row, columns=['current_time',
                                                              'prefix',
                                                              'origin_AS',
                                                              'number_of_AS'])
            df_number_of_autonomous_system = pd.concat([df_number_of_autonomous_system, df_groupby_temp],
                                                       ignore_index=True).set_index('current_time').\
                sort_values(by=['current_time', 'prefix', 'origin_AS'])

            # print(df_number_of_autonomous_system)
            # current_time             prefix  origin_AS  number_of_AS
            # 1203897897      208.65.152.0/22          0             0
            # 1203897897      208.65.152.0/22      17557             0
            # 1203897897      208.65.152.0/22      36561           143
            # 1203897897      208.65.153.0/24          0             0
            # 1203897897      208.65.153.0/24      17557            34
            # 1203897897      208.65.153.0/24      36561           109
            # 1203897897      208.65.153.0/25          0             0
            # 1203897897      208.65.153.0/25      17557             0
            # 1203897897      208.65.153.0/25      36561           143
            # 1203897897    208.65.153.128/25          0            37
            # 1203897897    208.65.153.128/25      17557             0
            # 1203897897    208.65.153.128/25      36561           106

            result = list()

            origin_AS_list_temp = copy.copy(origin_AS_list)
            origin_AS_list_temp.insert(0, 0)

            for prefix in prefix_list:
                for origin_AS in origin_AS_list_temp:
                    result_temp = list()
                    result_temp.append(prefix)
                    result_temp.append(origin_AS)
                    for current_time in current_time_list:
                        for row in df_number_of_autonomous_system.iterrows():
                            if row[0] == current_time and row[1][0] == prefix and row[1][1] == origin_AS:
                                result_temp.append(row[1][2])
                    result.append(result_temp)

            for r in result:
                print(r)
            # ['208.65.152.0/22', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            # ['208.65.152.0/22', 17557, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            # ['208.65.152.0/22', 36561, 143, 143, 143, 143, 143, 143, 143, 143, 143, 143]
            # ['208.65.153.0/24', 0, 143, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            # ['208.65.153.0/24', 17557, 0, 143, 143, 143, 143, 143, 64, 64, 64, 34]
            # ['208.65.153.0/24', 36561, 0, 0, 0, 0, 0, 0, 79, 79, 79, 109]
            # ['208.65.153.0/25', 0, 143, 143, 143, 143, 143, 143, 143, 0, 0, 0]
            # ['208.65.153.0/25', 17557, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            # ['208.65.153.0/25', 36561, 0, 0, 0, 0, 0, 0, 0, 143, 143, 143]
            # ['208.65.153.128/25', 0, 143, 143, 143, 143, 143, 143, 143, 40, 40, 37]
            # ['208.65.153.128/25', 17557, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            # ['208.65.153.128/25', 36561, 0, 0, 0, 0, 0, 0, 0, 103, 103, 106]

        except Exception as error:
            print(error)

    @staticmethod
    def equal_paths(all_data_log, all_data_json, current_time_list, prefix_list):
        try:

            result = list()
            equal_paths = list()
            different_paths = list()

            for prefix in prefix_list:

                result_temp = list()
                result_temp.append(prefix)

                for current_time in current_time_list:
                    sum_of_equal_paths = 0
                    sum_of_different_paths = 0
                    for idx_log in all_data_log.index:
                        for idx_json in all_data_json.index:

                            if prefix == all_data_json['prefix'][idx_json] and \
                                    current_time == all_data_json['current_time'][idx_json] and \
                                    all_data_log['current_time'][idx_log] == all_data_json['current_time'][idx_json] and \
                                    all_data_log['monitored_AS'][idx_log] == all_data_json['monitored_AS'][idx_json] and \
                                    all_data_log['prefix'][idx_log] == all_data_json['prefix'][idx_json] and \
                                    all_data_log['route_path'][idx_log] == all_data_json['route_path'][idx_json]:

                                equal_paths.append(
                                    [all_data_log['current_time'][idx_log], all_data_log['monitored_AS'][idx_log],
                                     all_data_log['prefix'][idx_log], ' -- ', all_data_log['route_path'][idx_log],
                                     ' - ', all_data_json['route_path'][idx_json]])

                                sum_of_equal_paths = sum_of_equal_paths + 1

                                #print('Equal path: ', all_data_log['current_time'][idx_log],
                                #      all_data_log['monitored_AS'][idx_log], all_data_log['prefix'][idx_log], ' -- ',
                                #      all_data_log['route_path'][idx_log], ' - ', all_data_json['route_path'][idx_json])

                            elif prefix == all_data_json['prefix'][idx_json] and \
                                    current_time == all_data_json['current_time'][idx_json] and \
                                    all_data_log['current_time'][idx_log] == all_data_json['current_time'][idx_json] and \
                                    all_data_log['monitored_AS'][idx_log] == all_data_json['monitored_AS'][idx_json] and \
                                    all_data_log['prefix'][idx_log] == all_data_json['prefix'][idx_json] and \
                                    all_data_log['route_path'][idx_log] != all_data_json['route_path'][idx_json]:

                                different_paths.append(
                                    [all_data_log['current_time'][idx_log], all_data_log['monitored_AS'][idx_log],
                                     all_data_log['prefix'][idx_log], ' -- ', all_data_log['route_path'][idx_log],
                                     ' - ', all_data_json['route_path'][idx_json]])

                                sum_of_different_paths = sum_of_different_paths + 1

                                #print('Different path: ', all_data_log['current_time'][idx_log],
                                #      all_data_log['monitored_AS'][idx_log], all_data_log['prefix'][idx_log], ' -- ',
                                #      all_data_log['route_path'][idx_log], ' - ', all_data_json['route_path'][idx_json])

                    result_temp.append([sum_of_equal_paths, sum_of_different_paths])
                result.append(result_temp)

            for r in result:
                print(r)

            return equal_paths, different_paths

        except Exception as error:
            print(error)


def main(argv=sys.argv[1:]):
    try:
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', None)

        parser = Parser(argv[0], argv[1])

        print('\n')
        print('Number of Autonomous Systems from Json:')
        parser.number_of_autonomous_system_from_json()

        print('\n')
        print('Clearing log files:')
        parser.clear_log_files()

        print('\n')
        print('List log files:')
        parser.list_log_files()

        print('\n')
        print('BGP Adjacency time (from log files):')
        print('\nAS,Adjacency time\n')
        parser.adjacency_time_from_log_file()

        print('\n')
        data = [['208.65.152.0/22', '17557']]
        print('Original convergence time for prefix: %s (from log files)' % data[0][0])
        print('\nAS,Convergence_time\n')
        parser.original_convergence_time_for_prefix_from_log_file(data)

        data = ['208.65.152.0/22', '208.65.153.0/24', '208.65.153.0/25', '208.65.153.128/25']

        # from log files

        print('\n')
        print('All data (from log files)')
        print('\ncurrent_time,monitored_AS,prefix,origin_AS,[route_path]\n')
        all_data_log, current_time, prefix, origin_AS = parser.all_data_from_log_file(data)

        print('\n')
        print('Number of AS per origin AS per time slot:')
        print('\ncurrent_time,prefix,origin_AS,number_of_AS\n')
        parser.number_of_autonomous_system(all_data_log, current_time, prefix, origin_AS)

        # from json file

        print('\n')
        print('All data (from json file)')
        print('\ncurrent_time,monitored_AS,prefix,origin_AS,[route_path]\n')
        all_data_json = parser.all_data_from_json_file(data, current_time)

        print('\n')
        print('Number of AS per origin AS per time slot:')
        print('\ncurrent_time,prefix,origin_AS,number_of_AS\n')
        parser.number_of_autonomous_system(all_data_json, current_time, prefix, origin_AS)

        print('\n')
        print('Equal paths in json and log (by current time, monitored AS and prefix):')
        equal_paths, different_paths = parser.equal_paths(all_data_log, all_data_json, current_time, prefix)

        print('\nEqual Paths:\n')
        print('\ncurrent_time,prefix,log_path - json_path\n')
        for equal_path in equal_paths:
            print(equal_path)

        print('\nDifferent Paths:\n')
        print('\ncurrent_time,prefix,log_path - json_path\n')
        for different_path in different_paths:
            print(different_path)

    except Exception as error:
        print(error)
        print('Usage: ./validate_scenario.py <logs directory> <ripe_json_file.MiniSecBGP>')


if __name__ == '__main__':
    main()
