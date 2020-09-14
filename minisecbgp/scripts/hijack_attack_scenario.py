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
                 topology, attacker, affected_area, target, attack_type, number_of_shortest_paths):
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
                affected_area = scenario.affected_area_list
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

            attackers = attacker.strip('][').split(',')
            attackers = map(int, attackers)
            attacker_list = list(attackers)
            for attacker_as in attacker_list:
                attacker_as_exist = dbsession.query(models.AutonomousSystem).\
                    filter_by(id_topology=id_topology_base).\
                    filter_by(autonomous_system=attacker_as).first()
                if not attacker_as_exist:
                    print('Autonomous System "%s" does not exist to be used as an attacker AS' % attacker_as)
                    attacker_list = ''

            affected_areas = affected_area.strip('][').split(',')
            affected_areas = map(int, affected_areas)
            affected_area_list = list(affected_areas)
            for affected_as in affected_area_list:
                affected_as_exist = dbsession.query(models.AutonomousSystem).\
                    filter_by(id_topology=id_topology_base).\
                    filter_by(autonomous_system=affected_as).first()
                if not affected_as_exist:
                    print('Autonomous System "%s" does not exist to be used as an affected AS' % affected_as)
                    affected_area_list = ''

            targets = target.strip('][').split(',')
            targets = map(int, targets)
            target_list = list(targets)
            for target_as in target_list:
                target_as_exist = dbsession.query(models.AutonomousSystem).\
                    filter_by(id_topology=id_topology_base).\
                    filter_by(autonomous_system=target_as).first()
                if not target_as_exist:
                    print('Autonomous System "%s" does not exist to be used as an target AS' % target_as)
                    target_list = ''

            topology_type = dbsession.query(models.TopologyType).\
                filter(func.lower(models.TopologyType.topology_type) == 'attack scenario').first()
            id_topology_type = topology_type.id

            id_scenario_attack_type = scenario_attack_type.id
            scenario_attack_type = scenario_attack_type.scenario_attack_type

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

            sr_autonomous_system = pd.concat([df_graph.reset_index()['autonomous_system1'],
                                              df_graph['autonomous_system2']], ignore_index=True)
            sr_autonomous_system = sr_autonomous_system.drop_duplicates(keep='first')
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
        self.affected_area_list = affected_area_list
        self.target_list = target_list
        self.id_scenario_attack_type = id_scenario_attack_type
        self.scenario_attack_type = scenario_attack_type.lower()
        self.number_of_shortest_paths = int(number_of_shortest_paths)
        self.id_topology_type = id_topology_type

        self.df_graph = df_graph
        self.graph = nx.from_pandas_edgelist(
            df_graph,
            source='autonomous_system1',
            target='autonomous_system2',
            edge_key='key',
            edge_attr=['id_autonomous_system1', 'id_autonomous_system2', 'link_agreement'],
            create_using=nx.MultiGraph()
        )
        self.autonomous_system = sr_autonomous_system

    def validate_path(self, path):
        agreements = list()
        for hop in range(len(path)):
            agreement = self.df_graph.query('autonomous_system1 == %s & autonomous_system2 == %s & key == %s' %
                                            (path[hop][0], path[hop][1], path[hop][2]))
            if agreement.empty:
                agreement = self.df_graph.query('autonomous_system1 == %s & autonomous_system2 == %s & key == %s' %
                                                (path[hop][1], path[hop][0], path[hop][2]))
                agreements.append(agreement.link_agreement.to_string(index=False)[::-1])
            else:
                agreements.append(agreement.link_agreement.to_string(index=False))
        for i in range(len(agreements)):
            agreement_base = agreements[i].strip()
            if agreement_base == 'p2p':
                for j in range(i+1, len(agreements), 1):
                    if agreements[j].strip() != 'p2c':
                        return False
            elif agreement_base == 'p2c':
                for j in range(i+1, len(agreements), 1):
                    if agreements[j].strip() != 'p2c':
                        return False
        return True

    def attack_scenario(self):
        if not self.failed:
            # topology
            try:
                self.dbsession.add(models.Topology(id_topology_type=self.id_topology_type,
                                                   topology=(self.scenario_name + ' - ' + self.topology_base)[:50],
                                                   description=self.scenario_description))
                self.dbsession.flush()
            except Exception as error:
                self.dbsession.rollback()
                print(error)
                return

            scenario_topology = self.dbsession.query(models.Topology).\
                filter_by(topology=(self.scenario_name + ' - ' + self.topology_base)[:50]).first()

            # scenario
            try:
                self.dbsession.add(models.Scenario(id_scenario_attack_type=self.id_scenario_attack_type,
                                                   id_topology=scenario_topology.id))
                self.dbsession.flush()
                self.dbsession.commit()
            except Exception as error:
                self.dbsession.rollback()
                print(error)
                return

            self.scenario = self.dbsession.query(models.Scenario).\
                filter_by(id_scenario_attack_type=self.id_scenario_attack_type).\
                filter_by(id_topology=scenario_topology.id).first()

            # scenario_item / path / path_item
            if self.attacker_list and self.affected_area_list and self.target_list:
                if self.scenario_attack_type == 'attraction':
                    self.attraction_attack_type()
                elif self.scenario_attack_type == 'interception':
                    self.interception_attack_type()
                else:
                    print('attack type unknown')
                    return

    def interception_attack_type(self):
        pass

    def attraction_attack_type(self):





        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', None)




        df_scenario_item = pd.DataFrame()
        df_path = pd.DataFrame()
        df_path_item = pd.DataFrame()

        # for each attacker
        for attacker_as in self.attacker_list:
            # for each affected_area AS
            for affected_as in self.affected_area_list:
                # for each prefix hijacked
                for target_as in self.target_list:
                    '''
                        Verify if the AS in affected area will be affected by attacker hijack
                    '''
                    # The first condition that must be met is the attacker AS, the affected AS,
                    # and the target AS must be different from each other
                    if not (attacker_as == affected_as) and \
                            not (attacker_as == target_as) and \
                            not (affected_as == target_as):

                        # return the affected_area AS to attacker AS distance
                        path_list = list()
                        affected_to_attacker_shortest_path_found = False
                        affected_to_attacker_valid_paths = list()
                        affected_to_attacker_shortest_path_length = ''
                        paths = nx.all_simple_edge_paths(self.graph, affected_as, attacker_as)

                        # order paths by path length
                        for path in paths:
                            path_list.append({'path_length': len(path), 'path': path})
                        df_path = pd.DataFrame(data=path_list, columns=['path_length', 'path'])
                        df_path.reset_index()
                        df_path.set_index('path_length', inplace=True)
                        df_path = df_path.sort_index()

                        print('===========================================')
                        print('paths: affected AS to attacker AS')
                        print(df_path)

                        count_index = 0
                        index_value = 0

                        for index, row in df_path.iterrows():
                            if index_value < index:
                                index_value = index
                                count_index = count_index + 1
                            if (count_index > self.number_of_shortest_paths) and (self.number_of_shortest_paths != 0):
                                break

                            if self.validate_path(list(row['path'])):
                                affected_to_attacker_valid_paths.append(row['path'])
                                if not affected_to_attacker_shortest_path_length:
                                    affected_to_attacker_shortest_path_length = len(row['path'])
                                affected_to_attacker_shortest_path_found = True

                        print('affected_to_attacker_shortest_path_found :', affected_to_attacker_shortest_path_found)
                        print('affected_to_attacker_valid_paths :', affected_to_attacker_valid_paths)
                        print('affected_to_attacker_shortest_path_length :', affected_to_attacker_shortest_path_length)

                        # it only continues to check the distance from the affected AS to the target AS if:
                        # - there is at least one valid path between the attacker AS and the affected AS.
                        if affected_to_attacker_shortest_path_found:

                            # return the affected_area AS to target AS distance
                            path_list = list()
                            affected_to_target_shortest_path_found = False
                            affected_to_target_valid_paths = list()
                            affected_to_target_shortest_path_length = ''
                            paths = nx.all_simple_edge_paths(self.graph, affected_as, target_as)

                            # order paths by path length
                            for path in paths:
                                path_list.append({'path_length': len(path), 'path': path})
                            df_path = pd.DataFrame(data=path_list, columns=['path_length', 'path'])
                            df_path.reset_index()
                            df_path.set_index('path_length', inplace=True)
                            df_path = df_path.sort_index()

                            print('\n\n===========================================')
                            print('paths: affected AS to target AS')
                            print(df_path)

                            count_index = 0
                            index_value = 0

                            for index, row in df_path.iterrows():
                                if index_value < index:
                                    index_value = index
                                    count_index = count_index + 1
                                if (count_index > self.number_of_shortest_paths) and (
                                        self.number_of_shortest_paths != 0):
                                    break

                                if self.validate_path(list(row['path'])):
                                    affected_to_target_valid_paths.append(row['path'])
                                    if not affected_to_target_shortest_path_length:
                                        affected_to_target_shortest_path_length = len(row['path'])
                                    affected_to_target_shortest_path_found = True

                            print('affected_to_target_shortest_path_found :', affected_to_target_shortest_path_found)
                            print('affected_to_target_valid_paths :', affected_to_target_valid_paths)
                            print('affected_to_target_shortest_path_length :', affected_to_target_shortest_path_length)

                            # it only continues if:
                            #  - there isn't a valid path between the affected AS and the target AS, OR
                            #  - the path length between attacker AS and affected AS is less or equal
                            # to the path length between the affected AS and target AS
                            if not affected_to_target_shortest_path_found \
                                    or (affected_to_target_shortest_path_found and
                                        (affected_to_attacker_shortest_path_length <= affected_to_target_shortest_path_length)):
                                print('O AS %s está na affected area do atacante %s fazendo hijack do target %s' % (affected_as, attacker_as, target_as))
                                print(self.id_topology_base, attacker_as, affected_as, target_as)

                                print('SALVA OS DADOS DO CENÁRIO')

                                # table: scenario_item

                                print('PRINTANDO O ID_CENARIO: ', self.scenario.id, self.scenario.id_scenario_attack_type, self.scenario.id_topology)

                                df_scenario_item = df_scenario_item.append({'id_scenario': self.scenario.id,
                                                                            'attacker_as': attacker_as,
                                                                            'affected_as': affected_as,
                                                                            'target_as': target_as},
                                                                           ignore_index=True)
                                df_scenario_item.to_sql('scenario_item', con=self.dbsession.bind, if_exists='append',
                                                        index=False)


                                # table: path

                                # table: path_item

                            else:
                                print('PRECISO AVISAR O USUÁRIO DE ALGUMA FORMA QUE ESSE ATACANTE PARA ESSE TARGET NÃO AFETA ESSE AS')


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
                aa.attack_scenario()
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
