import argparse
import getopt
import json
import os
import subprocess
import sys
import ipaddress

import pandas as pd

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy import func
from sqlalchemy.exc import OperationalError, IntegrityError

from minisecbgp import models


class BGPlayTopology(object):
    def __init__(self, file):
        self.file_from = file

    def create(self, dbsession):

        with open(self.file_from) as json_file:
            data = json.load(json_file)
        json_file.close()

        # Topology
        try:
            topology_type = dbsession.query(models.TopologyType).\
                filter(func.lower(models.TopologyType.topology_type) == 'ripe ncc bgplay').first()
            dictionary_topology = {'id_topology_type': [topology_type.id],
                                   'topology': [self.file_from.split('-')[1:][0].split('.')[:-1][0]],
                                   'description': ['RIPE NCC BGPlay topology (from json file)']}
            df_topology = pd.DataFrame(data=dictionary_topology)
            df_topology.to_sql('topology', con=dbsession.bind, if_exists='append', index=False)

            # get Topology ID
            id_topology = dbsession.query(models.Topology.id).filter_by(topology=self.file_from.split('-')[1:][0].split('.')[:-1][0]).first()
        except IntegrityError as error:
            return 'The topology name "%s" already exists.' % data['topology_name']
        except Exception as error:
            return error

        try:
            list_autonomous_system = list()
            list_router_id_ip_address = list()
            list_region_autonomous_system = list()

            origin_autonomous_system = list()
            events = data['data']['events']
            for event in events:
                if event['type'] == 'A':
                    print(event['attr']['target_prefix'])
                    origin_autonomous_system.append(event['attrs']['path'][-1])
            origin_autonomous_system = set(origin_autonomous_system)

            nodes = data['data']['nodes']
            for node in nodes:

                # "autonomous_system"
                autonomous_system = str(node['as_number'])

                # "region" and "router_id"
                region = "other"
                router_id = None
                sources = data['data']['sources']

                for source in sources:
                    if node['as_number'] == source['as_number']:
                        region = "Collector peer"
                        router_id = source['id'].split('-')[1]

                if node['as_number'] in origin_autonomous_system:
                    region = "Origin AS"

                list_autonomous_system.append(autonomous_system)
                list_router_id_ip_address.append(router_id)
                list_region_autonomous_system.append(region)

            # Region
            list_region = list(['-- undefined region --']) + list_region_autonomous_system
            df_region = pd.DataFrame({'region': list_region})
            df_region = df_region.drop_duplicates(keep='first')
            df_region = df_region.dropna()
            df_region = df_region.reset_index(drop=True)

            colors = dbsession.query(models.Color.id).all()
            df_region = pd.concat([df_region, pd.DataFrame({'id_color': colors})], axis=1)
            df_region = df_region.dropna()

            df_region = pd.concat([df_region.assign(id_topology=id_topology) for id_topology in id_topology])
            df_region.to_sql('region', con=dbsession.bind, if_exists='append', index=False)
            # get Region ID
            regions = dbsession.query(models.Region).filter_by(id_topology=id_topology).all()

            # Autonomous System
            df_autonomous_system = pd.DataFrame({'autonomous_system': list_autonomous_system,
                                                 'id_region': list_region_autonomous_system,
                                                 'stub': False})
            df_autonomous_system.fillna(value='-- undefined region --', inplace=True)
            df_autonomous_system.reset_index()
            df_autonomous_system.set_index('id_region', inplace=True)
            for region in regions:
                df_autonomous_system.rename(index={region.region: region.id}, inplace=True)
            df_autonomous_system = df_autonomous_system.reset_index().copy()
            df_autonomous_system = df_autonomous_system.drop_duplicates(keep='first')
            df_autonomous_system = pd.concat(
                [df_autonomous_system.assign(id_topology=id_topology) for id_topology in id_topology])
            df_autonomous_system.to_sql('autonomous_system', con=dbsession.bind, if_exists='append', index=False)
            # get Autonomous System ID
            autonomous_systems = dbsession.query(models.AutonomousSystem).filter_by(id_topology=id_topology).all()

            # Router_id
            df_router_id = pd.DataFrame({'id_autonomous_system': list_autonomous_system,
                                         'router_id': list_router_id_ip_address})
            df_router_id = df_router_id.dropna()
            df_router_id.reset_index()
            df_router_id.set_index('id_autonomous_system', inplace=True)
            for autonomous_system in autonomous_systems:
                df_router_id.rename(index={str(autonomous_system.autonomous_system): autonomous_system.id}, inplace=True)
            df_router_id = df_router_id.reset_index().copy()

            df_router_id.to_sql('router_id', con=dbsession.bind, if_exists='append', index=False)

            # Peers
            data_peers = dict()
            data_peers['links'] = list()

            events = data['data']['events']

            paths = list()
            # for each event
            for event in events:
                # if it is an update event (because withdraw event has no path)
                if event['type'] == 'A':
                    paths.append(event['attrs']['path'])

            # remove duplicated paths

            paths = set(tuple(i) for i in paths)

            hops = []
            for path in paths:
                previous_autonomous_system = ''
                for autonomous_system in path:

                    # "and previous_autonomous_system != autonomous_system" -- to remove prepended ASs from paths
                    if previous_autonomous_system and previous_autonomous_system != autonomous_system:
                        hops.append([previous_autonomous_system, autonomous_system])

                    previous_autonomous_system = autonomous_system

            # removes duplicated hops
            hops = set(tuple(i) for i in hops)

            # removes duplicated inverted hops
            final_hops = []
            for hop in hops:
                inverted_hop = tuple([hop[1], hop[0]])
                if inverted_hop not in final_hops:
                    final_hops.append(tuple([hop[0], hop[1]]))
            hops = final_hops

            list_link_source = list()
            list_link_destination = list()
            list_link_ip_source = list()
            list_link_ip_destination = list()
            list_link_mask = list()
            list_link_description = list()
            list_link_agreement = list()
            list_link_bandwidth = list()
            list_link_delay = list()
            list_link_load = list()
            list_stub = list()

            # initialize IP address variable (1.0.0.0)
            prefix_ip = 16777216

            for hop in hops:
                list_link_source.append(hop[0])
                list_link_destination.append(hop[1])
                list_link_ip_source.append(str(ipaddress.ip_address(prefix_ip + 1)))
                list_link_ip_destination.append(str(ipaddress.ip_address(prefix_ip + 2)))
                list_link_mask.append(30)
                list_link_description.append(None)
                list_link_agreement.append(None)
                list_link_bandwidth.append(None)
                list_link_delay.append(None)
                list_link_load.append(None)
                list_stub.append(hop[0])
                list_stub.append(hop[1])

                prefix_ip = prefix_ip + 4

            for i in range(len(list_link_agreement)):
                if list_link_agreement[i] is None:
                    list_link_agreement[i] = 'a2a'

            df_link = pd.DataFrame({'id_link_agreement': list_link_agreement,
                                    'id_autonomous_system1': list_link_source,
                                    'id_autonomous_system2': list_link_destination,
                                    'ip_autonomous_system1': list_link_ip_source,
                                    'ip_autonomous_system2': list_link_ip_destination,
                                    'mask': list_link_mask,
                                    'description': list_link_description,
                                    'bandwidth': list_link_bandwidth,
                                    'delay': list_link_delay,
                                    'load': list_link_load})

            link_agreements = dbsession.query(models.LinkAgreement).all()
            df_link.reset_index()
            df_link.set_index('id_link_agreement', inplace=True)
            for link_agreement in link_agreements:
                df_link.rename(index={str(link_agreement.agreement): link_agreement.id}, inplace=True)
            df_link = df_link.reset_index().copy()

            df_link.reset_index()
            df_link.set_index('id_autonomous_system1', inplace=True)
            for autonomous_system in autonomous_systems:
                df_link.rename(index={autonomous_system.autonomous_system: autonomous_system.id}, inplace=True)
            df_link = df_link.reset_index().copy()

            df_link.reset_index()
            df_link.set_index('id_autonomous_system2', inplace=True)
            for autonomous_system in autonomous_systems:
                df_link.rename(index={autonomous_system.autonomous_system: autonomous_system.id}, inplace=True)
            df_link = df_link.reset_index().copy()

            df_link = pd.concat([df_link.assign(id_topology=id_topology) for id_topology in id_topology])
            df_link.to_sql('link', con=dbsession.bind, if_exists='append', index=False)

            # Autonomous System Stub
            df_stub = pd.DataFrame({'id_autonomous_system': list_stub})
            df_stub = df_stub.drop_duplicates(keep=False)

            df_stub.reset_index()
            df_stub.set_index('id_autonomous_system', inplace=True)
            for autonomous_system in autonomous_systems:
                df_stub.rename(index={autonomous_system.autonomous_system: autonomous_system.id}, inplace=True)
            df_stub = df_stub.reset_index().copy()
            for row in df_stub.itertuples():
                autonomous_system = dbsession.query(models.AutonomousSystem).filter_by(id=row[1]).first()
                autonomous_system.stub = True

        except Exception as error:
            arguments = ['--config-file=minisecbgp.ini',
                         '--topology=%s' % id_topology]
            subprocess.Popen(['./venv/bin/MiniSecBGP_delete_topology'] + arguments)
            return error

    @staticmethod
    def downloading(dbsession, downloading):
        entry = dbsession.query(models.DownloadingTopology).first()
        entry.downloading = downloading

    def erase_file(self):
        os.remove(self.file_from)


