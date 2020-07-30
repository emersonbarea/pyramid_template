import argparse
import getopt
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from minisecbgp import models


class DeleteTopology(object):
    def __init__(self):
        pass

    @staticmethod
    def delete(dbsession, id_topology):
        try:
            router_id = 'delete from router_id where id_autonomous_system in (' \
                        'select id from autonomous_system where id_topology = %s);' % id_topology
            prefix = 'delete from prefix where id_autonomous_system in (' \
                     'select id from autonomous_system where id_topology = %s);' % id_topology
            link = 'delete from link where id_autonomous_system1 in (' \
                   'select id from autonomous_system where id_topology = %s);' % id_topology
            autonomous_system = 'delete from autonomous_system where id_topology = %s;' % id_topology
            type_of_service_autonomous_system = 'delete from type_of_service_autonomous_system where id_autonomous_system in (' \
                                                'select id from autonomous_system where id_topology = %s);' % id_topology
            type_of_user_autonomous_system = 'delete from type_of_user_autonomous_system where id_autonomous_system in (' \
                                             'select id from autonomous_system where id_topology = %s);' % id_topology
            type_of_user = 'delete from type_of_user where id_topology = %s' % id_topology
            type_of_service = 'delete from type_of_service where id_topology = %s' % id_topology
            autonomous_system_internet_exchange_point = 'delete from autonomous_system_internet_exchange_point where id_autonomous_system in (' \
                                                        'select id from autonomous_system where id_topology = %s);' % id_topology
            internet_exchange_point = 'delete from internet_exchange_point where id_topology = %s;' % id_topology

            region = 'delete from region where id_topology = %s;' % id_topology
            topology = 'delete from topology where id = %s;' % id_topology

            dbsession.bind.execute(router_id)
            dbsession.bind.execute(prefix)
            dbsession.bind.execute(link)
            dbsession.bind.execute(autonomous_system_internet_exchange_point)
            dbsession.bind.execute(type_of_service_autonomous_system)
            dbsession.bind.execute(type_of_user_autonomous_system)
            dbsession.bind.execute(autonomous_system)
            dbsession.bind.execute(type_of_user)
            dbsession.bind.execute(type_of_service)
            dbsession.bind.execute(internet_exchange_point)
            dbsession.bind.execute(region)
            dbsession.bind.execute(topology)
        except Exception as error:
            dbsession.rollback()
            print('Database error: ', error)

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
        opts, args = getopt.getopt(argv, "h", ["config-file=", "topology="])
    except getopt.GetoptError:
        print('\n'
              'Usage: MiniSecBGP_delete_topology [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
              '--topology=3                                     the topology ID to be deleted\n')
        sys.exit(2)
    config_file = topology = ''
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
                  '--topology=3                                     the topology ID to be deleted\n')
            sys.exit()
        elif opt == '--config-file':
            config_file = arg
        elif opt == '--topology':
            topology = arg
    if config_file and topology:
        args = parse_args(config_file)
        setup_logging(args.config_uri)
        env = bootstrap(args.config_uri)
        dt = DeleteTopology()
        with env['request'].tm:
            dbsession = env['request'].dbsession
            downloading = 1
            dt.downloading(dbsession, downloading)

        with env['request'].tm:
            dbsession = env['request'].dbsession
            dt.delete(dbsession, topology)

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
              '--topology=3                                     the topology ID to be deleted\n')
