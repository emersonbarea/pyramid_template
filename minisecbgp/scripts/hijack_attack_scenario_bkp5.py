import argparse
import getopt
import time
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

            query = 'select l.id as id_link, '\
                    'l.id_autonomous_system1 as id_autonomous_system1, '\
                    'l.id_autonomous_system2 as id_autonomous_system2, '\
                    '(select la.agreement from link_agreement la where la.id = l.id_link_agreement) as agreement ' \
                    'from link l ' \
                    'where l.id_topology = %s;' % id_topology_base
            result_proxy = dbsession.bind.execute(query)
            df_graph = pd.DataFrame(result_proxy, columns=['id_link',
                                                           'id_autonomous_system1',
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
        self.attacker_list = attacker_list
        self.affected_area_list = affected_area_list
        self.target_list = target_list
        self.id_scenario_attack_type = id_scenario_attack_type
        self.scenario_attack_type = scenario_attack_type.lower()
        self.number_of_shortest_paths = int(number_of_shortest_paths)
        self.id_topology_type = id_topology_type

        self.df_graph = df_graph

        print(self.df_graph)

    def children(self, parent):
        try:
            children_temp1 = self.df_graph.set_index('id_autonomous_system1'). \
                loc[[parent]][['id_link', 'id_autonomous_system2', 'agreement']]
            children_temp1.columns = ['id_link', 'peer_id_autonomous_system', 'agreement']
        except KeyError:
            children_temp1 = pd.DataFrame(columns=['id_link', 'peer_id_autonomous_system', 'agreement'])

        # changing p2p to 2 and p2c to 3 where needed
        if not children_temp1.empty:
            try:
                children_temp1.loc[children_temp1['agreement'] == 'p2p', 'agreement'] = 2
            except KeyError:
                pass

            try:
                children_temp1.loc[children_temp1['agreement'] == 'p2c', 'agreement'] = 3
            except KeyError:
                pass

        try:
            children_temp2 = self.df_graph.set_index('id_autonomous_system2'). \
                loc[[parent]][['id_link', 'id_autonomous_system1', 'agreement']]
            children_temp2.columns = ['id_link', 'peer_id_autonomous_system', 'agreement']
        except KeyError:
            children_temp2 = pd.DataFrame(columns=['id_link', 'peer_id_autonomous_system', 'agreement'])

        # changing p2p to 2 and p2c to 1 where needed
        if not children_temp2.empty:
            try:
                children_temp2.loc[children_temp2['agreement'] == 'p2p', 'agreement'] = 2
            except KeyError:
                pass

            try:
                children_temp2.loc[children_temp2['agreement'] == 'p2c', 'agreement'] = 1
            except KeyError:
                pass

        children = pd.concat([children_temp1, children_temp2])
        #children = children.reset_index()


        return children

    def attack_scenario(self):
#        if not self.failed:
#            # topology
#            try:
#                scenario_topology = models.Topology(id_topology_type=self.id_topology_type,
#                                                    topology=(self.scenario_name + ' - ' + self.topology_base)[:50],
#                                                    description=self.scenario_description)
#                self.dbsession.add(scenario_topology)
#                self.dbsession.flush()
#            except Exception as error:
#                self.dbsession.rollback()
#                print(error)
#                return

            # scenario
#            try:
#                self.dbsession.add(models.Scenario(id_scenario_attack_type=self.id_scenario_attack_type,
#                                                   id_topology=scenario_topology.id))
#                self.dbsession.flush()
#            except Exception as error:
#                self.dbsession.rollback()
#                print(error)
#                return

#            self.id_scenario = self.dbsession.query(models.Scenario.id). \
#                filter_by(id_scenario_attack_type=self.id_scenario_attack_type). \
#                filter_by(id_topology=scenario_topology.id).first()

            return self.attacker_list, self.affected_area_list, self.target_list, self.scenario_attack_type

    def interception_attack_type(self):
        pass

    def attraction_attack_type(self):

        valid_paths = pd.DataFrame(columns=['source', 'target', 'path'])

        for source in self.affected_area_list:
            for target in self.target_list:

                print('\n----------------------------')
                print('\nsource: ', source)
                print('target: ', target)

                parent = source
                visited = pd.DataFrame({'visited': [source]})
                print('\n----------------------------')
                print('visited:\n', visited)

                path = list()
                last_agreement = 1                # c2p = 1, p2p = 2 and p2c = 3

                '''
                    getting all source's peers (children) from df_graph 
                '''
                children = self.children(source)
                print('\n----------------------------')
                print('children:\n', children)

                print('\nVERIFICANDO CHILDREN (while)')

                # while children has child and target not found in path, repeat
                while not children.empty:

                    print('\n=========================================================')
                    '''
                        if target is in children
                    '''

                    print('\n----------------------------')
                    print('verificando se target está em children')

                    try:

                        target_found = children[children.peer_id_autonomous_system == target]

                        print('\n----------------------------')
                        print('target_found \n', target_found, type(target_found))

                        '''
                            validate the agreement between parent and children item (the target)
                        '''
                        while not target_found.empty:

                            # for each register found in target_found
                            target_temp = target_found.iloc[-1]

                            print('\n----------------------------')
                            print('pegando o último target da lista de targets_found: ', target_temp['id_link'])

                            '''
                                validate agreement between parent and child to recursively find new children
                            '''
                            # if last_agreement_value == 1, child['agreement'] should be in (1, 2, 3)
                            # if last_agreement_value == 2, child['agreement'] must be == 3
                            # if last_agreement_value == 3, child['agreement'] must be == 3

                            print('\n----------------------------')
                            print('verificando se o agreement é válido')

                            if ((last_agreement == 1 and target_temp['agreement'] >= 1)
                                    or (last_agreement > 1 and target_temp['agreement'] > 2)):

                                print('\n----------------------------')
                                print('agreement válido !!!')

                                # put the path in the valid_paths dataframe
                                path.append(target_temp['id_link'])

                                print('\n----------------------------')
                                print('acrescentando o id_link do target no path:\n', path)

                                #valid_paths = valid_paths.append({'source': source, 'target': target, 'path': path}, ignore_index=True)

                            else:
                                print('\n----------------------------')
                                print('agreement INválido !!!')

                            # removes this target from target_temp
                            target_found = target_found[:-1]
                            print('\n----------------------------')
                            print('removendo o target_temp %s do target_found: \n' % target_temp['id_link'], target_found)

                            # removes this target from children
                            children = children[children.id_link != target_temp.id_link]
                            print('\n----------------------------')
                            print('removendo o target_temp %s do children: \n' % target_temp['id_link'], children)

                    except IndexError:
                        # raises keyError exception if target is not in children

                        print('\n----------------------------')
                        print('target not found !!!\n', target)

                        '''
                            take the child from children
                        '''
                        child = children.iloc[-1]
                        print('\n----------------------------')
                        print('pegando o child: \n', child['peer_id_autonomous_system'])

                        '''
                            validate agreement between parent and child to recursively find new children
                        '''

                        print('\n----------------------------')
                        print('verificando se o agreement é válido')

                        # if last_agreement_value == 1, child['agreement'] should be in (1, 2, 3)
                        # if last_agreement_value == 2, child['agreement'] must be == 3
                        # if last_agreement_value == 3, child['agreement'] must be == 3
                        if ((last_agreement == 1 and child['agreement'] >= 1)
                                or (last_agreement > 1 and child['agreement'] > 2)):

                            print('\n----------------------------')
                            print('agreement válido !!!')

                            # last_agreement_value receive the new agreement value to use in next child path agreement verification
                            last_agreement = child['agreement']
                            print('\n----------------------------')
                            print('atualizando o agreement: ', last_agreement)

                            # put the link in path
                            path.append(child['id_link'])
                            print('\n----------------------------')
                            print('incluindo o id_link no path: ', path)

                            # put the child in visited
                            visited = visited.append({'visited': child['peer_id_autonomous_system']}, ignore_index=True)
                            print('\n----------------------------')
                            print('incluindo o child no visited: \n', visited)

                            # find child's children
                            children = self.children(child['peer_id_autonomous_system'])
                            print('\n----------------------------')
                            print('consultando novo children do child %s (loop): \n' % child['peer_id_autonomous_system'], children)

                        else:
                            print('\n----------------------------')
                            print('agreement INválido !!!')

                        # removes this child from children
                        #children = children[:-1]

                        '''
                            erase children items that exist in visited list
                        '''
                        children = children[~children.peer_id_autonomous_system.isin(visited.visited)]
                        print('\ntirando visited items de children:\n', children)


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
