import argparse
import getopt
import os
import subprocess
import sys
from datetime import datetime

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

            query = 'select l.id_autonomous_system1 as id_autonomous_system1, '\
                    'l.id_autonomous_system2 as id_autonomous_system2, '\
                    '(select la.agreement from link_agreement la where la.id = l.id_link_agreement) as agreement, ' \
                    'l.id as id_link '\
                    'from link l ' \
                    'where l.id_topology = %s;' % id_topology_base
            result_proxy = dbsession.bind.execute(query)
            df_links = pd.DataFrame(result_proxy, columns=['id_autonomous_system1',
                                                           'id_autonomous_system2',
                                                           'agreement',
                                                           'id_link'])

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

        self.df_links = df_links

    def all_paths(self):

        df_links_temp1 = self.df_links[['id_autonomous_system1',
                                        'id_autonomous_system2',
                                        'agreement',
                                        'id_link']]

        df_links_temp2 = self.df_links[['id_autonomous_system2',
                                        'id_autonomous_system1',
                                        'agreement',
                                        'id_link']]
        df_links_temp2.rename(columns={'id_autonomous_system2': 'id_autonomous_system1',
                                       'id_autonomous_system1': 'id_autonomous_system2'}, inplace=True)

        # changing p2p to 2 and p2c to 3 in df_links
        if not df_links_temp1.empty:
            try:
                df_links_temp1.loc[df_links_temp1['agreement'] == 'p2p', 'agreement'] = 2
            except KeyError:
                pass
            try:
                df_links_temp1.loc[df_links_temp1['agreement'] == 'p2c', 'agreement'] = 3
            except KeyError:
                pass

        # changing p2p to 2 and p2c to 1 in df_links_inverted
        if not df_links_temp2.empty:
            try:
                df_links_temp2.loc[df_links_temp2['agreement'] == 'p2p', 'agreement'] = 2
            except KeyError:
                pass
            try:
                df_links_temp2.loc[df_links_temp2['agreement'] == 'p2c', 'agreement'] = 1
            except KeyError:
                pass

        df_links = pd.concat([df_links_temp1, df_links_temp2], ignore_index=True)

        links = list()
        for index, row in df_links.iterrows():
            links.append(str(row[0]) + '-' + str(row[1]) + '-' + str(row[2]) + '-' + str(row[3]))

        return links

    def attack_scenario(self):

        attacker_list = str(self.attacker_list).strip('[]').replace(' ', '')
        affected_area_list = str(self.affected_area_list).strip('[]').replace(' ', '')
        target_list = str(self.target_list).strip('[]').replace(' ', '')
        links = str(self.all_paths()).strip('[]').replace(' ', '').replace('\'', '')


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

                print('iniciando o objeto')

                aa = AttackScenario(dbsession, scenario_id, scenario_name, scenario_description, topology,
                                    attacker, affected_area, target, attack_type, number_of_shortest_paths)

                print('iniciando o attack_scenario')
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
