import argparse
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from minisecbgp.scripts.services import ssh, local_command
from minisecbgp import models


def create_minisecbgpuser(dbsession, argv):
    # argv[3] --> argv[0] = hostname
    # argv[4] --> argv[1] = username
    # argv[5] --> argv[2] = password
    command = 'echo %s | sudo -S apt install whois -y;' \
              'sudo userdel -r minisecbgpuser 2> /dev/null;' \
              'sudo useradd -m -p $(mkpasswd -m sha-512 -S saltsalt -s <<< %s) -s /bin/bash minisecbgpuser;' \
              'echo "minisecbgpuser    ALL=NOPASSWD: ALL" | sudo tee --append /etc/sudoers;' \
              'echo "%s    ALL=(minisecbgpuser) NOPASSWD: ALL" | sudo tee --append /etc/sudoers' \
              % (argv[2], argv[2], argv[1])
    node = dbsession.query(models.Node).filter(models.Node.node == argv[0]).first()
    try:
        discard, discard, node.conf_user, node.conf_user_status = ssh.ssh(argv[0], argv[1], argv[2], command)
        dbsession.flush()
    except Exception as error:
        print('Database error for "minisecbgpuser" creation on node: %s - %s' % node.node, error)


def configure_ssh(dbsession, argv):
    # argv[3] --> argv[0] = hostname
    # argv[5] --> argv[2] = password
    command = 'ssh-keygen -t rsa -N "" -f /home/minisecbgpuser/.ssh/id_rsa;' \
              'cat /home/minisecbgpuser/.ssh/id_rsa.pub | ' \
              'tee --append /home/minisecbgpuser/.ssh/authorized_keys;' \
              'chmod 755 /home/minisecbgpuser/.ssh/authorized_keys;' \
              'echo -e "Host *\nStrictHostKeyChecking no" | tee --append /home/minisecbgpuser/.ssh/config;' \
              'chmod 400 /home/minisecbgpuser/.ssh/config'
    node = dbsession.query(models.Node).filter(models.Node.node == argv[0]).first()
    try:
        ssh.ssh(argv[0], 'minisecbgpuser', argv[2], command)
        conf_ssh_status = ''
        # update of the authorized_keys file to allow remote connections via ssh of the user "minisecbgpuser" without
        # the need for a password
        if node.master == 0:
            command = 'sudo -u minisecbgpuser sshpass -p "%s" scp -o StrictHostKeyChecking=no ' \
                      'minisecbgpuser@%s:/home/minisecbgpuser/.ssh/authorized_keys ' \
                      '/home/minisecbgpuser/.ssh/authorized_keys.tmp' % (argv[2], argv[0])
            result = local_command.execute_command(command)
            conf_ssh_status = str(result[2].decode()[:55])

            command = 'sudo -u minisecbgpuser cat /home/minisecbgpuser/.ssh/authorized_keys.tmp |' \
                      'sudo -u minisecbgpuser tee --append /home/minisecbgpuser/.ssh/authorized_keys'
            result = local_command.execute_command(command)
            conf_ssh_status = conf_ssh_status + str(result[2].decode()[:55])

            command = 'sudo -u minisecbgpuser sshpass -p "%s" scp -o StrictHostKeyChecking=no ' \
                      '/home/minisecbgpuser/.ssh/authorized_keys minisecbgpuser@%s:/home/minisecbgpuser/.ssh/' \
                      % (argv[2], argv[0])
            result = local_command.execute_command(command)
            conf_ssh_status = conf_ssh_status + str(result[2].decode()[:55])

        # testing ssh connection
        command = 'sudo -u minisecbgpuser ssh %s exit' % argv[0]
        result = local_command.execute_command(command)
        conf_ssh_status = conf_ssh_status + str(result[2].decode()[:55])

        node.conf_ssh = result[0]
        node.conf_ssh_status = conf_ssh_status

        dbsession.flush()
    except Exception as error:
        print('Database error for ssh configuration on node: %s - %s' % (node.node, error))


def install_remote_prerequisites(dbsession, argv):
    # argv[3] --> argv[0] = hostname
    # argv[5] --> argv[2] = password
    command = 'sudo apt install python3-pip cmake -y;' \
              'pip3 install --upgrade --force-reinstall -U Pyro4'
    node = dbsession.query(models.Node).filter(models.Node.node == argv[0]).first()
    try:
        discard, discard, node.install_remote_prerequisites, node.install_remote_prerequisites_status = \
            ssh.ssh(argv[0], 'minisecbgpuser', argv[2], command)
        dbsession.flush()
    except Exception as error:
        print('Database error for remote prerequisites installation on node: %s - %s' % node.node, error)


