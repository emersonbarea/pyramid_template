#!/usr/bin/python3
import sys
import os
import math

from datetime import datetime

import pandas as pd


class Parser(object):
    def __init__(self, argv):

        self.config_directory = argv + '/AS/'
        self.log_directory = argv + '/log/'

        self.log_files = list()
        for file in os.listdir(self.log_directory):
            if file.startswith('bgp'):
                self.log_files.append(file)

        self.monitor_files = list()
        for file in os.listdir(self.log_directory):
            if file.startswith('monitor'):
                self.monitor_files.append(file)

    def read_file(self, path, file):
        try:
            with open(path + '/' + file, 'r') as opened_file:
                data = opened_file.read()
        except Exception as error:
            print(error)
        finally:
            opened_file.close()
            return data

    def adjacency_time(self):
        try:
            for file in self.log_files:
                data = self.read_file(self.log_directory, file)
                start_time = False
                for line in data.splitlines():

                    # get file start_time
                    if not start_time:
                        start_time = datetime.timestamp(
                            datetime.strptime(str(line.split('BGP:')[0])[:-3], '%Y/%m/%d %H:%M:%S.%f'))

                    # get last "%ADJCHANGE: neighbor ... Up" event before hijack
                    if '%ADJCHANGE: neighbor ' in line and line.endswith('Up'):
                        last_adjacency_time = datetime.timestamp(
                            datetime.strptime(str(line.split('BGP:')[0])[:-3], '%Y/%m/%d %H:%M:%S.%f'))

                # print the BGP adjacency time per AS
                print('%s,%s' % (file.split('-')[1].split('.')[0], str(last_adjacency_time - start_time)))

        except Exception as error:
            print(error)

    def original_convergence_time_for_prefix(self, data):
        try:
            for prefix, prefix_hijacker in data:
                for file in self.log_files:
                    data = self.read_file(self.log_directory, file)
                    for line in data.splitlines():

                        # get last "%ADJCHANGE: neighbor ... Up" event before hijack
                        if '%ADJCHANGE: neighbor ' in line and line.endswith('Up'):
                            last_adjacency_time = datetime.timestamp(
                                datetime.strptime(str(line.split('BGP:')[0])[:-3], '%Y/%m/%d %H:%M:%S.%f'))

                    for line in data.splitlines():

                        # get last "prefix" valid route add event
                        if 'Zebra send: IPv4 route add %s nexthop' % prefix in line:
                            last_route_add_event = datetime.timestamp(
                                datetime.strptime(str(line.split('BGP:')[0])[:-3], '%Y/%m/%d %H:%M:%S.%f'))

                        # break when "rcvd UPDATE w/ attr: nexthop ... "prefix_hijacker"" was found
                        if 'rcvd UPDATE w/ attr: nexthop ' in line and line.endswith(prefix_hijacker):
                            break

                    # print the original route convergence time per AS
                    print('%s,%s' % (file.split('-')[1].split('.')[0], str(last_route_add_event - last_adjacency_time)))

        except Exception as error:
            print(error)

    def original_route_path(self, data):
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
                    prefix = prefix.split('/')[0]

                for file in self.monitor_files:
                    data = self.read_file(self.log_directory, file)
                    prefix_found = False
                    for line in data.splitlines():

                        if line.startswith('-->current_time:'):
                            current_time = line.split(':')[1]
                            prefix_found = False

                        if len(line.split()) == 2 and line.startswith('*>'):
                            prefix_found = True
                            continue

                        if line.startswith('*>') and line.split()[1] == prefix and line.split()[2] == '0.0.0.0':
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

                        if line.startswith('*>') and line.split()[1] == prefix:
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

                        if len(line.split()) > 1 and line.split()[1] == prefix and not line.startswith('*>'):
                            prefix_found = True

            df_original_route_path = pd.DataFrame(data=row, columns=['current_time',
                                                                     'monitored_AS',
                                                                     'prefix',
                                                                     'origin_AS',
                                                                     'route_path'])
            print('Original BGP route path for prefix:')
            print('\ncurrent_time,monitored_AS,prefix,origin_AS,[route_path]\n')
            print(df_original_route_path)

            df_groupby = df_original_route_path[['current_time',
                                                 'monitored_AS',
                                                 'prefix',
                                                 'origin_AS']].groupby(['current_time',
                                                                         'prefix',
                                                                         'origin_AS']).agg(['count'])
            df_groupby.columns = ['number_of_AS']

            current_time_set = set(current_time_list)
            prefix_set = set(prefix_list)
            origin_AS_set = set(origin_AS_list)

            row = list()
            for current_time in current_time_set:
                for prefix in prefix_set:
                    for origin_AS in origin_AS_set:
                        if df_groupby.query("current_time == '%s' and prefix == '%s' and origin_AS == '%s'" %
                                            (current_time, prefix, origin_AS)).empty:
                            row.append([current_time, prefix, origin_AS, 0])

            df_groupby_temp = pd.DataFrame(data=row, columns=['current_time',
                                                              'prefix',
                                                              'origin_AS',
                                                              'number_of_AS'])
            df_groupby.reset_index(inplace=True)
            df = pd.concat([df_groupby, df_groupby_temp], ignore_index=True).set_index('current_time')

            print('Number of AS routing byOriginal BGP route path for prefix:')
            print('\ncurrent_time,monitored_AS,prefix,origin_AS,[route_path]\n')
            print(df.sort_values(by=['current_time', 'prefix', 'origin_AS']))

        except Exception as error:
            print(error)


def main(argv=sys.argv[1:]):
    try:
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', None)

        parser = Parser(argv[0])

        print('\n')
        print('BGP Adjacency time:')
        print('\nAS,Adjacency time\n')
        parser.adjacency_time()

        print('\n')
        data = [['208.65.152.0/22', '17557']]
        print('Original convergence time for prefix: %s' % data[0][0])
        print('\nAS,Convergence_time\n')
        parser.original_convergence_time_for_prefix(data)

        print('\n')
        data = ['208.65.152.0/22', '208.65.153.0/24', '208.65.153.0/25', '208.65.153.128/25']
        parser.original_route_path(data)

    except Exception as error:
        print(error)
        print('Usage: ./parser_testbed_show_commands.py <logs directory>')


if __name__ == '__main__':
    main()
