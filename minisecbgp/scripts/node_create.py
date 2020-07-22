import argparse
import getopt
import ipaddress
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError, IntegrityError

from minisecbgp import models


class CreateClusterNode(object):
    def __init__(self, dbsession, node_ip_address, master):
        self.dbsession = dbsession
        self.node_ip_address = int(ipaddress.ip_address(node_ip_address))
        self.master = master

    def create_cluster_node(self):
        print('Creating cluster node ...')
        try:
            services = self.dbsession.query(models.Service).all()
            configurations = self.dbsession.query(models.Configuration).all()
            installs = self.dbsession.query(models.Install).all()

            node = models.Node(node=self.node_ip_address,
                               master=self.master)
            self.dbsession.add(node)
            self.dbsession.flush()

            for service in services:
                self.dbsession.add(models.NodeService(id_node=node.id,
                                                      id_service=service.id,
                                                      status=2,
                                                      log="installing"))

            for configuration in configurations:
                self.dbsession.add(models.NodeConfiguration(id_node=node.id,
                                                            id_configuration=configuration.id,
                                                            status=2,
                                                            log="installing"))

            for install in installs:
                self.dbsession.add(models.NodeInstall(id_node=node.id,
                                                      id_install=install.id,
                                                      status=2,
                                                      log="installing"))

            self.dbsession.flush()
        except IntegrityError as error:
            self.dbsession.rollback()
            print('Node "%s" already exists in cluster.' % ipaddress.ip_address(self.node_ip_address))
        except Exception as error:
            self.dbsession.rollback()
            print('Database error for create node: %s - %s' % (ipaddress.ip_address(self.node_ip_address), error))


def parse_args(config_file):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(config_file.split())


def str2bool(master):
    if isinstance(master, bool):
        return master
    if master.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif master.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def main(argv=sys.argv[1:]):
    try:
        opts, args = getopt.getopt(argv, 'h:', ["config-file=", "node-ip-address=", "master="])
    except getopt.GetoptError:
        print('MiniSecBGP_create_node '
              '--config-file=<pyramid config file .ini> '
              '--node-ip-address=<cluster node IP address> '
              '--master=<True | False>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('MiniSecBGP_create_node '
                  '--config-file=<pyramid config file .ini> '
                  '--node-ip-address=<cluster node IP address> '
                  '--master=<True | False>')
            sys.exit()
        elif opt == '--config-file':
            config_file = arg
        elif opt == '--node-ip-address':
            node_ip_address = arg
        elif opt == '--master':
            master = str2bool(arg)

    args = parse_args(config_file)
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)
    try:
        with env['request'].tm:
            dbsession = env['request'].dbsession
            ccn = CreateClusterNode(dbsession, node_ip_address, master)
            ccn.create_cluster_node()
    except OperationalError:
        print('Database error')
