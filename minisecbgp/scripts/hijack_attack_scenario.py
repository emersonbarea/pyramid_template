import argparse
import getopt

import networkx as nx
import sys

import pandas as pd

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy import func
from sqlalchemy.exc import OperationalError

from minisecbgp import models


class AttackScenario(object):
    def __init__(self, dbsession, scenario_id, scenario_name, scenario_description,
                 topology, attacker, affected, target, attack_type, number_of_shortest_paths):
        self.failed = False
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

            attackers = attacker.strip('][').split(',')
            attackers = map(int, attackers)
            attacker_list_temp = list(attackers)
            attacker_list = list()
            for attacker_as in attacker_list_temp:
                attacker_as_exist = dbsession.query(models.AutonomousSystem).\
                    filter_by(id_topology=id_topology_base).\
                    filter_by(autonomous_system=attacker_as).first()
                if not attacker_as_exist:
                    print('Autonomous System "%s" does not exist to be used as an attacker AS' % attacker_as)
                    attacker_list = ''
                else:
                    attacker_list.append(attacker_as_exist.id)

            print('affected')

            affecteds = affected.strip('][').split(',')
            affecteds = map(int, affecteds)
            affected_list_temp = list(affecteds)
            affected_list = list()
            for affected_as in affected_list_temp:
                affected_as_exist = dbsession.query(models.AutonomousSystem).\
                    filter_by(id_topology=id_topology_base).\
                    filter_by(autonomous_system=affected_as).first()
                if not affected_as_exist:
                    print('Autonomous System "%s" does not exist to be used as an affected AS' % affected_as)
                    affected_list = ''
                else:
                    affected_list.append(affected_as_exist.id)

            print('targets')

            targets = target.strip('][').split(',')
            targets = map(int, targets)
            target_list_temp = list(targets)
            target_list = list()
            for target_as in target_list_temp:
                target_as_exist = dbsession.query(models.AutonomousSystem).\
                    filter_by(id_topology=id_topology_base).\
                    filter_by(autonomous_system=target_as).first()
                if not target_as_exist:
                    print('Autonomous System "%s" does not exist to be used as an target AS' % target_as)
                    target_list = ''
                else:
                    target_list.append(target_as_exist.id)

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

            print('pandas dataframe graph')

            query = 'select l.id as key, ' \
                    'l.id_autonomous_system1 as id_AS_1, ' \
                    '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system1) as autonomous_system1, ' \
                    'l.id_autonomous_system2 as id_AS_2, ' \
                    '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system2) as autonomous_system2, ' \
                    '(select la.agreement from link_agreement la where la.id = l.id_link_agreement) as link_agreement ' \
                    'from link l ' \
                    'where l.id_topology = %s;' % id_topology_base
            result_proxy = dbsession.bind.execute(query)
            df_graph = pd.DataFrame(result_proxy, columns=['key', 'id_autonomous_system1', 'autonomous_system1',
                                                           'id_autonomous_system2', 'autonomous_system2', 'link_agreement'])

        except Exception as error:
            print('Error: ', error)
            return

        self.dbsession = dbsession
        self.scenario_id = scenario_id
        self.scenario_name = scenario_name
        self.scenario_description = scenario_description
        self.id_topology_base = id_topology_base
        self.topology_base = topology_base
        self.attacker_list = attacker_list
        self.affected_list = affected_list
        self.target_list = target_list
        self.id_scenario_attack_type = id_scenario_attack_type
        self.scenario_attack_type = scenario_attack_type.lower()
        self.number_of_shortest_paths = int(number_of_shortest_paths)
        self.id_topology_type = id_topology_type

        self.df_graph = df_graph

        print('networkx graph')

        self.graph = nx.from_pandas_edgelist(
            df_graph,
            source='id_autonomous_system1',
            target='id_autonomous_system2',
            edge_key='key',
            edge_attr=['autonomous_system1', 'autonomous_system2', 'link_agreement'],
            create_using=nx.MultiGraph()
        )

        print('attacker length: ', len(self.attacker_list))
        print('affected length: ', len(self.affected_list))
        print('target length: ', len(self.target_list))

        print('finalizei o init')

    def validate_path(self, path):
        agreements = list()
        for hop in range(len(path)):
            agreement = self.df_graph.query('id_autonomous_system1 == %s & id_autonomous_system2 == %s & key == %s' %
                                            (path[hop][0], path[hop][1], path[hop][2]))
            if agreement.empty:
                agreement = self.df_graph.query('id_autonomous_system1 == %s & id_autonomous_system2 == %s & key == %s' %
                                                (path[hop][1], path[hop][0], path[hop][2]))
                agreements.append(agreement.link_agreement.to_string(index=False)[::-1])
            else:
                agreements.append(agreement.link_agreement.to_string(index=False))
        for i in range(len(agreements)):
            agreement_base = agreements[i].strip()
            if agreement_base == 'p2p':
                for j in range(i+1, len(agreements), 1):
                    if agreements[j].strip() != 'p2c':
                        print(' - validando o path %s - INVÁLIDO - %s' % (path, agreements))
                        return False
            elif agreement_base == 'p2c':
                for j in range(i+1, len(agreements), 1):
                    if agreements[j].strip() != 'p2c':
                        print(' - validando o path %s - INVÁLIDO - %s' % (path, agreements))
                        return False
        print(' - validando o path %s - válido - %s' % (path, agreements))
        return True

    @staticmethod
    def path_already_researched(searched_paths, source, target):
        for path in searched_paths:
            if (path[0] == source and path[1] == target) or (path[1] == source and path[0] == target):
                return True
        return False

    def attack_scenario(self):
        if not self.failed:
            # topology
            try:
                scenario_topology = models.Topology(id_topology_type=self.id_topology_type,
                                                    topology=(self.scenario_name + ' - ' + self.topology_base)[:50],
                                                    description=self.scenario_description)
                self.dbsession.add(scenario_topology)
                self.dbsession.flush()
            except Exception as error:
                self.dbsession.rollback()
                print(error)
                return

            # scenario
            try:
                self.dbsession.add(models.Scenario(id_scenario_attack_type=self.id_scenario_attack_type,
                                                   id_topology=scenario_topology.id))
                self.dbsession.flush()
            except Exception as error:
                self.dbsession.rollback()
                print(error)
                return

            self.id_scenario = self.dbsession.query(models.Scenario.id).\
                filter_by(id_scenario_attack_type=self.id_scenario_attack_type).\
                filter_by(id_topology=scenario_topology.id).first()

            return self.attacker_list, self.affected_list, self.target_list, self.scenario_attack_type

    def interception_attack_type(self):
        pass

    def attraction_attack_type(self):

        print('attraction_attack_type')
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', None)

        # for each affected:
        # - look for the shortest path from the affected to the target
        #   - if this path has not been found before
        # - look for the path from the affected to the attacker
        #   - if this path has not been found before
        #   - if this path is less than the path between affected to target

        searched_paths = list()

        for affected_as in self.affected_list:

            # for each target AS
            for target_as in self.target_list:

                # look for the path only if this path has not been found before
                if affected_as != target_as and not self.path_already_researched(searched_paths, affected_as, target_as):

                    # put the affected - target in the "searched_paths" list
                    print('\n', affected_as, target_as)
                    paths = nx.all_shortest_paths(self.graph, source=affected_as, target=target_as)
                    for path in paths:
                        print(path)
                    searched_paths.append([affected_as, target_as])

            # for each attacker
#            for attacker_as in self.attacker_list:
#                pass


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
            with env['request'].tm:
                dbsession = env['request'].dbsession
                aa = AttackScenario(dbsession, scenario_id, scenario_name, scenario_description, topology,
                                    attacker, affected_area, target, attack_type, number_of_shortest_paths)
                attacker_list, affected_area_list, target_list, scenario_attack_type = aa.attack_scenario()

            # scenario_item / path / path_item
            if attacker_list and affected_area_list and target_list:
                if scenario_attack_type == 'attraction':
                    with env['request'].tm:
                        aa.attraction_attack_type()
                elif scenario_attack_type == 'interception':
                    with env['request'].tm:
                        aa.interception_attack_type()
                else:
                    print('attack type unknown')
                    return

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
