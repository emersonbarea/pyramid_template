#!/usr/bin/python3
import ipaddress
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
            for node in nodes:
                self.nodes.append(node['as_number'])
        except Exception as error:
            print(error)
        else:
            print('\nTotal number of Nodes: %s' % len(set(self.nodes)))
            print('Total number of Sources: %s\n' % len(set(self.sources)))

    def network_by_autonomous_system(self, number_of_slots, networks):

        """
            know which as_number announces which network
        """
        try:
            networks_announced_by_autonomous_systems_temp = list()
            networks_announced_by_autonomous_systems = list()
            for network in networks:
                networks_announced_by_autonomous_systems.append([network, 0])

            # sources
            sources = self.data_from['data']['sources']
            sources_list = list()
            for source in sources:
                sources_list.append([source['id'], source['as_number']])
            df_sources = pd.DataFrame(data=sources_list, columns=['id', 'id_as_number'])
            df_sources.set_index('id', inplace=True)

#            print('\n-------------------------\n')
#            print('df_sources')
#            print(df_sources)
#            print('\n-------------------------\n')

            # from initial state
            initial_states = self.data_from['data']['initial_state']
            for initial_state in initial_states:
                for network in networks:
                    if network == initial_state['target_prefix']:
                        networks_announced_by_autonomous_systems_temp.append([network, initial_state['path'][-1]])

            # from events
            events = self.data_from['data']['events']
            for event in events:
                for network in networks:
                    if network == event['attrs']['target_prefix']:
                        networks_announced_by_autonomous_systems_temp.append([network, event['attrs']['path'][-1]])

            if networks_announced_by_autonomous_systems_temp:
                for network_announced_by_autonomous_system_temp in networks_announced_by_autonomous_systems_temp:
                    if not networks_announced_by_autonomous_systems:
                        networks_announced_by_autonomous_systems.append(network_announced_by_autonomous_system_temp)
                    else:
                        for i, network_announced_by_autonomous_system in enumerate(networks_announced_by_autonomous_systems):
                            if (str(network_announced_by_autonomous_system[0])) == str(network_announced_by_autonomous_system_temp[0]) and \
                                    (str(network_announced_by_autonomous_system[1]) == str(network_announced_by_autonomous_system_temp[1])):
                                break
                            if i == len(networks_announced_by_autonomous_systems) - 1:
                                networks_announced_by_autonomous_systems.append(network_announced_by_autonomous_system_temp)

            df_networks_announced_by_autonomous_systems = pd.DataFrame(networks_announced_by_autonomous_systems, columns=['network', 'autonomous_system'])
            df_networks_announced_by_autonomous_systems = df_networks_announced_by_autonomous_systems.set_index(['network', 'autonomous_system'])
            df_networks_announced_by_autonomous_systems['slot-0'] = 0

#            print('\n-------------------------\n')
#            print('df_networks_announced_by_autonomous_systems')
#            print(df_networks_announced_by_autonomous_systems)
#            print('\n-------------------------\n')

        except Exception as error:
            print(error)

        """
            how many autonomous systems announces each network prefix in time slot 0
        """
        # from initial state
        try:
            initial_states = self.data_from['data']['initial_state']
            prefix_by_as_number = list()
            for initial_state in initial_states:
                if initial_state['target_prefix'] in networks:
                    source = df_sources.loc[initial_state['source_id']]['id_as_number']
                    prefix_by_as_number.append([source, initial_state['target_prefix'], initial_state['path'][-1]])
            df_prefix_by_as_number_in_time_slot = pd.DataFrame(data=prefix_by_as_number, columns=['id_as_number', 'network', 'autonomous_system'])
            df_prefix_by_as_number_in_time_slot = df_prefix_by_as_number_in_time_slot.drop_duplicates(subset=['id_as_number', 'network'], keep='last')

            df_prefix_by_as_number_in_time_slot = df_prefix_by_as_number_in_time_slot.groupby(['network', 'autonomous_system']).count()['id_as_number'].reset_index()
            df_prefix_by_as_number_in_time_slot.columns = ['network', 'autonomous_system', 'slot']

#            print('\n-------------------------\n')
#            print('df_prefix_by_as_number_in_time_slot')
#            print(df_prefix_by_as_number_in_time_slot)
#            print('\n-------------------------\n')

            for index, row in df_prefix_by_as_number_in_time_slot.iterrows():
                registry = df_networks_announced_by_autonomous_systems.loc[row['network'], row['autonomous_system']]
                registry['slot-0'] = registry['slot-0'] + row['slot']

            df_networks_announced_by_autonomous_systems = df_networks_announced_by_autonomous_systems.reset_index()
            df_networks_announced_by_autonomous_systems = df_networks_announced_by_autonomous_systems.set_index('network')

