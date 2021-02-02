#!/usr/bin/python3
import ipaddress
import itertools
import sys
import json
import pandas as pd
from datetime import datetime


class Parser(object):
    def __init__(self, argv):
        self.file_from = argv
        self.nodes = list()
        self.sources = list()
        self.start_datetime = None
        self.end_datetime = None

        # read BGPlay json file and parse it
        try:
            with open(self.file_from) as file:
                self.data_from = json.load(file)
        except Exception as error:
            print(error)
        finally:
            file.close()

    def time_interval(self):
        try:
            self.start_datetime = int(datetime.strptime(
                str(self.data_from['data']['query_starttime']).replace('T', ' '),
                '%Y-%m-%d %H:%M:%S').strftime('%s'))
            self.end_datetime = int(datetime.strptime(
                str(self.data_from['data']['query_endtime']).replace('T', ' '),
                '%Y-%m-%d %H:%M:%S').strftime('%s'))
        except Exception as error:
            print(error)

    def number_of_autonomous_system(self):
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
            self.sources = list(set(self.sources))
            for node in nodes:
                self.nodes.append(node['as_number'])
            self.nodes = list(set(self.nodes))
        except Exception as error:
            print(error)
        else:
            print('\nTotal number of Nodes: %s' % len(self.nodes))
            print('Total number of Sources: %s\n' % len(self.sources))

    def announcements(self, number_of_slots, networks):
        """
            know which as_number announces which network
        """
        try:

            # sources
            sources = self.data_from['data']['sources']
            sources_list = list()
            for source in sources:
                sources_list.append([source['id'], source['as_number']])
            df_sources = pd.DataFrame(data=sources_list, columns=['id', 'id_as_number'])
            df_sources.set_index('id', inplace=True)

            #print('\n-------------------------\n')
            #print('df_sources')
            #print(df_sources)
            #print('\n-------------------------\n')

        except Exception as error:
            print(error)

        """
            create the announcements list
        """
        try:
            announcements = list()

            # from initial state
            initial_states = self.data_from['data']['initial_state']
            for initial_state in initial_states:
                for network in networks:
                    if network == initial_state['target_prefix']:
                        source = df_sources.loc[initial_state['source_id']]['id_as_number']
                        announcements.append([network, source, initial_state['path'][-1], self.start_datetime])

            # from events
            events = self.data_from['data']['events']
            for event in events:
                # for announcement events only (not withdrawn events)
                if event['type'] == 'A':
                    for network in networks:
                        if network == event['attrs']['target_prefix']:
                            source = df_sources.loc[event['attrs']['source_id']]['id_as_number']
                            announcements.append([network,
                                                  source,
                                                  event['attrs']['path'][-1],
                                                  int(datetime.strptime(str(event['timestamp']).replace('T', ' '),
                                                                        '%Y-%m-%d %H:%M:%S').strftime('%s'))])

            #print('\n-------------------------\n')
            #print('announcements\n')
            #for announcement in announcements:
            #    print(announcement)
            #print('\n-------------------------\n')

        except Exception as error:
            print(error)

        """
            time slots
        """
        try:
            # time interval and slots
            slot_interval = (self.end_datetime - self.start_datetime) // number_of_slots
            slots = list()
            slot_value = self.start_datetime
            while slot_value <= self.end_datetime:
                slots.append(slot_value)
                slot_value = slot_value + slot_interval

            print('\n-------------------------\n')
            print('slots\n')
            print(slots)
            print('\n-------------------------\n')

        except Exception as error:
            print(error)

        """
            get announced networks per AS number
        """
        announced_networks_per_as_number = list()
        try:
            for announcement in announcements:
                announced_networks_per_as_number.append([announcement[0], announcement[2]])
                announced_networks_per_as_number.append([announcement[0], 0])
            announced_networks_per_as_number.sort()
            announced_networks_per_as_number = list(
                announced_networks_per_as_number for announced_networks_per_as_number, _ in
                itertools.groupby(announced_networks_per_as_number))

            #print('\n-------------------------\n')
            #print('announced_networks_per_as_number\n')
            #for announced_network_per_as_number in announced_networks_per_as_number:
            #    print(announced_network_per_as_number)
            #print('\n-------------------------\n')

        except Exception as error:
            print(error)

        """
            get the last announcement per as_number per time slot
        """
        try:
            # get the amount of ASs that announces networks per time slot
            results_temp = announced_networks_per_as_number[:]
            for slot in slots:
                sources = self.sources[:]
                results = list()
                for row_temp in results_temp:                               # [['147.65.0.0/16', 0], ['147.65.0.0/16', 1916] ...]
                    row = list()
                    for item in row_temp:                                   # '147.65.0.0/16', 0
                        row.append(item)
                    if row_temp[1] == 0:                                    # if "undefined"
                        row.append(len(set(self.sources)))                  # ['147.65.0.0/16', 0, 80]
                    else:
                        row.append(0)                                       # ['147.65.0.0/16', 3256, 80]
                    results.append(row)

                for announcement in reversed(announcements):                # [['150.161.0.0/16', 27664, 1916, 1228515620], ['150.161.0.0/16', 7018, 3333, 1228515620] ...]
                    if announcement[3] <= slot:                             # if the announcement is in valid time slot
                        for result in results:                              # [['147.65.0.0/16', 0], ['147.65.0.0/16', 1916] ...]
                            if announcement[0] == result[0] and \
                                    announcement[2] == result[1]:
                                if announcement[1] in sources:
                                    result[-1] = result[-1] + 1             # adding one more value on "result"
                                    sources.remove(announcement[1])
                                    for undefined in results:               # removing one value from undefined
                                        if announcement[0] == undefined[0] and \
                                                undefined[1] == 0:       #
                                            undefined[-1] = undefined[-1] - 1

                results_temp = results[:]

            print('\n-------------------------\n')
            print('result\n')
            results.sort()
            for result in results:
                print(result)
            print('\n-------------------------\n')

        except Exception as error:
            print(error)


def main(argv=sys.argv[1:]):
    try:
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', None)

        parser = Parser(argv[0])

        parser.time_interval()
        parser.number_of_autonomous_system()

        # 8400 seconds divided in 4 slots (minutes range: 2100, 4200, 6300)
        # Obs.: the extremes will be used too (0 and 8400)
        number_of_slots = 10
        # look for path to networks
        networks = ['208.65.153.0/24', '208.65.153.0/25', '208.65.153.128/25']
        #
        parser.announcements(number_of_slots, networks)
    except:
        print('usage: ./parser_ripe.py file.json')


if __name__ == '__main__':
    main()
