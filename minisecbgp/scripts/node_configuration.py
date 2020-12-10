import argparse
import getopt
import ipaddress
import os
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from minisecbgp import models
from minisecbgp.scripts.services import ssh, local_command


def node_configuration_status(dbsession, node):
    configurations = dbsession.query(models.Node, models.NodeConfiguration). \
        filter(models.Node.node == node). \
        filter(models.Node.id == models.NodeConfiguration.id_node).all()
    for configuration in configurations:
        if configuration.NodeConfiguration.status == 1:
            return False

    return True


class ConfigClusterNode(object):
    def __init__(self, dbsession, node_ip_address, username, password):
        self.dbsession = dbsession
        self.node_ip_address = str(ipaddress.ip_address(node_ip_address))
        self.username = username
        self.password = password

    def validate_hostname(self):
        print('\nValidating unique hostname ...')
        try:
            node_configuration = self.dbsession.query(models.Node, models.NodeConfiguration, models.Configuration). \
                filter(models.Node.node == self.node_ip_address). \
                filter(models.Node.id == models.NodeConfiguration.id_node). \
                filter(models.NodeConfiguration.id_configuration == models.Configuration.id). \
                filter(models.Configuration.configuration == 'hostname').first()

            if node_configuration_status(self.dbsession, self.node_ip_address):
                nodes = self.dbsession.query(models.Node).all()
                command = 'hostname'
                service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                    ssh.ssh(self.node_ip_address, self.username, self.password, command)
                if service_ssh == 1:
                    node_configuration.NodeConfiguration.status = 1
                    node_configuration.NodeConfiguration.log = service_ssh_status[:250]
                    self.dbsession.flush()
                    return
                else:
                    if command_status != 0:
                        node_configuration.NodeConfiguration.status = 1
                        node_configuration.NodeConfiguration.log = service_ssh_status[:250]
                        self.dbsession.flush()
                        return
                    for node in nodes:
                        if node.hostname == command_output and node.id != node_configuration.Node.id:
                            node_configuration.NodeConfiguration.status = 1
                            node_configuration.NodeConfiguration.log = \
                                'Hostname already configured on another cluster node: %s' % node.node
                            self.dbsession.flush()
                            return
                node_configuration.NodeConfiguration.status = 0
                node_configuration.NodeConfiguration.log = ''
                node_configuration.Node.hostname = command_output
            else:
                node_configuration.NodeConfiguration.status = 1
                node_configuration.NodeConfiguration.log = 'Aborted'

            self.dbsession.flush()
        except Exception as error:
            self.dbsession.rollback()
            print('Database error for hostname validation on node: %s - %s' % (self.node_ip_address, error))

    def create_minisecbgpuser(self):
        print('\nCreating user "minisecbgpuser" ...')
        try:
            node_configuration = self.dbsession.query(models.Node, models.NodeConfiguration, models.Configuration). \
                filter(models.Node.node == self.node_ip_address). \
                filter(models.Node.id == models.NodeConfiguration.id_node). \
                filter(models.NodeConfiguration.id_configuration == models.Configuration.id). \
                filter(models.Configuration.configuration == 'user').first()

            if node_configuration_status(self.dbsession, self.node_ip_address):
                commands = ['echo %s | sudo -S apt install whois -y' % self.password,
                            'echo %s | sudo -S killall -9 -u minisecbgpuser 2>/dev/null || exit 0' % self.password,
                            'echo %s | sudo -S userdel -r minisecbgpuser 2>/dev/null || exit 0' % self.password,
                            'echo %s | sudo -S useradd -m -p $(mkpasswd -m sha-512 -S saltsalt -s <<< %s) -s /bin/bash minisecbgpuser' % (
                                self.password, self.password),
                            'echo %s | sudo -S bash -c "sed --i \'/minisecbgpuser/d\' /etc/sudoers | sudo -S tee --append /etc/sudoers"' % self.password,
                            'echo %s | sudo -S bash -c "echo \'minisecbgpuser   ALL=NOPASSWD: ALL\' | sudo -S tee --append /etc/sudoers"' % self.password,
                            'echo %s | sudo -S bash -c "echo \'%s           ALL=(minisecbgpuser) NOPASSWD: ALL\' | sudo -S tee --append /etc/sudoers"' % (
                                self.password, self.username)]
                for command in commands:
                    service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                        ssh.ssh(self.node_ip_address, self.username, self.password, command)
                    if service_ssh == 1:
                        node_configuration.NodeConfiguration.status = 1
                        node_configuration.NodeConfiguration.log = service_ssh_status[:250]
                        self.dbsession.flush()
                        return
                    else:
                        if command_status != 0:
                            node_configuration.NodeConfiguration.status = 1
                            node_configuration.NodeConfiguration.log = service_ssh_status[:250]
                            self.dbsession.flush()
                            return
                node_configuration.NodeConfiguration.status = 0
                node_configuration.NodeConfiguration.log = ''

            else:

                node_configuration.NodeConfiguration.status = 1
                node_configuration.NodeConfiguration.log = 'Aborted'

            self.dbsession.flush()
        except Exception as error:
            self.dbsession.rollback()
            print('Database error for "minisecbgpuser" creation on node: %s - %s' % (self.node_ip_address, error))

    def configure_ssh(self):
        print('\nConfiguring ssh ...')
        try:
            node_configuration = self.dbsession.query(models.Node, models.NodeConfiguration, models.Configuration). \
                filter(models.Node.node == self.node_ip_address). \
                filter(models.Node.id == models.NodeConfiguration.id_node). \
                filter(models.NodeConfiguration.id_configuration == models.Configuration.id). \
                filter(models.Configuration.configuration == 'ssh').first()

            if node_configuration_status(self.dbsession, self.node_ip_address):

                node_configuration.NodeConfiguration.status = 0
                node_configuration.NodeConfiguration.log = ''

                commands = ['ssh-keygen -t rsa -N "" -f /home/minisecbgpuser/.ssh/id_rsa',
                            'echo "Host *\nStrictHostKeyChecking no" | tee --append /home/minisecbgpuser/.ssh/config',
                            'chmod 400 /home/minisecbgpuser/.ssh/config']
                for command in commands:
                    service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                        ssh.ssh(self.node_ip_address, 'minisecbgpuser', self.password, command)
                    if service_ssh == 1:
                        node_configuration.NodeConfiguration.status = 1
                        node_configuration.NodeConfiguration.log = service_ssh_status[:250]
                        self.dbsession.flush()
                        return
                    else:
                        if command_status != 0:
                            node_configuration.NodeConfiguration.status = 1
                            node_configuration.NodeConfiguration.log = service_ssh_status[:62]

                # update authorized_keys file on Workers to allow "minisecbgpuser" ssh remote connections without password
                command = 'sudo -u minisecbgpuser sshpass -p "%s" scp -o StrictHostKeyChecking=no ' \
                          'minisecbgpuser@%s:/home/minisecbgpuser/.ssh/id_rsa.pub ' \
                          '/home/minisecbgpuser/.ssh/authorized_keys.tmp' % (self.password, self.node_ip_address)
                result = local_command.local_command(command)
                if result[0] == 1:
                    node_configuration.NodeConfiguration.status = result[0]
                    node_configuration.NodeConfiguration.log = node_configuration.NodeConfiguration.log + str(
                        result[2].decode()[:62])

                command = 'sudo -u minisecbgpuser cat /home/minisecbgpuser/.ssh/authorized_keys.tmp |' \
                          'sudo -u minisecbgpuser tee --append /home/minisecbgpuser/.ssh/authorized_keys'
                result = local_command.local_command(command)
                if result[0] == 1:
                    node_configuration.NodeConfiguration.status = result[0]
                    node_configuration.NodeConfiguration.log = node_configuration.NodeConfiguration.log + str(
                        result[2].decode()[:62])

                command = 'sudo -u minisecbgpuser sshpass -p "%s" scp -o StrictHostKeyChecking=no ' \
                          '/home/minisecbgpuser/.ssh/authorized_keys minisecbgpuser@%s:/home/minisecbgpuser/.ssh/' \
                          % (self.password, self.node_ip_address)
                result = local_command.local_command(command)
                if result[0] == 1:
                    node_configuration.NodeConfiguration.status = result[0]
                    node_configuration.NodeConfiguration.log = node_configuration.NodeConfiguration.log + str(
                        result[2].decode()[:62])

            else:

                node_configuration.NodeConfiguration.status = 1
                node_configuration.NodeConfiguration.log = 'Aborted'

            self.dbsession.flush()
        except Exception as error:
            self.dbsession.rollback()
            print('Database error for ssh configuration on node: %s - %s' % (self.node_ip_address, error))

    def configure_crontab(self):
        print('\nConfiguring crontab ...')
        try:
            node_configuration = self.dbsession.query(models.Node, models.NodeConfiguration, models.Configuration). \
                filter(models.Node.node == self.node_ip_address). \
                filter(models.Node.id == models.NodeConfiguration.id_node). \
                filter(models.NodeConfiguration.id_configuration == models.Configuration.id). \
                filter(models.Configuration.configuration == 'crontab').first()

            if node_configuration_status(self.dbsession, self.node_ip_address):
                home_dir = os.getcwd()
                command = 'sudo -u minisecbgpuser bash -c \'echo -e "# Start job every 1 minute (monitor %s)\n' \
                          '* * * * * minisecbgpuser %s/venv/bin/MiniSecBGP_node_service ' \
                          '--config-file=%s/minisecbgp.ini ' \
                          '--execution-type=scheduled ' \
                          '--node-ip-address=%s" | ' \
                          'sudo tee /etc/cron.d/MiniSecBGP_node_service_%s\'' % \
                          (self.node_ip_address, home_dir, home_dir, self.node_ip_address, self.node_ip_address)
                result = local_command.local_command(command)
                if result[0] == 1:
                    node_configuration.NodeConfiguration.status = 1
                    node_configuration.NodeConfiguration.log = str(result[2].decode())
                    self.dbsession.flush()
                    return

                node_configuration.NodeConfiguration.status = 0
                node_configuration.NodeConfiguration.log = ''
            else:
                node_configuration.NodeConfiguration.status = 1
                node_configuration.NodeConfiguration.log = 'Aborted'

            self.dbsession.flush()
        except Exception as error:
            self.dbsession.rollback()
            print('Database error for crontab configuration on node: %s - %s' % (self.node_ip_address, error))


