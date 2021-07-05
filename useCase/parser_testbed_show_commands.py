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

    def all_data(self, data):
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
                    for line in data.splitlines():

                        if line.startswith('-->current_time:'):
                            current_time = line.split(':')[1]
                            prefix_found = False

                        if len(line.split()) == 2 and line.startswith('*>'):
                            prefix_found = True
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

            df_all_data = pd.DataFrame(data=row, columns=['current_time',
                                                          'monitored_AS',
                                                          'prefix',
                                                          'origin_AS',
                                                          'route_path'])
            current_time_list = sorted(list(set(current_time_list)))
            prefix_list = sorted(list(set(prefix_list)))
            origin_AS_list = sorted(list(set(origin_AS_list)))

            # print(df_all_data)
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

    def number_of_autonomous_system(self, df_all_data, current_time_list, prefix_list, origin_AS_list):
        try:

            df_groupby = df_all_data[['current_time',
                                      'monitored_AS',
                                      'prefix',
                                      'origin_AS']].groupby(['current_time',
                                                             'prefix',
                                                             'origin_AS']).agg(['count'])
            df_groupby.columns = ['number_of_AS']

            # print(df_groupby)
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

            number_of_ASes = 143
            row = list()
            for current_time in current_time_list:
                for prefix in prefix_list:
                    sum_of_AS = 0
                    for row1 in df_number_of_autonomous_system.iterrows():
                        if current_time == row1[1][0] and prefix == row1[1][1]:
                            sum_of_AS = sum_of_AS + row1[1][3]
                    row.append([current_time, prefix, 0, number_of_ASes - sum_of_AS])

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
            origin_AS_list.insert(0, 0)
            for prefix in prefix_list:
                for origin_AS in origin_AS_list:
                    result_temp = list()
                    result_temp.append(prefix)
                    result_temp.append(origin_AS)
                    for current_time in current_time_list:
                        for row in df_number_of_autonomous_system.iterrows():
                            if row[0] == current_time and row[1][0] == prefix and row[1][1] == origin_AS:
                                result_temp.append(row[1][2])
                    result.append(result_temp)

#             for r in result:
#                 print(r)
#             ['208.65.152.0/22', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
#             ['208.65.152.0/22', 17557, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
#             ['208.65.152.0/22', 36561, 143, 143, 143, 143, 143, 143, 143, 143, 143, 143]
#             ['208.65.153.0/24', 0, 143, 0, 0, 0, 0, 0, 0, 0, 0, 0]
#             ['208.65.153.0/24', 17557, 0, 143, 143, 143, 143, 143, 64, 64, 64, 34]
#             ['208.65.153.0/24', 36561, 0, 0, 0, 0, 0, 0, 79, 79, 79, 109]
#             ['208.65.153.0/25', 0, 143, 143, 143, 143, 143, 143, 143, 0, 0, 0]
#             ['208.65.153.0/25', 17557, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
#             ['208.65.153.0/25', 36561, 0, 0, 0, 0, 0, 0, 0, 143, 143, 143]
#             ['208.65.153.128/25', 0, 143, 143, 143, 143, 143, 143, 143, 40, 40, 37]
#             ['208.65.153.128/25', 17557, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
#             ['208.65.153.128/25', 36561, 0, 0, 0, 0, 0, 0, 0, 103, 103, 106]

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
        print('All data:')
        print('\ncurrent_time,monitored_AS,prefix,origin_AS,[route_path]\n')
        all_data, current_time, prefix, origin_AS = parser.all_data(data)

        print('\n')
        print('Number of AS per origin AS per time slot:')
        print('\ncurrent_time,prefix,origin_AS,number_of_AS\n')
        parser.number_of_autonomous_system(all_data, current_time, prefix, origin_AS)

    except Exception as error:
        print(error)
        print('Usage: ./parser_testbed_show_commands.py <logs directory>')


if __name__ == '__main__':
    main()
