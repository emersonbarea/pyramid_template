#!/usr/bin/python3
import sys
import os
import math
import time

from datetime import datetime

import pandas as pd


class Parser(object):
    def __init__(self, argv):
        self.directory = argv
        self.files = list()
        for file in os.listdir(self.directory):
            if file.startswith('bgp'):
                self.files.append(file)

    def read_file(self, file):
        try:
            with open(self.directory + '/' + file, 'r') as bgp_file:
                data = bgp_file.read()
        except Exception as error:
            print(error)
        finally:
            bgp_file.close()
            return data

    def adjacency_time(self):
        try:
            for file in self.files:
                data = self.read_file(file)
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
            for file in self.files:
                data = self.read_file(file)
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
            for file in self.files:
                data = self.read_file(file)

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
            for file in self.files:
                data = self.read_file(file)

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
            data = self.read_file('system_date_time')
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
                    for file in self.files:
                        data = self.read_file(file)

                        announcer_path = list()
                        nexthop = False
                        found_route = False
                        for line in reversed(data.splitlines()):

                            # read all lines less than or equal to the time slot
                            line_datetime = datetime.timestamp(datetime.strptime(line.split('.')[0], '%Y/%m/%d %H:%M:%S'))
                            if int(line_datetime) <= int(time_slot):

                                # tenho que verificar quando é o próprio emissor da rota
                                # tenho que cuidar do prepend
                                # tenho que cuidar do withdrawn

                                if 'Zebra send: IPv4 route add %s nexthop' % prefix in line:
                                    nexthop = line.split('nexthop ')[1].split(' ')[0]
                                if 'BGP: %s rcvd UPDATE w/ attr: nexthop %s,' % (nexthop, nexthop) in line:
                                    path = line.split(' path')[-1]
                                    for hop in path.split(' '):
                                        if hop:
                                            announcer_path.append(int(hop))
                                    found_route = True
                                    break
                        if not found_route:
                            announcer_path.append(None)

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
        data = [['208.65.152.0/22', '17557']]
        for prefix, prefix_hijacker in data:
            print('Original BGP convergence time for prefix %s:' % prefix)
            print('\nAS,Convergence_time\n')
            parser.original_convergence_time_for_prefix(prefix, prefix_hijacker)

        print('\n')
        data = [['208.65.152.0/22', '17557']]
        for prefix, prefix_hijacker in data:
            print('Original BGP route path for prefix %s:' % prefix)
            print('\nAS,[Route_path]\n')
            parser.original_route_path(prefix, prefix_hijacker)

        print('\n')
        data = [['208.65.152.0/22', '17557']]
        for prefix, prefix_hijacker in data:
            print('Original announcer AS for the prefix %s:' % prefix)
            print('\nAS,AS_announcer\n')
            parser.original_AS_route_origin(prefix, prefix_hijacker)

        print('\n')
        print('PER TIME SLOT')

        print('\n')
        time_slot_number = 9
        prefixes = ['208.65.153.0/24', '208.65.153.0/25', '208.65.153.128/25']
        print('BGP route origin per time slot for the prefixes %s:' % prefixes)
        print('\nprefix,time_slot,AS,[Route_path]\n')
        parser.per_time_slot_route_path_per_prefix(prefixes, time_slot_number)

        print('\n\n\n\n')
        print('-- BGP route path per prefix per time slot')

    except:
        print('usage: ./parser_testbed.py <logs directory>')


if __name__ == '__main__':
    main()
