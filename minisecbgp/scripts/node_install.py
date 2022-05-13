import argparse
import getopt
import ipaddress
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from minisecbgp import models
from minisecbgp.scripts.services import ssh, local_command


def node_install_status(dbsession, node):
    configurations = dbsession.query(models.Node, models.NodeConfiguration). \
        filter(models.Node.node == node). \
        filter(models.Node.id == models.NodeConfiguration.id_node).all()
    for configuration in configurations:
        if configuration.NodeConfiguration.status == 1:
            return False

    installs = dbsession.query(models.Node, models.NodeInstall). \
        filter(models.Node.node == node). \
        filter(models.Node.id == models.NodeInstall.id_node).all()
    for install in installs:
        if install.NodeInstall.status == 1:
            return False

    return True


class ConfigClusterNode(object):
    def __init__(self, dbsession, node_ip_address, username, password):
        self.dbsession = dbsession
        self.node_ip_address = str(ipaddress.ip_address(node_ip_address))
        self.username = username
        self.password = password

    def install_linux_prerequisites(self):
        print('\nInstalling Linux prerequisites ...')
        try:
            node_install = self.dbsession.query(models.Node, models.NodeInstall, models.Install). \
                filter(models.Node.node == self.node_ip_address). \
                filter(models.Node.id == models.NodeInstall.id_node). \
                filter(models.NodeInstall.id_install == models.Install.id). \
                filter(models.Install.install == 'prerequisites').first()

            if node_install_status(self.dbsession, self.node_ip_address):

                commands = ['export DEBIAN_FRONTEND=noninteractive; '
                            'sudo -E apt update; '
                            'sudo -E apt upgrade -yq',
                            'sudo apt install git autoconf screen cmake build-essential sysstat expect '
                            'python-matplotlib uuid-runtime ansible aptitude python-pip python3-pip -y',
                            'pip install pathlib termcolor pexpect setuptools docker',
                            'pip3 install --upgrade --force-reinstall -U Pyro4 docker',
                            'sudo timedatectl set-timezone America/Sao_Paulo']
                for command in commands:
                    service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                        ssh.ssh(self.node_ip_address, 'minisecbgpuser', self.password, command)

                    if service_ssh == 1:
                        node_install.NodeInstall.status = service_ssh
                        node_install.NodeInstall.log = service_ssh_status[:250]
                        self.dbsession.flush()
                        return
                    else:
                        if command_status != 0:
                            node_install.NodeInstall.status = 1
                            node_install.NodeInstall.log = command_error_warning[:250]
                            self.dbsession.flush()
                            return

                node_install.NodeInstall.status = 0
                node_install.NodeInstall.log = ''

            else:

                node_install.NodeInstall.status = 1
                node_install.NodeInstall.log = 'Aborted'

            self.dbsession.flush()
        except Exception as error:
            self.dbsession.rollback()
            print('Database error for remote prerequisites installation on node: %s - %s' % (self.node_ip_address, error))

    def install_mininet(self):
        print('\nInstalling Mininet ...\n'
              'take a coffee and wait ...')
        try:
            node_install = self.dbsession.query(models.Node, models.NodeInstall, models.Install). \
                filter(models.Node.node == self.node_ip_address). \
                filter(models.Node.id == models.NodeInstall.id_node). \
                filter(models.NodeInstall.id_install == models.Install.id). \
                filter(models.Install.install == 'mininet').first()

            if node_install_status(self.dbsession, self.node_ip_address):

                commands = [
                    'git clone https://github.com/mininet/mininet /home/minisecbgpuser/mininet',
                    'cd /home/minisecbgpuser/mininet; git checkout -b 2.2.1rc1 2.2.1rc1; cd util/; ./install.sh']
                for command in commands:
                    service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                        ssh.ssh(self.node_ip_address, 'minisecbgpuser', self.password, command)
                    if service_ssh == 1:
                        node_install.NodeInstall.status = service_ssh
                        node_install.NodeInstall.log = service_ssh_status[:250]
                        self.dbsession.flush()
                        return
                    else:
                        if command_status != 0:
                            node_install.NodeInstall.status = 1
                            node_install.NodeInstall.log = command_error_warning[:250]
                            self.dbsession.flush()
                            return
                node_install.NodeInstall.status = 0
                node_install.NodeInstall.log = ''

            else:

                node_install.NodeInstall.status = 1
                node_install.NodeInstall.log = 'Aborted'

            self.dbsession.flush()
        except Exception as error:
            self.dbsession.rollback()
            print('Database error for Mininet installation on node: %s - %s' % (self.node_ip_address, error))

    def install_containernet(self):
        print('\nInstalling Containernet ...')
        try:
            node_install = self.dbsession.query(models.Node, models.NodeInstall, models.Install). \
                filter(models.Node.node == self.node_ip_address). \
                filter(models.Node.id == models.NodeInstall.id_node). \
                filter(models.NodeInstall.id_install == models.Install.id). \
                filter(models.Install.install == 'containernet').first()

            if node_install_status(self.dbsession, self.node_ip_address):

                commands = ['grep "localhost ansible_connection=local" /etc/ansible/hosts >/dev/null; '
                            'if [ $? -ne 0 ]; then echo "localhost ansible_connection=local" | '
                            'sudo tee -a /etc/ansible/hosts; fi',
                            'sudo rm -rf /home/minisecbgpuser/openflow &> /dev/null',
                            'git clone https://github.com/containernet/containernet /home/minisecbgpuser/containernet',
                            'cd /home/minisecbgpuser/containernet/ansible; '
                            'sed -i "s/update_cache: yes/update_cache: false/g" install.yml; '
                            'sudo ansible-playbook -i "localhost," -c local install.yml',
                            'cd /home/minisecbgpuser/containernet/; sudo python3 setup.py install',
                            'sudo pip uninstall backports.ssl-match-hostname -y',
                            'sudo apt-get install python-backports.ssl-match-hostname -y']
                for command in commands:
                    service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                        ssh.ssh(self.node_ip_address, 'minisecbgpuser', self.password, command)
                    if service_ssh == 1:
                        node_install.NodeInstall.status = service_ssh
                        print(service_ssh)
                        node_install.NodeInstall.log = service_ssh_status[:250]
                        print(service_ssh_status)
                        self.dbsession.flush()
                        return
                    else:
                        if command_status != 0:
                            node_install.NodeInstall.status = 1
                            node_install.NodeInstall.log = command_error_warning[:250]
                            print(command_error_warning)
                            self.dbsession.flush()
                            return
                node_install.NodeInstall.status = 0
                node_install.NodeInstall.log = ''

            else:

                node_install.NodeInstall.status = 1
                node_install.NodeInstall.log = 'Aborted'

            self.dbsession.flush()
        except Exception as error:
            self.dbsession.rollback()
            print('Database error for Containernet installation on node: %s - %s' % (self.node_ip_address, error))

    def install_metis(self):
        print('\nInstalling Metis ...')
        try:
            node_install = self.dbsession.query(models.Node, models.NodeInstall, models.Install). \
                filter(models.Node.node == self.node_ip_address). \
                filter(models.Node.id == models.NodeInstall.id_node). \
                filter(models.NodeInstall.id_install == models.Install.id). \
                filter(models.Install.install == 'metis').first()

            if node_install_status(self.dbsession, self.node_ip_address):
                if node_install.Node.master:    # install Metis only on master node
                    try:
                        command = 'sshpass -p "%s" scp -o StrictHostKeyChecking=no ./programs/metis-5.1.0.tar.gz ' \
                                  'minisecbgpuser@%s:/home/minisecbgpuser/' % (self.password, self.node_ip_address)
                        result = local_command.local_command(command)
                        if result[0] == 1:
                            node_install.NodeInstall.status = 1
                            node_install.NodeInstall.log = str(result[2].decode()[:250])
                            self.dbsession.flush()
                            return

                        commands = ['tar -xvzf /home/minisecbgpuser/metis-5.1.0.tar.gz -C /home/minisecbgpuser',
                                    'cd /home/minisecbgpuser/metis-5.1.0;'
                                    'sudo make config shared=1;'
                                    'sudo make;'
                                    'sudo make install;'
                                    'sudo ldconfig']
                        for command in commands:
                            service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                                ssh.ssh(self.node_ip_address, 'minisecbgpuser', self.password, command)
                            if service_ssh == 1:
                                node_install.NodeInstall.status = service_ssh
                                node_install.NodeInstall.log = service_ssh_status[:250]
                                self.dbsession.flush()
                                return
                            else:
                                if command_status != 0:
                                    node_install.NodeInstall.status = 1
                                    node_install.NodeInstall.log = command_error_warning[:250]
                                    self.dbsession.flush()
                                    return
                        node_install.NodeInstall.status = 0
                        node_install.NodeInstall.log = ''

                        self.dbsession.flush()
                    except Exception as error:
                        self.dbsession.rollback()
                        print('Database error for Metis installation on node: %s - %s' % (self.node_ip_address, error))
                else:
                    try:
                        node_install.NodeInstall.status = 0
                        node_install.NodeInstall.log = 'Metis installation is not necessary on Workers'

                        self.dbsession.flush()
                    except Exception as error:
                        self.dbsession.rollback()
                        print('Database error for Metis installation on node: %s - %s' % (self.node_ip_address, error))

            else:
                node_install.NodeInstall.status = 1
                node_install.NodeInstall.log = 'Aborted'

            self.dbsession.flush()
        except Exception as error:
            self.dbsession.rollback()
            print('Database error for Metis installation on node: %s - %s' % (self.node_ip_address, error))

    def install_maxinet(self):
        print('\nInstalling Maxinet ...')
        try:
            node_install = self.dbsession.query(models.Node, models.NodeInstall, models.Install). \
                filter(models.Node.node == self.node_ip_address). \
                filter(models.Node.id == models.NodeInstall.id_node). \
                filter(models.NodeInstall.id_install == models.Install.id). \
                filter(models.Install.install == 'maxinet').first()

            nodes = self.dbsession.query(models.Node).all()

            if node_install_status(self.dbsession, self.node_ip_address):

                # install MaxiNet on all cluster nodes
                commands = ['git clone https://github.com/MaxiNet/MaxiNet.git',
                            'cd /home/minisecbgpuser/MaxiNet;'
                            'git checkout v1.2;'
                            'sudo make install']
                for command in commands:
                    service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                        ssh.ssh(self.node_ip_address, 'minisecbgpuser', self.password, command)
                    if service_ssh == 1:
                        node_install.NodeInstall.status = service_ssh
                        node_install.NodeInstall.log = service_ssh_status[:250]
                        self.dbsession.flush()
                        return
                    else:
                        if command_status != 0:
                            node_install.NodeInstall.status = 1
                            node_install.NodeInstall.log = command_error_warning[:250]
                            self.dbsession.flush()
                            return

                # create MaxiNetFrontendServer and MaxiNetWorker services (on Master)
                if node_install.Node.master:
                    command = 'sudo -u minisecbgpuser bash -c \'' \
                              'echo "[Unit]\n' \
                              'Description=Pox Controller\n' \
                              'After=syslog.target network.target\n\n' \
                              '[Service]\n' \
                              'ExecStart=/home/minisecbgpuser/pox/pox.py forwarding.l2_learning\n\n' \
                              '[Install]\n' \
                              'WantedBy=default.target\n" | sudo tee /etc/systemd/system/pox.service; \'; ' \
                              'sudo -u minisecbgpuser bash -c \'' \
                              'echo "[Unit]\n' \
                              'Description=MaxiNetFrontendServer\n' \
                              'After=syslog.target network.target\n\n' \
                              '[Service]\n' \
                              'ExecStart=/usr/local/bin/MaxiNetFrontendServer\n\n' \
                              '[Install]\n' \
                              'WantedBy=default.target\n" | sudo tee /etc/systemd/system/MaxiNetFrontendServer.service; \'; ' \
                              'sudo -u minisecbgpuser bash -c \'' \
                              'echo "[Unit]\n' \
                              'Description=MaxiNetWorker\n' \
                              'After=syslog.target network.target MaxiNetFrontendServer.service\n\n' \
                              '[Service]\n' \
                              'ExecStart=/usr/local/bin/MaxiNetWorker\n\n' \
                              '[Install]\n' \
                              'WantedBy=default.target\n" | sudo tee /etc/systemd/system/MaxiNetWorker.service; \'; ' \
                              'sudo -u minisecbgpuser bash -c \'' \
                              'sudo systemctl daemon-reload; ' \
                              'sudo systemctl enable MaxiNetFrontendServer; \''
                    result = local_command.local_command(command)
                    if result[0] == 1:
                        node_install.NodeInstall.status = 1
                        node_install.NodeInstall.log = str(result[2].decode()[:250])
                        self.dbsession.flush()
                        return

                # configure MaxiNet.cfg
                for node in nodes:
                    if node.master:
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
                                  'threadpool = 256\n" | sudo tee /etc/MaxiNet.cfg; \'' % \
                                  (node.node, node.node)
                        result = local_command.local_command(command)
                        if result[0] == 1:
                            node_install.NodeInstall.status = 1
                            node_install.NodeInstall.log = str(result[2].decode()[:250])
                            self.dbsession.flush()
                            return

                    command = 'sudo -u minisecbgpuser bash -c \'' \
                              'echo "[%s]\n' \
                              'ip = %s\n' \
                              'share = 1\n" | sudo tee --append /etc/MaxiNet.cfg; \'' % \
                              (node.hostname, node.node)
                    result = local_command.local_command(command)
                    if result[0] == 1:
                        node_install.NodeInstall.status = 1
                        node_install.NodeInstall.log = str(result[2].decode()[:250])
                        self.dbsession.flush()
                        return

                # send MaxiNet.cfg and MaxiNetWorker.service files to all Workers cluster nodes
                for node in nodes:
                    if not node.master:
                        command = 'sudo -u minisecbgpuser bash -c \'' \
                                  'scp -o StrictHostKeyChecking=no /etc/MaxiNet.cfg minisecbgpuser@%s:/home/minisecbgpuser; ' \
                                  'scp -o StrictHostKeyChecking=no /etc/systemd/system/MaxiNetWorker.service minisecbgpuser@%s:/home/minisecbgpuser; ' \
                                  'ssh %s sudo mv /home/minisecbgpuser/MaxiNet.cfg /etc/MaxiNet.cfg; ' \
                                  'ssh %s sudo mv /home/minisecbgpuser/MaxiNetWorker.service /etc/systemd/system/MaxiNetWorker.service; \'' \
                                  % (node.node, node.node, node.node, node.node)
                        result = local_command.local_command(command)
                        if result[0] == 1:
                            node_install.NodeInstall.status = 1
                            node_install.NodeInstall.log = str(result[2].decode()[:250])
                            self.dbsession.flush()
                            return

                # configure /etc/hosts on all cluster nodes
                for node in nodes:
                    command = 'sudo -u minisecbgpuser bash -c \'' \
                              'ssh %s "sudo sed --i \\"/# MiniSecBGP cluster node/d\\" /etc/hosts | sudo tee --append /etc/hosts;"; \'' % node.node
                    result = local_command.local_command(command)
                    if result[0] == 1:
                        node_install.NodeInstall.status = 1
                        node_install.NodeInstall.log = str(result[2].decode()[:250])
                        self.dbsession.flush()
                        return

                    for host in nodes:
                        command = 'sudo -u minisecbgpuser bash -c \'' \
                                  'ssh %s "echo %s %s \# MiniSecBGP cluster node | sudo tee --append /etc/hosts"; \'' \
                                  % (node.node, host.node, host.hostname)
                        result = local_command.local_command(command)
                        if result[0] == 1:
                            node_install.NodeInstall.status = 1
                            node_install.NodeInstall.log = str(result[2].decode()[:250])
                            self.dbsession.flush()
                            return

                # restart MaxiNet services (MaxiNetFrontendServer and MaxiNetWorker) on all cluster nodes
                for node in nodes:
                    if node.master:
                        command = 'sudo -u minisecbgpuser bash -c \'' \
                                  'sudo systemctl restart MaxiNetFrontendServer; ' \
                                  'sleep 5; \''
                        result = local_command.local_command(command)
                        if result[0] == 1:
                            node_install.NodeInstall.status = 1
                            node_install.NodeInstall.log = str(result[2].decode()[:250])
                            self.dbsession.flush()
                            return

                    command = 'sudo -u minisecbgpuser bash -c \'' \
                              'ssh %s sudo systemctl daemon-reload; ' \
                              'ssh %s sudo systemctl enable pox; ' \
                              'ssh %s sudo systemctl restart pox; ' \
                              'ssh %s sudo systemctl enable MaxiNetWorker; ' \
                              'ssh %s sudo systemctl restart MaxiNetWorker; \'' % \
                              (node.node, node.node, node.node, node.node, node.node)
                    result = local_command.local_command(command)
                    if result[0] == 1:
                        node_install.NodeInstall.status = 1
                        node_install.NodeInstall.log = str(result[2].decode()[:250])
                        self.dbsession.flush()
                        return

                node_install.NodeInstall.status = 0
                node_install.NodeInstall.log = ''

            else:

                node_install.NodeInstall.status = 1
                node_install.NodeInstall.log = 'Aborted'

            self.dbsession.flush()
        except Exception as error:
            self.dbsession.rollback()
            print('Database error for MaxiNet installation on node: %s - %s' % (self.node_ip_address, error))

    def install_quagga(self):
        print('\nInstalling Quagga router ...')
        try:
            node_install = self.dbsession.query(models.Node, models.NodeInstall, models.Install). \
                filter(models.Node.node == self.node_ip_address). \
                filter(models.Node.id == models.NodeInstall.id_node). \
                filter(models.NodeInstall.id_install == models.Install.id). \
                filter(models.Install.install == 'quagga').first()

            if node_install_status(self.dbsession, self.node_ip_address):

                commands = ['sudo killall -9 -u quagga 2>/dev/null || exit 0',
                            'sudo userdel -r quagga 2>/dev/null || exit 0',
                            'sudo groupdel quaggavty 2>/dev/null || exit 0',
                            'sudo addgroup --system --gid 92 quagga',
                            'sudo addgroup --system --gid 85 quaggavty',
                            'sudo adduser --system --ingroup quagga --home /var/run/quagga/ --gecos "Quagga routing suite" --shell /bin/false quagga',
                            'sudo apt install libreadline-dev pkg-config libc-ares-dev gawk -y',
                            'rm -f /home/minisecbgpuser/quagga-1.2.4.tar.gz 2>/dev/null || exit 0',
                            'rm -f /home/minisecbgpuser/quagga-1.2.4.tar 2>/dev/null || exit 0',
                            'rm -rf /home/minisecbgpuser/quagga-1.2.4 2>/dev/null || exit 0']
                for command in commands:
                    service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                        ssh.ssh(self.node_ip_address, 'minisecbgpuser', self.password, command)

                    if service_ssh == 1:
                        node_install.NodeInstall.status = service_ssh
                        node_install.NodeInstall.log = service_ssh_status[:250]
                        self.dbsession.flush()
                        return
                    else:
                        if command_status != 0:
                            node_install.NodeInstall.status = 1
                            node_install.NodeInstall.log = command_error_warning[:250]
                            self.dbsession.flush()
                            return

                command = 'ssh-keygen -R %s; sshpass -p "%s" scp -o StrictHostKeyChecking=no ./programs/quagga-1.2.4.tar.gz ' \
                          'minisecbgpuser@%s:/home/minisecbgpuser/' % (self.node_ip_address, self.password, self.node_ip_address)
                result = local_command.local_command(command)
                if result[0] == 1:
                    node_install.NodeInstall.status = 1
                    node_install.NodeInstall.log = str(result[2].decode()[:250])
                    self.dbsession.flush()
                    return

                commands = ['tar -xvzf /home/minisecbgpuser/quagga-1.2.4.tar.gz -C /home/minisecbgpuser;'
                            'cd /home/minisecbgpuser/quagga-1.2.4/;'
                            './configure --prefix=/home/minisecbgpuser/quagga-1.2.4 --localstatedir=/var/run/quagga/ --enable-vtysh;'
                            'cd /home/minisecbgpuser/quagga-1.2.4/; make;'
                            'cd /home/minisecbgpuser/quagga-1.2.4/; make install']
                for command in commands:
                    service_ssh, service_ssh_status, command_output, command_error_warning, command_status = \
                        ssh.ssh(self.node_ip_address, 'minisecbgpuser', self.password, command)

                    if service_ssh == 1:
                        node_install.NodeInstall.status = service_ssh
                        node_install.NodeInstall.log = service_ssh_status[:250]
                        self.dbsession.flush()
                        return
                    else:
                        if command_status != 0:
                            node_install.NodeInstall.status = 1
                            node_install.NodeInstall.log = command_error_warning[:250]
                            self.dbsession.flush()
                            return

                node_install.NodeInstall.status = 0
                node_install.NodeInstall.log = ''

            else:

                node_install.NodeInstall.status = 1
                node_install.NodeInstall.log = 'Aborted'

            self.dbsession.flush()
        except Exception as error:
            self.dbsession.rollback()
            print('Database error for Quagga installation on node: %s - %s' % (self.node_ip_address, error))


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
    except getopt.GetoptError as error:
        print('\n'
              'Usage: MiniSecBGP_node_install [options]\n'
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
                  'Usage: MiniSecBGP_node_install [options]\n'
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
                ccn.install_linux_prerequisites()
            with env['request'].tm:
                dbsession = env['request'].dbsession
                ccn = ConfigClusterNode(dbsession, node_ip_address, username, password)
                ccn.install_mininet()
            with env['request'].tm:
                dbsession = env['request'].dbsession
                ccn = ConfigClusterNode(dbsession, node_ip_address, username, password)
                ccn.install_containernet()
            with env['request'].tm:
                dbsession = env['request'].dbsession
                ccn = ConfigClusterNode(dbsession, node_ip_address, username, password)
                ccn.install_metis()
            with env['request'].tm:
                dbsession = env['request'].dbsession
                ccn = ConfigClusterNode(dbsession, node_ip_address, username, password)
                ccn.install_maxinet()
            with env['request'].tm:
                dbsession = env['request'].dbsession
                ccn = ConfigClusterNode(dbsession, node_ip_address, username, password)
                ccn.install_quagga()
            print('that\'s all')
        except OperationalError:
            print('Database error')
    else:
        print('\n'
              'Usage: MiniSecBGP_node_install [options]\n'
              '\n'
              'options (with examples):\n'
              '\n'
              '-h                                               this help\n'
              '\n'
              '--config-file=minisecbgp.ini                     pyramid config filename [.ini]\n'
              '--node-ip-address=[192.168.0.1|3232239375]       cluster node IP address\n'
              '--username=ubuntu                                the username to use to configure the cluster node\n'
              '--password=ubuntu                                the user password to access the cluster node\n')
