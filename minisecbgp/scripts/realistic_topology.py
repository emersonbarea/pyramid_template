import bz2
import argparse
import getopt
import ipaddress
import os
import sys

import pandas as pd

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy import func
from sqlalchemy.exc import OperationalError

from minisecbgp import models


class RealisticTopology(object):
    def __init__(self, file):
        self.file = file
        self.output_file = self.file[:-4]
        self.topology_name = self.output_file[:-4]
        self.path = '/tmp/'

    def as_relationship(self):

        # uncompressing file
        uncompressed_file = bz2.open(self.path + self.file, 'rt')
        data = uncompressed_file.read()
        f = open(self.path + self.output_file, 'w+')
        f.write(data)
        f.close()

        # parsing downloaded file
        df_from_file = pd.read_csv(self.path + self.output_file,
                                   sep='|',
                                   comment='#',
                                   header=None,
                                   skip_blank_lines=True,
                                   usecols=[0, 1, 2, 3],
                                   names=['AS1', 'AS2', 'pp_cp', 'got_from'],
                                   index_col=['AS1'])
        pandas_autonomous_systems = pd.concat([df_from_file.reset_index()['AS1'], df_from_file['AS2']], ignore_index=True)
        pandas_stub_autonomous_systems = pandas_autonomous_systems.drop_duplicates(keep=False)      # only stub ASes
        pandas_unique_autonomous_systems = pandas_autonomous_systems.drop_duplicates(keep='first')  # all unique ASes (stub and not stub)

        return pandas_unique_autonomous_systems, pandas_stub_autonomous_systems, df_from_file

    def topology(self, dbsession):
        topology = models.Topology(topology=self.topology_name,
                                   description='CAIDA AS-Relationship - %s' % self.file,
                                   id_topology_type=dbsession.query(models.TopologyType.id).filter(
                                       func.lower(models.TopologyType.topology_type) == 'caida as-relationship'))
        dbsession.add(topology)

    def get_topology_id(self, dbsession):
        id_topology = dbsession.query(models.Topology.id).filter_by(topology=self.topology_name).first()

        return id_topology

    @staticmethod
    def region(dbsession, id_topology):
        region = models.Region(region='-- undefined region --',
                               id_topology=id_topology,
                               id_color=1)
        dbsession.add(region)

    @staticmethod
    def get_region_id(dbsession, id_topology):
        id_region = dbsession.query(models.Region.id).filter_by(id_topology=id_topology).first()

        return id_region

    @staticmethod
    def autonomous_system(dbsession, id_topology, id_region, pandas_unique_autonomous_systems, pandas_stub_autonomous_systems):
        df_autonomous_system = pd.DataFrame({'autonomous_system': pandas_unique_autonomous_systems.values})
        df_autonomous_system = pd.concat([df_autonomous_system.assign(id_topology=id_topology) for id_topology in id_topology])
        df_autonomous_system = pd.concat([df_autonomous_system.assign(id_region=id_region) for id_region in id_region])

        df_autonomous_system_stub = pd.DataFrame({'autonomous_system_stub': pandas_stub_autonomous_systems.values})
        df_autonomous_system_stub = pd.concat([df_autonomous_system_stub.assign(stub=True)])

        df_autonomous_system.set_index('autonomous_system', inplace=True)

        df_autonomous_system_stub.set_index('autonomous_system_stub', inplace=True)

        df_autonomous_system = pd.concat([df_autonomous_system, df_autonomous_system_stub], axis=1, join='outer')
        df_autonomous_system = df_autonomous_system.fillna(False).reset_index()
        df_autonomous_system.columns = ['autonomous_system', 'id_topology', 'id_region', 'stub']

        df_autonomous_system.to_sql('autonomous_system', con=dbsession.bind, if_exists='append', index=False)

    @staticmethod
    def automatic_router_id(dbsession, id_topology):
        df_router_id = pd.read_sql(dbsession.query(models.AutonomousSystem.id).
                                   filter_by(id_topology=id_topology).
                                   order_by(models.AutonomousSystem.id.asc()).
                                   statement, con=dbsession.bind)
        df_router_id.columns = ['id_autonomous_system']
        router_id_ip = 2147483647
        list_router_id = list()
        for row in df_router_id.itertuples():
            list_router_id.append(str(ipaddress.ip_address(router_id_ip)))
            router_id_ip = router_id_ip - 1
        df_router_id['router_id'] = list_router_id
        df_router_id.to_sql('router_id', con=dbsession.bind, if_exists='append', index=False)

    @staticmethod
    def automatic_prefix(dbsession, id_topology):
        df_prefix = pd.read_sql(dbsession.query(models.AutonomousSystem.id).
                                filter_by(id_topology=id_topology).
                                order_by(models.AutonomousSystem.id.asc()).
                                statement, con=dbsession.bind)
        df_prefix.columns = ['id_autonomous_system']
        prefix_ip = 335544320
        list_prefix = list()
        list_mask = list()
        for row in df_prefix.itertuples():
            list_prefix.append(str(ipaddress.ip_address(prefix_ip)))
            list_mask.append(30)
            prefix_ip = prefix_ip + 4

        df_prefix['prefix'] = list_prefix
        df_prefix['mask'] = list_mask

        df_prefix.to_sql('prefix', con=dbsession.bind, if_exists='append', index=False)

    @staticmethod
    def automatic_link(dbsession, id_topology, df_from_file):
        # autonomous_system
        autonomous_systems = pd.read_sql(dbsession.query(models.AutonomousSystem).
                                         filter_by(id_topology=id_topology).
                                         order_by(models.AutonomousSystem.id.asc()).
                                         statement, con=dbsession.bind)
        df_autonomous_system = autonomous_systems.reset_index()[['id', 'autonomous_system', 'id_topology']].copy()

        # links
        df_link = df_from_file.reset_index()[['AS1', 'AS2', 'pp_cp']].copy()
        df_link.columns = ['autonomous_system1', 'autonomous_system2', 'id_link_agreement']

        # links for autonomous_system 1
        df_link.set_index('autonomous_system1', inplace=True)
        df_autonomous_system1 = df_autonomous_system.copy()
        df_autonomous_system1.columns = ['id_autonomous_system1', 'autonomous_system1', 'id_topology']
        df_autonomous_system1.set_index('autonomous_system1', inplace=True)
        df_link = pd.concat([df_link, df_autonomous_system1], axis=1, join='inner')

        # links for autonomous_system 2
        df_link.set_index('autonomous_system2', inplace=True)
        df_autonomous_system2 = df_autonomous_system[['id', 'autonomous_system']].copy()
        df_autonomous_system2.columns = ['id_autonomous_system2', 'autonomous_system2']
        df_autonomous_system2.set_index('autonomous_system2', inplace=True)
        df_link = pd.concat([df_link, df_autonomous_system2], axis=1, join='inner')

        # agreements
        df_link.reset_index()
        df_link.set_index('id_link_agreement', inplace=True)
        agreements = dbsession.query(models.LinkAgreement, models.RealisticTopologyLinkAgreement).\
            filter(models.LinkAgreement.id == models.RealisticTopologyLinkAgreement.id_link_agreement)
        for agreement in agreements:
            df_link.rename(index={int(agreement.RealisticTopologyLinkAgreement.value): agreement.LinkAgreement.id}, inplace=True)

        prefix_ip = 16777216
        list_ip_autonomous_system1 = list()
        list_ip_autonomous_system2 = list()
        list_mask = list()
        for row in df_link.itertuples():
            list_ip_autonomous_system1.append(str(ipaddress.ip_address(prefix_ip + 1)))
            list_ip_autonomous_system2.append(str(ipaddress.ip_address(prefix_ip + 2)))
            list_mask.append(30)
            prefix_ip = prefix_ip + 4

        df_link['ip_autonomous_system1'] = list_ip_autonomous_system1
        df_link['ip_autonomous_system2'] = list_ip_autonomous_system2
        df_link['mask'] = list_mask

        df_link = df_link.reset_index().copy()
        df_link.to_sql('link', con=dbsession.bind, if_exists='append', index=False)

    @staticmethod
    def downloading(dbsession, downloading):
        entry = dbsession.query(models.DownloadingTopology).first()
        entry.downloading = downloading

    def erase_file(self):
        os.remove(self.path + self.file)
        os.remove(self.path + self.output_file)


