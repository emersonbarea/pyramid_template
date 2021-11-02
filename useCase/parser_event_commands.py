#!/usr/bin/python3

import copy
import sys
import os
import json
import ipaddress

from datetime import datetime

import pandas as pd


class Parser(object):
    def __init__(self, argv0):

        self.event_commands_file = argv0 + 'event_commands.MiniSecBGP'
        self.file_to_write = argv0 + 'event_commands.new.MiniSecBGP'

        self.commands = list()
        self.timestamps = [1203889500,
                           1203890433,
                           1203891366,
                           1203892299,
                           1203893232,
                           1203894165,
                           1203895038,
                           1203895971,
                           1203896964,
                           1203897897]
        self.data = list()
        # read event_command file
        try:
            with open(self.event_commands_file, 'r') as file:
                data = file.read()
                for row in data.splitlines():
                    self.data.append(row)
        except Exception as error:
            print(error)
        finally:
            file.close()
            

    def parser_event_commands_file(self):
        commands = list()
        for idx, line in enumerate(self.data):
            if line.startswith('    if current_time == '):
                commands.append([line.split()[-1][:-1], self.data[idx + 1].lstrip()])

        # for x in commands:
        #     print(x)
        # 
        # ['1203897669', 'os.popen("sudo -u minisecbgpuser sudo mnexec -a %s /usr/bin/python -c \\" ...
        # ['1203897681', 'os.popen("sudo -u minisecbgpuser sudo mnexec -a %s /usr/bin/python -c \\" ...
        # ['1203897682', 'os.popen("sudo -u minisecbgpuser sudo mnexec -a %s /usr/bin/python -c \\" ...

        for idx, timestamp in enumerate(self.timestamps):

            low_timestamp = timestamp
            high_timestamp = self.timestamps[idx + 1] if idx + 1 < len(self.timestamps) else timestamp

            for command in commands:
                if int(command[0]) >= int(low_timestamp) and int(command[0]) < int(high_timestamp):
                    self.commands.append([low_timestamp, command[1]])

        #for x in self.commands:
        #    print(x)
        # 
        # [1203897897, 'os.popen("sudo -u minisecbgpuser sudo mnexec -a %s /usr/bin/python -c \\" ...
        # [1203897897, 'os.popen("sudo -u minisecbgpuser sudo mnexec -a %s /usr/bin/python -c \\" ...
        # [1203897897, 'os.popen("sudo -u minisecbgpuser sudo mnexec -a %s /usr/bin/python -c \\" ...
        # [1203897897, 'os.popen("sudo -u minisecbgpuser sudo mnexec -a %s /usr/bin/python -c \\" ...

        with open(self.file_to_write, 'w') as file:
            for timestamp in self.timestamps:
                file.write('\n\nprint(\'Sleeping 1800 sec for BGP complete convergence...\')\n')
                file.write('\ntime.sleep(1800)\n')
                file.write('\nprint(\'Monitoring timestamp %s\')\n' % timestamp)
                file.write('\nos.popen("./monitor.py %s")\n' % timestamp)
                file.write('\nprint(\'Sleeping 500 sec for monitoring...\')\n')
                file.write('\ntime.sleep(500)\n\n')                
                for command in self.commands:
                    if timestamp == command[0]:
                        file.write('%s\n\n' % command[1])
        file.close()


def main(argv=sys.argv[1:]):
    try:
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', None)

        parser = Parser(argv[0])

        print('\n')
        parser.parser_event_commands_file()
        

    except Exception as error:
        print(error)
        print('Usage: ./parser_event_commands.py <topology directory>')


if __name__ == '__main__':
    main()
