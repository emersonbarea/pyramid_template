import argparse
import sys
import socket

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from .. import models


def setup_models(dbsession):
    admin = models.User(username='admin', role='admin')
    admin.set_password('admin')
    dbsession.add(admin)

    viewer = models.User(username='viewer', role='viewer')
    viewer.set_password('viewer')
    dbsession.add(viewer)

    node = models.Node(node=socket.gethostname(),
                       username='minisecbgp',
                       master=1,
                       serv_ping=2,
                       serv_ssh=2,
                       serv_app=2,
                       conf_user=2,
                       conf_ssh=2,
                       conf_containernet=2,
                       conf_metis=2,
                       conf_maxinet=2
                       )
    dbsession.add(node)


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(argv[1:])


def main(argv=sys.argv):
    args = parse_args(argv)
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)
    try:
        with env['request'].tm:
            dbsession = env['request'].dbsession
            setup_models(dbsession)
    except OperationalError:
        print('Database error')
