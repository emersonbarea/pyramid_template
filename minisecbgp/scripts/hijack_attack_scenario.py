import argparse
import getopt
import os
import sys
import time

import pandas as pd

from multiprocessing import Pool
from functools import partial

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy import func
from sqlalchemy.exc import OperationalError

from minisecbgp import models


class AttackScenario(object):
    def __init__(self, dbsession, scenario_id, scenario_name, scenario_description,
                 topology, attacker, affected, target, attack_type, number_of_shortest_paths):
        self.failed = False
        num_processes = os.cpu_count()
        self.pool = Pool(processes=num_processes)

        try:
            if scenario_id:
                scenario = dbsession.query(models.ScenarioStuff).\
                    filter_by(id=scenario_id).first()
                scenario_name = scenario.scenario_name
                scenario_description = scenario.scenario_description

                topology = dbsession.query(models.Topology).\
                    filter_by(id=scenario.id_topology).first()
                id_topology_base = topology.id
                topology_base = topology.topology

                attacker = scenario.attacker_list
                affected = scenario.affected_area_list
                target = scenario.target_list

                scenario_attack_type = dbsession.query(models.ScenarioAttackType).\
                    filter_by(id=scenario.attack_type).first()

                number_of_shortest_paths = scenario.number_of_shortest_paths
            else:
                try:
                    topology = dbsession.query(models.Topology).\
                        filter_by(id=topology).first()
                    id_topology_base = topology.id
                    topology_base = topology.topology
                except Exception:
                    self.failed = True
                    print('The topology does not exist')
                    return
                try:
                    scenario_attack_type = dbsession.query(models.ScenarioAttackType).\
                        filter(func.lower(models.ScenarioAttackType.scenario_attack_type) == func.lower(attack_type)).first()
                except Exception:
                    self.failed = True
                    print('The attacker type does not exist')
                    return

            print('attackers')

            attacker_list_temp = list(map(int, attacker.strip('][').split(',')))
            attacker_list = list()
            for attacker in dbsession.query(models.AutonomousSystem).\
                    filter_by(id_topology=id_topology_base).\
                    filter(models.AutonomousSystem.autonomous_system.in_(attacker_list_temp)).all():
                attacker_list.append(attacker.id)
            attacker_list.sort()

            print('affected')

            affected_list_temp = list(map(int, affected.strip('][').split(',')))
            affected_list = list()
            for affected in dbsession.query(models.AutonomousSystem).\
                    filter_by(id_topology=id_topology_base).\
                    filter(models.AutonomousSystem.autonomous_system.in_(affected_list_temp)).all():
                affected_list.append(affected.id)
            affected_list.sort()

            print('targets')

            target_list_temp = list(map(int, target.strip('][').split(',')))
            target_list = list()
            for target in dbsession.query(models.AutonomousSystem).\
                    filter_by(id_topology=id_topology_base).\
                    filter(models.AutonomousSystem.autonomous_system.in_(target_list_temp)).all():
                target_list.append(target.id)
            target_list.sort()

            topology_type = dbsession.query(models.TopologyType).\
                filter(func.lower(models.TopologyType.topology_type) == 'attack scenario').first()
            id_topology_type = topology_type.id

            id_scenario_attack_type = scenario_attack_type.id
            scenario_attack_type = scenario_attack_type.scenario_attack_type

            self.affected_vantage_point_actor = dbsession.query(models.VantagePointActor.id). \
                filter(func.lower(models.VantagePointActor.vantage_point_actor) == 'affected').first()

            self.attacker_vantage_point_actor = dbsession.query(models.VantagePointActor.id).\
                filter(func.lower(models.VantagePointActor.vantage_point_actor) == 'attacker').first()

            self.target_vantage_point_actor = dbsession.query(models.VantagePointActor.id). \
                filter(func.lower(models.VantagePointActor.vantage_point_actor) == 'target').first()

            print('link_raw')

            self.autonomous_systems = dbsession.query(models.AutonomousSystem).\
                filter_by(id_topology=id_topology_base).all()

            query = 'select l.id_autonomous_system1 as id_autonomous_system1, ' \
                    'l.id_autonomous_system2 as id_autonomous_system2, ' \
                    '(select la.agreement from link_agreement la where la.id = l.id_link_agreement) as agreement ' \
                    'from link l ' \
                    'where l.id_topology = %s;' % id_topology_base
            result_proxy = dbsession.bind.execute(query)
            link_raw = pd.DataFrame(result_proxy, columns=['id_autonomous_system1',
                                                           'id_autonomous_system2',
                                                           'agreement'])

        except Exception as error:
            print('Error: ', error)
            return

        self.dbsession = dbsession
        self.scenario_id = scenario_id
        self.scenario_name = scenario_name
        self.scenario_description = scenario_description
        self.id_topology_base = id_topology_base
        self.topology_base = topology_base
        self.attacker = attacker_list
        self.affected = affected_list
        self.target = target_list
        self.link_raw = link_raw
        self.id_scenario_attack_type = id_scenario_attack_type
        self.scenario_attack_type = scenario_attack_type.lower()
        self.number_of_shortest_paths = int(number_of_shortest_paths)
        self.id_topology_type = id_topology_type

        print('finalizei o init')

    def topology_graph(self):
        link_temp1 = self.link_raw[['id_autonomous_system1',
                                    'id_autonomous_system2',
                                    'agreement']]
        link_temp2 = self.link_raw[['id_autonomous_system2',
                                    'id_autonomous_system1',
                                    'agreement']]
        link_temp2.rename(columns={'id_autonomous_system2': 'id_autonomous_system1',
                                   'id_autonomous_system1': 'id_autonomous_system2'}, inplace=True)

        # changing p2p to 2 and p2c to 3 in df_links
        if not link_temp1.empty:
            try:
                link_temp1.loc[link_temp1['agreement'] == 'p2p', 'agreement'] = 2
            except KeyError:
                pass
            try:
                link_temp1.loc[link_temp1['agreement'] == 'p2c', 'agreement'] = 3
            except KeyError:
                pass

        # changing p2p to 2 and p2c to 1 in df_links_inverted
        if not link_temp2.empty:
            try:
                link_temp2.loc[link_temp2['agreement'] == 'p2p', 'agreement'] = 2
            except KeyError:
                pass
            try:
                link_temp2.loc[link_temp2['agreement'] == 'p2c', 'agreement'] = 1
            except KeyError:
                pass

        link_temp = pd.concat([link_temp1, link_temp2], ignore_index=True).set_index('id_autonomous_system1')

        graph = dict()
        for index, row in link_temp.iterrows():
            vector = []
            if index in graph:
                vector = graph[index]
            vector.append({row[0]: row[1]})
            graph[index] = vector

        return graph

    @staticmethod
    def bfs_shortest_path(graph, peers_for_query):
        queue = [[{peers_for_query[0]: 1}]]
        all_paths = list()
        path_found = False
        while queue:
            path = queue.pop(0)
            node = list(path[-1].keys())[0]
            neighbours = graph[node]
            for neighbour in neighbours:
                parent_agreement = list(path[-1].values())[0]
                neighbour_agreement = list(neighbour.values())[0]
                if parent_agreement == 1 or (parent_agreement > 1 and neighbour_agreement == 3):
                    neighbour_key = list(neighbour.keys())[0]
                    new_path = path[:-1] + [list(path[-1].keys())[0]]
                    new_path.append(neighbour)
                    if neighbour_key not in path:
                        if neighbour_key == peers_for_query[1]:
                            path_found_length = len(new_path[:-1] + [list(new_path[-1].keys())[0]])
                            for i in range(len(queue) - 1, -1, -1):
                                if len(queue[i]) >= path_found_length:
                                    queue.pop(i)
                            all_paths.append(new_path[:-1] + [list(new_path[-1].keys())[0]])
                            path_found = True
                        if not path_found:
                            queue.append(new_path)
        os.system('echo "%s" >> /tmp/paths.txt' % str(all_paths))
        return all_paths

    @staticmethod
    def peers_already_registered(peers_for_query, source, target):
        for path in peers_for_query:
            if path[1] == source and path[0] == target:
                return True
        return False

    def attack_scenario(self):
        print('montando o grafo')

        t1 = time.time()
        topology_graph = self.topology_graph()
        os.system('echo "montando o grafo: %s" >> /tmp/teste.txt' % str(time.time() - t1))

        print('\nmontando o peers_for_query\n')

        #self.affected = list(range(1, 10001))
        #self.target = list(range(1, 10001))

        t1 = time.time()
        # peers_for_query = [[1,2], [3,4], [5,6], [7,8], [9,1]]
        peers_for_query = list()
        # for each affected AS
        #print('self.affected: ', self.affected)
        #print('self.target: ', self.target)

        set_affected = set(self.affected)
        set_target = set(self.target)

        for affected_as in set_affected:
            number = affected_as / 100
            if number.is_integer():
                os.system('free -h | grep Mem >> /tmp/teste.txt')
                os.system('echo "%s - %s" >> /tmp/teste.txt' % (str(affected_as), str(time.time() - t1)))
                os.system('echo "" >> /tmp/teste.txt')
            # for each target AS
            for target_as in set_target:
                #print(affected_as, target_as)
                # look for the path only if this path has not been found before
                if affected_as == target_as:
                    #print('continue')
                    continue
                if target_as < affected_as and target_as in set_affected and affected_as in set_target:
                    #print('continue')
                    continue
                #print('vou apendar', affected_as, target_as)
                peers_for_query.append([affected_as, target_as])

        os.system('echo "quantidade de peers: %s" >> /tmp/teste.txt' % str(len(peers_for_query)))
        os.system('echo "inserção: %s" >> /tmp/teste.txt' % str(time.time() - t1))
        os.system('free -h | grep Mem >> /tmp/teste.txt')

        print(peers_for_query)

        print('\niniciando o multiprocessing')

        function = partial(self.bfs_shortest_path, topology_graph)
        all_paths = self.pool.map(function, peers_for_query)

        #os.system('echo "%s" > /tmp/paths.txt' % str(all_paths))


def clear_database(dbsession, scenario_id):
    try:
        delete = 'delete from scenario_stuff where id = %s' % scenario_id
        dbsession.bind.execute(delete)
        dbsession.flush()
    except Exception as error:
        dbsession.rollback()
        print('clear_database: ', error)


def save_to_database(dbsession, field, value):
    try:
        for i in range(len(field)):
            update = 'update realistic_analysis set %s = \'%s\'' % (field[i], str(value[i]))
            dbsession.bind.execute(update)
            dbsession.flush()
    except Exception as error:
        dbsession.rollback()
        print(error)


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
            os.system('free -h | grep Mem > /tmp/teste.txt')
            with env['request'].tm:
                dbsession = env['request'].dbsession
                aa = AttackScenario(dbsession, scenario_id, scenario_name, scenario_description, topology,
                                    attacker, affected_area, target, attack_type, number_of_shortest_paths)
                aa.attack_scenario()

            with env['request'].tm:
                if scenario_id:
                    clear_database(dbsession, scenario_id)
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