def parse_args(config_file):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(config_file.split())


def main(argv=sys.argv[1:]):
    try:
        opts, args = getopt.getopt(argv, "h", ["config-file=", "file="])
    except getopt.GetoptError:
        print('\n'
              'Usage: MiniSecBGP_bgplay_topology [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
              '--file=BGPlay-Scenario-1.BGPlay                  json topology filename from BGPlay(.BGPlay extension)\n')
        sys.exit(2)
    config_file = file = ''
    for opt, arg in opts:
        if opt == '-h':
            print('\n'
                  'Usage: MiniSecBGP_bgplay_topology [options]\n'
                  '\n'
                  'options (with examples):\n'
                  '\n'
                  '-h                                               this help\n'
                  '\n'
                  '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
                  '--file=BGPlay-Scenario-1.BGPlay                  json topology filename from BGPlay(.BGPlay extension)\n')
            sys.exit()
        elif opt == '--config-file':
            config_file = arg
        elif opt == '--file':
            file = arg
    if config_file and file:
        args = parse_args(config_file)
        setup_logging(args.config_uri)
        env = bootstrap(args.config_uri)
        try:
            bgplayt = BGPlayTopology(file)
            with env['request'].tm:
                dbsession = env['request'].dbsession
                downloading = 1
                bgplayt.downloading(dbsession, downloading)
            with env['request'].tm:
                dbsession = env['request'].dbsession
                result = bgplayt.create(dbsession)
            with env['request'].tm:
                dbsession = env['request'].dbsession
                downloading = 0
                bgplayt.downloading(dbsession, downloading)
            bgplayt.erase_file()
            if result:
                print(result)
        except OperationalError:
            print('Database error')
    else:
        print('\n'
              'Usage: MiniSecBGP_manual_topology [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
              '--file=BGPlay-Scenario-1.BGPlay                  json topology filename from BGPlay(.BGPlay extension)\n')