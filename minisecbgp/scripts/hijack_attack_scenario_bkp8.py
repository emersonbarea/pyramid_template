import argparse
import getopt

import networkx as nx
import sys

import pandas as pd

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy import func
from sqlalchemy.exc import OperationalError

from graph_tool.all import *
import timeit

from minisecbgp import models

import time


class AttackScenario(object):
    def __init__(self, dbsession, scenario_id, scenario_name, scenario_description,
                 topology, attacker, affected_area, target, attack_type, number_of_shortest_paths):

        t = time.time()
        print('\n<-- getting autonomous systems')
        query = 'select asys.id as id_autonomous_system, ' \
                'asys.id_topology as id_topology, ' \
                'asys.id_region as id_region, ' \
                'asys.autonomous_system as autonomous_system, ' \
                'asys.stub as stub ' \
                'from autonomous_system asys ' \
                'where asys.id_topology = %s;' % 1
        result_proxy = dbsession.bind.execute(query)
        df_autonomous_system = pd.DataFrame(result_proxy, columns=['id_autonomous_system',
                                                                   'id_topology',
                                                                   'id_region',
                                                                   'autonomous_system',
                                                                   'stub'])
        print('--> autonomous systems ok - ', time.time() - t)
        print(df_autonomous_system)

        t = time.time()
        print('\n<-- getting links')
        query = 'select l.id as id_link, ' \
                'l.id_topology as id_topology, ' \
                'l.id_link_agreement as id_link_agreement, ' \
                'l.id_autonomous_system1 as id_autonomous_system1, ' \
                'l.id_autonomous_system2 as id_autonomous_system2, ' \
                'l.ip_autonomous_system1 as ip_autonomous_system1, ' \
                'l.ip_autonomous_system2 as ip_autonomous_system2, ' \
                'l.mask as mask, ' \
                'l.description as description, ' \
                'l.bandwidth as bandwidth, ' \
                'l.delay as delay, ' \
                'l.load as load ' \
                'from link l ' \
                'where l.id_topology = %s;' % 1
        result_proxy = dbsession.bind.execute(query)
        df_link = pd.DataFrame(result_proxy, columns=['id_link',
                                                      'id_topology',
                                                      'id_link_agreement',
                                                      'id_autonomous_system1',
                                                      'id_autonomous_system2',
                                                      'ip_autonomous_system1',
                                                      'ip_autonomous_system2',
                                                      'mask',
                                                      'description',
                                                      'bandwidth',
                                                      'delay',
                                                      'load'])
        print('--> links ok - ', time.time() - t)

        print(df_link)

        print('<-- transforma o índice do df LINK em campo')
        t = time.time()
        df_link.reset_index(level=0, inplace=True)
        print('--> ok - ', time.time() - t)

        print('<-- renomeia o campo (antigo índice) do df LINK')
        t = time.time()
        df_link.columns = ['id_index_link', 'id_link', 'id_topology', 'id_link_agreement', 'id_autonomous_system1',
                           'id_autonomous_system2', 'ip_autonomous_system1', 'ip_autonomous_system2', 'mask',
                           'description', 'bandwidth', 'delay', 'load']
        print('--> ok - ', time.time() - t)

        print('<-- transforma o índice do df AUTONOMOUS_SYSTEM em campo')
        t = time.time()
        df_autonomous_system.reset_index(level=0, inplace=True)
        print('--> ok - ', time.time() - t)

        print('<-- renomeia o campo (antigo índice) para usar no primeiro concat para autonomous_system1')
        t = time.time()
        df_autonomous_system.columns = ['id_index_autonomous_system1', 'id_autonomous_system', 'id_topology',
                                        'id_region', 'autonomous_system', 'stub']
        print('--> ok - ', time.time() - t)

        print('<-- concatena o df_autonomous_system no df_link baseado no autonomous_system1 do df_link')
        t = time.time()
        df_link_autonomous_system = pd.concat([df_link.set_index('id_autonomous_system1'),
                                               df_autonomous_system.set_index('id_autonomous_system')],
                                              axis=1,
                                              join='inner')
        print('-->  ok - ', time.time() - t)

        print('<-- reset index df_link_autonomous_system')
        t = time.time()
        df_link_autonomous_system.reset_index(inplace=True)
        print('-->  ok - ', time.time() - t)

        print('<-- renomeia o campo (antigo índice) para usar no segundo concat para autonomous_system2')
        t = time.time()
        df_autonomous_system.columns = ['id_index_autonomous_system2', 'id_autonomous_system', 'id_topology',
                                        'id_region', 'autonomous_system', 'stub']
        print('-->  ok - ', time.time() - t)

        print('<-- concatena o df_autonomous_system no df_link baseado no autonomous_system2 do df_link')
        t = time.time()
        df_link_autonomous_system = pd.concat([df_link_autonomous_system.set_index('id_autonomous_system2'),
                                               df_autonomous_system.set_index('id_autonomous_system')],
                                              axis=1,
                                              join='inner')
        print('-->  ok - ', time.time() - t)

        print('<-- renomeia o campo (antigo índice) para o nome original que ficará daqui em diante')
        t = time.time()
        df_autonomous_system.columns = ['id_index_autonomous_system', 'id_autonomous_system', 'id_topology',
                                        'id_region', 'autonomous_system', 'stub']
        print('-->  ok - ', time.time() - t)

        print('<-- reset index df_link_autonomous_system')
        t = time.time()
        df_link_autonomous_system.reset_index(inplace=True)
        print('-->  ok - ', time.time() - t)

        print('<-- retira os campos não utilizados do df_link_autonomous_system')
        t = time.time()
        df_link_autonomous_system = df_link_autonomous_system[['id_index_autonomous_system1', 'id_index_autonomous_system2']]
        print('-->  ok - ', time.time() - t)

        #pd.set_option('display.max_rows', None)
        #pd.set_option('display.max_columns', None)
        #pd.set_option('display.width', None)
        #pd.set_option('display.max_colwidth', None)

        print(df_autonomous_system)
        print(df_link)
        print(df_link_autonomous_system)

        #g = Graph(directed=False)
        #g.add_edge_list(df_link_autonomous_system.values, hashed=True)
        #print('print graph vertices: ', g.get_vertices())
        #print('print graph edges: ', g.get_edges())

        #for path in graph_tool.all.all_paths(g, 67025, 1):
        #    print(path)
        #print('------------------------------------------------')
        #print(graph_tool.all.shortest_distance(g, source=1916))
        #print('------------------------------------------------')

        print('<-- MONTANDO O NETWORKX GRAPH')
        t = time.time()
        self.graph = nx.from_pandas_edgelist(
            df_link_autonomous_system,
            source='id_index_autonomous_system1',
            target='id_index_autonomous_system2',
            create_using=nx.MultiGraph()
        )
        print('-->  ok - ', time.time() - t)

        print('<-- PROCURANDO OS PATHS DE 1916 PARA 1421')
        t = time.time()
        paths = nx.all_simple_edge_paths(self.graph, 1916, 1421, cutoff=5)
        print('-->  ok - ', time.time() - t)

        print('<-- PRINTANDO OS PATHS')
        t = time.time()
        print(list(paths))
        print('-->  ok - ', time.time() - t)