def install_mininet(dbsession, argv):
    # argv[3] --> argv[0] = hostname
    # argv[5] --> argv[2] = password
    command = 'git clone git://github.com/mininet/mininet /home/minisecbgpuser/mininet;' \
              'cd /home/minisecbgpuser/mininet;' \
              'git checkout -b 2.3.0d4 2.3.0d4;' \
              'sed -i -- "s/iproute /iproute2 /g" /home/minisecbgpuser/mininet/util/install.sh;' \
              'sudo /home/minisecbgpuser/mininet/util/install.sh -a'
    node = dbsession.query(models.Node).filter(models.Node.node == argv[0]).first()
    try:
        discard, discard, node.install_mininet, node.install_mininet_status = ssh.ssh(argv[0], 'minisecbgpuser',
                                                                                      argv[2], command)
        dbsession.flush()
    except Exception as error:
        print('Database error for Mininet installation on node: %s - %s' % node.node, error)


def install_metis(dbsession, argv):
    # argv[3] --> argv[0] = hostname
    install_metis_status = ''
    node = dbsession.query(models.Node).filter(models.Node.node == argv[0]).first()
    try:
        if node.master == 1:
            command = 'sudo -u minisecbgpuser cp ./metis/metis-5.1.0.tar.gz /home/minisecbgpuser/metis-5.1.0.tar.gz;' \
                      'sudo -u minisecbgpuser tar -xvzf /home/minisecbgpuser/metis-5.1.0.tar.gz -C ' \
                      '/home/minisecbgpuser;' \
                      'cd /home/minisecbgpuser/metis-5.1.0;' \
                      'sudo make config shared=1;' \
                      'sudo make;' \
                      'sudo make install;' \
                      'sudo ldconfig'
            result = local_command.execute_command(command)
            install_metis_status = install_metis_status + str(result[2].decode()[:55])

            node.install_metis = result[0]
            node.install_metis_status = install_metis_status

        else:
            node.install_metis = '0'
            node.install_metis_status = 'Metis does not need to be installed on workers'

        dbsession.flush()
    except Exception as error:
        print('Database error for Metis installation on node: %s - %s' % (node.node, error))


def install_maxinet(dbsession, argv):
    # argv[3] --> argv[0] = hostname
    # argv[5] --> argv[2] = password
    command = 'git clone git://github.com/MaxiNet/MaxiNet.git;' \
              'cd /home/minisecbgpuser/MaxiNet;' \
              'git checkout v1.2;' \
              'sudo make install;' \
              'sudo cp /home/minisecbgpuser/MaxiNet/share/MaxiNet-cfg-sample /etc/MaxiNet.cfg;' \
              'sudo sed -i -- "s/password = HalloWelt/password = MiniSecBGPUser/g" /etc/MaxiNet.cfg'
    node = dbsession.query(models.Node).filter(models.Node.node == argv[0]).first()
    try:
        discard, discard, node.install_maxinet, node.install_maxinet_status = ssh.ssh(argv[0], 'minisecbgpuser',
                                                                                      argv[2], command)
        dbsession.flush()
    except Exception as error:
        print('Database error for MaxiNet installation on node: %s - %s' % node.node, error)


def install_containernet(dbsession, argv):
    # argv[3] --> argv[0] = hostname
    # argv[5] --> argv[2] = password
    pass


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(argv[1:])


def main(argv=sys.argv):
    # argv[0] = python program
    # argv[1] = configuration file .ini
    # argv[2] = 0 = creating node | 1 = job scheduled
    # argv[3] --> argv[0] = hostname
    # argv[4] --> argv[1] = username
    # argv[5] --> argv[2] = password

    args = parse_args(argv[0:2])
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)
    try:
        with env['request'].tm:
            dbsession = env['request'].dbsession
            if argv[2] == '0':
                create_minisecbgpuser(dbsession, argv[3:])
                configure_ssh(dbsession, argv[3:])
                install_remote_prerequisites(dbsession, argv[3:])
                install_mininet(dbsession, argv[3:])
                install_metis(dbsession, argv[3:])
                install_maxinet(dbsession, argv[3:])
                install_containernet(dbsession, argv[3:])
    except OperationalError:
        print('Database error')
