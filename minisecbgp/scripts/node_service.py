import argparse
import getopt
import ipaddress
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from minisecbgp import models
from minisecbgp.scripts.services import ssh, local_command


class TestClusterNode(object):
    def __init__(self, dbsession, execution_type, node_ip_address, username, password):
        self.dbsession = dbsession
        self.execution_type = execution_type
        self.node_ip_address = str(ipaddress.ip_address(node_ip_address))
        self.username = username
        self.password = password

    def test_ping(self):
        print('\nTesting ping ...')
        try:
            node_service = self.dbsession.query(models.Node, models.NodeService, models.Service).\
                filter(models.Node.node == self.node_ip_address).\
                filter(models.Node.id == models.NodeService.id_node).\
                filter(models.NodeService.id_service == models.Service.id).\
                filter(models.Service.service == 'ping').first()

            node_service.NodeService.status = 0
            node_service.NodeService.log = ''

            command = 'ping %s -c 1 -W 15' % node_service.Node.node
            result = local_command.local_command(command)
            if result[0] != 0:
                node_service.NodeService.status = 1
                node_service.NodeService.log = str(result[1].decode()[:250])

            self.dbsession.flush()
        except Exception as error:
            self.dbsession.rollback()
            print('Database error for ping test on node: %s - %s' % (self.node_ip_address, error))

    def test_ssh(self):
        print('\nTesting ssh ...')
        try:
            if self.execution_type == 'manual':
                username = self.username
            elif self.execution_type == 'scheduled':
                username = 'minisecbgpuser'

            node_service = self.dbsession.query(models.Node, models.NodeService, models.Service). \
                filter(models.Node.node == self.node_ip_address). \
                filter(models.Node.id == models.NodeService.id_node). \
                filter(models.NodeService.id_service == models.Service.id). \
                filter(models.Service.service == 'ssh').first()

            command = ''
            service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                ssh.ssh(node_service.Node.node, username, self.password, command)

            node_service.NodeService.status = service_ssh
            node_service.NodeService.log = service_ssh_status

            self.dbsession.flush()

        except Exception as error:
            self.dbsession.rollback()
            print('Database error for ssh test on node: %s - %s' % (self.node_ip_address, error))


def parse_args(config_file):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(config_file.split())


def main(argv=sys.argv[1:]):
    try:
        opts, args = getopt.getopt(argv, 'h', ["config-file=", "execution-type=",
                                               "node-ip-address=", "username=",
                                               "password="])
    except getopt.GetoptError:
        print('\n'
              'Usage: MiniSecBGP_node_service [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
              '--execution-type=[manual|scheduled]              manual = when user execute this function in CLI\n'
              '                                                 scheduled = when this function is executed by crontab\n'
              '--node-ip-address=[192.168.0.1|3232239375]       cluster node IP address\n'
              '--username=ubuntu                                the username to use to configure the cluster node\n'
              '--password=ubuntu                                the user password to access the cluster node\n')
        sys.exit(2)
    config_file = execution_type = node_ip_address = username = password = ''
    for opt, arg in opts:
        if opt == '-h':
            print('\n'
                  'Usage: MiniSecBGP_node_service [options]\n'
                  '\n'
                  'options (with examples):\n'
                  '\n'
                  '-h                                               this help\n'
                  '\n'
                  '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
                  '--execution-type=[manual|scheduled]              manual = when user execute this function in CLI\n'
                  '                                                 scheduled = when this function is executed by crontab\n'
                  '--node-ip-address=[192.168.0.1|3232239375]       cluster node IP address\n'
                  '--username=ubuntu                                the username to use to configure the cluster node\n'
                  '--password=ubuntu                                the user password to access the cluster node\n')
            sys.exit()
        elif opt == '--config-file':
            config_file = arg
        elif opt == '--execution-type' and (arg == 'manual' or arg == 'scheduled'):
            execution_type = arg
        elif opt == '--node-ip-address':
            node_ip_address = arg
        elif opt == '--username':
            username = arg
        elif opt == '--password':
            password = arg
    if config_file and execution_type and node_ip_address:
        args = parse_args(config_file)
        setup_logging(args.config_uri)
        env = bootstrap(args.config_uri)
        try:
            with env['request'].tm:
                dbsession = env['request'].dbsession
                ccn = TestClusterNode(dbsession, execution_type, node_ip_address, username, password)
                ccn.test_ping()
                ccn.test_ssh()
        except OperationalError:
            print('Database error')
    else:
        print('\n'
              'Usage: MiniSecBGP_node_service [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
              '--execution-type=[manual|scheduled]              manual = when user execute this function in CLI\n'
              '                                                 scheduled = when this function is executed by crontab\n'
              '--node-ip-address=[192.168.0.1|3232239375]       cluster node IP address\n'
              '--username=ubuntu                                the username to use to configure the cluster node\n'
              '--password=ubuntu                                the user password to access the cluster node\n')