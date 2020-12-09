import argparse
import getopt
import subprocess
import sys
from datetime import timedelta, date

import requests
import re
import urllib

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy import func
from sqlalchemy.exc import OperationalError

from minisecbgp import models


class DownloadTopology(object):
    def __init__(self, dbsession):
        self.dbsession = dbsession

    def download_topology(self):
        try:
            scheduledDownload = self.dbsession.query(models.RealisticTopologyScheduleDownload).first()
            if date.today() == scheduledDownload.date:
                scheduledDownload.date = scheduledDownload.date + timedelta(days=scheduledDownload.loop)
                downloadParameters = self.dbsession.query(models.RealisticTopologyDownloadParameter).first()
                site = requests.get(downloadParameters.url)
                databases = re.findall(r'\d{8}' + downloadParameters.file_search_string, site.text)
                databases = list(dict.fromkeys(databases))
                databases.sort(reverse=True)
                installed_databases = self.dbsession.query(models.Topology, models.TopologyType).\
                    filter(models.Topology.id_topology_type == models.TopologyType.id). \
                    filter(func.lower(models.TopologyType.topology_type) == 'caida as-relationship').all()
                for installed_database in installed_databases:
                    if databases[0] == installed_database.Topology.topology:
                        print('Topology already installed')
                        return
                urllib.request.urlretrieve(downloadParameters.url + databases[0] + '.txt.bz2',
                                           '/tmp/' + databases[0] + '.txt.bz2')
                arguments = ['--config-file=minisecbgp.ini',
                             '--file=%s.txt.bz2' % databases[0]]
                subprocess.Popen(['./venv/bin/MiniSecBGP_realistic_topology'] + arguments)

        except Exception as error:
            print(error)


def parse_args(config_file):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(config_file.split())


def main(argv=sys.argv[1:]):
    try:
        opts, args = getopt.getopt(argv, 'h', ["config-file="])
    except getopt.GetoptError:
        print('\n'
              'Usage: MiniSecBGP_realistic_topology_scheduled_download [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n')
        sys.exit(2)
    config_file = ''
    for opt, arg in opts:
        if opt == '-h':
            print('\n'
                  'Usage: MiniSecBGP_realistic_topology_scheduled_download [options]\n'
                  '\n'
                  'options (with examples):\n'
                  '\n'
                  '-h                                               this help\n'
                  '\n'
                  '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n')
            sys.exit()
        elif opt == '--config-file':
            config_file = arg
    if config_file:
        args = parse_args(config_file)
        setup_logging(args.config_uri)
        env = bootstrap(args.config_uri)
        try:
            with env['request'].tm:
                dbsession = env['request'].dbsession
                dt = DownloadTopology(dbsession)
                dt.download_topology()
        except OperationalError:
            print('Database error')
    else:
        print('\n'
              'Usage: MiniSecBGP_realistic_topology_scheduled_download [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n')