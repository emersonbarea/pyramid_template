import argparse
import getopt
import getpass
import ipaddress
import sys
from datetime import date

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from .. import models


def setup_models(dbsession, master_ip_address):

    # User

    admin = models.User(username='admin',
                        role='admin')
    admin.set_password('admin')
    dbsession.add(admin)

    viewer = models.User(username='viewer',
                         role='viewer')
    viewer.set_password('viewer')
    dbsession.add(viewer)

    # Node Service
    services = [['ping', 'Ping'],
                ['ssh', 'SSH']]
    for service in services:
        dbsession.add(models.Service(service=service[0],
                                     description=service[1]))

    # Node Configuration
    configurations = [['hostname', 'Hostname'],
                      ['user', '"minisecbgpuser" user'],
                      ['ssh', 'SSH']]
    for configuration in configurations:
        dbsession.add(models.Configuration(configuration=configuration[0],
                                           description=configuration[1]))

    # Node Install
    installs = [['prerequisites', 'Linux prerequisites', ''],
                ['mininet', 'Mininet', 'http://www.mininet.org'],
                ['containernet', 'Containernet', 'https://containernet.github.io/'],
                ['programs', 'Metis', 'http://glaros.dtc.umn.edu/gkhome/metis/metis/overview'],
                ['maxinet', 'Maxinet', 'https://maxinet.github.io/'],
                ['quagga', 'Quagga', 'https://www.quagga.net/']]
    for install in installs:
        dbsession.add(models.Install(install=install[0],
                                     description=install[1],
                                     url=install[2]))

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

    # Color

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

    # Hijack

    topology_distribution_methods = ['Customer Cone', 'Metis', 'Manual', 'Round Robin']
    for topology_distribution_method in topology_distribution_methods:
        dbsession.add(models.TopologyDistributionMethod(topology_distribution_method=topology_distribution_method))

    emulation_platforms = ['Mininet', 'Docker']
    for emulation_platform in emulation_platforms:
        dbsession.add(models.EmulationPlatform(emulation_platform=emulation_platform))

    router_platforms = ['Quagga']
    for router_platform in router_platforms:
        dbsession.add(models.RouterPlatform(router_platform=router_platform))


def parse_args(config_file):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(config_file.split())


def main(argv=sys.argv[1:]):
    try:
        opts, args = getopt.getopt(argv, 'h:', ["config-file=", "master-ip-address="])
    except getopt.GetoptError:
        print('* Usage: initialize_db '
              '--config-file=<pyramid config file .ini> '
              '--master-ip-address={master cluster node IP address (Ex.: 192.168.0.1}')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('* Usage: initialize_db '
                  '--config-file=<pyramid config file .ini> '
                  '--master-ip-address={master cluster node IP address (Ex.: 192.168.0.1}')
            sys.exit()
        elif opt == '--config-file':
            config_file = arg
        elif opt == '--master-ip-address':
            master_ip_address = arg

    args = parse_args(config_file)
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)
    try:
        with env['request'].tm:
            dbsession = env['request'].dbsession
            setup_models(dbsession, master_ip_address)
    except OperationalError:
        print('Database error')
