import argparse
import getopt
import re

import networkx as nx
import sys
import time

import pandas as pd

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from minisecbgp import models


class AttackScenario(object):
    def __init__(self, dbsession, scenario_id, scenario_name, scenario_description,
                 topology, attacker, affected_area, target, attack_type):
        try:
            if scenario_id:
                scenario = dbsession.query(models.ScenarioStuff).\
                    filter_by(id=scenario_id).first()
                scenario_name = scenario.scenario_name
                scenario_description = scenario.scenario_description
                id_topology_base = scenario.id_topology
                attacker = scenario.attacker_list
                affected_area = scenario.affected_area_list
                target = scenario.target_list
                attack_type = scenario.attack_type
            else:
                topology_base = dbsession.query(models.Topology).\
                    filter_by(id=topology).first()
                if topology_base:
                    id_topology_base = topology_base.id
                else:
                    self.id_topology_base = ''
                    print('The topology does not exist')
                    return

            attackers = attacker.strip('][').split(',')
            attackers = map(int, attackers)
            attacker_list = list(attackers)

            affected_areas = affected_area.strip('][').split(',')
            affected_areas = map(int, affected_areas)
            affected_area_list = list(affected_areas)

            targets = target.strip('][').split(',')
            targets = map(int, targets)
            target_list = list(targets)

            query = 'select l.id_autonomous_system1 as id_AS_1, ' \
                    '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system1) as autonomous_system1, ' \
                    'l.id_autonomous_system2 as id_AS_2, ' \
                    '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system2) as autonomous_system2, ' \
                    '(select la.agreement from link_agreement la where la.id = l.id_link_agreement) as link_agreement ' \
                    'from link l ' \
                    'where l.id_topology = %s;' % id_topology_base
            result_proxy = dbsession.bind.execute(query)
            df_graph = pd.DataFrame(result_proxy, columns=['id_autonomous_system1', 'autonomous_system1',
                                                           'id_autonomous_system2', 'autonomous_system2',
                                                           'link_agreement'])

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
        self.attacker_list = attacker_list
        self.affected_area_list = affected_area_list
        self.target_list = target_list
        self.attack_type = attack_type.lower()

        self.df_graph = df_graph
        self.graph = nx.from_pandas_edgelist(df_graph, source='autonomous_system1', target='autonomous_system2')
        self.autonomous_system = sr_autonomous_system

    def valid_interception_path_found(self, attacker_as, attacker_to_target_paths, affected_to_attacker_paths):

        print('AS atacante: ', attacker_as)
        print('caminhos do atacante para o atacado: ', attacker_to_target_paths)
        print('caminhos do atacante para o afetadp: ', affected_to_attacker_paths)

        for attacker_to_target_path in attacker_to_target_paths:
            print('peguei o caminho do atacante para o atacado: ', attacker_to_target_path)
            attacker_to_target_autonomous_system = re.sub('[\[\]() ]', '', str(attacker_to_target_path)).split(',')
            attacker_to_target_autonomous_system.remove(str(attacker_as))
            print('destrinchei os AS desse caminho: ', attacker_to_target_autonomous_system)
            for affected_to_attacker_path in affected_to_attacker_paths:
                print('')
                print('peguei o caminho do atacamte para o afetado: ', affected_to_attacker_path)
                affected_to_attacker_autonomous_system = re.sub('[\[\]() ]', '', str(affected_to_attacker_path)).split(',')
                affected_to_attacker_autonomous_system.remove(str(attacker_as))
                print('destrinchei os AS desse caminho: ', affected_to_attacker_autonomous_system)
                invalid_path = set(attacker_to_target_autonomous_system) & set(affected_to_attacker_autonomous_system)
                print('verifico se existe um AS em comum nos dois caminhos.')
                if not invalid_path:
                    return True

        return False

    def validate_path(self, path):
        agreements = list()
        for hop in range(len(path)):
            agreement = self.df_graph.query('autonomous_system1 == %s & autonomous_system2 == %s' %
                                            (path[hop][0], path[hop][1]))
            if agreement.empty:
                agreement = self.df_graph.query('autonomous_system1 == %s & autonomous_system2 == %s' %
                                                (path[hop][1], path[hop][0]))
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

    def all_simple_paths(self):
        print('attackers: ', self.attacker_list)
        print('affecteds: ', self.affected_area_list)
        print('targets: ', self.target_list)
        for attacker_as in self.attacker_list:
            # for each affected_area AS
            for affected_as in self.affected_area_list:
                # for each prefix hijacked
                for target_as in self.target_list:
                    print('\nvou rodar o networkx para o atacante %s, o affected AS %s e o target %s\n' %(attacker_as, affected_as, target_as))
                    paths = list(nx.all_simple_paths(self.graph, source=affected_as, target=attacker_as))
                    print(paths)


    def attack_scenario(self):
        if self.id_topology_base:
            # for each attacker
            for attacker_as in self.attacker_list:
                # for each affected_area AS
                for affected_as in self.affected_area_list:
                    # for each prefix hijacked
                    for target_as in self.target_list:
                        '''
                            Verify if the AS in affected area will be affected by attacker hijack
                        '''
                        # The first condition that must be met is that the attacker AS must be different from the
                        # affected AS which must be different from the target AS
                        print(attacker_as, affected_as, target_as)
                        if not (attacker_as == affected_as) and \
                                not (attacker_as == target_as) and \
                                not (affected_as == target_as):
                            # affected_area AS to attacker AS distance
                            affected_to_attacker_shortest_path_found = False
                            affected_to_attacker_path = list()
                            affected_to_attacker_path_length = ''
                            for cutoff in range(len(self.graph.nodes())):
                                if not affected_to_attacker_shortest_path_found:
                                    paths = list(nx.all_simple_paths(self.graph, source=affected_as,
                                                                     target=attacker_as, cutoff=cutoff))
                                    if len(paths) > 0:
                                        for path in map(nx.utils.pairwise, paths):
                                            path = list(path)
                                            if self.validate_path(list(path)):
                                                affected_to_attacker_path.append(path)
                                                affected_to_attacker_path_length = len(path)
                                                affected_to_attacker_shortest_path_found = True

                            # it only continues to check the distance from the affected AS to the target AS, and from the
                            # attacker AS to the target AS (in the traffic interception attack) if:
                            # - there is at least one valid path between the attacker AS and the affected AS.
                            if affected_to_attacker_shortest_path_found:

                                # affected_area AS to target AS distance
                                affected_to_target_shortest_path_found = False
                                affected_to_target_path = list()
                                affected_to_target_path_length =''
                                for cutoff in range(len(self.graph.nodes())):
                                    if not affected_to_target_shortest_path_found:
                                        paths = list(nx.all_simple_paths(self.graph, source=affected_as,
                                                                         target=target_as, cutoff=cutoff))
                                        if len(paths) > 0:
                                            for path in map(nx.utils.pairwise, paths):
                                                path = list(path)
                                                if self.validate_path(list(path)):
                                                    affected_to_target_path.append(path)
                                                    affected_to_target_path_length = len(path)
                                                    affected_to_target_shortest_path_found = True

                                # it only continues if:
                                #  - there isn't a valid path between the affected AS and the target AS, OR
                                #  - the path length between attacker AS and affected AS is less or equal
                                # to the path length between the affected AS and target AS
                                if not affected_to_target_shortest_path_found \
                                        or (affected_to_target_shortest_path_found and
                                            (affected_to_attacker_path_length <= affected_to_target_path_length)):

                                    # if attack traffic type equal interception,
                                    # - find the shortest path between the attacker AS and the target AS

                                    #   - that does not pass through affected AS

                                    # - checks if the same AS does not exist either in:
                                    #   - the shortest path between the attacker AS and the affected AS, as well as in
                                    #   - the shortest path between the attacker AS and the target AS
                                    if self.attack_type == 'interception':

                                        # attacker AS to target AS distance
                                        attacker_to_target_shortest_path_found = False
                                        attacker_to_target_path = list()
                                        attacker_to_target_path_length = ''
                                        for cutoff in range(len(self.graph.nodes())):
                                            if not attacker_to_target_shortest_path_found:
                                                paths = list(nx.all_simple_paths(self.graph, source=attacker_as,
                                                                                 target=target_as, cutoff=cutoff))
                                                if len(paths) > 0:
                                                    for path in map(nx.utils.pairwise, paths):
                                                        path = list(path)
                                                        if self.validate_path(list(path)):
                                                            attacker_to_target_path.append(path)
                                                            attacker_to_target_path_length = len(path)
                                                            attacker_to_target_shortest_path_found = True

                                        # in interception attack there must be at least one path between the attacker AS
                                        # and the target AS
                                        if not attacker_to_target_shortest_path_found:
                                            print('There is no path between the attacker AS and the target AS.\n'
                                                  'This condition must be met in interception attacks.')
                                            return

                                        # in the interception attack, for a given scenario item, the same AS cannot exist either
                                        # in the shortest path between the attacker AS and the affected AS, as well as in the
                                        # shortest path between the attacker AS and the target AS
                                        if self.valid_interception_path_found(attacker_as, attacker_to_target_path, affected_to_attacker_path):
                                            print('CAMINHO SUPER VÁLIDO')
                                            return
                                        else:
                                            print('CAMINHO NÃO VALIDADO')
                                            print('existe um mesmo AS no caminho')
                                            return



                                        # se o cenário for de interceptação e o caminho do affected AS para o atacante for menor do que o do caminho do
                                        # affected AS para o target, consulto o caminho do atacante para o target

                                            # procuro o caminho do attacante para o target (Obs.: esse caminho não pode passar por um mesmo AS do caminho entre o affected e o target

                                            # se não existir esse caminho, então finaliza para esse target

                                        # se o caminho existir

                                    else: # se for igual interception
                                        pass

                        else:
                            print('o atacante é o mesmo que o target que o affected')



            #print('affected_to_attacker_path: ', affected_to_attacker_path)
            #print('affected_to_target_path: ', affected_to_target_path)




