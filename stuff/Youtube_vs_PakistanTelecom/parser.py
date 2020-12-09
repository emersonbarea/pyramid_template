import sys
import json
import ipaddress
from datetime import datetime
from datetime import timezone


class BGPlay(object):
    def __init__(self, argv):
        self.file_from = argv
        self.file_topology = str(argv.split('.')[:-1]).replace('[\'','').replace('\']', '') + '.MiniSecBGP'
        self.file_event = str(argv.split('.')[:-1]).replace('[\'','').replace('\']', '') + '.events'

    def head(self):
        head = {'topology_name': "Youtube vs. Pakistan Telecom"}

        return head

    def autonomous_systems(self):
        data_autonomous_systems = {}
        data_autonomous_systems['autonomous_systems'] = []

        # read BGPlay json file and parse it
        with open(self.file_from) as file:
            data_from = json.load(file)

        origin_autonomous_system = []
        events = data_from['data']['events']
        for event in events:
            if event['type'] == 'A':
                origin_autonomous_system.append(event['attrs']['path'][-1])
        origin_autonomous_system = set(origin_autonomous_system)

        nodes = data_from['data']['nodes']        
        for node in nodes:

            # "autonomous_system"
            autonomous_system = str(node['as_number'])

            # "region" and "router_id"
            region = "other"
            router_id = None
            sources = data_from['data']['sources']
            
            for source in sources:
                if node['as_number'] == source['as_number']:
                    region = "Collector peer"
                    router_id = source['id'].split('-')[1]

            if node['as_number'] in origin_autonomous_system:
                region = "Origin AS"

            # "internet_exchange_points"
            internet_exchange_points = [{'internet_exchange_point': None, 'region': None}]

            # "type_of_users"
            type_of_users = [{'type_of_user': None, 'number': None}]

            # "type_of_services"
            type_of_services = [None]

            # "prefixes"
            prefixes = [{'prefix': None, 'mask': None}]

            data_autonomous_systems['autonomous_systems'].append({
                'autonomous_system': autonomous_system,
                'region': region,
                'router_id': router_id,
                'internet_exchange_points': internet_exchange_points,
                'type_of_users': type_of_users,
                'type_of_services': type_of_services,
                'prefixes': prefixes
            })

        return data_autonomous_systems

    def peers(self):
        data_peers = {}
        data_peers['links'] = []

        # read BGPlay json file and parse it
        with open(self.file_from) as file: 
            data_from = json.load(file)

        events = data_from['data']['events']
        paths = []
            
        # for each event
        for event in events:

            # if it is an announce event (because withdraw event has no path)
            if event['type'] == 'A':
                paths.append(event['attrs']['path'])

        # remove duplicated paths
        paths = set(tuple(i) for i in paths)

        # initialize IP address variable (1.0.0.0)
        prefix_ip = 16777216

        hops = []
        for path in paths:
            previous_autonomous_system = ''
            for autonomous_system in path:

                # "and previous_autonomous_system != autonomous_system" -- to remove prepended ASs from paths
                if previous_autonomous_system and previous_autonomous_system != autonomous_system:
                    hops.append([previous_autonomous_system, autonomous_system])

                previous_autonomous_system = autonomous_system

        # remove duplicated hops
        hops = set(tuple(i) for i in hops)

        for hop in hops:
            # "source"
            source = str(hop[0])

            # "destination"
            destination = str(hop[1])

            # "ip_source"
            ip_source = str(ipaddress.ip_address(prefix_ip + 1))

            # "ip_destination"
            ip_destination = str(ipaddress.ip_address(prefix_ip + 2))

            # "mask"
            mask = "30"

            # "description"
            description = None

            # "agreement"
            agreement = None

            # "bandwidth"
            bandwidth = None

            # "delay"
            delay = None

            # "load"
            load = None

            data_peers['links'].append({
                'source': source,
                'destination': destination,
                'ip_source': ip_source,
                'ip_destination': ip_destination,
                'mask': mask,
                'description': description,
                'agreement': agreement,
                'bandwidth': bandwidth,
                'delay': delay,
                'load': load
            })
                
            prefix_ip = prefix_ip + 4            

        return data_peers

    def json(self, head, autonomous_systems, peers):
        with open(self.file_topology, 'w') as file:
            data = head
            data.update(autonomous_systems)
            data.update(peers)
            json.dump(data, file)

    def bgp_events(self):

        def announce_timestamp(phrase, query_starttime, query_endtime):
            timestamp = input('%s' % phrase)
            try:
                if datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S') < \
                datetime.strptime(query_starttime.replace('T', ' '), '%Y-%m-%d %H:%M:%S') or \
                datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S') > \
                datetime.strptime(query_endtime.replace('T', ' '), '%Y-%m-%d %H:%M:%S'):
                    raise excpection                
            except Exception:
                print('Not a valid timestamp')
                return announce_timestamp(phrase, query_starttime, query_endtime)            

            return timestamp

        def announce_prefix(phrase):
            prefix = input('%s' % phrase)
            try:
                ipaddress.ip_network(prefix)
            except Exception:
                print('Not a valid network address')
                return announce_prefix(phrase)

            return prefix            

        def announce_autonomous_system(phrase, autonomous_systems):
            autonomous_system = input('%s' % phrase)
            try:
                if int(autonomous_system) not in autonomous_systems:
                    raise excpection
            except Exception:
                print('Not a valid Autonomous System in topology')
                return announce_autonomous_system(phrase, autonomous_systems)

            return autonomous_system            

        def times_prepended(phrase):
            is_int = False
            while not is_int:
                try:
                    times = int(input('%s' % phrase))
                    is_int = True
                except ValueError:
                    print('Only int. values')
                    return times_prepended(phrase)

            return times

        # read BGPlay json file and parse it
        with open(self.file_from) as file: 
            data_from = json.load(file)

        query_starttime = data_from['data']['query_starttime']
        query_endtime = data_from['data']['query_endtime']

        nodes = data_from['data']['nodes']
        autonomous_systems = []
        for node in nodes:
            autonomous_systems.append(node['as_number'])

        print('\nThis scenario reproduces the use case Youtube vs. Pakistan Telecom, ' \
              'covering the period between %s and %s.' % (query_starttime, query_endtime))
        
        option = ''
        announcements = []
        prepends = []
        while option not in ('x', 'X'):
            print('\nChoose the option below that corresponds to the type of event you want ' \
                  'to create or exit.\n')
            print('1 - Add a prefix announcement\n' \
                  '2 - Prepend an Autonomous System\n' \
                  'X - exit\n')
            option = input('Option: ')
            
            while option not in ('1', '2', 'x', 'X'):
                print('press only valid options')
                option = input('Option: ')

            if option == '1':

                phrase = 'Write the timestamp of the prefix announcement (Ex.: 2008-02-24 18:47:57): '
                timestamp = announce_timestamp(phrase, query_starttime, query_endtime)
                
                phrase = 'Write the prefix/mask to announce (Ex.: 200.1.2.0/24): '
                prefix = announce_prefix(phrase)
                
                phrase = 'Write the Autonomous System that will announced (Ex.: 1916): '
                autonomous_system = announce_autonomous_system(phrase, autonomous_systems)
                
                announcements.append([timestamp, prefix, autonomous_system])

            elif option == '2':
                
                phrase = 'Write the timestamp of the prepend announcement (Ex.: 2008-02-24 18:47:57): '
                timestamp = announce_timestamp(phrase, query_starttime, query_endtime)
                
                phrase = 'Write the Autonomous System that will be prepended (Ex.: 1916): '
                prepended_AS = announce_autonomous_system(phrase, autonomous_systems)

                phrase = 'Write how many times AS %s will be prepende (Ex.: 2): ' % prepended_AS
                times = times_prepended(phrase)
                
                phrase = 'Write the Autonomous System that will originate the prepended announcements (Ex.: 1916): '
                prepender_AS = announce_autonomous_system(phrase, autonomous_systems)

                prepends.append([timestamp, prepended_AS, times, prepender_AS])

            elif option in ('x', 'X'):
                return

            print('\nAnnouncements added until now:\n')
            for announce in announcements:    
                print('Timestamp: %s - Prefix: %s - Source: %s' % 
                    (announce[0], announce[1], announce[2]))
            
            print('\nPrepends added until now:\n')
            for prepend in prepends:    
                print('Timestamp: %s - Prepended AS: %s - How many times: %s - Prepender AS: %s' % 
                    (prepend[0], prepend[1], prepend[2], prepend[3]))

        


def main(argv=sys.argv[1]):    
    bgplay = BGPlay(argv)
    head = bgplay.head()
    autonomous_systems = bgplay.autonomous_systems()
    peers = bgplay.peers()
    bgplay.json(head, autonomous_systems, peers)
    bgplay.bgp_events()


if __name__ == '__main__':
    main()