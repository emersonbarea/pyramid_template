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

    link_agreement_c2p = models.LinkAgreement(agreement='p2c',
                                              description='Customer ASes pay ISPs (providers) for access to the rest of '
                                                          'the Internet, also known as transit. In this scenario, '
                                                          'customers ASes does not retransmit the routes published '
                                                          'by transit ISPs. The format is: <provider-as> - <customer-as>')

    link_agreement_p2p = models.LinkAgreement(agreement='p2p',
                                              description='A p2p link connects two ISPs who have agreed to exchange '
                                                          'traffic on a quid pro quo basis. The format is: <peer-as> - <peer-as>')

    dbsession.add(link_agreement_c2p)
    dbsession.add(link_agreement_p2p)

    id_link_agreement_c2p = dbsession.query(models.LinkAgreement.id).filter_by(agreement='p2c')
    realistic_topology_link_agreement_c2p = models.RealisticTopologyLinkAgreement(id_link_agreement=id_link_agreement_c2p,
                                                                                  value='-1')
    dbsession.add(realistic_topology_link_agreement_c2p)

    id_link_agreement_p2p = dbsession.query(models.LinkAgreement.id).filter_by(agreement='p2p')
    realistic_topology_link_agreement_p2p = models.RealisticTopologyLinkAgreement(id_link_agreement=id_link_agreement_p2p,
                                                                                  value='0')
    dbsession.add(realistic_topology_link_agreement_p2p)

    dbsession.add(realistic_topology_link_agreement_p2p)

    download_parameters = models.RealisticTopologyDownloadParameter(url='http://data.caida.org/datasets/as-relationships/serial-2/',
                                                                    file_search_string='.as-rel2')
    dbsession.add(download_parameters)

    schedule_downloads = models.RealisticTopologyScheduleDownload(loop=0,
                                                                  date=date.today())
    dbsession.add(schedule_downloads)

    downloading = models.DownloadingTopology(downloading=0)
    dbsession.add(downloading)

    # color
    colors = [{'background': 'FF0000', 'text': '000000'},
              {'background': '00FF00', 'text': '000000'},
              {'background': '0000FF', 'text': 'FFFFFF'},
              {'background': 'FFFF00', 'text': '000000'},
              {'background': '00FFFF', 'text': '000000'},
              {'background': 'FF00FF', 'text': '000000'},
              {'background': 'C0C0C0', 'text': '000000'},
              {'background': '808080', 'text': '000000'},
              {'background': '800000', 'text': 'FFFFFF'},
              {'background': '808000', 'text': '000000'},
              {'background': '008000', 'text': '000000'},
              {'background': '800080', 'text': '000000'},
              {'background': '008080', 'text': '000000'},
              {'background': '000080', 'text': 'FFFFFF'},
              {'background': 'FFFFFF', 'text': '000000'},
              {'background': '000000', 'text': 'FFFFFF'},
              {'background': 'FF8C00', 'text': '000000'},
              {'background': '90EE90', 'text': '000000'},
              {'background': 'D8BFD8', 'text': '000000'},
              {'background': 'FFFACD', 'text': '000000'},
              {'background': 'D2691E', 'text': '000000'},
              {'background': '708090', 'text': '000000'},
              {'background': '1E90FF', 'text': '000000'},
              {'background': 'DC143C', 'text': '000000'},
              {'background': 'FFA07A', 'text': '000000'},
              {'background': 'EEE8AA', 'text': '000000'},
              {'background': '32CD32', 'text': '000000'},
              {'background': '5F9EA0', 'text': '000000'},
              {'background': '00008B', 'text': 'FFFFFF'},
              {'background': 'C71585', 'text': '000000'},
              {'background': '2E8B57', 'text': '000000'},
              {'background': '3CB371', 'text': '000000'},
              {'background': '20B2AA', 'text': '000000'},
              {'background': 'FF4500', 'text': '000000'},
              {'background': 'BDB76B', 'text': '000000'},
              {'background': 'AFEEEE', 'text': '000000'},
              {'background': '87CEEB', 'text': '000000'},
              {'background': '8A2BE2', 'text': '000000'},
              {'background': '483D8B', 'text': 'FFFFFF'},
              {'background': '9370DB', 'text': '000000'},
              {'background': 'FFC0CB', 'text': '000000'},
              {'background': 'FAEBD7', 'text': '000000'},
              {'background': '660000', 'text': 'FFFFFF'},
              {'background': '333300', 'text': 'FFFFFF'},
              {'background': '003319', 'text': 'FFFFFF'},
              {'background': '190033', 'text': 'FFFFFF'},
              {'background': '404040', 'text': 'FFFFFF'}]
    for color in colors:
        dbsession.add(models.Color(background_color=color['background'],
                                   text_color=color['text']))


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