def parse_args(config_file):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(config_file.split())


def main(argv=sys.argv[1:]):
    try:
        opts, args = getopt.getopt(argv, "h", ["config-file=", "node-ip-address=", "username=", "password="])
    except getopt.GetoptError:
        print('\n'
              'Usage: MiniSecBGP_node_configuration [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
              '--node-ip-address=[192.168.0.1|3232239375]       cluster node IP address\n'
              '--username=ubuntu                                the username to use to configure the cluster node\n'
              '--password=ubuntu                                the user password to access the cluster node\n')
        sys.exit(2)
    config_file = node_ip_address = username = password = ''
    for opt, arg in opts:
        if opt == '-h':
            print('\n'
                  'Usage: MiniSecBGP_node_configuration [options]\n'
                  '\n'
                  'options (with examples):\n'
                  '\n'
                  '-h                                               this help\n'
                  '\n'
                  '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
                  '--node-ip-address=[192.168.0.1|3232239375]       cluster node IP address\n'
                  '--username=ubuntu                                the username to use to configure the cluster node\n'
                  '--password=ubuntu                                the user password to access the cluster node\n')
            sys.exit()
        elif opt == '--config-file':
            config_file = arg
        elif opt == '--node-ip-address':
            node_ip_address = arg
        elif opt == '--username':
            username = arg
        elif opt == '--password':
            password = arg
    if config_file and node_ip_address and username and password:
        args = parse_args(config_file)
        setup_logging(args.config_uri)
        env = bootstrap(args.config_uri)
        try:
            with env['request'].tm:
                dbsession = env['request'].dbsession
                ccn = ConfigClusterNode(dbsession, node_ip_address, username, password)
                ccn.validate_hostname()

            with env['request'].tm:
                dbsession = env['request'].dbsession
                ccn = ConfigClusterNode(dbsession, node_ip_address, username, password)
                ccn.create_minisecbgpuser()
                ccn.configure_ssh()
                ccn.configure_crontab()
        except OperationalError:
            print('Database error')
    else:
        print('\n'
              'Usage: MiniSecBGP_node_configuration [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
              '--node-ip-address=[192.168.0.1|3232239375]       cluster node IP address\n'
              '--username=ubuntu                                the username to use to configure the cluster node\n'
              '--password=ubuntu                                the user password to access the cluster node\n')
