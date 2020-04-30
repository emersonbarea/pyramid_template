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
    def __init__(self, dbsession, topology_path):
        self.dbsession = dbsession
        self.topology_path = topology_path

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
                installed_databases = self.dbsession.query(models.Topology).\
                    filter(models.Topology.id_topology_type == self.dbsession.query(models.TopologyType.id).
                           filter_by(topology_type='Realistic')).all()
                for database in installed_databases:
                    if databases[0] == database.topology:
                        print('Topology already installed')
                        return
                urllib.request.urlretrieve(downloadParameters.url + databases[0] + '.txt.bz2',
                                           '/tmp/' + databases[0] + '.txt.bz2')
                arguments = ['--config-file=%s/minisecbgp.ini' % self.topology_path,
                             '--file=%s.txt.bz2' % databases[0]]
                subprocess.Popen(['%s./venv/bin/realistic_topology' % self.topology_path] + arguments)

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
        opts, args = getopt.getopt(argv, 'h:', ["config-file=", "topology-path="])
    except getopt.GetoptError:
        print('realisticTopologyScheduledDownload '
              '--config-file=<pyramid config file .ini> '
              '--topology-path=<path for topology script file>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('realisticTopologyScheduledDownload '
                  '--config-file=<pyramid config file .ini> '
                  '--topology-path=<path for topology script file>')
            sys.exit()
        elif opt == '--config-file':
            config_file = arg
        elif opt == '--topology-path':
            topology_path = arg

    args = parse_args(config_file)
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)
    try:
        with env['request'].tm:
            dbsession = env['request'].dbsession
            dt = DownloadTopology(dbsession, topology_path)
            dt.download_topology()
    except OperationalError:
        print('Database error')
