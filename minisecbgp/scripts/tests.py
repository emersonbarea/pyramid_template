import argparse
import getopt
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from minisecbgp import models
from minisecbgp.scripts.services import ssh, local_command


class TestClusterNode(object):
    def __init__(self, dbsession, execution_type, hostname, username, password):
        self.dbsession = dbsession
        self.execution_type = execution_type
        self.hostname = hostname
        self.username = username
        self.password = password
        if self.username:
            nodes = [self.dbsession.query(models.Node).filter(models.Node.node == self.hostname).first()]
        else:
            nodes = self.dbsession.query(models.Node).all()
        self.nodes = nodes

    def test_ping(self):
        print('Testing ping ...')
        try:
            for server in self.nodes:
                service_ping = 0
                command = 'ping %s -c 1 -W 15' % server.node
                result = local_command.local_command(command)
                if result[0] != 0:
                    service_ping = 1
                server.service_ping = service_ping
                return
        except Exception as error:
            print('Database error for ping test on node: %s - %s' % (self.nodes.node, error))

    def test_ssh(self):
        print('Testing ssh ...')
        try:
            if self.execution_type == 'create_node':
                username = self.username
            elif self.execution_type == 'job_scheduled':
                username = 'minisecbgpuser'
            for server in self.nodes:
                command = ''
                service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                    ssh.ssh(server.node, username, self.password, command)
                server.service_ssh = service_ssh
                server.service_ssh_status = service_ssh_status
        except Exception as error:
            print('Database error for ssh test on node: %s - %s' % (self.nodes.node, error))


def parse_args(config_file):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(config_file.split())


def main(argv=sys.argv[1:]):
    try:
        opts, args = getopt.getopt(argv, 'h:', ["config_file=", "execution_type=", "hostname=", "username=", "password="])
    except getopt.GetoptError:
        print('config.py '
              '--config_file=<pyramid config file .ini> '
              '--execution_type=create_node|job_scheduled '
              '--hostname=<cluster node name or IP address> '
              '--username=<cluster node username> '
              '--password=<cluster node user password>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('config.py '
                  '--config_file=<pyramid config file .ini> '
                  '--execution_type=create_node|job_scheduled '
                  '--hostname=<cluster node name or IP address> '
                  '--username=<cluster node username> '
                  '--password=<cluster node user password>')
            sys.exit()
        elif opt == '--config_file':
            config_file = arg
        elif opt == '--execution_type' and (arg == 'create_node' or arg == 'job_scheduled'):
            execution_type = arg
        elif opt == '--hostname':
            hostname = arg
        elif opt == '--username':
            username = arg
        elif opt == '--password':
            password = arg

    args = parse_args(config_file)
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)
    try:
        with env['request'].tm:
            dbsession = env['request'].dbsession
            ccn = TestClusterNode(dbsession, execution_type, hostname, username, password)
            ccn.test_ping()
            ccn.test_ssh()
    except OperationalError:
        print('Database error')
