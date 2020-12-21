import argparse
import getopt
import sys
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

    # Node Service
    services = [['ping', 'Ping'],
                ['ssh', 'SSH']]
    for service in services:
        dbsession.add(models.Service(service=service[0],
                                     description=service[1]))

    # Node Configuration
    configurations = [['hostname', 'Hostname'],
                      ['user', '"minisecbgpuser" user'],
                      ['ssh', 'SSH'],
                      ['crontab', 'Crontab']]
    for configuration in configurations:
        dbsession.add(models.Configuration(configuration=configuration[0],
                                           description=configuration[1]))

    # Node Install
    installs = [['prerequisites', 'Linux prerequisites', ''],
                ['mininet', 'Mininet', 'http://www.mininet.org'],
                ['containernet', 'Containernet', 'https://containernet.github.io/'],
                ['metis', 'Metis', 'http://glaros.dtc.umn.edu/gkhome/metis/metis/overview'],
                ['maxinet', 'Maxinet', 'https://maxinet.github.io/'],
                ['quagga', 'Quagga', 'https://www.quagga.net/']]
    for install in installs:
        dbsession.add(models.Install(install=install[0],
                                     description=install[1],
                                     url=install[2]))

    # Topology

    topology_types = [{'topology_type': 'MiniSecBGP', 'description': 'Manually Created Topologies'},
                      {'topology_type': 'CAIDA AS-Relationship', 'description': 'CAIDA AS-Relationship imported topologies'},
                      {'topology_type': 'Attack Scenario', 'description': 'Topologies automatically generated from the Attack Scenario procedure'},
                      {'topology_type': 'RIPE NCC BGPlay', 'description': 'RIPE NCC BGPlay imported topologies'}]
    for topology_type in topology_types:
        dbsession.add(models.TopologyType(topology_type=topology_type['topology_type'],
                                          description=topology_type['description']))

    link_agreement_c2p = models.LinkAgreement(agreement='p2c',
                                              description='Customer ASes pay ISPs (providers) for access to the rest of '
                                                          'the Internet, also known as transit. In this scenario, '
                                                          'customers ASes does not retransmit the routes published '
                                                          'by transit ISPs. The format is: <provider-as> - <customer-as>')

    link_agreement_p2p = models.LinkAgreement(agreement='p2p',
                                              description='A p2p link connects two ISPs who have agreed to exchange '
                                                          'traffic on a quid pro quo basis. The format is: <peer-as> - <peer-as>')

    link_agreement_none = models.LinkAgreement(agreement='a2a',
                                               description='It means the absence of an agreement between the peers, '
                                                           'so all BGP traffic is allowed (all to all).')
    dbsession.add(link_agreement_c2p)
    dbsession.add(link_agreement_p2p)
    dbsession.add(link_agreement_none)

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

    colors = [{'background': 'C0C0C0', 'text': '000000'},
              {'background': '000000', 'text': 'FFFFFF'},
              {'background': '0000FF', 'text': 'FFFFFF'},
              {'background': 'FF0000', 'text': '000000'},
              {'background': '00FF00', 'text': '000000'},
              {'background': 'FFFF00', 'text': '000000'},
              {'background': '00FFFF', 'text': '000000'},
              {'background': 'FF00FF', 'text': '000000'},
              {'background': '808080', 'text': '000000'},
              {'background': '800000', 'text': 'FFFFFF'},
              {'background': '808000', 'text': '000000'},
              {'background': '008000', 'text': '000000'},
              {'background': '800080', 'text': '000000'},
              {'background': '008080', 'text': '000000'},
              {'background': '000080', 'text': 'FFFFFF'},
              {'background': 'FFFFFF', 'text': '000000'},
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

    #topology_distribution_methods = ['Customer Cone', 'Metis', 'Manual', 'Round Robin']
    topology_distribution_methods = ['Round Robin', 'Vertex Degree']
    for topology_distribution_method in topology_distribution_methods:
        dbsession.add(models.TopologyDistributionMethod(topology_distribution_method=topology_distribution_method))

    emulation_platforms = ['Mininet', 'Docker']
    for emulation_platform in emulation_platforms:
        dbsession.add(models.EmulationPlatform(emulation_platform=emulation_platform))

    router_platforms = ['Quagga']
    for router_platform in router_platforms:
        dbsession.add(models.RouterPlatform(router_platform=router_platform))

    scenario_attack_types = [{'scenario_attack_type': 'Attraction',
                              'description': 'In the traffic attraction attack type, '
                                             'the attacker must just attract the traffic '
                                             'of hijacked target.'},
                             {'scenario_attack_type': 'Interception',
                              'description': 'In the traffic interception attack type, '
                                             'the attacker must attract the traffic and '
                                             'redirect it to the real hijacked target.'}]
    for scenario_attack_type in scenario_attack_types:
        dbsession.add(models.ScenarioAttackType(scenario_attack_type=scenario_attack_type['scenario_attack_type'],
                                                description=scenario_attack_type['description']))

    vantage_point_actors = [{'vantage_point_actor': 'Attacker',
                             'description': 'The autonomous system that announces the hijacked prefixes.'},
                            {'vantage_point_actor': 'Affected',
                             'description': 'The autonomous system that receives and accepts the hijacked prefixes from the attacker.'},
                            {'vantage_point_actor': 'Target',
                             'description': 'The autonomous system that has its prefixes hijacked.'}]
    for vantage_point_actor in vantage_point_actors:
        dbsession.add(models.VantagePointActor(vantage_point_actor=vantage_point_actor['vantage_point_actor'],
                                               description=vantage_point_actor['description']))


def parse_args(config_file):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(config_file.split())


def main(argv=sys.argv[1:]):
    try:
        opts, args = getopt.getopt(argv, 'h', ["config-file="])
    except getopt.GetoptError:
        print('\n'
              'Usage: MiniSecBGP_initialize_db [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n')
        sys.exit(2)
    config_file = ''
    for opt, arg in opts:
        if opt == '-h':
            print('\n'
                  'Usage: MiniSecBGP_initialize_db [options]\n'
                  '\n'
                  'options (with examples):\n'
                  '\n'
                  '-h                                               this help\n'
                  '\n'
                  '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n')
            sys.exit()
        elif opt == '--config-file':
            config_file = arg
    if config_file:
        args = parse_args(config_file)
        setup_logging(args.config_uri)
        env = bootstrap(args.config_uri)
        try:
            with env['request'].tm:
                dbsession = env['request'].dbsession
                setup_models(dbsession)
        except OperationalError:
            print('Database error')
    else:
        print('\n'
              'Usage: MiniSecBGP_initialize_db [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n')