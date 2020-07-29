import argparse
import getopt
import ipaddress
import sys
import time

import pandas as pd
import os
import shutil

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy import func
from sqlalchemy.exc import OperationalError

from minisecbgp import models


class AffectedArea(object):
    def __init__(self, dbsession, include_stub, attacker_all, target_all, prefix_target, prefix_all, all_paths,
                 scenario_name, scenario_description, topology, attacker_region, attacker_autonomous_system,
                 target_region, target_autonomous_system, prefix_region, prefix_autonomous_system, prefix_address,
                 number_of_shortest_paths):
        self.dbsession = dbsession

        print(include_stub, attacker_all, target_all, prefix_target, prefix_all, all_paths,
              scenario_name, scenario_description, topology, attacker_region, attacker_autonomous_system,
              target_region, target_autonomous_system, prefix_region, prefix_autonomous_system, prefix_address,
              number_of_shortest_paths)


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
                                   ["config-file=", "scenario-name=", "scenario-description=", "topology=", "include-stub",
                                    "attacker-all", "attacker-region=", "attacker-autonomous-system=", "target-all",
                                    "target-region=", "target-autonomous-system=", "prefix-target", "prefix-all",
                                    "prefix-region=", "prefix-autonomous-system=", "prefix-address=", "all-paths",
                                    "number-of-shortest-paths="])
    except getopt.GetoptError as error:
        print('\n'
              'Use: MiniSecBGP_affected_area [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--include-stub                                   to include stub ASs from original topology\n'
              '--config-file="minisecbgp.ini"                   pyramid config fileaname [.ini]\n'
              '--scenario-name="Test topology"                  the name that will be used to identify this scenario\n'
              '--scenario-description="date 20200729"           the scenario description\n'
              '--topology=3                                     the topology ID that bases this scenario\n'
              '\n'
              'choose one option:\n'
              '     --attacker-all                              use all ASs as the attacker\n'
              '     --attacker-region="north"                   use all ASs from specific region(s) as the attacker>\n'
              '     --attacker-autonomous-system=[65001,65002]  explicitly define which AS(s) will be the attacker\n'
              '\n'
              'choose one option:\n'
              '     --target-all                                use all ASs as the target\n'
              '     --target-region="south"                     use all ASs from specific region(s) as the target>\n'
              '     --target-autonomous-system=[65001]          explicitly define which AS(s) will be the target\n'
              '\n'
              'choose one option:\n'
              '     --prefix-target                             use the target prefix\n'
              '     --prefix-all                                use all prefixes of all topology ASs\n'
              '     --prefix-region="south"                     use all prefixes of all routers in the region(s)\n'                  
              '     --prefix-autonomous-system=[65001,65002]    use the prefix of a specific AS\n'
              '     --prefix-address=                           choose the prefix to hijack\n'
              '\n'
              'choose one option:\n'
              '     --all-paths                                 use all possible paths from attacker\'s AS to target\'s AS\n'
              '     --number-of-shortest-paths=3                define the max number of shortest paths to use between the attacker and target\n')
        sys.exit(2)
    include_stub = attacker_all = target_all = prefix_target = prefix_all = all_paths = False
    config_file = scenario_name = scenario_description = topology = attacker_region = \
        attacker_autonomous_system = target_region = target_autonomous_system = prefix_region = \
        prefix_autonomous_system = prefix_address = number_of_shortest_paths = ''
    for opt, arg in opts:
        if opt == '-h':
            print('\n'
                  'Use: MiniSecBGP_affected_area [options]\n'
                  '\n'
                  'options (with examples):\n'
                  '\n'
                  '-h                                               this help\n'
                  '\n'
                  '--include-stub                                   to include stub ASs from original topology\n'
                  '--config-file="minisecbgp.ini"                   pyramid config fileaname [.ini]\n'
                  '--scenario-name="Test topology"                  the name that will be used to identify this scenario\n'
                  '--scenario-description="date 20200729"           the scenario description\n'
                  '--topology=3                                     the topology ID that bases this scenario\n'
                  '\n'
                  'choose one option:\n'
                  '     --attacker-all                              use all ASs as the attacker\n'
                  '     --attacker-region="north"                   use all ASs from specific region(s) as the attacker>\n'
                  '     --attacker-autonomous-system=[65001,65002]  explicitly define which AS(s) will be the attacker\n'
                  '\n'
                  'choose one option:\n'
                  '     --target-all                                use all ASs as the target\n'
                  '     --target-region="south"                     use all ASs from specific region(s) as the target>\n'
                  '     --target-autonomous-system=[65001]          explicitly define which AS(s) will be the target\n'
                  '\n'
                  'choose one option:\n'
                  '     --prefix-target                             use the target prefix\n'
                  '     --prefix-all                                use all prefixes of all topology ASs\n'
                  '     --prefix-region="south"                     use all prefixes of all routers in the region(s)\n'
                  '     --prefix-autonomous-system=[65001,65002]    use the prefix of a specific AS\n'
                  '     --prefix-address=                           choose the prefix to hijack\n'
                  '\n'
                  'choose one option:\n'
                  '     --all-paths                                 use all possible paths from attacker\'s AS to target\'s AS\n'
                  '     --number-of-shortest-paths=3                define the max number of shortest paths to use between the attacker and target\n')
            sys.exit()
        elif opt == '--include-stub':
            include_stub = True
        elif opt == '--attacker-all':
            attacker_all = True
        elif opt == '--target-all':
            target_all = True
        elif opt == '--prefix-target':
            prefix_target = True
        elif opt == '--prefix-all':
            prefix_all = True
        elif opt == '--all-paths':
            all_paths = True
        elif opt == '--config-file':
            config_file = arg
        elif opt == '--scenario-name':
            scenario_name = arg
        elif opt == '--scenario-description':
            scenario_description = arg
        elif opt == '--topology':
            topology = arg
        elif opt == '--attacker-region':
            attacker_region = arg
        elif opt == '--attacker-autonomous-system':
            attacker_autonomous_system = arg
        elif opt == '--target-region':
            target_region = arg
        elif opt == '--target-autonomous-system':
            target_autonomous_system = arg
        elif opt == '--prefix-region':
            prefix_region = arg
        elif opt == '--prefix-autonomous-system':
            prefix_autonomous_system = arg
        elif opt == '--prefix-address':
            prefix_address = arg
        elif opt == '--number-of-shortest-paths':
            number_of_shortest_paths = arg

    args = parse_args(config_file)
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)
    try:
        with env['request'].tm:
            dbsession = env['request'].dbsession
            aa = AffectedArea(dbsession, include_stub, attacker_all, target_all, prefix_target, prefix_all, all_paths,
                              scenario_name, scenario_description, topology, attacker_region,
                              attacker_autonomous_system, target_region, target_autonomous_system, prefix_region,
                              prefix_autonomous_system, prefix_address, number_of_shortest_paths)
    except OperationalError:
        print('Database error')
