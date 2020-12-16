import argparse
import getopt
import subprocess
import sys

import pandas as pd
from pyramid.paster import bootstrap, setup_logging

from minisecbgp import models


class DuplicateTopology(object):
    def __init__(self):
        pass

    @staticmethod
    def duplicate_topology(dbsession, old_id_topology, new_topology_name):
        try:

            # Topology
            old_topology = dbsession.query(models.Topology).\
                filter_by(id=old_id_topology).first()
            new_topology = models.Topology(topology=new_topology_name,
                                           id_topology_type=old_topology.id_topology_type,
                                           description=old_topology.description)
            dbsession.add(new_topology)

            dbsession.flush()

            return new_topology.id

        except Exception as error:
            print('Error -------- 1 -------- : ', error)
            dbsession.rollback()

    @staticmethod
    def duplicate_region_data(dbsession, old_id_topology, new_id_topology):
        try:

            # Region
            old_regions = dbsession.query(models.Region). \
                filter_by(id_topology=old_id_topology).all()
            for old_region in old_regions:
                new_region = models.Region(id_topology=new_id_topology,
                                           id_color=old_region.id_color,
                                           region=old_region.region)
                dbsession.add(new_region)

            # Type of Service
            old_types_of_service = dbsession.query(models.TypeOfService). \
                filter_by(id_topology=old_id_topology).all()
            for old_type_of_service in old_types_of_service:
                new_type_of_service = models.TypeOfService(id_topology=new_id_topology,
                                                           type_of_service=old_type_of_service.type_of_service)
                dbsession.add(new_type_of_service)

            # Type of User
            old_types_of_user = dbsession.query(models.TypeOfUser). \
                filter_by(id_topology=old_id_topology).all()
            for old_type_of_user in old_types_of_user:
                new_type_of_user = models.TypeOfUser(id_topology=new_id_topology,
                                                     type_of_user=old_type_of_user.type_of_user)
                dbsession.add(new_type_of_user)

            dbsession.flush()

        except Exception as error:
            print('Error -------- 2 -------- : ', error)
            dbsession.rollback()
            arguments = ['--config-file=minisecbgp.ini',
                         '--topology=%s' % new_id_topology]
            subprocess.Popen(['./venv/bin/MiniSecBGP_delete_topology'] + arguments)

    @staticmethod
    def duplicate_autonomous_system_data(dbsession, old_id_topology, new_id_topology):
        try:

            new_region_list = dbsession.query(models.Region).\
                filter_by(id_topology=new_id_topology).all()

            # Internet Exchange Point
            query = 'select %s as id_topology, ' \
                    '(select r.region ' \
                    'from region r ' \
                    'where r.id_topology = ixp.id_topology and ' \
                    'r.id = ixp.id_region) as id_region, ' \
                    'internet_exchange_point as internet_exchange_point ' \
                    'from internet_exchange_point ixp ' \
                    'where ixp.id_topology  = %s;' % (new_id_topology, old_id_topology)
            result_proxy = dbsession.bind.execute(query)
            df_internet_exchange_point = pd.DataFrame(
                result_proxy, columns=['id_topology', 'id_region', 'internet_exchange_point'])

            df_internet_exchange_point.reset_index()
            df_internet_exchange_point.set_index('id_region', inplace=True)

            for region in new_region_list:
                df_internet_exchange_point.rename(index={str(region.region): region.id}, inplace=True)
            df_internet_exchange_point = df_internet_exchange_point.reset_index().copy()

            df_internet_exchange_point.to_sql(
                'internet_exchange_point', con=dbsession.bind, if_exists='append', index=False)

            # Autonomous System
            query = 'select %s as id_topology, ' \
                    '(select r.region ' \
                    'from region r ' \
                    'where r.id_topology = asys.id_topology and ' \
                    'r.id = asys.id_region) as id_region, ' \
                    'asys.autonomous_system as autonomous_system, ' \
                    'asys.stub as stub ' \
                    'from autonomous_system asys ' \
                    'where asys.id_topology  = %s;' % (new_id_topology, old_id_topology)
            result_proxy = dbsession.bind.execute(query)
            df_autonomous_system = pd.DataFrame(
                result_proxy, columns=['id_topology', 'id_region', 'autonomous_system', 'stub'])

            df_autonomous_system.reset_index()
            df_autonomous_system.set_index('id_region', inplace=True)

            for region in new_region_list:
                df_autonomous_system.rename(index={str(region.region): region.id}, inplace=True)
            df_autonomous_system = df_autonomous_system.reset_index().copy()

            df_autonomous_system.to_sql(
                'autonomous_system', con=dbsession.bind, if_exists='append', index=False)

            dbsession.flush()

        except Exception as error:
            print('Error -------- 3 -------- : ', error)
            dbsession.rollback()
            arguments = ['--config-file=minisecbgp.ini',
                         '--topology=%s' % new_id_topology]
            subprocess.Popen(['./venv/bin/MiniSecBGP_delete_topology'] + arguments)

    @staticmethod
    def duplicate_another_data(dbsession, old_id_topology, new_id_topology):
        try:

            new_autonomous_system_list = dbsession.query(models.AutonomousSystem).\
                filter_by(id_topology=new_id_topology).all()

            # Type of User - Autonomous System
            new_type_of_user_list = dbsession.query(models.TypeOfUser). \
                filter_by(id_topology=new_id_topology).all()

            query = 'select asys.autonomous_system as autonomous_system, ' \
                    'tou.type_of_user as type_of_user, ' \
                    'touasys.number as number ' \
                    'from autonomous_system asys, ' \
                    'type_of_user tou, ' \
                    'type_of_user_autonomous_system touasys ' \
                    'where asys.id_topology = %s ' \
                    'and asys.id = touasys.id_autonomous_system ' \
                    'and touasys.id_type_of_user = tou.id;' % old_id_topology
            result_proxy = dbsession.bind.execute(query)
            df_type_of_user_autonomous_system = pd.DataFrame(
                result_proxy, columns=['id_autonomous_system', 'id_type_of_user', 'number'])

            df_type_of_user_autonomous_system.reset_index()
            df_type_of_user_autonomous_system.set_index('id_autonomous_system', inplace=True)

            for autonomous_system in new_autonomous_system_list:
                df_type_of_user_autonomous_system.rename(
                    index={autonomous_system.autonomous_system: autonomous_system.id}, inplace=True)
            df_type_of_user_autonomous_system = df_type_of_user_autonomous_system.reset_index().copy()

            df_type_of_user_autonomous_system.reset_index()
            df_type_of_user_autonomous_system.set_index('id_type_of_user', inplace=True)
            for type_of_user in new_type_of_user_list:
                df_type_of_user_autonomous_system.rename(
                    index={str(type_of_user.type_of_user): type_of_user.id}, inplace=True)
            df_type_of_user_autonomous_system = df_type_of_user_autonomous_system.reset_index().copy()

            df_type_of_user_autonomous_system.to_sql(
                'type_of_user_autonomous_system', con=dbsession.bind, if_exists='append', index=False)

            # Type of Service - Autonomous System
            new_type_of_service_list = dbsession.query(models.TypeOfService). \
                filter_by(id_topology=new_id_topology).all()

            query = 'select asys.autonomous_system as autonomous_system, ' \
                    'tos.type_of_service as type_of_service ' \
                    'from autonomous_system asys, ' \
                    'type_of_service tos, ' \
                    'type_of_service_autonomous_system tosasys ' \
                    'where asys.id_topology = %s ' \
                    'and asys.id = tosasys.id_autonomous_system ' \
                    'and tosasys.id_type_of_service = tos.id;' % old_id_topology
            result_proxy = dbsession.bind.execute(query)
            df_type_of_service_autonomous_system = pd.DataFrame(
                result_proxy, columns=['id_autonomous_system', 'id_type_of_service'])

            df_type_of_service_autonomous_system.reset_index()
            df_type_of_service_autonomous_system.set_index('id_autonomous_system', inplace=True)

            for autonomous_system in new_autonomous_system_list:
                df_type_of_service_autonomous_system.rename(
                    index={autonomous_system.autonomous_system: autonomous_system.id}, inplace=True)
            df_type_of_service_autonomous_system = df_type_of_service_autonomous_system.reset_index().copy()

            df_type_of_service_autonomous_system.reset_index()
            df_type_of_service_autonomous_system.set_index('id_type_of_service', inplace=True)
            for type_of_service in new_type_of_service_list:
                df_type_of_service_autonomous_system.rename(
                    index={str(type_of_service.type_of_service): type_of_service.id}, inplace=True)
            df_type_of_service_autonomous_system = df_type_of_service_autonomous_system.reset_index().copy()

            df_type_of_service_autonomous_system.to_sql(
                'type_of_service_autonomous_system', con=dbsession.bind, if_exists='append', index=False)

            # Internet eXchange Point - Autonomous System
            query = 'select asys.autonomous_system as autonomous_system, ' \
                    'ixp.internet_exchange_point as internet_exchange_point, ' \
                    'r.region as region ' \
                    'from autonomous_system asys, ' \
                    'autonomous_system_internet_exchange_point asysixp, ' \
                    'internet_exchange_point ixp, ' \
                    'region r ' \
                    'where asys.id_topology = %s ' \
                    'and asys.id = asysixp.id_autonomous_system ' \
                    'and asysixp.id_internet_exchange_point = ixp.id ' \
                    'and ixp.id_region = r.id;' % old_id_topology
            result_proxy = dbsession.bind.execute(query)
            df_oldAsysixp = pd.DataFrame(
                result_proxy, columns=['autonomous_system', 'internet_exchange_point', 'region'])

            query = 'select asys.id as id_autonomous_system, ' \
                    'asys.autonomous_system as autonomous_system ' \
                    'from autonomous_system asys ' \
                    'where asys.id_topology = %s;' % new_id_topology
            result_proxy = dbsession.bind.execute(query)
            df_newAsys = pd.DataFrame(
                result_proxy, columns=['id_autonomous_system', 'autonomous_system'])

            query = 'select ixp.id as id_internet_exchange_point, ' \
                    'ixp.internet_exchange_point as internet_exchange_point, ' \
                    'r.region as region ' \
                    'from internet_exchange_point ixp, ' \
                    'region r ' \
                    'where ixp.id_topology = %s ' \
                    'and ixp.id_region = r.id;' % new_id_topology
            result_proxy = dbsession.bind.execute(query)
            df_newIxp = pd.DataFrame(
                result_proxy, columns=['id_internet_exchange_point', 'internet_exchange_point', 'region'])

            df_oldAsysixp_newAsys_temp1 = df_oldAsysixp.merge(
                df_newAsys, how='inner', left_on=['autonomous_system'], right_on=['autonomous_system'])

            df_oldAsysixp_newAsys_temp2 = df_oldAsysixp_newAsys_temp1.merge(
                df_newIxp, how='inner', left_on=['internet_exchange_point', 'region'], right_on=['internet_exchange_point', 'region'])

            df_asysixp = df_oldAsysixp_newAsys_temp2[['id_autonomous_system', 'id_internet_exchange_point']].copy()

            df_asysixp.to_sql('autonomous_system_internet_exchange_point', con=dbsession.bind, if_exists='append', index=False)

            # Peers
            query = 'select %s as id_topology, ' \
                    'l.id_link_agreement as id_link_agreement, ' \
                    '(select asys.autonomous_system ' \
                    'from autonomous_system asys ' \
                    'where asys.id_topology = l.id_topology and ' \
                    'asys.id = l.id_autonomous_system1) as id_autonomous_system1, ' \
                    '(select asys.autonomous_system ' \
                    'from autonomous_system asys ' \
                    'where asys.id_topology = l.id_topology and ' \
                    'asys.id = l.id_autonomous_system2) as id_autonomous_system2, ' \
                    'l.ip_autonomous_system1 as ip_autonomous_system1, ' \
                    'l.ip_autonomous_system2 as ip_autonomous_system2, ' \
                    'l.mask as mask, ' \
                    'l.description as description, ' \
                    'l.bandwidth as bandwidth, ' \
                    'l.delay as delay, ' \
                    'l.load as load ' \
                    'from link l ' \
                    'where l.id_topology = %s;' % (new_id_topology, old_id_topology)
            result_proxy = dbsession.bind.execute(query)
            df_link = pd.DataFrame(result_proxy, columns=['id_topology', 'id_link_agreement', 'id_autonomous_system1',
                                                          'id_autonomous_system2','ip_autonomous_system1',
                                                          'ip_autonomous_system2', 'mask', 'description',
                                                          'bandwidth', 'delay', 'load'])

            df_link.reset_index()
            df_link.set_index('id_autonomous_system1', inplace=True)
            for autonomous_system in new_autonomous_system_list:
                df_link.rename(index={autonomous_system.autonomous_system: autonomous_system.id}, inplace=True)
            df_link = df_link.reset_index().copy()

            df_link.reset_index()
            df_link.set_index('id_autonomous_system2', inplace=True)
            for autonomous_system in new_autonomous_system_list:
                df_link.rename(index={autonomous_system.autonomous_system: autonomous_system.id}, inplace=True)
            df_link = df_link.reset_index().copy()

            df_link.to_sql('link', con=dbsession.bind, if_exists='append', index=False)

            # Prefix
            query = 'select (select asys.autonomous_system ' \
                    'from autonomous_system asys ' \
                    'where asys.id = p.id_autonomous_system) as id_autonomous_system, ' \
                    'p.prefix as prefix, ' \
                    'p.mask as mask ' \
                    'from prefix p ' \
                    'where p.id_autonomous_system in (' \
                    'select asys.id ' \
                    'from autonomous_system asys ' \
                    'where asys.id_topology = %s);' % old_id_topology
            result_proxy = dbsession.bind.execute(query)
            df_prefix = pd.DataFrame(result_proxy, columns=['id_autonomous_system', 'prefix', 'mask'])

            df_prefix.reset_index()
            df_prefix.set_index('id_autonomous_system', inplace=True)
            for autonomous_system in new_autonomous_system_list:
                df_prefix.rename(index={autonomous_system.autonomous_system: autonomous_system.id}, inplace=True)
            df_prefix = df_prefix.reset_index().copy()

            df_prefix.to_sql('prefix', con=dbsession.bind, if_exists='append', index=False)

            # Router-id
            query = 'select (select asys.autonomous_system ' \
                    'from autonomous_system asys ' \
                    'where asys.id = r.id_autonomous_system) as id_autonomous_system, ' \
                    'r.router_id as router_id ' \
                    'from router_id r ' \
                    'where r.id_autonomous_system in (' \
                    'select asys.id ' \
                    'from autonomous_system asys ' \
                    'where asys.id_topology = %s);' % old_id_topology
            result_proxy = dbsession.bind.execute(query)
            df_router_id = pd.DataFrame(result_proxy, columns=['id_autonomous_system', 'router_id'])

            df_router_id.reset_index()
            df_router_id.set_index('id_autonomous_system', inplace=True)
            for autonomous_system in new_autonomous_system_list:
                df_router_id.rename(index={autonomous_system.autonomous_system: autonomous_system.id}, inplace=True)
            df_router_id = df_router_id.reset_index().copy()

            df_router_id.to_sql('router_id', con=dbsession.bind, if_exists='append', index=False)

            dbsession.flush()

        except Exception as error:
            print('Error -------- 4 -------- : ', error)
            dbsession.rollback()
            arguments = ['--config-file=minisecbgp.ini',
                         '--topology=%s' % new_id_topology]
            subprocess.Popen(['./venv/bin/MiniSecBGP_delete_topology'] + arguments)

    @staticmethod
    def downloading(dbsession, downloading):
        entry = dbsession.query(models.DownloadingTopology).first()
        entry.downloading = downloading


