import argparse
import getopt
import subprocess
import sys
from datetime import timedelta, date

import requests
import re
import urllib

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from minisecbgp import models


class DownloadTopology(object):
    def __init__(self, dbsession):
        self.dbsession = dbsession

    def download_topology(self):
        try:
            scheduledDownload = self.dbsession.query(models.ScheduledDownload).first()
            if date.today() == scheduledDownload.date:
                scheduledDownload.date = scheduledDownload.date + timedelta(days=scheduledDownload.loop)
                parametersDownload = self.dbsession.query(models.ParametersDownload).first()
                site = requests.get(parametersDownload.url)
                databases = re.findall(r'\d{8}' + parametersDownload.string_file_search, site.text)
                databases = list(dict.fromkeys(databases))
                databases.sort(reverse=True)
                installed_databases = self.dbsession.query(models.Topology).filter_by(type=0).all()
                for database in installed_databases:
                    if databases[0] == database.topology:
                        print('Topology already installed')
                        return
                urllib.request.urlretrieve(parametersDownload.url + databases[0] + '.txt.bz2',
                                           './CAIDA_AS_Relationship/' + databases[0] + '.txt.bz2')
                arguments = ['--config_file=minisecbgp.ini',
                             '--path=./CAIDA_AS_Relationship/',
                             '--file=%s.txt' % databases[0],
                             '--zip_file=%s.txt.bz2' % databases[0]]
                subprocess.Popen(['./venv/bin/initialize_CAIDA_AS_Relationship'] + arguments)
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
        opts, args = getopt.getopt(argv, 'h:', ["config_file="])
    except getopt.GetoptError:
        print('realisticTopologyScheduledDownload '
              '--config_file=<pyramid config file .ini> ')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('realisticTopologyScheduledDownload '
                  '--config_file=<pyramid config file .ini> ')
            sys.exit()
        elif opt == '--config_file':
            config_file = arg

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
