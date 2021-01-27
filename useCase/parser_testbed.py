#!/usr/bin/python3
import sys
import os

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
            print('\n')
            print('BGP Adjacency time:')
            for file in self.files:
                data = self.read_file(file)
                start_time = False
                for line in data.splitlines():

                    # get file start_time
                    if not start_time:
                        start_time = datetime.timestamp(datetime.strptime(str(line.split('BGP:')[0]).split('.')[0], '%Y/%m/%d %H:%M:%S'))

                    # get last "%ADJCHANGE: neighbor ... Up" event before hijack
                    if '%ADJCHANGE: neighbor ' in line and line.endswith('Up'):
                        last_adjacency_time = datetime.timestamp(datetime.strptime(str(line.split('BGP:')[0])[:-3], '%Y/%m/%d %H:%M:%S.%f'))

                # print the BGP adjacency time per AS
                print('%s,%s' % (file.split('-')[1].split('.')[0], str(last_adjacency_time - start_time)))

        except Exception as error:
            print(error)

    def original_route_convergence_time(self):
        try:
            print('\n')
            print('BGP Original route convergence time:')
            for file in self.files:
                data = self.read_file(file)
                for line in data.splitlines():

                    # get last "%ADJCHANGE: neighbor ... Up" event before hijack
                    if '%ADJCHANGE: neighbor ' in line and line.endswith('Up'):
                        last_adjacency_time = datetime.timestamp(datetime.strptime(str(line.split('BGP:')[0])[:-3], '%Y/%m/%d %H:%M:%S.%f'))

                for line in data.splitlines():

                    # # get last 208.65.152.0/22 valid route add event
                    if 'Zebra send: IPv4 route add 208.65.152.0/22 nexthop' in line:
                        last_route_add_event = datetime.timestamp(datetime.strptime(str(line.split('BGP:')[0])[:-3], '%Y/%m/%d %H:%M:%S.%f'))

                    # break when "rcvd UPDATE w/ attr: nexthop ... 17557" was found
                    if 'rcvd UPDATE w/ attr: nexthop ' in line and line.endswith('17557'):
                        break

                # print the original route convergence time per AS
                print('%s,%s' % (file.split('-')[1].split('.')[0], str(last_route_add_event - last_adjacency_time)))

        except Exception as error:
            print(error)

    def original_route_path(self):
        try:
            print('\n')
            print('BGP Original route path:')
            for file in self.files:
                data = self.read_file(file)

                lines = list()
                for line in data.splitlines():

                    lines.append(line)

                    # get last 208.65.152.0/22 valid route add event
                    if 'Zebra send: IPv4 route add 208.65.152.0/22 nexthop' in line:
                        nexthop = str(line.split('nexthop')[1].split(' ')[1])

                    # break when "rcvd UPDATE w/ attr: nexthop ... 17557" was found
                    if 'rcvd UPDATE w/ attr: nexthop ' in line and line.endswith('17557'):
                        break

                for line in reversed(lines):

                    # get the original route path
                    if '%s rcvd UPDATE w/ attr: nexthop %s, origin i,' % (nexthop, nexthop) in line:
                        path = list(map(int, line.split('path ')[1].split(' ')))

                # print the original route convergence time per AS
                print('%s,%s' % (file.split('-')[1].split('.')[0], path))

        except Exception as error:
            print(error)


def main(argv=sys.argv[1:]):
    try:
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', None)

        parser = Parser(argv[0])
        parser.adjacency_time()
        parser.original_route_convergence_time()
        parser.original_route_path()
        #parser.slot_route_origin()
        #parser.slot_route_path()
    except:
        print('usage: ./parser_testbed.py <logs directory>')


if __name__ == '__main__':
    main()
