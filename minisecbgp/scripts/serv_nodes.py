import argparse
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from minisecbgp.scripts import ping
from minisecbgp import models


def service_ping(dbsession, argv):
    if argv[0]:     # if hostname received
        node = dbsession.query(models.Cluster).filter(models.Cluster.node == argv[0]).first()
        entry = ping.ping(argv[0])
        try:
            if entry == 0:
                node.serv_ping = 0
            else:
                node.serv_ping = 1
            dbsession.flush()
        except:
            print('Database error for ping service verification node: %s' % node.node)
    else:
        nodes = dbsession.query(models.Cluster).all()
        for node in nodes:
            entry = ping.ping(node.node)
            try:
                if entry == 0:
                    node.serv_ping = 0
                else:
                    node.serv_ping = 1
                dbsession.flush()
            except:
                print('Database error for ping service verification node: %s' % node.node)


def service_ssh(dbsession, argv):
    pass


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(argv[1:])


def main(argv=sys.argv):
    # argv[0] = python program
    # argv[1] = configuration file .ini
    # argv[2] --> argv[0] = hostname
    # argv[3] --> argv[1] = username
    # argv[4] --> argv[2] = password

    args = parse_args(argv[0:2])
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)
    try:
        with env['request'].tm:
            dbsession = env['request'].dbsession
            service_ping(dbsession, argv[2:])
    except OperationalError:
        print('Database error')
