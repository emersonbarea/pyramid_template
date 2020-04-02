import argparse
import getpass
import sys
import socket
from datetime import date

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from .. import models


def setup_models(dbsession):

    # User

    admin = models.User(username='admin',
                        role='admin')
    admin.set_password('admin')
    dbsession.add(admin)

    viewer = models.User(username='viewer',
                         role='viewer')
    viewer.set_password('viewer')
    dbsession.add(viewer)

    # Node

    node = models.Node(node=socket.gethostname(),
                       status=2,
                       hostname=2,
                       username=getpass.getuser(),
                       master=1,
                       service_ping=2,
                       service_ssh=2,
                       all_services=2,
                       conf_user=2,
                       conf_ssh=2,
                       install_remote_prerequisites=2,
                       install_containernet=2,
                       install_metis=2,
                       install_maxinet=2,
                       all_install=2)
    dbsession.add(node)

    # Topology

    topologyTypeRealistic = models.TopologyType(topology_type='Realistic')
    topologyTypeSynthetic = models.TopologyType(topology_type='Synthetic')
    dbsession.add(topologyTypeRealistic)
    dbsession.add(topologyTypeSynthetic)

    topologyAgreementsC2P = models.RealisticTopologyAgreements(agreement='customer to provider',
                                                               value='-1')
    topologyAgreementsP2P = models.RealisticTopologyAgreements(agreement='provider to provider',
                                                               value='0')
    dbsession.add(topologyAgreementsC2P)
    dbsession.add(topologyAgreementsP2P)

    downloadParameters = models.RealisticTopologyDownloadParameters(url='http://data.caida.org/datasets/as-relationships/serial-2/',
                                                                    file_search_string='.as-rel2')
    dbsession.add(downloadParameters)

    scheduleDownloads = models.RealisticTopologyScheduleDownloads(loop=0,
                                                                  date=date.today())
    dbsession.add(scheduleDownloads)

    downloading = models.RealisticTopologyDownloadingCaidaDatabase(downloading=0)
    dbsession.add(downloading)


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