#                            # affected_area AS to target distance
#                            paths = list(nx.all_simple_paths(self.graph,
#                                                             source=affected_area_as,
#                                                             target=target_as,
#                                                             cutoff=cutoff))
#                            if len(paths) > 0 and not affected_as_to_target_distance:
#                                print('\npara cada path dos paths, vou verificar se ele é válido !!!')
#                                print('cutoff: ', cutoff, '\n')
#                                for path in map(nx.utils.pairwise, paths):
#                                    path = list(path)
#                                    if self.validate_path(list(path)):
#                                        affected_as_to_target_distance = len(path)
#                                        affected_as_to_target_path = path
#                                        affected_as_to_target_shortest_path_cutoff = cutoff
#                                        break

#                            if affected_as_to_target_distance and affected_as_to_attacker_distance:

#                                print('Affected Area AS to Target: ',
#                                      '- path: ', affected_as_to_target_path,
#                                      '- distance: ', affected_as_to_target_distance,
#                                      '- cutoff: ', affected_as_to_target_shortest_path_cutoff)
#                                print('Affected Area AS to Attacker: ',
#                                      '- path: ', affected_as_to_attacker_path,
#                                      '- distance: ', affected_as_to_attacker_distance,
#                                      '- cutoff: ', affected_as_to_attacker_shortest_path_cutoff)
#                                break


                        #target_to_affected_area_as_distance = \
                        #    nx.shortest_path_length(self.graph, source=target_as, target=affected_area_as)
                        #attacker_to_affected_area_as_distance = \
                        #    nx.shortest_path_length(self.graph, source=attacker_as, target=affected_area_as)



            # ver se o affected_as será comprometido
            #t3 = time.time()
            #for autonomous_system in sr_autonomous_system:
            #    shortest_path_to_attacker = nx.shortest_path_length(graph, source=autonomous_system, target=2)
            #    shortest_path_to_target = nx.shortest_path_length(graph, source=autonomous_system, target=8)
            #    if shortest_path_to_target >= shortest_path_to_attacker:
            #        print('autonomous system comprometido: %s (distância atacante: %s - distância target: %s)' % (
            #        autonomous_system, shortest_path_to_attacker, shortest_path_to_target))
            #    else:
            #        print('NÃO COMPROMETIDO: %s (distância atacante: %s - distância target: %s)' % (
            #            autonomous_system, shortest_path_to_attacker, shortest_path_to_target))
            #print('exec time: %s\n' % (time.time() - t3))

            # se o affected_as for comprometido, preciso pegar o "menor" caminho entre o affected_as e o attacker
            # obs.: "os menores caminhos" de acordo com o valor de shortest_paths informados pelo usuário

            #count = 0
            #for z in nx.all_simple_paths(graph, source=8241, target=1916, cutoff=3):
            #    if str(z) == '[8241, 6939, 1916]':
            #        print(count, str(z))
            #    count = count + 1
            #print(count)








            #t4 = time.time()
            #cutoff_has_path = 0
            #for cutoff in range(len(graph.nodes())):
            #    paths = list(nx.all_simple_paths(graph, source=8241, target=1916, cutoff=cutoff))
            #    if len(paths) > 0:
            #        cutoff_has_path = cutoff_has_path + 1
            #    if self.number_of_shortest_paths and cutoff_has_path == int(self.number_of_shortest_paths):
            #        break
            #t4 = time.time() - t4

            #print('print resultado final')
            #for path in paths:
            #    print(path, len(path))

            #print(cutoff_has_path, cutoff)
            #print(t4)






            #for z in nx.shortest_simple_paths(graph, source=2, target=8):
            #    print(z)




    def xdi_graph(self, df_graph, df_autonomous_system):
        graph = nx.from_pandas_edgelist(df_graph, source='autonomous_system1', target='autonomous_system2')
        #graph = nx.from_pandas_edgelist(df_as,
        #                                source='autonomous_system1',
        #                                target='autonomous_system2',
        #                                create_using=nx.DiGraph())

        #print('--------------')
        #print(graph.nodes())
        print('Number of nodes: %s\n' % len(graph.nodes()))
        #print(graph.edges())
        print('Number of edges: %s\n' % len(graph.edges()))

        #print('--------------')
        #path = nx.dijkstra_path(graph, source=1, target=1916)
        #print(path)

        #print('--------------')
        #path = nx.all_simple_paths(graph, source=8241, target=1916, cutoff=1)
        #for p in path:
        #    print(p)

        t3 = time.time()
        #for x in nx.all_simple_paths(graph, source=1, target=8, cutoff=2):
        for x in nx.all_simple_paths(graph, source=8241, target=1916, cutoff=nx.shortest_path_length(graph, source=8241, target=1916)):
            print(x)
        print('nx.all_simple_paths: %s\n' % (time.time() - t3))

        t2 = time.time()
        print(nx.dijkstra_path(graph, source=8241, target=1916))
        print('nx.dijkstra_path: %s\n' % (time.time() - t2))

        t1 = time.time()
        for b in nx.all_shortest_paths(graph, source=8241, target=1916):
            print(b)
        print('nx.shortest_path: %s\n' % (time.time() - t1))


        #t4 = time.time()
        #for z in range(len(graph.nodes())):
        #    for y in nx.all_simple_paths(graph, source=8241, target=1916, cutoff=z):
        #        print(y)
        #    if z == 3:
        #        break
        #print('%s\n' % (time.time() - t4))

        print(graph.is_directed())