def str2bool(master):
    if isinstance(master, bool):
        return master
    if master.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif master.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def parse_args(config_file):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(config_file.split())


def main(argv=sys.argv[1:]):
    try:
        opts, args = getopt.getopt(argv, "h",
                                   ["config-file=", "scenario-id=", "scenario-name=", "scenario-description=",
                                    "topology=", "attacker=", "affected-area=", "target=", "attack-type=",
                                    "all-paths", "number-of-shortest-paths="])
    except getopt.GetoptError:
        print('\n'
              'ERROR\n'
              'Usage: MiniSecBGP_hijack_attack_scenario [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                                       this help\n'
              '\n'
              '--config-file="minisecbgp.ini"                           pyramid config filename [.ini]\n'
              '--scenario-name="Test topology"                          the name that will be used to identify this scenario\n'
              '--scenario-description="date 20200729"                   the scenario description\n'
              '--topology=3                                             the topology used as the original base of the scenario\n'
              '--attacker=[65001,65002]                                 define which AS(s) will be the attacker\n'
              '--affected-area=[65001,65003]                            define which these AS(s) will receive and accept the hijacked routes\n'
              '--target=[\'10.0.0.0/24\',\'20.0.0.0/24\']                   define the prefix(s) and mask(s) that will be hijacked by the attacker(s)\n'
              '--attack-type=attraction|interception                    if the attack is an attraction attack or an interception attack\n'
              '--all-paths or --number-of-shortest-paths=[1..999]       number of valid paths between the attacker AS, affected AS and target AS\n'
              '\n'
              'or\n'
              '\n'
              '--scenario-id=16                                         scenario ID\n')
        sys.exit(2)
    config_file = scenario_id = scenario_name = scenario_description = topology = attacker = \
        affected_area = target = attack_type = number_of_shortest_paths = ''
    for opt, arg in opts:
        if opt == '-h':
            print('\n'
                  'HELP\n'
                  'Usage: MiniSecBGP_hijack_attack_scenario [options]\n'
                  '\n'
                  'options (with examples):\n'
                  '\n'
                  '-h                                                       this help\n'
                  '\n'
                  '--config-file="minisecbgp.ini"                           pyramid config filename [.ini]\n'
                  '--scenario-name="Test topology"                          the name that will be used to identify this scenario\n'
                  '--scenario-description="date 20200729"                   the scenario description\n'
                  '--topology=3                                             the topology used as the original base of the scenario\n'
                  '--attacker=[65001,65002]                                 define which AS(s) will be the attacker\n'
                  '--affected-area=[65001,65003]                            define which these AS(s) will receive and accept the hijacked routes\n'
                  '--target=[\'10.0.0.0/24\',\'20.0.0.0/24\']                   define the prefix(s) and mask(s) that will be hijacked by the attacker(s)\n'
                  '--attack-type=attraction|interception                    if the attack is an attraction attack or an interception attack\n'
                  '--all-paths or --number-of-shortest-paths=[1..999]       number of valid paths between the attacker AS, affected AS and target AS\n'
                  '\n'
                  'or\n'
                  '\n'
                  '--scenario-id=16                                         scenario ID\n')
            sys.exit()
        if opt == '--config-file':
            config_file = arg
        elif opt == '--scenario-id':
            scenario_id = arg
        elif opt == '--scenario-name':
            scenario_name = arg
        elif opt == '--scenario-description':
            scenario_description = arg
        elif opt == '--topology':
            topology = arg
        elif opt == '--attacker':
            attacker = arg
        elif opt == '--affected-area':
            affected_area = arg
        elif opt == '--target':
            target = arg
        elif opt == '--attack-type':
            attack_type = arg
        elif opt == '--all-paths':
            number_of_shortest_paths = '0'
        elif opt == '--number-of-shortest-paths':
            number_of_shortest_paths = arg

    if (config_file and scenario_name and topology and attacker and affected_area and target and attack_type and number_of_shortest_paths) \
            or (config_file and scenario_id):
        args = parse_args(config_file)
        setup_logging(args.config_uri)
        env = bootstrap(args.config_uri)
        try:
            with env['request'].tm:
                dbsession = env['request'].dbsession
                aa = AttackScenario(dbsession, scenario_id, scenario_name, scenario_description, topology,
                                    attacker, affected_area, target, attack_type, number_of_shortest_paths)
        except OperationalError:
            print('Database error')
    else:
        print('\n'
              'Usage: MiniSecBGP_hijack_attack_scenario [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                                       this help\n'
              '\n'
              '--config-file="minisecbgp.ini"                           pyramid config filename [.ini]\n'
              '--scenario-name="Test topology"                          the name that will be used to identify this scenario\n'
              '--scenario-description="date 20200729"                   the scenario description\n'
              '--topology=3                                             the topology used as the original base of the scenario\n'
              '--attacker=[65001,65002]                                 define which AS(s) will be the attacker\n'
              '--affected-area=[65001,65003]                            define which these AS(s) will receive and accept the hijacked routes\n'
              '--target=[\'10.0.0.0/24\',\'20.0.0.0/24\']                   define the prefix(s) and mask(s) that will be hijacked by the attacker(s)\n'
              '--attack-type=attraction|interception                    if the attack is an attraction attack or an interception attack\n'
              '--all-paths or --number-of-shortest-paths=[1..999]       number of valid paths between the attacker AS, affected AS and target AS\n'
              '\n'
              'or\n'
              '\n'
              '--scenario-id=16                                         scenario ID\n')
