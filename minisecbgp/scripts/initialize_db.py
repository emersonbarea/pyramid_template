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

    topology_types = ['Realistic', 'Synthetic', 'Manual']
    for topology_type in topology_types:
        dbsession.add(models.TopologyType(topology_type=topology_type))

    link_agreement_c2p = models.LinkAgreement(agreement='provider to customer (p2c)',
                                              description='Customer ASes pay ISPs (providers) for access to the rest of '
                                                          'the Internet, also known as transit. In this scenario, '
                                                          'customers ASes does not retransmit the routes published '
                                                          'by transit ISPs. The format is: <provider-as> - <customer-as>')

    link_agreement_p2p = models.LinkAgreement(agreement='peer to peer - or provider to provider (p2p)',
                                              description='A p2p link connects two ISPs who have agreed to exchange '
                                                          'traffic on a quid pro quo basis. The format is: <peer-as> - <peer-as>')
    dbsession.add(link_agreement_c2p)
    dbsession.add(link_agreement_p2p)

    id_link_agreement_c2p = dbsession.query(models.LinkAgreement.id).filter_by(agreement='provider to customer (p2c)')
    realistic_topology_link_agreement_c2p = models.RealisticTopologyLinkAgreement(id_link_agreement=id_link_agreement_c2p,
                                                                                  value='-1')
    dbsession.add(realistic_topology_link_agreement_c2p)

    id_link_agreement_p2p = dbsession.query(models.LinkAgreement.id).filter_by(agreement='peer to peer - or provider to provider (p2p)')
    realistic_topology_link_agreement_p2p = models.RealisticTopologyLinkAgreement(id_link_agreement=id_link_agreement_p2p,
                                                                                  value='0')
    dbsession.add(realistic_topology_link_agreement_p2p)

    download_parameters = models.RealisticTopologyDownloadParameter(url='http://data.caida.org/datasets/as-relationships/serial-2/',
                                                                    file_search_string='.as-rel2')
    dbsession.add(download_parameters)

    schedule_downloads = models.RealisticTopologyScheduleDownload(loop=0,
                                                                  date=date.today())
    dbsession.add(schedule_downloads)

    downloading = models.DownloadingTopology(downloading=0)
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
