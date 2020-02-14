import argparse
import getopt
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from minisecbgp import models
from minisecbgp.scripts.services import ssh, local_command


class ConfigClusterNode(object):
    def __init__(self, dbsession, hostname, username, password):
        self.dbsession = dbsession
        self.hostname = hostname
        self.username = username
        self.password = password

        node = self.dbsession.query(models.Node).filter(models.Node.node == self.hostname).first()
        self.node = node
        nodes = self.dbsession.query(models.Node).all()
        self.nodes = nodes

    def validate_hostname(self):
        try:
            hostname = 0
            command = 'hostname'
            service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                ssh.ssh(self.hostname, self.username, self.password, command)
            hostname_status = command_output
            if service_ssh == 1:
                self.node.status = self.node.status = self.node.hostname = service_ssh
                self.node.hostname_status = service_ssh_status[:240]
                return
            else:
                if command_status != 0:
                    self.node.status = self.node.status = self.node.hostname = 1
                    self.node.hostname_status = command_error_warning[:240]
                    return
                for server in self.nodes:
                    if server.hostname_status == command_output and server.id != self.node.id:
                        self.node.status = self.node.status = self.node.hostname = 1
                        self.node.hostname_status = 'Hostname already configured on another cluster node: %s' % server.node
                        return
            self.node.hostname = hostname
            self.node.hostname_status = hostname_status
            return
        except Exception as error:
            print('Database error for hostname validation on node: %s - %s' % (self.node.node, error))

    def create_minisecbgpuser(self):
        try:
            if self.node.status != 1:
                conf_user = 0
                conf_user_status = ''
                commands = ['echo %s | sudo -S apt install whois -y' % self.password,
                            'echo %s | sudo -S userdel -r minisecbgpuser 2>/dev/null || exit 0' % self.password,
                            'echo %s | sudo -S useradd -m -p $(mkpasswd -m sha-512 -S saltsalt -s <<< %s) -s /bin/bash minisecbgpuser' % (
                                self.password, self.password),
                            'echo %s | sudo -S bash -c "echo \'minisecbgpuser   ALL=NOPASSWD: ALL\' | sudo -S tee --append /etc/sudoers"' % self.password,
                            'echo %s | sudo -S bash -c "echo \'%s           ALL=(minisecbgpuser) NOPASSWD: ALL\' | sudo -S tee --append /etc/sudoers"' % (
                                self.password, self.username)]
                for command in commands:
                    service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                        ssh.ssh(self.hostname, self.username, self.password, command)
                    if service_ssh == 1:
                        self.node.status = self.node.conf_user = service_ssh
                        self.node.conf_user_status = service_ssh_status[:240]
                        return
                    else:
                        if command_status != 0:
                            conf_user = 1
                            conf_user_status = conf_user_status + command_error_warning[:45]
                self.node.status = self.node.conf_user = conf_user
                self.node.conf_user_status = conf_user_status[:240]
                return
            else:
                self.node.conf_user = \
                    self.node.conf_ssh = \
                    self.node.install_remote_prerequisites = \
                    self.node.install_mininet = \
                    self.node.install_metis = \
                    self.node.install_maxinet = \
                    self.node.install_containernet = \
                    self.node.service_app = 1
                self.node.conf_user_status = \
                    self.node.conf_ssh_status = \
                    self.node.install_remote_prerequisites_status = \
                    self.node.install_mininet_status = \
                    self.node.install_metis_status = \
                    self.node.install_maxinet_status = \
                    self.node.install_containernet_status = \
                    self.node.service_app_status = 'Aborted'
                return
        except Exception as error:
            print('Database error for "minisecbgpuser" creation on node: %s - %s' % (self.node.node, error))

    def configure_ssh(self):
        try:
            if self.node.status == 0:
                conf_ssh = 0
                conf_ssh_status = ''
                commands = ['ssh-keygen -t rsa -N "" -f /home/minisecbgpuser/.ssh/id_rsa',
                            'echo "Host *\nStrictHostKeyChecking no" | tee --append /home/minisecbgpuser/.ssh/config',
                            'chmod 400 /home/minisecbgpuser/.ssh/config']
                for command in commands:
                    service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                        ssh.ssh(self.hostname, 'minisecbgpuser', self.password, command)
                    if service_ssh == 1:
                        self.node.status = self.node.conf_ssh = service_ssh
                        self.node.conf_ssh_status = service_ssh_status[:240]
                        return
                    else:
                        if command_status != 0:
                            conf_ssh = 1
                            conf_ssh_status = conf_ssh_status + command_error_warning[:45]

                # update authorized_keys file on Workers to allow "minisecbgpuser" ssh remote connections without password
                command = 'sudo -u minisecbgpuser sshpass -p "%s" scp -o StrictHostKeyChecking=no ' \
                          'minisecbgpuser@%s:/home/minisecbgpuser/.ssh/id_rsa.pub ' \
                          '/home/minisecbgpuser/.ssh/authorized_keys.tmp' % (self.password, self.hostname)
                result = local_command.local_command(command)
                if result[0] == 1:
                    conf_ssh = result[0]
                    conf_ssh_status = conf_ssh_status + str(result[2].decode()[:40])

                command = 'sudo -u minisecbgpuser cat /home/minisecbgpuser/.ssh/authorized_keys.tmp |' \
                          'sudo -u minisecbgpuser tee --append /home/minisecbgpuser/.ssh/authorized_keys'
                result = local_command.local_command(command)
                if result[0] == 1:
                    conf_ssh = result[0]
                    conf_ssh_status = conf_ssh_status + str(result[2].decode()[:40])

                command = 'sudo -u minisecbgpuser sshpass -p "%s" scp -o StrictHostKeyChecking=no ' \
                          '/home/minisecbgpuser/.ssh/authorized_keys minisecbgpuser@%s:/home/minisecbgpuser/.ssh/' \
                          % (self.password, self.hostname)
                result = local_command.local_command(command)
                if result[0] == 1:
                    conf_ssh = result[0]
                    conf_ssh_status = conf_ssh_status + str(result[2].decode()[:40])

                self.node.status = self.node.conf_ssh = conf_ssh
                self.node.conf_ssh_status = conf_ssh_status[:240]
                return
            else:
                self.node.conf_ssh = \
                    self.node.install_remote_prerequisites = \
                    self.node.install_mininet = \
                    self.node.install_metis = \
                    self.node.install_maxinet = \
                    self.node.install_containernet = \
                    self.node.service_app = 1
                self.node.conf_ssh_status = \
                    self.node.install_remote_prerequisites_status = \
                    self.node.install_mininet_status = \
                    self.node.install_metis_status = \
                    self.node.install_maxinet_status = \
                    self.node.install_containernet_status = \
                    self.node.service_app_status = 'Aborted'
                return
        except Exception as error:
            print('Database error for ssh configuration on node: %s - %s' % (self.node.node, error))

    def install_remote_prerequisites(self):
        try:
            if self.node.status == 0:
                install_remote_prerequisites = 0
                install_remote_prerequisites_status = ''
                if self.node.master == 1:
                    command = 'pip3 install --upgrade --force-reinstall -U ryu'
                    service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                        ssh.ssh(self.hostname, 'minisecbgpuser', self.password, command)
                    if service_ssh == 1:
                        self.node.status = self.node.install_remote_prerequisites = service_ssh
                        self.node.install_remote_prerequisites_status = service_ssh_status[:240]
                        return
                    else:
                        if command_status != 0:
                            install_remote_prerequisites = 1
                            install_remote_prerequisites_status = install_remote_prerequisites_status + command_error_warning[45]

                commands = ['sudo apt install python3-pip cmake -y',
                            'pip3 install --upgrade --force-reinstall -U Pyro4 docker']
                for command in commands:
                    service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                        ssh.ssh(self.hostname, 'minisecbgpuser', self.password, command)
                    if service_ssh == 1:
                        self.node.status = self.node.install_remote_prerequisites = service_ssh
                        self.node.install_remote_prerequisites_status = service_ssh_status[:240]
                        return
                    else:
                        if command_status != 0:
                            install_remote_prerequisites = 1
                            install_remote_prerequisites_status = install_remote_prerequisites_status + command_error_warning[:45]
                self.node.status = self.node.install_remote_prerequisites = install_remote_prerequisites
                self.node.install_remote_prerequisites_status = install_remote_prerequisites_status[:240]
                return
            else:
                self.node.install_remote_prerequisites = \
                    self.node.install_mininet = \
                    self.node.install_metis = \
                    self.node.install_maxinet = \
                    self.node.install_containernet = \
                    self.node.service_app = 1
                self.node.install_remote_prerequisites_status = \
                    self.node.install_mininet_status = \
                    self.node.install_metis_status = \
                    self.node.install_maxinet_status = \
                    self.node.install_containernet_status = \
                    self.node.service_app_status = 'Aborted'
                return
        except Exception as error:
            print('Database error for remote prerequisites installation on node: %s - %s' % (self.node.node, error))

    def install_mininet(self):
        try:
            if self.node.status == 0:
                install_mininet = 0
                install_mininet_status = ''
                commands = ['git clone git://github.com/mininet/mininet /home/minisecbgpuser/mininet',
                            'cd /home/minisecbgpuser/mininet; '
                            'git checkout -b 2.3.0d4 2.3.0d4; '
                            'sudo /home/minisecbgpuser/mininet/util/install.sh -nfv']
                for command in commands:
                    service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                        ssh.ssh(self.hostname, 'minisecbgpuser', self.password, command)
                    if service_ssh == 1:
                        self.node.status = self.node.install_mininet = service_ssh
                        self.node.install_mininet_status = service_ssh_status[:240]
                        return
                    else:
                        if command_status != 0:
                            install_mininet = 1
                            install_mininet_status = install_mininet_status + command_error_warning[:60]
                self.node.status = self.node.install_mininet = install_mininet
                self.node.install_mininet_status = install_mininet_status[:240]
                return
            else:
                self.node.install_mininet = \
                    self.node.install_metis = \
                    self.node.install_maxinet = \
                    self.node.install_containernet = \
                    self.node.service_app = 1
                self.node.install_mininet_status = \
                    self.node.install_metis_status = \
                    self.node.install_maxinet_status = \
                    self.node.install_containernet_status = \
                    self.node.service_app_status = 'Aborted'
                return
        except Exception as error:
            print('Database error for Mininet installation on node: %s - %s' % (self.node.node, error))

    def install_metis(self):
        try:
            if self.node.status == 0:
                if self.node.master == 1:                   # install Metis only on master node
                    try:
                        install_metis = 0
                        install_metis_status = ''
                        command = 'sshpass -p "%s" scp -o StrictHostKeyChecking=no ./metis/metis-5.1.0.tar.gz ' \
                                  'minisecbgpuser@%s:/home/minisecbgpuser/' % (self.password, self.hostname)
                        result = local_command.local_command(command)
                        if result[0] == 1:
                            install_metis = result[0]
                            install_metis_status = str(result[2].decode()[:80])

                        commands = ['tar -xvzf /home/minisecbgpuser/metis-5.1.0.tar.gz -C /home/minisecbgpuser',
                                    'cd /home/minisecbgpuser/metis-5.1.0;'
                                    'sudo make config shared=1;'
                                    'sudo make;'
                                    'sudo make install;'
                                    'sudo ldconfig']
                        for command in commands:
                            service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                                ssh.ssh(self.hostname, 'minisecbgpuser', self.password, command)
                        if service_ssh == 1:
                            self.node.status = self.node.install_metis = service_ssh
                            self.node.install_metis_status = install_metis_status + service_ssh_status[:240]
                            return
                        else:
                            if command_status != 0:
                                install_metis = 1
                                install_metis_status = install_metis_status + command_error_warning[:80]
                        self.node.status = self.node.install_metis = install_metis
                        self.node.install_metis_status = install_metis_status[:240]
                        return
                    except Exception as error:
                        print('Database error for Metis installation on node: %s - %s' % (self.node.node, error))
                else:
                    try:
                        self.node.status = self.node.install_metis = 0
                        self.node.install_metis_status = 'Metis installation is not necessary on Workers'
                        return
                    except Exception as error:
                        print('Database error for Metis installation on node: %s - %s' % (self.node.node, error))
            else:
                self.node.install_metis = \
                    self.node.install_maxinet = \
                    self.node.install_containernet = \
                    self.node.service_app = 1
                self.node.install_metis_status = \
                    self.node.install_maxinet_status = \
                    self.node.install_containernet_status = \
                    self.node.service_app_status = 'Aborted'
                return
        except Exception as error:
            print('Database error for Metis installation on node: %s - %s' % (self.node.node, error))

    def install_maxinet(self):
        try:
            if self.node.status == 0:
                master = self.dbsession.query(models.Node).filter(models.Node.master == 1).first()
                install_maxinet = 0
                install_maxinet_status = ''
                commands = ['git clone git://github.com/MaxiNet/MaxiNet.git',
                            'cd /home/minisecbgpuser/MaxiNet;'
                            'git checkout v1.2;'
                            'sudo make install']
                for command in commands:
                    service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                        ssh.ssh(self.hostname, 'minisecbgpuser', self.password, command)
                    if service_ssh == 1:
                        self.node.status = self.node.install_maxinet = service_ssh
                        self.node.install_maxinet_status = service_ssh_status[:240]
                        return
                    else:
                        if command_status != 0:
                            install_maxinet = 1
                            install_maxinet_status = command_error_warning[:60]

                # configure MaxiNet.cfg on Master
                command = 'sudo -u minisecbgpuser bash -c \'' \
                          'echo "[all]\n' \
                          'password = MiniSecBGP\n' \
                          'controller = %s:6633\n' \
                          'logLevel = ERROR\n' \
                          'port_ns = 9090\n' \
                          'port_sshd = 5345\n' \
                          'runWith1500MTU = False\n' \
                          'useMultipleIPs = 0\n' \
                          'deactivateTSO = True\n' \
                          'sshuser = minisecbgpuser\n' \
                          'usesudo = True\n' \
                          'useSTT = False\n\n' \
                          '[FrontendServer]\n' \
                          'ip = %s\n' \
                          'threadpool = 256\n" | sudo tee /etc/MaxiNet.cfg\'' % \
                          (master.hostname, master.hostname)
                result = local_command.local_command(command)
                if result[0] == 1:
                    install_maxinet = result[0]
                    install_maxinet_status = install_maxinet_status + str(result[2].decode()[:240])

                for server in self.nodes:
                    command = 'sudo -u minisecbgpuser bash -c \'' \
                              'echo "[%s]\n' \
                              'ip = %s\n' \
                              'share = 1\n" | sudo tee --append /etc/MaxiNet.cfg\'' % \
                              (server.hostname, server.hostname)
                    result = local_command.local_command(command)
                    if result[0] == 1:
                        install_maxinet = result[0]
                        install_maxinet_status = install_maxinet_status + str(result[2].decode()[:10])

                # send MaxiNet.cfg to all Workers
                for server in self.nodes:
                    if server.master != 1:
                        command = 'sudo -u minisecbgpuser bash -c \'' \
                                  'scp -o StrictHostKeyChecking=no /etc/MaxiNet.cfg minisecbgpuser@%s:/home/minisecbgpuser;' \
                                  'ssh %s "sudo mv /home/minisecbgpuser/MaxiNet.cfg /etc/MaxiNet.cfg; exit" \'' \
                                  % (server.node, server.node)
                        result = local_command.local_command(command)
                        if result[0] == 1:
                            install_maxinet = result[0]
                            install_maxinet_status = install_maxinet_status + str(result[2].decode()[:10])

                self.node.status = self.node.install_maxinet = install_maxinet
                self.node.install_maxinet_status = install_maxinet_status[:240]
                return
            else:
                self.node.install_maxinet = \
                    self.node.install_containernet = \
                    self.node.service_app = 1
                self.node.install_maxinet_status = \
                    self.node.install_containernet_status = \
                    self.node.service_app_status = 'Aborted'
                return
        except Exception as error:
            print('Database error for "minisecbgpuser" creation on node: %s - %s' % (self.node.node, error))

    def install_containernet(self):
        try:
            if self.node.status == 0:
                if self.node.master == 1:                   # install Containernet only on master node
                    try:
                        install_containernet = 0
                        install_containernet_status = ''
                        commands = ['git clone git://github.com/containernet/containernet /home/minisecbgpuser/containernet',
                                    'cd /home/minisecbgpuser/containernet/ansible; '
                                    'sudo ansible-playbook -i "localhost," -c local install.yml; '
                                    'cd ..; '
                                    'sudo python setup.py install']
                        for command in commands:
                            service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                                ssh.ssh(self.hostname, 'minisecbgpuser', self.password, command)
                            if service_ssh == 1:
                                self.node.status = self.node.install_containernet = service_ssh
                                self.node.install_containernet_status = service_ssh_status[:240]
                                return
                            else:
                                if command_status != 0:
                                    install_containernet = 1
                                    install_containernet_status = install_containernet_status + command_error_warning[:60]
                        self.node.service_app = self.node.status = self.node.install_containernet = install_containernet
                        self.node.service_app_status = self.node.install_containernet_status = install_containernet_status[:240]
                        return
                    except Exception as error:
                        print('Database error for Containernet installation on node: %s - %s' % (self.node.node, error))
                else:
                    try:
                        self.node.service_app = self.node.status = self.node.install_containernet = 0
                        self.node.install_containernet_status = 'Containernet installation is not necessary on Workers'
                        return
                    except Exception as error:
                        print('Database error for Containernet installation on node: %s - %s' % (self.node.node, error))
            else:
                self.node.install_containernet = \
                    self.node.service_app = 1
                self.node.install_containernet_status = \
                    self.node.service_app_status = 'Aborted'
                return
        except Exception as error:
            print('Database error for Containernet installation on node: %s - %s' % (self.node.node, error))


def parse_args(config_file):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(config_file.split())


def main(argv=sys.argv[1:]):
    try:
        opts, args = getopt.getopt(argv, "h:", ["config_file=", "hostname=", "username=", "password="])
    except getopt.GetoptError as error:
        print('config.py '
              '--config_file=<pyramid config file .ini> '
              '--hostname=<cluster node name or IP address> '
              '--username=<cluster node username> '
              '--password=<cluster node user password>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('config.py '
                  '--config_file=<pyramid config file .ini> '
                  '--hostname=<cluster node name or IP address> '
                  '--username=<cluster node username> '
                  '--password=<cluster node user password>')
            sys.exit()
        elif opt == '--config_file':
            config_file = arg
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
            ccn = ConfigClusterNode(dbsession, hostname, username, password)
            ccn.validate_hostname()

        with env['request'].tm:
            dbsession = env['request'].dbsession
            ccn = ConfigClusterNode(dbsession, hostname, username, password)
            ccn.create_minisecbgpuser()
            ccn.configure_ssh()
            ccn.install_remote_prerequisites()
            ccn.install_mininet()
            ccn.install_metis()
            ccn.install_maxinet()
            ccn.install_containernet()
    except OperationalError:
        print('Database error')
