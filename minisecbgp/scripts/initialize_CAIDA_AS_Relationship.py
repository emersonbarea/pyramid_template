import bz2
import argparse
import getopt
import os
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from minisecbgp import models


class CaidaAsRelationship(object):
    def __init__(self):
        pass

    @staticmethod
    def uncompress_file(path, zip_file):
        output_file = zip_file[:-4]
        file = bz2.open(path + zip_file, 'rt')
        data = file.read()
        file = open(path + output_file, 'w+')
        file.write(data)
        file.close()
        if zip_file != '20200201.as-rel2.txt.bz2':
            os.remove(path + zip_file)

    @staticmethod
    def save_data_to_bd(dbsession, path, file):
        print('Creating Realistic Topology from CAIDA AS-Relationship file ...\n'
              'Take a coffee and wait ...')
        topology = models.Topology(topology=file[:-4],
                                   type=0)
        with open(path + file, 'r') as topology_file:
            lines = topology_file.readlines()
        topology_file.close()
        os.remove(path + file)
        for line in lines:
            if not line.startswith('#'):
                realistic_topology = models.RealisticTopology(as1=line.split('|')[0],
                                                              as2=line.split('|')[1],
                                                              agreement=line.split('|')[2])
                topology.realistic_topology.append(realistic_topology)
        dbsession.add(topology)
        updating = dbsession.query(models.TempCaidaDatabases).one()
        updating.updating = 0
        dbsession.add(updating)


def parse_args(config_file):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(config_file.split())


def main(argv=sys.argv[1:]):
    try:
        opts, args = getopt.getopt(argv, 'h:', ["config_file=", "path=", "file=", "zip_file="])
    except getopt.GetoptError:
        print('config '
              '--config_file=<pyramid config file .ini> '
              '--path=<system path where compressed and decompressed files are> '
              '--file=<file name to save to database> '
              '--zip_file=<bz2 file name>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('config '
                  '--config_file=<pyramid config file .ini> '
                  '--path=<system path where compressed and decompressed files are> '
                  '--file=<file name to save to database> '
                  '--zip_file=<bz2 file name>')
            sys.exit()
        elif opt == '--config_file':
            config_file = arg
        elif opt == '--path':
            path = arg
        elif opt == '--file':
            file = arg
        elif opt == '--zip_file':
            zip_file = arg

    args = parse_args(config_file)
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)
    try:
        with env['request'].tm:
            dbsession = env['request'].dbsession
            car = CaidaAsRelationship()
            if 'zip_file' in locals():
                car.uncompress_file(path, zip_file)
            if 'file' in locals():
                car.save_data_to_bd(dbsession, path, file)
    except OperationalError:
        print('Database error')
