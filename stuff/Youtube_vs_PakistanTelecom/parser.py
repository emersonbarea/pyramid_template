import json
import ipaddress


class BGPlay(object):
    def __init__(self):
        self.file_from = 'BGPlay.json'
        self.file_to = 'Youtbe_vs_PakistanTelecom.MiniSecBGP'

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
        with open(self.file_to, 'w') as file:
            data = head
            data.update(autonomous_systems)
            data.update(peers)
            json.dump(data, file)


def main():    
    bgplay = BGPlay()
    head = bgplay.head()
    autonomous_systems = bgplay.autonomous_systems()
    peers = bgplay.peers()
    bgplay.json(head, autonomous_systems, peers)


if __name__ == '__main__':
    main()