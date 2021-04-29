#!/usr/bin/python3
import sys
import os
import math
import time

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

    def original_convergence_time_for_prefix(self, prefix, prefix_hijacker):
        try:
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

    def original_route_path(self, prefix, prefix_hijacker):
        try:
            for file in self.log_files:
                data = self.read_file(self.log_directory, file)

                lines = list()
                for line in data.splitlines():

                    lines.append(line)

                    # get last "prefix" valid route add event
                    if 'Zebra send: IPv4 route add %s nexthop' % prefix in line:
                        nexthop = str(line.split('nexthop')[1].split(' ')[1])

                    # break when "rcvd UPDATE w/ attr: nexthop ... "prefix_hijacker"" was found
                    if 'rcvd UPDATE w/ attr: nexthop ' in line and line.endswith(prefix_hijacker):
                        break

                for line in reversed(lines):

                    # get the original route path
                    if '%s rcvd UPDATE w/ attr: nexthop %s, origin i,' % (nexthop, nexthop) in line:
                        path = list(map(int, line.split('path ')[1].split(' ')))

                # print the original route convergence time per AS
                print('%s,%s' % (file.split('-')[1].split('.')[0], path))

        except Exception as error:
            print(error)

    def original_AS_route_origin(self, prefix, prefix_hijacker):
        try:
            for file in self.log_files:
                data = self.read_file(self.log_directory, file)

                lines = list()
                for line in data.splitlines():

                    lines.append(line)

                    # get last "prefix" valid route add event
                    if 'Zebra send: IPv4 route add %s nexthop' % prefix in line:
                        nexthop = str(line.split('nexthop')[1].split(' ')[1])

                    # break when "rcvd UPDATE w/ attr: nexthop ... "prefix_hijacker"" was found
                    if 'rcvd UPDATE w/ attr: nexthop ' in line and line.endswith(prefix_hijacker):
                        break

                for line in reversed(lines):

                    # get the original route path
                    if '%s rcvd UPDATE w/ attr: nexthop %s, origin i,' % (nexthop, nexthop) in line:
                        AS = line.split('path ')[1].split(' ')[-1]

                # print the original route convergence time per AS
                print('%s,%s' % (file.split('-')[1].split('.')[0], AS))

        except Exception as error:
            print(error)

    def per_time_slot_route_path_per_prefix(self, prefixes, time_slot_number):
        try:

            # get start_datetime and end_datetime
            data = self.read_file(self.log_directory, '/system_date_time')
            for line in data.splitlines():
                if line.startswith('start_datetime:'):
                    start_datetime = int(line.split(':')[-1])
                elif line.startswith('end_datetime:'):
                    end_datetime = int(line.split(':')[-1])

            # defining time slots
            time_slots = list()
            time_slot_interval = int(math.modf((end_datetime - start_datetime) / time_slot_number)[1])
            for time_event in range(start_datetime, end_datetime, time_slot_interval):
                time_slots.append(time_event)

            # for each prefix
            for prefix in prefixes:
                for time_slot in time_slots:
                    print('')
                    for file in self.log_files:

                        announcer_path = [None]
                        nexthop = False
                        remote_announcement_received = False

                        # checking if the prefix was announced at the scenario startup
                        data = self.read_file(self.config_directory + '/' + file.split('.')[0].split('-')[1], 'bgpd.conf')
                        for line in reversed(data.splitlines()):
                            if ' network %s' % prefix in line:
                                announcer_path = [int(file.split('.')[0].split('-')[1])]
                                break

                        # checking if the prefix was announced at the scenario startup
                        data = self.read_file(self.log_directory, file)
                        for line in reversed(data.splitlines()):

                            # read all lines less than or equal to the time slot
                            line_datetime = datetime.timestamp(datetime.strptime(line.split('.')[0], '%Y/%m/%d %H:%M:%S'))
                            if int(line_datetime) <= int(time_slot):

                                # LAST PREFIX ANNOUNCEMENT

                                # 1 - looking for the prefix announcement on the router itself during scenario execution
                                if '127.0.0.1(config-router)# network %s' % prefix in line and not remote_announcement_received:
                                    announcer_path = [int(file.split('-')[1].split('.')[0])]
                                    break

                                # 2 - looking for the prefix announcement received from another router during scenario execution
                                # Obs.: pega withdrawn, prepend out
                                # Obs.: não pega a mudança de path no roteador onde ocorre o "prepend in" (não consegue pegar que o path aumenta com o prepend)
                                if 'Zebra send: IPv4 route add %s nexthop' % prefix in line and not remote_announcement_received:
                                    nexthop = line.split('nexthop ')[1].split(' ')[0]
                                    remote_announcement_received = True
                                if 'BGP: %s rcvd UPDATE w/ attr: nexthop %s,' % (nexthop, nexthop) in line and remote_announcement_received:
                                    path_temp = line.split(' path')[-1]
                                    path = list()
                                    for hop in path_temp.split(' '):
                                        if hop:
                                            path.append(int(hop))
                                    announcer_path = path
                                    break

                                # LAST PREFIX REMOVAL/WITHDRAWN

                                # looking for the prefix removal/withdrawn on the router itself during scenario execution
                                if '127.0.0.1(config-router)# no network %s' % prefix in line and not remote_announcement_received:
                                    break
                                # looking for the prefix removal/withdrawn from another router during scenario execution
                                if 'rcvd UPDATE about %s -- withdrawn' % prefix in line and not remote_announcement_received:
                                    break

                                # looking for prepended routes



                                #looking for withdrawn routes




                        print('\'%s\',%s,%s,%s' % (prefix, time_slot, file.split('-')[1].split('.')[0], announcer_path))

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
        #data = [['208.65.152.0/22', '17557']]
        data = [['20.0.0.0/24', '333']]
        for prefix, prefix_hijacker in data:
            print('Original BGP convergence time for prefix %s:' % prefix)
            print('\nAS,Convergence_time\n')
            parser.original_convergence_time_for_prefix(prefix, prefix_hijacker)

        print('\n')
        #data = [['208.65.152.0/22', '17557']]
        data = [['20.0.0.0/24', '333']]
        for prefix, prefix_hijacker in data:
            print('Original BGP route path for prefix %s:' % prefix)
            print('\nAS,[Route_path]\n')
            parser.original_route_path(prefix, prefix_hijacker)

        print('\n')
        #data = [['208.65.152.0/22', '17557']]
        data = [['20.0.0.0/24', '333']]
        for prefix, prefix_hijacker in data:
            print('Original announcer AS for the prefix %s:' % prefix)
            print('\nAS,AS_announcer\n')
            parser.original_AS_route_origin(prefix, prefix_hijacker)

        print('\n')
        print('PER TIME SLOT')

        print('\n')
        time_slot_number = 9
        #prefixes = ['208.65.153.0/24', '208.65.153.0/25', '208.65.153.128/25']
        prefixes = ['20.0.0.0/24']
        print('BGP route origin per time slot for the prefixes %s:' % prefixes)
        print('\nprefix,time_slot,AS,[Route_path]\n')
        parser.per_time_slot_route_path_per_prefix(prefixes, time_slot_number)

        print('\n\n\n\n')
        print('-- BGP route path per prefix per time slot')

    except Exception as error:
        print(error)
        print('Usage: ./parser_testbed.py <logs directory>')


if __name__ == '__main__':
    main()