def clear_database(dbsession, scenario_id):
    try:
        delete = 'delete from affected_area_stuff where id = %s' % scenario_id
        dbsession.bind.execute(delete)
        dbsession.flush()
    except Exception as error:
        dbsession.rollback()
        print(error)


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
                                    "topology=", "attacker=", "affected-area=", "target=", "attack-type="])
    except getopt.GetoptError:
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
              '\n'
              'or\n'
              '\n'
              '--scenario-id=16                                         scenario ID\n')
        sys.exit(2)
    config_file = scenario_id = scenario_name = scenario_description = topology = attacker = affected_area = target = attack_type = ''
    for opt, arg in opts:
        if opt == '-h':
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

    if (config_file and scenario_name and topology and attacker and affected_area and target and attack_type) \
            or (config_file and scenario_id):
        args = parse_args(config_file)
        setup_logging(args.config_uri)
        env = bootstrap(args.config_uri)
        try:
            with env['request'].tm:
                dbsession = env['request'].dbsession
                aa = AttackScenario(dbsession, scenario_id, scenario_name, scenario_description, topology,
                                    attacker, affected_area, target, attack_type)
                #aa.attack_scenario()
                aa.all_simple_paths()
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
              '\n'
              'or\n'
              '\n'
              '--scenario-id=16                                         scenario ID\n')