#            print('\n-------------------------\n')
#            print('df_networks_announced_by_autonomous_systems')
#            print(df_networks_announced_by_autonomous_systems)
#            print('\n-------------------------\n')

            df_networks_announced_by_autonomous_systems_temp = pd.DataFrame(df_networks_announced_by_autonomous_systems.groupby('network').sum()['slot-0'])

            df_networks_announced_by_autonomous_systems = df_networks_announced_by_autonomous_systems.reset_index()
            df_networks_announced_by_autonomous_systems = df_networks_announced_by_autonomous_systems.set_index(['network', 'autonomous_system'])
            for index, row in df_networks_announced_by_autonomous_systems_temp.iterrows():
                registry = df_networks_announced_by_autonomous_systems.loc[index, 0]
                registry['slot-0'] = len(set(self.sources)) - row['slot-0']

            print('\n-------------------------\n')
            print('df_networks_announced_by_autonomous_systems')
            print(df_networks_announced_by_autonomous_systems)
            print('\n-------------------------\n')

        except Exception as error:
            print(error)

        """
            how many autonomous systems announces each network prefix by time slot
        """

        # time interval and slots
        time_interval = self.end_datetime - self.start_datetime
        slot_interval = time_interval // number_of_slots
        slots = list()
        for i in range(1, time_interval):
            if (i / slot_interval).is_integer():
                slots.append(i)

#        print(slots)

        # for each node, get its state for each time slot.
        for i, slot in enumerate(slots):

            print('SLOT: ', i + 1, ' - ', slot)
            df_networks_announced_by_autonomous_systems['slot-%s' % str(i + 1)] = 0

            # from events
            try:
                events = self.data_from['data']['events']
                prefix_by_as_number = list()
                for event in events:
                    if event['attrs']['target_prefix'] in networks:
                        source = df_sources.loc[event['attrs']['source_id']]['id_as_number']
                        prefix_by_as_number.append([source, event['attrs']['target_prefix'], event['attrs']['path'][-1]])
                df_prefix_by_as_number_in_time_slot = pd.DataFrame(data=prefix_by_as_number,columns=['id_as_number', 'network', 'autonomous_system'])
                df_prefix_by_as_number_in_time_slot = df_prefix_by_as_number_in_time_slot.drop_duplicates(subset=['id_as_number', 'network'], keep='last')

                df_prefix_by_as_number_in_time_slot = df_prefix_by_as_number_in_time_slot.groupby(['network', 'autonomous_system']).count()['id_as_number'].reset_index()
                df_prefix_by_as_number_in_time_slot.columns = ['network', 'autonomous_system', 'slot']

                #print('\n-------------------------\n')
                #print('df_prefix_by_as_number_in_time_slot')
                #print(df_prefix_by_as_number_in_time_slot)
                #print('\n-------------------------\n')

                for index, row in df_prefix_by_as_number_in_time_slot.iterrows():
                    registry = df_networks_announced_by_autonomous_systems.loc[row['network'], row['autonomous_system']]
                    registry['slot-%s' % str(i + 1)] = registry['slot-%s' % str(i + 1)] + row['slot']

                df_networks_announced_by_autonomous_systems = df_networks_announced_by_autonomous_systems.reset_index()
                df_networks_announced_by_autonomous_systems = df_networks_announced_by_autonomous_systems.set_index('network')

                #print('\n-------------------------\n')
                #print('df_networks_announced_by_autonomous_systems')
                #print(df_networks_announced_by_autonomous_systems)
                #print('\n-------------------------\n')

                df_networks_announced_by_autonomous_systems_temp = pd.DataFrame(df_networks_announced_by_autonomous_systems.groupby('network').sum()['slot-%s' % str(i + 1)])

                df_networks_announced_by_autonomous_systems = df_networks_announced_by_autonomous_systems.reset_index()
                df_networks_announced_by_autonomous_systems = df_networks_announced_by_autonomous_systems.set_index(['network', 'autonomous_system'])
                for index, row in df_networks_announced_by_autonomous_systems_temp.iterrows():
                    registry = df_networks_announced_by_autonomous_systems.loc[index, 0]
                    registry['slot-%s' % str(i + 1)] = len(set(self.sources)) - row['slot-%s' % str(i + 1)]

                print('\n-------------------------\n')
                print('df_networks_announced_by_autonomous_systems')
                print(df_networks_announced_by_autonomous_systems)
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
        number_of_slots = 4
        # look for path to networks
        #networks = ['208.65.153.0/24', '208.65.153.0/25', '208.65.153.128/25']
        networks = ['147.65.0.0/16', '150.161.0.0/16', '208.65.153.128/25']
        #
        parser.network_by_autonomous_system(number_of_slots, networks)
    except:
        print('usage: ./parser.py file.json')


if __name__ == '__main__':
    main()