def parse_args(config_file):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(config_file.split())


def main(argv=sys.argv[1:]):
    try:
        opts, args = getopt.getopt(argv, "h", ["config-file=", "topology=", "new-topology-name="])
    except getopt.GetoptError:
        print('\n'
              'Usage: MiniSecBGP_duplicate_topology [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
              '--topology=3                                     the topology ID to be deleted\n'
              '--new-topology-name=<new topology name>          the name to be used in new topology\n')
        sys.exit(2)
    config_file = old_id_topology = new_topology_name = ''
    for opt, arg in opts:
        if opt == '-h':
            print('\n'
                  'Usage: MiniSecBGP_delete_topology [options]\n'
                  '\n'
                  'options (with examples):\n'
                  '\n'
                  '-h                                               this help\n'
                  '\n'
                  '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
                  '--topology=3                                     the topology ID to be deleted\n'
                  '--new-topology-name=<new topology name>          the name to be used in new topology\n')
            sys.exit()
        elif opt == '--config-file':
            config_file = arg
        elif opt == '--topology':
            old_id_topology = arg
        elif opt == '--new-topology-name':
            new_topology_name = arg
    if config_file and old_id_topology and new_topology_name:
        args = parse_args(config_file)
        setup_logging(args.config_uri)
        env = bootstrap(args.config_uri)
        dt = DuplicateTopology()
        with env['request'].tm:
            dbsession = env['request'].dbsession
            downloading = 1
            dt.downloading(dbsession, downloading)

        with env['request'].tm:
            dbsession = env['request'].dbsession
            new_id_topology = dt.duplicate_topology(dbsession, old_id_topology, new_topology_name)

        with env['request'].tm:
            dbsession = env['request'].dbsession
            dt.duplicate_region_data(dbsession, old_id_topology, new_id_topology)

        with env['request'].tm:
            dbsession = env['request'].dbsession
            dt.duplicate_autonomous_system_data(dbsession, old_id_topology, new_id_topology)

        with env['request'].tm:
            dbsession = env['request'].dbsession
            dt.duplicate_another_data(dbsession, old_id_topology, new_id_topology)

        with env['request'].tm:
            dbsession = env['request'].dbsession
            downloading = 0
            dt.downloading(dbsession, downloading)
    else:
        print('\n'
              'Usage: MiniSecBGP_delete_topology [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
              '--topology=3                                     the topology ID to be deleted\n'
              '--new-topology-name=<new topology name>          the name to be used in new topology\n')
