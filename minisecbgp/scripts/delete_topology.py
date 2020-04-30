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
        opts, args = getopt.getopt(argv, 'h:', ["id_topology="])
    except getopt.GetoptError:
        print('* Usage: delete_topology --id_topology=id_topology')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('* Usage: delete_topology --id_topology=id_topology')
            sys.exit()
        elif opt == '--id_topology':
            id_topology = arg

    args = parse_args('minisecbgp.ini')
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)
    try:
        dt = DeleteTopology()

        with env['request'].tm:
            dbsession = env['request'].dbsession
            downloading = 1
            dt.downloading(dbsession, downloading)

        with env['request'].tm:
            dbsession = env['request'].dbsession
            dt.delete(dbsession, id_topology)
            
        with env['request'].tm:
            dbsession = env['request'].dbsession
            downloading = 0
            dt.downloading(dbsession, downloading)

    except OperationalError:
        print('Database error')
