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


class ManualTopology(object):
    def __init__(self, file):
        self.file = file

    def create(self, dbsession):
        with open(self.file) as json_file:
            data = json.load(json_file)
        json_file.close()

        # Topology
        try:
            topology_type = dbsession.query(models.TopologyType).\
                filter(func.lower(models.TopologyType.topology_type) == 'minisecbgp').first()
            dictionary_topology = {'id_topology_type': [topology_type.id],
                                   'topology': [data['topology_name']],
                                   'description': ['Manual topology (from json file)']}
            df_topology = pd.DataFrame(data=dictionary_topology)
            df_topology.to_sql('topology', con=dbsession.bind, if_exists='append', index=False)
            # get Topology ID
            id_topology = dbsession.query(models.Topology.id).filter_by(topology=data['topology_name']).first()
        except IntegrityError as error:
            return 'The topology name "%s" already exists.' % data['topology_name']
        except Exception as error:
            return error

        try:
            list_autonomous_system = list()
            list_router_id_ip_address = list()
            list_region_autonomous_system = list()
            list_region_internet_exchange_point = list()
            list_autonomous_system_internet_exchange_point = list()
            list_internet_exchange_point = list()
            list_type_of_user = list()
            list_type_of_user_number = list()
            list_type_of_user_autonomous_system = list()
            list_type_of_service = list()
            list_type_of_service_autonomous_system = list()
            list_prefix_autonomous_system = list()
            list_prefix = list()
            list_prefix_mask = list()

            for row1 in range(len(data['autonomous_systems'])):
                list_autonomous_system.append(data['autonomous_systems'][row1]['autonomous_system'])
                list_region_autonomous_system.append(data['autonomous_systems'][row1]['region'])
                list_router_id_ip_address.append(data['autonomous_systems'][row1]['router_id'])

                for row2 in range(len(data['autonomous_systems'][row1]['internet_exchange_points'])):
                    list_autonomous_system_internet_exchange_point.append(data['autonomous_systems'][row1]['autonomous_system'])
                    list_internet_exchange_point.append(
                        data['autonomous_systems'][row1]['internet_exchange_points'][row2]['internet_exchange_point'])
                    list_region_internet_exchange_point.append(
                        data['autonomous_systems'][row1]['internet_exchange_points'][row2]['region'])

                for row3 in range(len(data['autonomous_systems'][row1]['type_of_users'])):
                    list_type_of_user_autonomous_system.append(data['autonomous_systems'][row1]['autonomous_system'])
                    list_type_of_user.append(data['autonomous_systems'][row1]['type_of_users'][row3]['type_of_user'])
                    list_type_of_user_number.append(data['autonomous_systems'][row1]['type_of_users'][row3]['number'])

                for row4 in range(len(data['autonomous_systems'][row1]['type_of_services'])):
                    list_type_of_service_autonomous_system.append(data['autonomous_systems'][row1]['autonomous_system'])
                    list_type_of_service.append(data['autonomous_systems'][row1]['type_of_services'][row4])

                for row5 in range(len(data['autonomous_systems'][row1]['prefixes'])):
                    list_prefix_autonomous_system.append(data['autonomous_systems'][row1]['autonomous_system'])
                    list_prefix.append(data['autonomous_systems'][row1]['prefixes'][row5]['prefix'])
                    list_prefix_mask.append(data['autonomous_systems'][row1]['prefixes'][row5]['mask'])

            # Region
            list_region = list(['-- undefined region --']) + list_region_autonomous_system + list_region_internet_exchange_point
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

            # Internet eXchange Point
            df_internet_exchange_point = pd.DataFrame({'internet_exchange_point': list_internet_exchange_point,
                                                      'id_region': list_region_internet_exchange_point})
            df_internet_exchange_point.reset_index()
            df_internet_exchange_point.set_index('id_region', inplace=True)
            for region in regions:
                df_internet_exchange_point.rename(index={region.region: region.id}, inplace=True)
            df_internet_exchange_point = df_internet_exchange_point.reset_index().copy()
            df_internet_exchange_point = df_internet_exchange_point.drop_duplicates(keep='first')
            df_internet_exchange_point = df_internet_exchange_point.dropna()
            df_internet_exchange_point = pd.concat(
                [df_internet_exchange_point.assign(id_topology=id_topology) for id_topology in id_topology])
            df_internet_exchange_point.to_sql('internet_exchange_point', con=dbsession.bind, if_exists='append', index=False)
            # get Internet eXchange Point ID
            internet_exchange_points = dbsession.query(models.InternetExchangePoint).filter_by(id_topology=id_topology).all()

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

            # Autonomous System in Internet eXchange Point
            df_autonomous_system_internet_exchange_point = pd.DataFrame(
                {'id_autonomous_system': list_autonomous_system_internet_exchange_point,
                 'internet_exchange_point': list_internet_exchange_point,
                 'id_internet_exchange_point': list_region_internet_exchange_point})
            df_autonomous_system_internet_exchange_point = df_autonomous_system_internet_exchange_point.drop_duplicates(keep='first')
            df_autonomous_system_internet_exchange_point = df_autonomous_system_internet_exchange_point.dropna()

            df_autonomous_system_internet_exchange_point.reset_index()
            df_autonomous_system_internet_exchange_point.set_index('id_autonomous_system', inplace=True)
            for autonomous_system in autonomous_systems:
                df_autonomous_system_internet_exchange_point.rename(
                    index={str(autonomous_system.autonomous_system): autonomous_system.id}, inplace=True)
            df_autonomous_system_internet_exchange_point = df_autonomous_system_internet_exchange_point.reset_index().copy()

            df_autonomous_system_internet_exchange_point.reset_index()
            df_autonomous_system_internet_exchange_point.set_index('id_internet_exchange_point', inplace=True)
            for region in regions:
                df_autonomous_system_internet_exchange_point.rename(index={region.region: region.id}, inplace=True)
            df_autonomous_system_internet_exchange_point = df_autonomous_system_internet_exchange_point.reset_index().copy()

            df_autonomous_system_internet_exchange_point['id_internet_exchange_point'] = \
                df_autonomous_system_internet_exchange_point['id_internet_exchange_point'].astype(str) + \
                df_autonomous_system_internet_exchange_point['internet_exchange_point']
            del df_autonomous_system_internet_exchange_point['internet_exchange_point']

            df_autonomous_system_internet_exchange_point.reset_index()
            df_autonomous_system_internet_exchange_point.set_index('id_internet_exchange_point', inplace=True)
            for internet_exchange_point in internet_exchange_points:
                df_autonomous_system_internet_exchange_point.rename(index={str(
                    internet_exchange_point.id_region) + internet_exchange_point.internet_exchange_point: internet_exchange_point.id},
                                                                    inplace=True)
            df_autonomous_system_internet_exchange_point = df_autonomous_system_internet_exchange_point.reset_index().copy()

            df_autonomous_system_internet_exchange_point.to_sql('autonomous_system_internet_exchange_point',
                                                                con=dbsession.bind, if_exists='append', index=False)

            # Type of User
            df_type_of_user = pd.DataFrame({'type_of_user': list_type_of_user})
            df_type_of_user = df_type_of_user.drop_duplicates(keep='first')
            df_type_of_user = df_type_of_user.dropna()
            df_type_of_user = pd.concat(
                [df_type_of_user.assign(id_topology=id_topology) for id_topology in id_topology])
            df_type_of_user.to_sql('type_of_user', con=dbsession.bind, if_exists='append', index=False)
            # get Type of User ID
            types_of_user = dbsession.query(models.TypeOfUser).filter_by(id_topology=id_topology).all()

            # Number of User by Type by Autonomous System
            df_type_of_user_autonomous_system = pd.DataFrame(
                {'id_autonomous_system': list_type_of_user_autonomous_system,
                 'id_type_of_user': list_type_of_user,
                 'number': list_type_of_user_number})
            df_type_of_user_autonomous_system = df_type_of_user_autonomous_system.drop_duplicates(keep='first')
            df_type_of_user_autonomous_system = df_type_of_user_autonomous_system.dropna()

            df_type_of_user_autonomous_system.reset_index()
            df_type_of_user_autonomous_system.set_index('id_autonomous_system', inplace=True)
            for autonomous_system in autonomous_systems:
                df_type_of_user_autonomous_system.rename(
                    index={str(autonomous_system.autonomous_system): autonomous_system.id}, inplace=True)
            df_type_of_user_autonomous_system = df_type_of_user_autonomous_system.reset_index().copy()

            df_type_of_user_autonomous_system.reset_index()
            df_type_of_user_autonomous_system.set_index('id_type_of_user', inplace=True)
            for type_of_user in types_of_user:
                df_type_of_user_autonomous_system.rename(index={type_of_user.type_of_user: type_of_user.id}, inplace=True)
            df_type_of_user_autonomous_system = df_type_of_user_autonomous_system.reset_index().copy()
            df_type_of_user_autonomous_system.to_sql('type_of_user_autonomous_system', con=dbsession.bind,
                                                     if_exists='append', index=False)

            # Type of Service
            df_type_of_service = pd.DataFrame({'type_of_service': list_type_of_service})
            df_type_of_service = df_type_of_service.drop_duplicates(keep='first')
            df_type_of_service = df_type_of_service.dropna()
            df_type_of_service = pd.concat(
                [df_type_of_service.assign(id_topology=id_topology) for id_topology in id_topology])
            df_type_of_service.to_sql('type_of_service', con=dbsession.bind, if_exists='append', index=False)
            # get Type of Service ID
            types_of_service = dbsession.query(models.TypeOfService).filter_by(id_topology=id_topology).all()

            # Type of Service by Autonomous System
            df_type_of_service_autonomous_system = pd.DataFrame(
                {'id_autonomous_system': list_type_of_service_autonomous_system,
                 'id_type_of_service': list_type_of_service})
            df_type_of_service_autonomous_system = df_type_of_service_autonomous_system.drop_duplicates(keep='first')
            df_type_of_service_autonomous_system = df_type_of_service_autonomous_system.dropna()

            df_type_of_service_autonomous_system.reset_index()
            df_type_of_service_autonomous_system.set_index('id_autonomous_system', inplace=True)
            for autonomous_system in autonomous_systems:
                df_type_of_service_autonomous_system.rename(
                    index={str(autonomous_system.autonomous_system): autonomous_system.id}, inplace=True)
            df_type_of_service_autonomous_system = df_type_of_service_autonomous_system.reset_index().copy()

            df_type_of_service_autonomous_system.reset_index()
            df_type_of_service_autonomous_system.set_index('id_type_of_service', inplace=True)
            for type_of_service in types_of_service:
                df_type_of_service_autonomous_system.rename(index={type_of_service.type_of_service: type_of_service.id}, inplace=True)
            df_type_of_service_autonomous_system = df_type_of_service_autonomous_system.reset_index().copy()
            df_type_of_service_autonomous_system.to_sql('type_of_service_autonomous_system', con=dbsession.bind,
                                                        if_exists='append', index=False)

            # Prefix
            df_prefix = pd.DataFrame({'id_autonomous_system': list_prefix_autonomous_system,
                                      'prefix': list_prefix,
                                      'mask': list_prefix_mask})
            df_prefix = df_prefix.dropna()
            df_prefix.reset_index()
            df_prefix.set_index('id_autonomous_system', inplace=True)
            for autonomous_system in autonomous_systems:
                df_prefix.rename(index={str(autonomous_system.autonomous_system): autonomous_system.id}, inplace=True)
            df_prefix = df_prefix.reset_index().copy()

            df_prefix.to_sql('prefix', con=dbsession.bind, if_exists='append', index=False)

            # Link
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

            for row1 in range(len(data['links'])):
                list_link_source.append(data['links'][row1]['source'])
                list_link_destination.append(data['links'][row1]['destination'])
                list_link_ip_source.append(str(ipaddress.ip_address(data['links'][row1]['ip_source'])))
                list_link_ip_destination.append(str(ipaddress.ip_address(data['links'][row1]['ip_destination'])))
                list_link_mask.append(data['links'][row1]['mask'])
                list_link_description.append(data['links'][row1]['description'])
                list_link_agreement.append(data['links'][row1]['agreement'])
                list_link_bandwidth.append(data['links'][row1]['bandwidth'])
                list_link_delay.append(data['links'][row1]['delay'])
                list_link_load.append(data['links'][row1]['load'])
                list_stub.append(data['links'][row1]['source'])
                list_stub.append(data['links'][row1]['destination'])

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
                df_link.rename(index={str(autonomous_system.autonomous_system): autonomous_system.id}, inplace=True)
            df_link = df_link.reset_index().copy()

            df_link.reset_index()
            df_link.set_index('id_autonomous_system2', inplace=True)
            for autonomous_system in autonomous_systems:
                df_link.rename(index={str(autonomous_system.autonomous_system): autonomous_system.id}, inplace=True)
            df_link = df_link.reset_index().copy()

            df_link = pd.concat([df_link.assign(id_topology=id_topology) for id_topology in id_topology])
            df_link.to_sql('link', con=dbsession.bind, if_exists='append', index=False)

            # Autonomous System Stub
            df_stub = pd.DataFrame({'id_autonomous_system': list_stub})
            df_stub = df_stub.drop_duplicates(keep=False)

            df_stub.reset_index()
            df_stub.set_index('id_autonomous_system', inplace=True)
            for autonomous_system in autonomous_systems:
                df_stub.rename(index={str(autonomous_system.autonomous_system): autonomous_system.id}, inplace=True)
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
        os.remove(self.file)


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
              'Usage: MiniSecBGP_manual_topology [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
              '--file=Manual-Topology-1.MiniSecBGP              json topology filename (.MiniSecBGP extension)\n')
        sys.exit(2)
    config_file = file = ''
    for opt, arg in opts:
        if opt == '-h':
            print('\n'
                  'Usage: MiniSecBGP_manual_topology [options]\n'
                  '\n'
                  'options (with examples):\n'
                  '\n'
                  '-h                                               this help\n'
                  '\n'
                  '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
                  '--file=Manual-Topology-1.MiniSecBGP              json topology filename (.MiniSecBGP extension)\n')
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
            mt = ManualTopology(file)
            with env['request'].tm:
                dbsession = env['request'].dbsession
                downloading = 1
                mt.downloading(dbsession, downloading)
            with env['request'].tm:
                dbsession = env['request'].dbsession
                result = mt.create(dbsession)
            with env['request'].tm:
                dbsession = env['request'].dbsession
                downloading = 0
                mt.downloading(dbsession, downloading)
            mt.erase_file()
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
              '--file=Manual-Topology-1.MiniSecBGP              json topology filename (.MiniSecBGP extension)\n')