def parse_args(config_file):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(config_file.split())


def main(argv=sys.argv[1:]):
    try:
        opts, args = getopt.getopt(argv, 'h', ["config-file=", "file="])
    except getopt.GetoptError:
        print('\n'
              'Usage: MiniSecBGP_realistic_topology [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
              '--file=20191201.as-rel2.txt.bz2                  CAIDA AS-Relationship compressed topology filename\n'
              '                                                 * the file must be in /tmp\n')
        sys.exit(2)
    config_file = file = ''
    for opt, arg in opts:
        if opt == '-h':
            print('\n'
                  'Usage: MiniSecBGP_realistic_topology [options]\n'
                  '\n'
                  'options (with examples):\n'
                  '\n'
                  '-h                                               this help\n'
                  '\n'
                  '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
                  '--file=20191201.as-rel2.txt.bz2                  CAIDA AS-Relationship compressed topology filename\n'
                  '                                                 * the file must be in /tmp\n')
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
            t = RealisticTopology(file)

            with env['request'].tm:
                dbsession = env['request'].dbsession
                downloading = 1
                t.downloading(dbsession, downloading)

            with env['request'].tm:
                pandas_unique_autonomous_systems, pandas_stub_autonomous_systems, df_from_file = t.as_relationship()

            with env['request'].tm:
                dbsession = env['request'].dbsession
                t.topology(dbsession)

            with env['request'].tm:
                dbsession = env['request'].dbsession
                id_topology = t.get_topology_id(dbsession)

            with env['request'].tm:
                dbsession = env['request'].dbsession
                t.region(dbsession, id_topology)

            with env['request'].tm:
                dbsession = env['request'].dbsession
                id_region = t.get_region_id(dbsession, id_topology)

            with env['request'].tm:
                dbsession = env['request'].dbsession
                t.autonomous_system(dbsession, id_topology, id_region, pandas_unique_autonomous_systems, pandas_stub_autonomous_systems)

            with env['request'].tm:
                dbsession = env['request'].dbsession
                t.automatic_router_id(dbsession, id_topology)

            with env['request'].tm:
                dbsession = env['request'].dbsession
                t.automatic_prefix(dbsession, id_topology)

            with env['request'].tm:
                dbsession = env['request'].dbsession
                t.automatic_link(dbsession, id_topology, df_from_file)

            with env['request'].tm:
                dbsession = env['request'].dbsession
                downloading = 0
                t.downloading(dbsession, downloading)

            t.erase_file()
        except OperationalError:
            print('Database error')
    else:
        print('\n'
              'Usage: MiniSecBGP_realistic_topology [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
              '--file=20191201.as-rel2.txt.bz2                  CAIDA AS-Relationship compressed topology filename\n'
              '                                                 * the file must be in /tmp\n')