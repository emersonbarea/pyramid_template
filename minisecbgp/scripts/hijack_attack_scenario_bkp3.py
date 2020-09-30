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

            affected_areas = affected_area.strip('][').split(',')
            affected_areas = map(int, affected_areas)
            affected_area_list_temp = list(affected_areas)
            affected_area_list = list()
            for affected_as in affected_area_list_temp:
                affected_as_exist = dbsession.query(models.AutonomousSystem).\
                    filter_by(id_topology=id_topology_base).\
                    filter_by(autonomous_system=affected_as).first()
                if not affected_as_exist:
                    print('Autonomous System "%s" does not exist to be used as an affected AS' % affected_as)
                    affected_area_list = ''
                else:
                    affected_area_list.append(affected_as_exist.id)

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

            print('\npandas dataframe graph')

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
            print(df_graph)

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

        print('networkx graph')

        self.graph = nx.from_pandas_edgelist(
            df_graph,
            source='id_autonomous_system1',
            target='id_autonomous_system2',
            edge_key='key',
            edge_attr=['autonomous_system1', 'autonomous_system2', 'link_agreement'],
            create_using=nx.MultiGraph()
        )

        print(list(self.graph.edges()))
        print(list(self.graph.edges()))

        attacker_count = 1
        affected_count = 1
        target_count = 1

        print('\nlistas:')
        print(' - self.attacker_list: ', self.attacker_list)
        print(' - self.affected_list: ', self.affected_area_list)
        print(' - self.target_list: ', self.target_list)

        for attacker_as in self.attacker_list:
            for affected_as in self.affected_area_list:
                for target_as in self.target_list:

                    print('\nATTACKER %s - %s de %s' % (attacker_as, attacker_count, len(self.attacker_list)))
                    print('AFFECTED %s - %s de %s' % (affected_as, affected_count, len(self.affected_area_list)))
                    print('TARGET %s - %s de %s' % (target_as, target_count, len(self.target_list)))

                    print(list(all_simple_paths(self.graph, source=affected_as, target=target_as, cutoff=4)))


def all_simple_paths(G, source, target, cutoff=None):
    print('\n--> all_simple_paths')
    # source = a source AS (type int)
    # target = a target AS (type int)
    # targets = a set of targets (type set)
    print(' -> source: ', source)
    if target in G:
        targets = {target}
        print(' -> targets: ', targets)
    if G.is_multigraph():
        return _all_simple_paths_multigraph(G, source, targets, cutoff)


def _all_simple_paths_multigraph(G, source, targets, cutoff):
    print('    --> _all_simple_paths_multigraph')
    # visited:  {67030: None} <class 'dict'>
    visited = dict.fromkeys([source])
    print('     -> visited: ', visited, type(visited))
    # stack:  [<generator object _all_simple_paths_multigraph.<locals>.<genexpr> at 0x7f4354b56780>] <class 'list'>
    # stack é uma lista que recebe todos os vértices que possuem link com o source. Ex.:
    # [(67030, 67032), (67030, 67029)]
    stack = [(v for u, v in G.edges(source))]
    print('     -> stack: ', G.edges(source), type(stack))

    # para cada elemento na lista
    print('\n     -> while stack')
    while stack:

        # OBS.: NÃO USAR GENERATOR. USAR LISTA NO LUGAR (se couber na memória) PORQUE ELA É MAIS RÁPIDA
        # https://realpython.com/introduction-to-python-generators/#building-generators-with-generator-expressions

        # OBS.: NÃO USAR SET. USAR PD.SERIES NO LUGAR PORQUE ELA É MAIS RÁPIDA PARA INTEIROS
        # https://stackoverflow.com/questions/46839277/series-unique-vs-list-of-set-performance

        # OBS.: ALGORITMO PARA BUSCA EM ÁRVORE (TREAP)
        # https://web.archive.org/web/20140327140251/http://www.cepis.org/upgrade/files/full-2004-V.pdf
        # Heger, Dominique A. (2004), "A Disquisition on The Performance Behavior of Binary Search Tree Data Structures",
        #   European Journal for the Informatics Professional, 5 (5): 67–75, archived from the original (PDF) on 2014-03-27, retrieved 2010-10-16

        # generator que contém todos peers do source. Ex.:
        # children: [67032, 67029] <class 'generator'>
        children = stack[-1]

        # child: pega um peer por vez, e vai pegando os peers desse peer original (e caminhando no path) Ex.:
        # child:  67032 <class 'int'>
        # child: 67053 <class 'int'>#
        # child: 67030 <class 'int'>
        # child: None <class 'NoneType'>
        child = next(children, None)
        print('       -> child: ', child, type(child))

        if child is None:
            # apaga o último item da lista e do dicionário quando não tiver mais peer para pesquisar
            stack.pop()
            visited.popitem()

        # se o número de peer visitados for menor que o cutoff
        elif len(visited) < cutoff:

            # se o peer já foi visitado, desconsidera ele e continua o loop dos peers
            if child in visited:
                continue

            # caso o peer em questão for o target desejado (chegou no destino)
            if child in targets:
                # inclui o peer na lista de visitados e volta para o início do loop, pegando o próximo peer (para descobrir novos caminhos a partir desse peer)
                yield list(visited) + [child]

            # incluo o peer visitado na lista de visitados
            # {67030: None, 67032: None}
            visited[child] = None

            # verifica se o target está no grupo de visitados
            # - subitrai o AS do targets se ele existir no grupo dos visitados
            #   - nesse caso o if será falso se existir
            if targets - set(visited.keys()):
                # se o target NÃO existir no visited
                # o stack recebe a lista de peers do child (AS que está sendo analisado nesse loop
                stack.append((v for u, v in G.edges(child)))
            else:
                # se o target EXISTIR no visited
                # tiro o target do visited porque ele não deve ser visitado, mas sim é o ponto final dessa análise
                visited.popitem()

        else:  # len(visited) == cutoff:
            for target in targets - set(visited.keys()):
                count = ([child] + list(children)).count(target)
                for i in range(count):
                    yield list(visited) + [target]
            stack.pop()
            visited.popitem()


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
